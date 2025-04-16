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
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
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

user_tasks = {}
user_semaphores = {}
user_renaming_operations = {}

METADATA_PATTERNS = [
    (re.compile(r'S(\d+)(?:E|EP|_|\s)(\d+)', re.IGNORECASE), ('season', 'episode')),
    (re.compile(r'Season\s*(\d+)\s*Episode\s*(\d+)', re.IGNORECASE), ('season', 'episode')),
    (re.compile(r'\[S(\d+)\]\[E(\d+)\]', re.IGNORECASE), ('season', 'episode')),
    (re.compile(r'S(\d+)[^\d]*(\d+)', re.IGNORECASE), ('season', 'episode')),
    (re.compile(r'(?:Vol|Volume|V)\s*(\d+)', re.IGNORECASE), ('volume', None)),
    (re.compile(r'(?:Ch|Chapter|C)\s*(\d+)', re.IGNORECASE), (None, 'chapter')),
    (re.compile(r'V(\d+)[^\d]*C(\d+)', re.IGNORECASE), ('volume', 'chapter')),
    (re.compile(r'Volume\s*(\d+)\s*Chapter\s*(\d+)', re.IGNORECASE), ('volume', 'chapter')),
    (re.compile(r'(?:E|EP|Episode)\s*(\d+)', re.IGNORECASE), (None, 'episode')),
    (re.compile(r'\b(\d+)\b', re.IGNORECASE), (None, 'episode'))
]

QUALITY_PATTERNS = [
    (re.compile(r'\b(\d{3,4}[pi])\b', re.IGNORECASE), lambda m: m.group(1).upper()),
    (re.compile(r'\b(4k|2160p)\b', re.IGNORECASE), lambda m: "4K"),
    (re.compile(r'\b(2k|1440p)\b', re.IGNORECASE), lambda m: "2K"),
    (re.compile(r'\b(HDRip|HDTV|WebRip|BluRay)\b', re.IGNORECASE), lambda m: m.group(1).upper()),
    (re.compile(r'\b(4kX264|4kX265|X264|X265|X26|DD\s*5\.1)\b', re.IGNORECASE), lambda m: "X264" if m.group(1).upper() == "X26" else m.group(1).upper()),
    (re.compile(r'\[(\d{3,4}[pi])\]', re.IGNORECASE), lambda m: m.group(1).upper())
]

def sanitize_filename(filename, keep_extension=True, max_length=200):
    if not filename:
        return "unnamed_file"
    
    name, ext = os.path.splitext(filename) if keep_extension else (filename, "")
    invalid_chars = r'[<>:"/\\|?*\x00-\x1F]'
    clean = re.sub(invalid_chars, '', name)
    clean = re.sub(r'\s+', '_', clean).strip('_')
    
    result = f"{clean}{ext}"[:max_length]
    result = result.strip('.')
    if not result:
        result = "unnamed_file"
    if keep_extension and ext and not result.endswith(ext):
        result = f"{result}{ext}"
    return result

def extract_metadata(input_text, rename_mode=None):
    if not input_text:
        logger.warning("No input text provided")
        return None, None, "01", "15", "Unknown_Title"
    input_text = str(input_text)
    
    title_match = re.match(r'^(.*?)(?:S\d+|Season|E\d+|Episode|\d{3,4}[pi]|WebRip|BluRay|Hin\s*Eng|DD\s*5\.1|\[|$)', input_text, re.IGNORECASE)
    title = title_match.group(1).strip().replace('.', ' ').title() if title_match else "Unknown_Title"
    if title:
        title = re.sub(r'\s+', ' ', title).strip()
    
    if rename_mode:
        for pattern, (key1, key2) in METADATA_PATTERNS:
            match = pattern.search(rename_mode)
            if match:
                if key1 == 'volume':
                    volume = match.group(1).zfill(2)
                    chapter = match.group(2).zfill(2) if key2 == 'chapter' and len(match.groups()) >= 2 else None
                    return volume, chapter, "01", "15", title
                elif key1 == 'season':
                    season = match.group(1).zfill(2)
                    episode = match.group(2).zfill(2) if key2 == 'episode' and len(match.groups()) >= 2 else "15"
                    logger.info(f"Extracted from rename_mode: season: {season}, episode: {episode}, title: {title}")
                    return None, None, season, episode, title
                elif key2 == 'chapter':
                    chapter = match.group(1).zfill(2)
                    return None, chapter, "01", "15", title
                elif key2 == 'episode':
                    episode = match.group(1).zfill(2)
                    return None, None, "01", episode, title

    for pattern, (key1, key2) in METADATA_PATTERNS:
        match = pattern.search(input_text)
        if match:
            if key1 == 'volume':
                volume = match.group(1).zfill(2)
                chapter = match.group(2).zfill(2) if key2 == 'chapter' and len(match.groups()) >= 2 else None
                return volume, chapter, "01", "15", title
            elif key1 == 'season':
                season = match.group(1).zfill(2)
                episode = match.group(2).zfill(2) if key2 == 'episode' and len(match.groups()) >= 2 else "15"
                logger.info(f"Extracted from input_text: season: {season}, episode: {episode}, title: {title}")
                return None, None, season, episode, title
            elif key2 == 'chapter':
                chapter = match.group(1).zfill(2)
                return None, chapter, "01", "15", title
            elif key2 == 'episode':
                episode = match.group(1).zfill(2)
                return None, None, "01", episode, title
    logger.warning(f"No metadata matched: {input_text}")
    return None, None, "01", "15", title

