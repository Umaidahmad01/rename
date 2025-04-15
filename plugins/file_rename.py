import os
import re
import time
import shutil
import asyncio
import logging
from datetime import datetime
from PIL import Image
from pyrogram import Client, filters
from pyrogram.errors import FloodWait, MessageNotModified, ChatAdminRequired
from pyrogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from hachoir.metadata import extractMetadata
from hachoir.parser import createParser
from plugins.antinsfw import check_anti_nsfw
from helper.utils import progress_for_pyrogram, humanbytes, send_log
from helper.database import codeflixbots
from config import Config, Txt

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

renaming_operations = {}
user_tasks = {}

SEASON_EPISODE_PATTERNS = [
    (re.compile(r'S(\d+)(?:E|EP)(\d+)', re.IGNORECASE), ('season', 'episode')),
    (re.compile(r'S(\d+)[\s-]*(?:E|EP)(\d+)', re.IGNORECASE), ('season', 'episode')),
    (re.compile(r'Season\s*(\d+)\s*Episode\s*(\d+)', re.IGNORECASE), ('season', 'episode')),
    (re.compile(r'\[S(\d+)\]\[E(\d+)\]', re.IGNORECASE), ('season', 'episode')),
    (re.compile(r'S(\d+)[^\d]*(\d+)', re.IGNORECASE), ('season', 'episode')),
    (re.compile(r'(?:E|EP|Episode)\s*(\d+)', re.IGNORECASE), (None, 'episode')),
    (re.compile(r'\b(\d+)\b', re.IGNORECASE), (None, 'episode'))
]

QUALITY_PATTERNS = [
    (re.compile(r'\b(\d{3,4}[pi])\b', re.IGNORECASE), lambda m: m.group(1)),
    (re.compile(r'\b(4k|2160p)\b', re.IGNORECASE), lambda m: "4k"),
    (re.compile(r'\b(2k|1440p)\b', re.IGNORECASE), lambda m: "2k"),
    (re.compile(r'\b(HDRip|HDTV)\b', re.IGNORECASE), lambda m: m.group(1)),
    (re.compile(r'\b(4kX264|4kx265)\b', re.IGNORECASE), lambda m: m.group(1)),
    (re.compile(r'\[(\d{3,4}[pi])\]', re.IGNORECASE), lambda m: m.group(1))
]

def sanitize_filename(filename):
    if not filename:
        return "unnamed_file"
    clean = re.sub(r'[^a-zA-Z0-9\s\-\[\]\(\)\.]', '_', filename)
    clean = re.sub(r'\s+', ' ', clean).strip('_ ')
    clean = clean.replace('..', '.').replace('__', '_')
    return clean[:100]

def extract_season_episode(input_text, rename_mode):
    if not input_text:
        logger.warning(f"No input text for rename_mode {rename_mode}")
        return None, None
    input_text = str(input_text)  # Ensure string to avoid NoneType
    for pattern, (season_group, episode_group) in SEASON_EPISODE_PATTERNS:
        match = pattern.search(input_text)
        if match:
            season = match.group(1) if season_group else None
            episode = match.group(2) if episode_group and len(match.groups()) >= 2 else match.group(1)
            logger.info(f"Extracted season: {season}, episode: {episode} from {rename_mode}")
            return season, episode
    logger.warning(f"No season/episode matched for {rename_mode}: {input_text}")
    return None, None

def extract_quality(filename):
    if not filename:
        return "Unknown"
    for pattern, extractor in QUALITY_PATTERNS:
        match = pattern.search(filename)
        if match:
            quality = extractor(match)
            logger.info(f"Extracted quality: {quality}")
            return quality
    logger.warning(f"No quality matched for {filename}")
    return "Unknown"

async def cleanup_files(*paths):
    for path in paths:
        try:
            if path and os.path.exists(path):
                os.remove(path)
        except Exception as e:
            logger.error(f"Error removing {path}: {e}")

