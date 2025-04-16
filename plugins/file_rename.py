import os
import re
import time
import shutil
import asyncio
import logging
from datetime import datetime
from PIL import Image
from pyrogram import Client, filters
from pyrogram.errors import FloodWait, ChatAdminRequired
from pyrogram.types import Message
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
    value = re.sub(r'[\x00-\x1F\x7F]', '', value).strip()
    return value[:255] if value else None

async def add_metadata(input_path, output_path, user_id):
    ffmpeg = shutil.which('ffmpeg')
    if not ffmpeg:
        logger.error("FFmpeg not found")
        return False
    
    if not os.path.exists(input_path):
        logger.error(f"Input file {input_path} does not exist")
        return False
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    async def run_ffmpeg(cmd):
        for attempt in range(5):  # Increased retries for stability
            try:
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=600.0)
                if process.returncode != 0:
                    logger.error(f"FFmpeg error (attempt {attempt + 1}): {stderr.decode()}")
                    continue
                if not os.path.exists(output_path):
                    logger.error(f"Output file {output_path} not created")
                    continue
                return True
            except asyncio.TimeoutError:
                logger.error(f"FFmpeg timed out (attempt {attempt + 1})")
            except Exception as e:
                logger.error(f"FFmpeg failed (attempt {attempt + 1}): {e}")
            await asyncio.sleep(2)  # Increased delay for Heroku
        return False

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
        return await run_ffmpeg(cmd)
    except Exception as e:
        logger.error(f"Metadata processing failed: {e}")
        return False

async def send_to_dump_channel(client, message, user_id):
    for attempt in range(5):  # Increased retries
        try:
            sent_message = await client.send_document(
                chat_id=Config.DUMP_CHANNEL,
                document=message.document.file_id,
                caption=f"From user {user_id}",
                disable_notification=True
            )
            logger.info(f"Sent file to dump channel for user {user_id} (attempt {attempt + 1})")
            return sent_message
        except FloodWait as fw:
            logger.warning(f"FloodWait in dump channel send, waiting {fw.value}s")
            await asyncio.sleep(fw.value)
        except ChatAdminRequired:
            logg
            er.error(f"ChatAdminRequired in dump channel for user {user_id}")
            return None
        except Exception as e:
            logger.error(f"Dump channel send failed (attempt {attempt + 1}): {e}")
        await asyncio.sleep(2)
    return None

@Client.on_message(filters.command("setsuffix") & filters.private)
async def set_suffix(client, message):
    user_id = message.from_user.id
    if len(message.command) < 2:
        return await message.reply_text("Please provide a suffix, e.g., /setsuffix Finished_Society")
    suffix = message.command[1]
    try:
        await codeflixbots.set_custom_suffix(user_id, suffix)
        await message.reply_text(f"Suffix set to: {suffix} ✅")
    except Exception as e:
        logger.error(f"Error setting suffix for user {user_id}: {e}")
        await message.reply_text("Error setting suffix. Try again later.")

@Client.on_message(filters.command("settemplate") & filters.private)
async def set_template(client, message):
    user_id = message.from_user.id
    if len(message.command) < 2:
        return await message.reply_text("Please provide a template, e.g., /settemplate [AS] [S{season}-E{episode}] {title} [{quality} ⌯ Sub] @{suffix}.mkv")
    template = " ".join(message.command[1:])
    try:
        await codeflixbots.set_format_template(user_id, template)
        await message.reply_text(f"Template set to: {template} ✅")
    except Exception as e:
        logger.error(f"Error setting template for user {user_id}: {e}")
        await message.reply_text("Error setting template. Try again later.")