def extract_quality(input_text):
    if not input_text:
        return "720P"
    for pattern, extractor in QUALITY_PATTERNS:
        match = pattern.search(input_text)
        if match:
            quality = extractor(match)
            logger.info(f"Extracted quality: {quality}")
            return quality
    logger.warning(f"No quality matched for {input_text}")
    return "720P"

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

def sanitize_metadata_value(value):
    if not value:
        return None
    value = re.sub(r'[\x00-\x1F\x7F"\']', '', value).strip()
    return value[:255] if value else None

async def add_metadata(input_path, output_path, user_id):
    ffmpeg = shutil.which('ffmpeg')
    logger.info(f"FFmpeg path: {ffmpeg}")
    if not ffmpeg:
        logger.error("FFmpeg not found")
        raise RuntimeError("FFmpeg not found")
    
    if not os.path.exists(input_path):
        logger.error(f"Input file {input_path} does not exist")
        raise RuntimeError(f"Input file {input_path} does not exist")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    try:
        metadata = {}
        for key, getter in [
            ('title', codeflixbots.get_title),
            ('artist', codeflixbots.get_artist),
            ('author', codeflixbots.get_author),
            ('video_title', codeflixbots.get_video),
            ('audio_title', codeflixbots.get_audio),
            ('subtitle', codeflixbots.get_subtitle)
        ]:
            try:
                value = await getter(user_id)
                metadata[key] = sanitize_metadata_value(value)
                logger.info(f"Retrieved {key} for user {user_id}: {metadata[key]}")
            except Exception as e:
                logger.error(f"Error retrieving {key} for user {user_id}: {e}")
                metadata[key] = None

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
        start_time = time.time()
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=600.0)
        
        if process.returncode != 0:
            logger.error(f"FFmpeg error (return code {process.returncode}): {stderr.decode()}")
            raise RuntimeError(f"FFmpeg failed: {stderr.decode()}")
        if not os.path.exists(output_path):
            logger.error(f"Output file {output_path} not created")
            raise RuntimeError(f"Output file {output_path} not created")
        logger.info(f"Metadata added in {time.time() - start_time:.2f}s")
        return True
    except asyncio.TimeoutError:
        logger.error(f"Metadata processing timed out after 600s")
        return False
    except Exception as e:
        logger.error(f"Metadata processing failed: {e}")
        raise

async def send_to_dump_channel(client, message, user_id):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            sent_message = await client.send_document(
                chat_id=Config.DUMP_CHANNEL,
                document=message.document.file_id,
                caption=f"From user {user_id}",
                disable_notification=True
            )
            logger.info(f"Sent file to dump channel for user {user_id} (attempt {attempt + 1})")
            return sent_message
        except Exception as e:
            if "MESSAGE_ID_INVALID" in str(e):
                logger.warning(f"Retry {attempt + 1}/{max_retries} for MESSAGE_ID_INVALID")
                await asyncio.sleep(1)
                continue
            logger.error(f"Dump channel send failed for user {user_id}: {e}")
            break
    return None

@Client.on_message(filters.command("setsuffix") & filters.private)
async def set_suffix(client, message):
    user_id = message.from_user.id
    if len(message.command) < 2:
        return await message.reply_text("Please provide a suffix, e.g., /setsuffix Finished_Society")
    suffix = message.command[1]
    await codeflixbots.set_custom_suffix(user_id, suffix)
    await message.reply_text(f"Suffix set to: {suffix} ✅")

@Client.on_message(filters.command("settemplate") & filters.private)
async def set_template(client, message):
    user_id = message.from_user.id
    if len(message.command) < 2:
        return await message.reply_text("Please provide a template, e.g., /settemplate {title}_S{season}E{episode}_{quality}_{suffix}.mkv")
    template = " ".join(message.command[1:])
    await codeflixbots.set_format_template(user_id, template)
    await message.reply_text(f"Template set to: {template} ✅")