async def process_thumbnail(thumb_path):
    if not thumb_path or not os.path.exists(thumb_path):
        return None
    try:
        with Image.open(thumb_path) as img:
            img = img.convert("RGB").resize((320, 320))
            img.save(thumb_path, "JPEG")
        return thumb_path
    except Exception as e:
        logger.error(f"Thumbnail processing failed: {e}")
        await cleanup_files(thumb_path)
        return None

async def add_metadata(input_path, output_path, user_id):
    ffmpeg = shutil.which('ffmpeg')
    if not ffmpeg:
        logger.error("FFmpeg not found")
        raise RuntimeError("FFmpeg not found")
    
    try:
        metadata = {
            'title': await codeflixbots.get_title(user_id),
            'artist': await codeflixbots.get_artist(user_id),
            'author': await codeflixbots.get_author(user_id),
            'video_title': await codeflixbots.get_video(user_id),
            'audio_title': await codeflixbots.get_audio(user_id),
            'subtitle': await codeflixbots.get_subtitle(user_id)
        }
        cmd = [ffmpeg, '-i', input_path, '-map', '0', '-c', 'copy', '-loglevel', 'error']
        has_metadata = False
        for key, value in metadata.items():
            if value:
                has_metadata = True
                if key == 'video_title':
                    cmd.extend(['-metadata:s:v', f'title={value}'])
                elif key == 'audio_title':
                    cmd.extend(['-metadata:s:a', f'title={value}'])
                elif key == 'subtitle':
                    cmd.extend(['-metadata:s:s', f'title={value}'])
                else:
                    cmd.extend(['-metadata', f'{key}={value}'])
        if not has_metadata:
            logger.info(f"No valid metadata for user {user_id}, skipping")
            return False
        cmd.append(output_path)
        
        logger.info(f"Running FFmpeg: {' '.join(cmd)}")
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            logger.error(f"FFmpeg error (return code {process.returncode}): {stderr.decode()}")
            raise RuntimeError(f"FFmpeg failed: {stderr.decode()}")
        if not os.path.exists(output_path):
            logger.error(f"Output file {output_path} not created")
            raise RuntimeError(f"Output file {output_path} not created")
        logger.info(f"Metadata added to {output_path}")
        return True
    except Exception as e:
        logger.error(f"Metadata processing failed: {e}")
        raise