@Client.on_message((filters.document | filters.video | filters.audio) & filters.private)
async def process_file(client, message):
    user_id = message.from_user.id
    file_id = (message.document or message.video or message.audio).file_id

    async def attempt_operation(operation, description, max_retries=5):  # Increased retries
        for attempt in range(max_retries):
            try:
                return await operation()
            except FloodWait as fw:
                logger.warning(f"FloodWait in {description}, waiting {fw.value}s")
                await asyncio.sleep(fw.value)
            except ChatAdminRequired:
                logger.error(f"ChatAdminRequired in {description} for user {user_id}")
                return None
            except Exception as e:
                logger.error(f"Error in {description} (attempt {attempt + 1}): {e}")
            await asyncio.sleep(2)  # Increased delay
        logger.error(f"Failed {description} after {max_retries} attempts")
        return None

    # Spawn a new coroutine for each file to allow unlimited concurrency
    async def process_single_file():
        download_path = None
        metadata_path = None
        thumb_path = None

        try:
            format_template = await attempt_operation(
                lambda: codeflixbots.get_format_template(user_id),
                "get format template"
            )
            rename_mode = await attempt_operation(
                lambda: codeflixbots.get_user_choice(user_id),
                "get user choice"
            )
            custom_suffix = await attempt_operation(
                lambda: codeflixbots.get_custom_suffix(user_id),
                "get custom suffix"
            ) or "Finished_Society"
            media_preference = await attempt_operation(
                lambda: codeflixbots.get_media_preference(user_id),
                "get media preference"
            )

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
                await message.reply_text("Unsupported file type")
                return

            if media_preference and media_preference != media_type:
                await message.reply_text(f"Your media preference is set to '{media_preference}'. Please upload a {media_preference} file or change it with /setmedia.")
                return

            if await check_anti_nsfw(file_name, message):
                await message.reply_text("NSFW content detected")
                return

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
                new_template = "[AS] [S{season}-E{episode}] {title} [{quality} ⌯ Sub] @{suffix}{ext}"
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
                new_filename = f"[AS] [S01-E15] Unknown_Title [720P ⌯ Sub] @{custom_suffix}"

            full_filename = f"{new_filename}{target_ext}"
            if len(full_filename) > 255:
                full_filename = full_filename[:255 - len(target_ext)] + target_ext

            download_path = f"downloads/{user_id}/{file_id}_{full_filename}"  # Unique path per file_id
            metadata_path = f"metadata/{user_id}/{file_id}_{full_filename}"

            os.makedirs(os.path.dirname(download_path), exist_ok=True)
            os.makedirs(os.path.dirname(metadata_path), exist_ok=True)

            msg = await attempt_operation(
                lambda: message.reply_text("**Downloading...**"),
                "send downloading message"
            )
            if not msg:
                return

            file_path = await attempt_operation(
                lambda: client.download_media(
                    message,
                    file_name=download_path,
                    progress=progress_for_pyrogram,
                    progress_args=("Downloading...", msg, time.time())
                ),
                "download media"
            )
            if not file_path or not os.path.exists(file_path):
                logger.error(f"Download failed for {full_filename}")
                await msg.edit("Error: Download failed.")
                return

            metadata_enabled = await attempt_operation(
                lambda: codeflixbots.get_metadata(user_id),
                "get metadata setting"
            ) == "On"
            if metadata_enabled:
                await msg.edit("**Processing metadata...**")
                if await add_metadata(file_path, metadata_path, user_id):
                    if os.path.exists(metadata_path):
                        os.remove(file_path)
                        file_path = metadata_path
                        logger.info(f"Using metadata file: {metadata_path}")
                    else:
                        logger.warning(f"Metadata file {metadata_path} not found, using {file_path}")

            await msg.edit("**Preparing upload...**")
            caption = f"**{full_filename}**"
            thumb = await attempt_operation(
                lambda: codeflixbots.get_thumbnail(user_id),
                "get thumbnail"
            )
            thumb_path = None

            if thumb:
                thumb_path = await attempt_operation(
                    lambda: client.download_media(thumb),
                    "download custom thumbnail"
                )
            elif media_type == "video" and message.video and message.video.thumbs:
                thumb_path = await attempt_operation(
                    lambda: client.download_media(message.video.thumbs[0].file_id),
                    "download video thumbnail"
                )
            
            thumb_path = await process_thumbnail(thumb_path)

            sent_message = await attempt_operation(
                lambda: client.send_document(
                    chat_id=message.chat.id,
                    document=file_path,
                    file_name=full_filename,
                    caption=caption,
                    thumb=thumb_path,
                    progress=progress_for_pyrogram,
                    progress_args=("Uploading...", msg, time.time())
                ),
                "upload document"
            )
            if sent_message:
                await msg.delete()
                await send_to_dump_channel(client, sent_message, user_id)
            else:
                await msg.edit("Error: Upload failed.")
        except Exception as e:
            logger.error(f"Processing failed for user {user_id}, file {file_id}: {e}")
            await msg.edit(f"Error: Processing failed: {e}")
        finally:
            await cleanup_files(download_path, metadata_path, thumb_path)

    # Run each file processing in a separate coroutine
    asyncio.create_task(process_single_file())
