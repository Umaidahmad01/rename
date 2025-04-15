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
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from hachoir.metadata import extractMetadata
from hachoir.parser import createParser
from plugins.antinsfw import check_anti_nsfw
from helper.utils import progress_for_pyrogram, humanbytes, send_log
from helper.database import codeflixbots
from config import Config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

renaming_operations = {}
user_tasks = {}

# Patterns for extracting volume, chapter, season, episode
METADATA_PATTERNS = [
    # Manga-specific: Volume and Chapter
    (re.compile(r'(?:Vol|Volume|V)\s*(\d+)', re.IGNORECASE), ('volume', None)),
    (re.compile(r'(?:Ch|Chapter|C)\s*(\d+)', re.IGNORECASE), (None, 'chapter')),
    (re.compile(r'V(\d+)[^\d]*C(\d+)', re.IGNORECASE), ('volume', 'chapter')),
    (re.compile(r'Volume\s*(\d+)\s*Chapter\s*(\d+)', re.IGNORECASE), ('volume', 'chapter')),
    # Video-specific: Season and Episode
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

def extract_metadata(input_text, rename_mode):
    if not input_text:
        logger.warning(f"No input text for rename_mode {rename_mode}")
        return None, None, None, None
    input_text = str(input_text)
    for pattern, (key1, key2) in METADATA_PATTERNS:
        match = pattern.search(input_text)
        if match:
            if key1 == 'volume':
                volume = match.group(1)
                chapter = match.group(2) if key2 == 'chapter' and len(match.groups()) >= 2 else None
                return volume, chapter, None, None
            elif key1 == 'season':
                season = match.group(1)
                episode = match.group(2) if key2 == 'episode' and len(match.groups()) >= 2 else None
                return None, None, season, episode
            elif key2 == 'chapter':
                chapter = match.group(1)
                return None, chapter, None, None
            elif key2 == 'episode':
                episode = match.group(1)
                return None, None, None, episode
    logger.warning(f"No metadata matched for {rename_mode}: {input_text}")
    return None, None, None, None

def extract_quality(filename):
    if not filename:
        return "UNKNOWN"
    for pattern, extractor in QUALITY_PATTERNS:
        match = pattern.search(filename)
        if match:
            quality = extractor(match)
            logger.info(f"Extracted quality: {quality}")
            return quality
    logger.warning(f"No quality matched for {filename}")
    return "UNKNOWN"

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
                    cmd.extend(['-metadata:s:v', f'title="{value}"'])
                elif key == 'audio_title':
                    cmd.extend(['-metadata:s:a', f'title="{value}"'])
                elif key == 'subtitle':
                    cmd.extend(['-metadata:s:s', f'title="{value}"'])
                else:
                    cmd.extend(['-metadata', f'{key}="{value}"'])
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
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=2.0)
        
        if process.returncode != 0:
            logger.error(f"FFmpeg error (return code {process.returncode}): {stderr.decode()}")
            raise RuntimeError(f"FFmpeg failed: {stderr.decode()}")
        if not os.path.exists(output_path):
            logger.error(f"Output file {output_path} not created")
            raise RuntimeError(f"Output file {output_path} not created")
        logger.info(f"Metadata added in {time.time() - start_time:.2f}s")
        return True
    except asyncio.TimeoutError:
        logger.error(f"Metadata processing timed out")
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

@Client.on_message((filters.document | filters.video | filters.audio) & filters.private)
async def process_file(client, message):
    user_id = message.from_user.id
    format_template = await codeflixbots.get_format_template(user_id)
    rename_mode = await codeflixbots.get_user_choice(user_id)

    if user_id not in user_tasks:
        user_tasks[user_id] = []

    download_path = None
    metadata_path = None
    thumb_path = None

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
        # Default renaming if no mode set
        if not rename_mode:
            rename_mode = "filename"  # Default to filename-based renaming
            logger.info(f"No rename_mode set for user {user_id}, defaulting to filename")

        # Extract metadata from filename or caption
        input_text = file_name if rename_mode == "filename" else (message.caption or file_name)
        volume, chapter, season, episode = extract_metadata(input_text, rename_mode)
        quality = extract_quality(file_name)

        # Use format_template if available, else fallback to filename
        if format_template:
            new_template = format_template
        else:
            new_template = os.path.splitext(file_name)[0]  # Use filename without extension
            logger.info(f"No format_template for user {user_id}, using filename: {new_template}")

        # Detect template extension
        template_ext_match = re.search(r'\.([a-zA-Z0-9]+)$', new_template)
        template_ext = f".{template_ext_match.group(1)}" if template_ext_match else None
        original_ext = os.path.splitext(file_name)[1] or ('.mp4' if media_type == "video" else '.mp3')
        target_ext = template_ext if template_ext else original_ext

        # Remove extension from template for processing
        if template_ext:
            new_template = re.sub(r'\.[a-zA-Z0-9]+$', '', new_template)

        # Replace placeholders with UNKNOWN for missing values
        replacements = {
            '{volume}': volume or 'UNKNOWN',
            '{chapter}': chapter or 'UNKNOWN',
            '{season}': season or 'UNKNOWN',
            '{episode}': episode or 'UNKNOWN',
            '{quality}': quality,
            'Volume': volume or 'UNKNOWN',
            'Chapter': chapter or 'UNKNOWN',
            'Season': season or 'UNKNOWN',
            'Episode': episode or 'UNKNOWN',
            'QUALITY': quality
        }

        for placeholder, value in replacements.items():
            new_template = new_template.replace(placeholder, str(value))

        if not new_template.strip():
            new_template = f"file_{user_id}"

        new_filename = sanitize_filename(f"{new_template}{target_ext}")
        download_path = f"downloads/{new_filename}"
        metadata_path = f"metadata/{new_filename}"

        os.makedirs(os.path.dirname(download_path), exist_ok=True)
        os.makedirs(os.path.dirname(metadata_path), exist_ok=True)

        msg = await message.reply_text("**Downloading...**")
        start_time = time.time()
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
        
        upload_start = time.time()
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
            sent_message = await upload_task
            logger.info(f"Uploaded to user in {time.time() - upload_start:.2f}s")
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

        # Send to dump channel in background
        try:
            if os.path.exists(file_path):
                asyncio.create_task(send_to_dump_channel(client, sent_message, user_id))
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