async def process_file(client, message):
    user_id = message.from_user.id
    format_template = await codeflixbots.get_format_template(user_id)
    rename_mode = await codeflixbots.get_user_choice(user_id)

    if user_id not in user_tasks:
        user_tasks[user_id] = []

    download_path = None
    metadata_path = None
    thumb_path = None

    if format_template:
        if message.document:
            file_id = message.document.file_id
            file_name = message.document.file_name or "document"
            file_size = message.document.file_size
            media_type = "document"
        elif message.video:
            file_id = message.video.file_id
            file_name = message.video.file_name or "video"
            file_size = message.video.file_size
            media_type = "video"
        elif message.audio:
            file_id = message.audio.file_id
            file_name = message.audio.file_name or "audio"
            file_size = message.audio.file_size
            media_type = "audio"
        else:
            return await message.reply_text("Unsupported file type")

        if await check_anti_nsfw(file_name, message):
            return await message.reply_text("NSFW content detected")

        if file_id in renaming_operations:
            if (datetime.now() - renaming_operations[file_id]).seconds < 10:
                return
        renaming_operations[file_id] = datetime.now()

        try:
            season, episode = extract_season_episode(file_name, "filename")
            quality = extract_quality(file_name)
            
            replacements = {
                '{season}': season or 'XX',
                '{episode}': episode or 'XX',
                '{quality}': quality,
                'Season': season or 'XX',
                'Episode': episode or 'XX',
                'QUALITY': quality
            }
            
            new_template = format_template
            for placeholder, value in replacements.items():
                new_template = new_template.replace(placeholder, str(value))
            
            if not new_template.strip():
                new_template = f"file_{user_id}"
            
            ext = os.path.splitext(file_name)[1] or ('.mp4' if media_type == "video" else '.mp3')
            new_filename = sanitize_filename(f"{new_template}{ext}")
            download_path = f"downloads/{new_filename}"
            metadata_path = f"metadata/{new_filename}"
            
            os.makedirs(os.path.dirname(download_path), exist_ok=True)
            os.makedirs(os.path.dirname(metadata_path), exist_ok=True)

            msg = await message.reply_text("**Downloading...**")
            download_task = asyncio.create_task(client.download_media(
                message,
                file_name=download_path,
                progress=progress_for_pyrogram,
                progress_args=("Downloading...", msg, time.time())
            ))
            user_tasks[user_id].append(download_task)
            try:
                file_path = await download_task
            except asyncio.CancelledError:
                logger.info(f"Download cancelled for user {user_id}")
                await msg.edit("Task cancelled.")
                return
            except ChatAdminRequired:
                logger.error(f"ChatAdminRequired during download")
                await msg.edit("Error: Bot lacks admin rights.")
                await send_log(client, message.from_user, f"Download failed: Bot lacks admin rights")
                return
            except Exception as e:
                logger.error(f"Download failed for user {user_id}: {e}")
                await msg.edit(f"Download failed: {e}")
                await send_log(client, message.from_user, f"Download failed: {str(e)}")
                return

            metadata_enabled = await codeflixbots.get_metadata(user_id)
            if metadata_enabled:
                await msg.edit("**Processing metadata...**")
                try:
                    if await add_metadata(file_path, metadata_path, user_id):
                        if os.path.exists(metadata_path):
                            file_path = metadata_path
                        else:
                            logger.warning(f"Metadata file {metadata_path} not found, using {file_path}")
                    else:
                        logger.info(f"No metadata applied for user {user_id}")
                except Exception as e:
                    logger.error(f"Metadata processing failed for user {user_id}: {e}")
                    await msg.edit(f"Metadata processing failed, proceeding without metadata: {e}")
                    await send_log(client, message.from_user, f"Metadata processing failed: {str(e)}")
            else:
                logger.info(f"Metadata disabled for user {user_id}")

            await msg.edit("**Preparing upload...**")
            caption = await codeflixbots.get_caption(user_id) or f"**{new_filename}**"
            thumb = await codeflixbots.get_thumbnail(user_id)
            thumb_path = None

            if thumb:
                thumb_path = await client.download_media(thumb)
            elif media_type == "video" and message.video and message.video.thumbs:
                thumb_path = await client.download_media(message.video.thumbs[0].file_id)
            
            thumb_path = await process_thumbnail(thumb_path)

            await msg.edit("**Uploading...**")
            if not os.path.exists(file_path):
                logger.error(f"Upload failed: File {file_path} does not exist")
                await msg.edit(f"Upload failed: File {new_filename} not found")
                await send_log(client, message.from_user, f"Upload failed: File {file_path} missing")
                return
            
            upload_task = asyncio.create_task(client.send_document(
                chat_id=message.chat.id,
                document=file_path,
                caption=caption,
                thumb=thumb_path,
                progress=progress_for_pyrogram,
                progress_args=("Uploading...", msg, time.time())
            ))
            user_tasks[user_id].append(upload_task)
            try:
                await upload_task
                await msg.delete()
            except asyncio.CancelledError:
                logger.info(f"Upload cancelled for user {user_id}")
                await msg.edit("Task cancelled.")
                return
            except ChatAdminRequired:
                logger.error(f"ChatAdminRequired during upload")
                await msg.edit("Error: Bot lacks admin rights.")
                await send_log(client, message.from_user, f"Upload failed: Bot lacks admin rights")
                return
            except Exception as e:
                logger.error(f"Upload failed for user {user_id}: {e}")
                await msg.edit(f"Upload failed: {e}")
                await send_log(client, message.from_user, f"Upload failed: {str(e)}")
                return

            # Send to dump channel *after* user upload
            try:
                if os.path.exists(file_path):
                    await msg.edit("**Sending to dump channel...**")
                    await codeflixbots.send_to_dump_channel(client, file_path, f"Renamed: {new_filename}")
                else:
                    logger.error(f"File {file_path} does not exist for dump channel")
                    await send_log(client, message.from_user, f"Dump channel failed: File {file_path} missing")
            except Exception as e:
                logger.error(f"Dump channel send failed for user {user_id}: {e}")
                await send_log(client, message.from_user, f"Dump channel send failed: {str(e)}")

        except Exception as e:
            logger.error(f"Processing error for user {user_id}: {e}")
            await message.reply_text(f"Error: {str(e)}")
            await send_log(client, message.from_user, f"Processing error: {str(e)}")
        finally:
            await cleanup_files(download_path, metadata_path, thumb_path)
            renaming_operations.pop(file_id, None)
            user_tasks[user_id] = [t for t in user_tasks[user_id] if not t.done()]

    elif rename_mode:
        if not message.document:
            await message.reply_text("Please send a document for extraction mode.")
            return

        file = message.document
        file_id = file.file_id
        new_name = ""
        input_text = file.file_name if rename_mode == "filename" else (message.caption or "")

        try:
            logger.info(f"Processing file for user {user_id} with rename_mode {rename_mode}")
            season, episode = extract_season_episode(input_text, rename_mode)
            if season or episode:
                base_name = f"S{season or 'XX'}E{episode or 'XX'}"
            else:
                base_name = input_text or f"unnamed_{user_id}"

            extension = file.file_name.split('.')[-1] if '.' in file.file_name else 'bin'
            new_name = sanitize_filename(f"{base_name}.{extension}")
            await message.reply_text(f"Renaming using {rename_mode}: {new_name}")

            logger.info(f"Downloading {file.file_name} for user {user_id}")
            download_task = asyncio.create_task(client.download_media(file))
            user_tasks[user_id].append(download_task)
            try:
                file_path = await download_task
            except asyncio.CancelledError:
                logger.info(f"Download cancelled for user {user_id}")
                await message.reply_text("Task cancelled.")
                return
            except ChatAdminRequired:
                logger.error(f"ChatAdminRequired during download")
                await message.reply_text("Error: Bot lacks admin rights.")
                await send_log(client, message.from_user, f"Download failed: Bot lacks admin rights")
                return
            except Exception as e:
                logger.error(f"Download error for user {user_id}: {e}")
                await message.reply_text(f"Error downloading: {e}")
                await send_log(client, message.from_user, f"Download error: {str(e)}")
                return

            renamed_file_path = f"downloads/{new_name}"
            logger.info(f"Renaming to {renamed_file_path}")
            os.makedirs("downloads", exist_ok=True)
            os.rename(file_path, renamed_file_path)

            logger.info(f"Uploading {new_name} for user {user_id}")
            if not os.path.exists(renamed_file_path):
                logger.error(f"Upload failed: File {renamed_file_path} does not exist")
                await message.reply_text(f"Upload failed: File {new_name} not found")
                await send_log(client, message.from_user, f"Upload failed: File {renamed_file_path} missing")
                return
            
            upload_task = asyncio.create_task(client.send_document(
                chat_id=message.chat.id,
                document=renamed_file_path,
                file_name=new_name
            ))
            user_tasks[user_id].append(upload_task)
            try:
                await upload_task
            except asyncio.CancelledError:
                logger.info(f"Upload cancelled for user {user_id}")
                await message.reply_text("Task cancelled.")
                return
            except ChatAdminRequired:
                logger.error(f"ChatAdminRequired during upload")
                await message.reply_text("Error: Bot lacks admin rights.")
                await send_log(client, message.from_user, f"Upload failed: Bot lacks admin rights")
                return
            except Exception as e:
                logger.error(f"Upload error for user {user_id}: {e}")
                await message.reply_text(f"Error uploading: {e}")
                await send_log(client, message.from_user, f"Upload error: {str(e)}")
                return

            # Send to dump channel *after* user upload
            try:
                if os.path.exists(renamed_file_path):
                    logger.info(f"Sending {new_name} to dump channel for user {user_id}")
                    await codeflixbots.send_to_dump_channel(client, renamed_file_path, f"Renamed: {new_name}")
                else:
                    logger.error(f"File {renamed_file_path} does not exist for dump channel")
                    await send_log(client, message.from_user, f"Dump channel failed: File {renamed_file_path} missing")
            except Exception as e:
                logger.error(f"Dump channel send failed for user {user_id}: {e}")
                await send_log(client, message.from_user, f"Dump channel send failed: {str(e)}")

            os.remove(renamed_file_path)
            await codeflixbots.delete_user_choice(user_id)
            logger.info(f"File processed, choice deleted for user {user_id}")

        except ChatAdminRequired:
            logger.error(f"ChatAdminRequired in file processing")
            await message.reply_text("Error: Bot lacks admin rights.")
            await send_log(client, message.from_user, f"Processing error: Bot lacks admin rights")
        except Exception as e:
            logger.error(f"Processing error for user {user_id}: {e}")
            if "ffmpeg" in str(e).lower():
                await message.reply_text("Error: FFmpeg not installed. Contact admin.")
                await send_log(client, message.from_user, f"FFmpeg error: {str(e)}")
            else:
                await message.reply_text(f"Error processing file: {e}")
                await send_log(client, message.from_user, f"Processing error: {str(e)}")
        finally:
            user_tasks[user_id] = [t for t in user_tasks[user_id] if not t.done()]
    else:
        await message.reply_text("Use /extraction to set a rename mode.")