@Client.on_message((filters.document | filters.video | filters.audio) & filters.private)
async def process_file(client, message):
    user_id = message.from_user.id
    file_id = (message.document or message.video or message.audio).file_id

    if user_id not in user_semaphores:
        user_semaphores[user_id] = asyncio.Semaphore(10)
    if user_id not in user_tasks:
        user_tasks[user_id] = []
    if user_id not in user_renaming_operations:
        user_renaming_operations[user_id] = set()

    if file_id in user_renaming_operations[user_id]:
        logger.info(f"File {file_id} already being processed for user {user_id}, skipping")
        return

    async with user_semaphores[user_id]:
        user_renaming_operations[user_id].add(file_id)
        download_path = None
        metadata_path = None
        thumb_path = None

        try:
            format_template = await codeflixbots.get_format_template(user_id)
            rename_mode = await codeflixbots.get_user_choice(user_id)
            custom_suffix = await codeflixbots.get_custom_suffix(user_id) or "Finished_Society"
            media_preference = await codeflixbots.get_media_preference(user_id)

            if message.document:
                file_name = message.document.file_name or "document"
                file_size = message.document.file_size
                media_type = "document"
            elif message.video:
                file_name = message.video.file_name or "video"
                file_size = message.video.file_size
                media_type = "video"
            elif message.audio:
                file_name = message.audio.file_name or "audio"
                file_size = message.audio.file_size
                media_type = "audio"
            else:
                return await message.reply_text("Unsupported file type")

            if media_preference and media_preference != media_type:
                return await message.reply_text(f"Your media preference is set to '{media_preference}'. Please upload a {media_preference} file or change it with /setmedia.")

            if await check_anti_nsfw(file_name, message):
                return await message.reply_text("NSFW content detected")

            try:
                input_text = message.caption or file_name
                volume, chapter, season, episode, title = extract_metadata(input_text, rename_mode)
                quality = extract_quality(rename_mode or input_text)

                title = title or "Unknown_Title"
                season = season or "01"
                episode = episode or "15"
                quality = quality or "720P"

                if format_template:
                    new_template = format_template
                else:
                    new_template = "{title}_S{season}E{episode}_{quality}_{suffix}{ext}"
                    logger.info(f"No format_template for user {user_id}, using default: {new_template}")

                original_ext = os.path.splitext(file_name)[1] or ('.mkv' if media_type == "video" else '.mp3' if media_type == "audio" else '.file')
                template_ext_match = re.search(r'\.([a-zA-Z0-9]+)$', new_template)
                template_ext = f".{template_ext_match.group(1)}" if template_ext_match else original_ext

                if '{ext}' in new_template:
                    new_template = new_template.replace('{ext}', '')
                    target_ext = original_ext
                elif template_ext_match:
                    new_template = re.sub(r'\.[a-zA-Z0-9]+$', '', new_template)
                    target_ext = template_ext
                else:
                    target_ext = original_ext

                replacements = {
                    '{volume}': volume or 'UNKNOWN',
                    '{chapter}': chapter or 'UNKNOWN',
                    '{season}': season,
                    '{episode}': episode,
                    '{quality}': quality,
                    '{title}': title,
                    '{suffix}': custom_suffix,
                    'Volume': volume or 'UNKNOWN',
                    'Chapter': chapter or 'UNKNOWN',
                    'Season': season,
                    'Episode': episode,
                    'QUALITY': quality,
                    'TITLE': title,
                    'SUFFIX': custom_suffix
                }

                new_filename = new_template
                for placeholder, value in replacements.items():
                    new_filename = new_filename.replace(placeholder, str(value))

                if not new_filename.strip():
                    new_filename = f"Unknown_Title_S01E15_720P_{custom_suffix}"

                full_filename = f"{new_filename}{target_ext}"

                if len(full_filename) > 200:
                    new_filename = f"Unknown_Title_S01E15_720P_{custom_suffix}"
                    full_filename = f"{new_filename}{target_ext}"

                new_filename = sanitize_filename(full_filename)
                download_path = f"downloads/{new_filename}"
                metadata_path = f"metadata/{new_filename}"

                os.makedirs(os.path.dirname(download_path), exist_ok=True)
                os.makedirs(os.path.dirname(metadata_path), exist_ok=True)

                msg = await message.reply_text("**Downloading...**")
                start_time = time.time()

                async def process_single_file():
                    nonlocal download_path, metadata_path, thumb_path
                    try:
                        # Download with proper filename
                        file_path = await client.download_media(
                            message,
                            file_name=download_path,
                            progress=progress_for_pyrogram,
                            progress_args=("Downloading...", msg, time.time())
                        )
                        if not file_path or not os.path.exists(file_path):
                            logger.error(f"Download failed for {new_filename}")
                            await msg.edit("Error: Download failed.")
                            return

                        # Process metadata
                        metadata_enabled = await codeflixbots.get_metadata(user_id) == "On"
                        if metadata_enabled:
                            await msg.edit("**Processing metadata...**")
                            try:
                                if await add_metadata(file_path, metadata_path, user_id):
                                    if os.path.exists(metadata_path):
                                        os.remove(file_path)
                                        file_path = metadata_path
                                        logger.info(f"Using metadata file: {metadata_path}")
                                    else:
                                        logger.warning(f"Metadata file {metadata_path} not found, using {file_path}")
                                else:
                                    logger.info(f"No metadata applied for user {user_id}")
                            except Exception as e:
                                logger.error(f"Metadata processing failed for user {user_id}: {e}")
                                await msg.edit(f"Metadata processing failed, proceeding without metadata: {e}")

                        # Prepare thumbnail
                        await msg.edit("**Preparing upload...**")
                        caption = f"**{new_filename}**"
                        thumb = await codeflixbots.get_thumbnail(user_id)
                        thumb_path = None

                        if thumb:
                            thumb_path = await client.download_media(thumb)
                        elif media_type == "video" and message.video and message.video.thumbs:
                            thumb_path = await client.download_media(message.video.thumbs[0].file_id)
                        
                        thumb_path = await process_thumbnail(thumb_path)

                        # Upload with proper filename
                        await msg.edit("**Uploading...**")
                        sent_message = await client.send_document(
                            chat_id=message.chat.id,
                            document=file_path,
                            file_name=new_filename,
                            caption=caption,
                            thumb=thumb_path,
                            progress=progress_for_pyrogram,
                            progress_args=("Uploading...", msg, time.time())
                        )
                        await msg.delete()
                        if sent_message:
                            asyncio.create_task(send_to_dump_channel(client, sent_message, user_id))
                    except Exception as e:
                        logger.error(f"Processing failed for user {user_id}: {e}")
                        await msg.edit(f"Processing failed, using default filename...")
                        default_filename = f"Unknown_Title_S01E15_720P_{custom_suffix}{target_ext}"
                        default_filename = sanitize_filename(default_filename)
                        default_path = f"downloads/{default_filename}"
                        
                        try:
                            file_path = await client.download_media(
                                message,
                                file_name=default_path
                            )
                            if file_path and os.path.exists(file_path):
                                sent_message = await client.send_document(
                                    chat_id=message.chat.id,
                                    document=file_path,
                                    file_name=default_filename,
                                    caption=f"**{default_filename}**",
                                    thumb=await process_thumbnail(thumb_path)
                                )
                                await msg.delete()
                                if sent_message:
                                    asyncio.create_task(send_to_dump_channel(client, sent_message, user_id))
                            else:
                                await msg.edit("Error: File not found.")
                        except Exception as download_error:
                            logger.error(f"Download failed for user {user_id}: {download_error}")
                            await msg.edit("Error: Unable to process file.")
                    finally:
                        await cleanup_files(download_path, metadata_path, thumb_path)

                # Start processing as a separate task
                task = asyncio.create_task(process_single_file())
                user_tasks[user_id].append(task)

            except Exception as e:
                logger.error(f"Processing error for user {user_id}: {e}")
                await message.reply_text(f"Error: {str(e)}, using default filename...")
                default_filename = f"Unknown_Title_S01E15_720P_{custom_suffix}{original_ext}"
                default_filename = sanitize_filename(default_filename)
                download_path = f"downloads/{default_filename}"
                metadata_path = f"metadata/{default_filename}"

                try:
                    file_path = await client.download_media(
                        message,
                        file_name=download_path
                    )
                    if file_path and os.path.exists(file_path):
                        sent_message = await client.send_document(
                            chat_id=message.chat.id,
                            document=file_path,
                            file_name=default_filename,
                            caption=f"**{default_filename}**",
                            thumb=await process_thumbnail(thumb_path)
                        )
                        if sent_message:
                            asyncio.create_task(send_to_dump_channel(client, sent_message, user_id))
                    else:
                        await message.reply_text("Error: File not found.")
                except Exception as download_error:
                    logger.error(f"Download failed for user {user_id}: {download_error}")
                    await message.reply_text("Error: Unable to process file.")
                finally:
                    await cleanup_files(download_path, metadata_path, thumb_path)

        finally:
            user_renaming_operations[user_id].discard(file_id)
            user_tasks[user_id] = [t for t in user_tasks[user_id] if not t.done()]