@Client.on_message(filters.command("extraction") & filters.private)
async def extraction_command(client: Client, message: Message) -> None:
    try:
        keyboard = [
            [InlineKeyboardButton("Filename", callback_data="filename")],
            [InlineKeyboardButton("Filecaption", callback_data="filecaption")]
        ]
        await message.reply_text(
            "Choose how to rename the file:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        logger.info(f"Sent extraction options to user {message.from_user.id}")
        await send_log(client, message.from_user, "Started /extraction command")
    except ChatAdminRequired:
        logger.error(f"ChatAdminRequired in extraction_command")
        await message.reply_text("Error: Bot lacks admin rights.")
        await send_log(client, message.from_user, "Extraction command failed: Bot lacks admin rights")
    except Exception as e:
        logger.error(f"Error in extraction_command: {e}")
        await message.reply_text("Error: Failed to send options.")
        await send_log(client, message.from_user, f"Extraction command error: {str(e)}")

@Client.on_callback_query()
async def cb_handler(client, query: CallbackQuery):
    data = query.data
    user_id = query.from_user.id

    logger.info(f"Callback data received: {data}")

    # Handle /extraction callbacks
    if data in ["filename", "filecaption"]:
        try:
            choice = data
            updated_keyboard = [
                [InlineKeyboardButton("Filename ✅" if choice == "filename" else "Filename", callback_data="filename")],
                [InlineKeyboardButton("Filecaption ✅" if choice == "filecaption" else "Filecaption", callback_data="filecaption")]
            ]

            try:
                await query.message.edit_reply_markup(InlineKeyboardMarkup(updated_keyboard))
                logger.info(f"Updated keyboard for user {user_id}")
            except MessageNotModified:
                logger.debug(f"Keyboard unchanged for user {user_id}")
            except ChatAdminRequired:
                logger.error(f"ChatAdminRequired for keyboard update")
                await query.message.reply_text("Error: Bot lacks admin rights.")
                await query.answer("Bot needs admin rights!", show_alert=True)
                await send_log(client, query.from_user, "Keyboard update failed: Bot lacks admin rights")
                return
            except Exception as e:
                logger.error(f"Keyboard update failed for user {user_id}: {e}")
                await query.message.reply_text("Error: Couldn't update buttons.")
                await send_log(client, query.from_user, f"Keyboard update error: {str(e)}")
                return

            success = await codeflixbots.set_user_choice(user_id, choice)
            if not success:
                logger.error(f"Failed to save choice '{choice}' for user {user_id}")
                await query.message.reply_text("Error: Couldn't save your choice.")
                await query.answer("Database error!", show_alert=True)
                await send_log(client, query.from_user, f"Failed to save choice: {choice}")
                return

            await query.message.reply_text(
                f"Please send the file to rename using its {choice}."
            )
            await query.answer("Option selected!")
            await send_log(client, query.from_user, f"Selected rename mode: {choice}")
        except ChatAdminRequired:
            logger.error(f"ChatAdminRequired in callback")
            await query.message.reply_text("Error: Bot lacks admin rights.")
            await query.answer("Bot needs admin rights!", show_alert=True)
            await send_log(client, query.from_user, "Callback failed: Bot lacks admin rights")
        except Exception as e:
            logger.error(f"Callback error for user {user_id}: {e}")
            await query.message.reply_text("Error: Something went wrong.")
            await query.answer("Error occurred!", show_alert=True)
            await send_log(client, query.from_user, f"Callback error: {str(e)}")

    # Handle /start and /help callbacks
    elif data == "home":
        await query.message.edit_text(
            text=Txt.START_TXT.format(query.from_user.mention),
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("• ᴍʏ ᴀʟʟ ᴄᴏᴍᴍᴀɴᴅs •", callback_data='help')],
                [InlineKeyboardButton('• ᴜᴘᴅᴀᴛᴇs', url='https://t.me/FILE_SHARINGBOTS'), InlineKeyboardButton('sᴜᴘᴘᴏʀᴛ •', url='https://t.me/CodeflixSupport')],
                [InlineKeyboardButton('• ᴀʙᴏᴜᴛ', callback_data='about'), InlineKeyboardButton('sᴏᴜʀᴄᴇ •', callback_data='source')]
            ])
        )
    elif data == "caption":
        await query.message.edit_text(
            text=Txt.CAPTION_TXT,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("• sᴜᴘᴘᴏʀᴛ", url='https://t.me/ahss_help_zone'), InlineKeyboardButton("ʙᴀᴄᴋ •", callback_data="help")]
            ])
        )
    elif data == "help":
        await query.message.edit_text(
            text=Txt.HELP_TXT.format((await client.get_me()).mention),
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("• ᴀᴜᴛᴏ ʀᴇɴᴀᴍᴇ ғᴏʀᴍᴀᴛ •", callback_data='file_names')],
                [InlineKeyboardButton('• ᴛʜᴜᴍʙɴᴀɪʟ', callback_data='thumbnail'), InlineKeyboardButton('ᴄᴀᴘᴛɪᴏɴ •', callback_data='caption')],
                [InlineKeyboardButton('• ᴍᴇᴛᴀᴅᴀᴛᴀ', callback_data='meta'), InlineKeyboardButton('ᴅᴏɴᴀᴛᴇ •', callback_data='donate')],
                [InlineKeyboardButton('• ʜᴏᴍᴇ', callback_data='home')]
            ])
        )
    elif data == "meta":
        await query.message.edit_text(
            text=Txt.SEND_METADATA,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("• ᴄʟᴏsᴇ", callback_data="close"), InlineKeyboardButton("ʙᴀᴄᴋ •", callback_data="help")]
            ])
        )
    elif data == "donate":
        await query.message.edit_text(
            text=Txt.DONATE_TXT,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("• ʙᴀᴄᴋ", callback_data="help"), InlineKeyboardButton("ᴏᴡɴᴇʀ •", url='https://t.me/i_killed_my_clan')]
            ])
        )
    elif data == "file_names":
        format_template = await codeflixbots.get_format_template(user_id)
        await query.message.edit_text(
            text=Txt.FILE_NAME_TXT.format(format_template=format_template),
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("• ᴄʟᴏsᴇ", callback_data="close"), InlineKeyboardButton("ʙᴀᴄᴋ •", callback_data="help")]
            ])
        )
    elif data == "thumbnail":
        await query.message.edit_caption(
            caption=Txt.THUMBNAIL_TXT,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("• ᴄʟᴏsᴇ", callback_data="close"), InlineKeyboardButton("ʙᴀᴄᴋ •", callback_data="help")]
            ])
        )
    elif data == "metadatax":
        await query.message.edit_caption(
            caption=Txt.SEND_METADATA,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("• ᴄʟᴏsᴇ", callback_data="close"), InlineKeyboardButton("ʙᴀᴄᴋ •", callback_data="help")]
            ])
        )
    elif data == "source":
        await query.message.edit_caption(
            caption=Txt.SOURCE_TXT,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("• ᴄʟᴏsᴇ", callback_data="close"), InlineKeyboardButton("ʙᴀᴄᴋ •", callback_data="home")]
            ])
        )
    elif data == "premiumx":
        await query.message.edit_caption(
            caption=Txt.PREMIUM_TXT,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("• ʙᴀᴄᴋ", callback_data="help"), InlineKeyboardButton("ʙᴜʏ ᴘʀᴇᴍɪᴜᴍ •", url='https://t.me/proobito')]
            ])
        )
    elif data == "plans":
        await query.message.edit_caption(
            caption=Txt.PREPLANS_TXT,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("• ᴄʟᴏsᴇ", callback_data="close"), InlineKeyboardButton("ʙᴜʏ ᴘʀᴇᴍɪᴜᴍ •", url='https://t.me/proobito')]
            ])
        )
    elif data == "about":
        await query.message.edit_text(
            text=Txt.ABOUT_TXT,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("• sᴜᴘᴘᴏʀᴛ", url='https://t.me/ahss_help_zone'), InlineKeyboardButton("ᴄᴏᴍᴍᴀɴᴅs •", callback_data="help")],
                [InlineKeyboardButton("• ᴅᴇᴠᴇʟᴏᴘᴇʀ", url='https://t.me/cosmic_awaken'), InlineKeyboardButton("ɴᴇᴛᴡᴏʀᴋ •", url='https://t.me/society_network')],
                [InlineKeyboardButton("• ʙᴀᴄᴋ •", callback_data="home")]
            ])
        )
    elif data == "close":
        try:
            await query.message.delete()
            await query.message.reply_to_message.delete()
            await query.message.continue_propagation()
        except:
            await query.message.delete()
            await query.message.continue_propagation()

@Client.on_message(filters.command("clear") & filters.private)
async def clear_tasks(client: Client, message: Message) -> None:
    user_id = message.from_user.id
    logger.info(f"Clearing tasks for user {user_id}")
    try:
        if user_id in user_tasks:
            tasks = user_tasks[user_id]
            for task in tasks:
                if not task.done():
                    task.cancel()
            user_tasks[user_id] = []
            logger.info(f"Cleared {len(tasks)} tasks for user {user_id}")

        await codeflixbots.delete_user_choice(user_id)
        await message.reply_text("All ongoing tasks and settings cleared!")
        await send_log(client, message.from_user, "Cleared all tasks and settings")
    except ChatAdminRequired:
        logger.error(f"ChatAdminRequired in clear")
        await message.reply_text("Error: Bot lacks admin rights.")
        await send_log(client, message.from_user, "Clear command failed: Bot lacks admin rights")
    except Exception as e:
        logger.error(f"Error clearing tasks for user {user_id}: {e}")
        await message.reply_text("Error: Couldn't clear tasks.")
        await send_log(client, message.from_user, f"Clear command error: {str(e)}")
