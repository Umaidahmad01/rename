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

# Manga-focused metadata patterns
METADATA_PATTERNS = [
    (re.compile(r'(?:Vol|Volume|V)\s*(\d+)(?:[\s_-]*(?:Ch|Chapter|C)\s*(\d+))?', re.IGNORECASE), ('volume', 'chapter')),
    (re.compile(r'V(\d+)[^\d]*(?:C)(\d+)', re.IGNORECASE), ('volume', 'chapter')),
    (re.compile(r'Volume\s*(\d+)\s*Chapter\s*(\d+)', re.IGNORECASE), ('volume', 'chapter')),
    (re.compile(r'S(\d+)(?:E|EP|_|\s)(\d+)', re.IGNORECASE), ('season', 'episode')),
    (re.compile(r'Season\s*(\d+)\s*Episode\s*(\d+)', re.IGNORECASE), ('season', 'episode')),
    (re.compile(r'\[S(\d+)\]\[E(\d+)\]', re.IGNORECASE), ('season', 'episode')),
    (re.compile(r'S(\d+)[^\d]*(\d+)', re.IGNORECASE), ('season', 'episode')),
    (re.compile(r'(?:Ch|Chapter|C)\s*(\d+)', re.IGNORECASE), (None, 'chapter')),
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

renaming_operations = {}

def extract_metadata(input_text, rename_mode=None):
    if not input_text:
        logger.warning("No input text provided")
        return "01", "01", "01", "15", "Unknown_Title"
    input_text = str(input_text)
    
    title_match = re.match(r'^(.*?)(?:Vol|Volume|V|S\d+|Season|E\d+|Episode|Ch|Chapter|\d{3,4}[pi]|WebRip|BluRay|Hin\s*Eng|DD\s*5\.1|\[|$)', input_text, re.IGNORECASE)
    title = title_match.group(1).strip().replace('.', ' ').title() if title_match else "Unknown_Title"
    if title:
        title = re.sub(r'\s+', ' ', title).strip()
    
    if rename_mode:
        for pattern, (key1, key2) in METADATA_PATTERNS:
            match = pattern.search(rename_mode)
            if match:
                if key1 == 'volume':
                    volume = match.group(1).zfill(2)
                    chapter = match.group(2).zfill(2) if key2 == 'chapter' and len(match.groups()) >= 2 else "01"
                    return volume, chapter, "01", "15", title
                elif key1 == 'season':
                    season = match.group(1).zfill(2)
                    episode = match.group(2).zfill(2) if key2 == 'episode' and len(match.groups()) >= 2 else "15"
                    return "01", "01", season, episode, title
                elif key2 == 'chapter':
                    chapter = match.group(1).zfill(2)
                    return "01", chapter, "01", "15", title
                elif key2 == 'episode':
                    episode = match.group(1).zfill(2)
                    return "01", "01", "01", episode, title
    for pattern, (key1, key2) in METADATA_PATTERNS:
        match = pattern.search(input_text)
        if match:
            if key1 == 'volume':
                volume = match.group(1).zfill(2)
                chapter = match.group(2).zfill(2) if key2 == 'chapter' and len(match.groups()) >= 2 else "01"
                return volume, chapter, "01", "15", title
            elif key1 == 'season':
                season = match.group(1).zfill(2)
                episode = match.group(2).zfill(2) if key2 == 'episode' and len(match.groups()) >= 2 else "15"
                return "01", "01", season, episode, title
            elif key2 == 'chapter':
                chapter = match.group(1).zfill(2)
                return "01", chapter, "01", "15", title
            elif key2 == 'episode':
                episode = match.group(1).zfill(2)
                return "01", "01", "01", episode, title
    logger.warning(f"No metadata matched: {input_text}")
    return "01", "01", "01", "15", title

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
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)
        except Exception as e:
            logger.error(f"Error removing {path}: {e}")

async def process_thumbnail(thumb_path):
    if not thumb_path or not os.path.exists(thumb_path):
        return None
    try:
        with Image.open(thumb_path) as img:
            img = img.convert("RGB").resize((200, 200))
            img.save(thumb_path, "JPEG", quality=85)
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
        
        for attempt in range(5):
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
            await asyncio.sleep(2)
        return False
    except Exception as e:
        logger.error(f"Metadata processing failed: {e}")
        return False

async def convert_file(input_path, output_path, target_ext):
    ffmpeg = shutil.which('ffmpeg')
    if not ffmpeg:
        logger.error("FFmpeg not found")
        return False
    
    if not os.path.exists(input_path):
        logger.error(f"Input file {input_path} does not exist")
        return False
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    cmd = [ffmpeg, '-i', input_path, '-c:v', 'copy', '-c:a', 'copy', '-loglevel', 'error', output_path]
    if target_ext == '.mp4':
        cmd.extend(['-f', 'mp4'])
    elif target_ext == '.mkv':
        cmd.extend(['-f', 'matroska'])

    for attempt in range(5):
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=600.0)
            if process.returncode != 0:
                logger.error(f"FFmpeg convert error (attempt {attempt + 1}): {stderr.decode()}")
                continue
            if not os.path.exists(output_path):
                logger.error(f"Output file {output_path} not created")
                continue
            return True
        except asyncio.TimeoutError:
            logger.error(f"FFmpeg convert timed out (attempt {attempt + 1})")
        except Exception as e:
            logger.error(f"FFmpeg convert failed (attempt {attempt + 1}): {e}")
        await asyncio.sleep(2)
    return False

async def send_to_dump_channel(client, message, user_id):
    for attempt in range(5):
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
            logger.error(f"ChatAdminRequired in dump channel for user {user_id}")
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
        return await message.reply_text("Please provide a template, e.g., /settemplate [AS] [Vol{volume}-Ch{chapter}] {title} [{quality}] @{suffix}.mkv")
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

    async def attempt_operation(operation, description, max_retries=5):
        backoff = 2
        for attempt in range(max_retries):
            try:
                result = await operation()
                logger.info(f"Success in {description} for user {user_id}, file {file_id}")
                return result
            except FloodWait as fw:
                logger.warning(f"FloodWait in {description} for user {user_id}, file {file_id}, waiting {fw.value}s")
                await asyncio.sleep(min(fw.value, 60))  # Cap at 60s
                backoff = min(backoff * 2, 16)
            except ChatAdminRequired:
                logger.error(f"ChatAdminRequired in {description} for user {user_id}, file {file_id}")
                return None
            except Exception as e:
                logger.error(f"Error in {description} (attempt {attempt + 1}) for user {user_id}, file {file_id}: {e}")
            await asyncio.sleep(backoff)
        logger.error(f"Failed {description} after {max_retries} attempts for user {user_id}, file {file_id}")
        return None

    # Stagger API calls to reduce throttling
    await asyncio.sleep(0.01)

    if file_id in renaming_operations:
        if (datetime.now() - renaming_operations[file_id]).seconds < 10:
            logger.info(f"Skipping duplicate file {file_id} for user {user_id}")
            return
    renaming_operations[file_id] = datetime.now()

    download_path = None
    metadata_path = None
    thumb_path = None
    convert_path = None

    async def run_processing():
        nonlocal download_path, metadata_path, thumb_path, convert_path
        try:
            logger.info(f"Starting processing for user {user_id}, file {file_id}")
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
            volume = volume or "01"
            chapter = chapter or "01"
            season = season or "01"
            episode = episode or "15"
            quality = quality or "720P"

            if format_template:
                new_template = format_template
            else:
                new_template = "[AS] [Vol{volume}-Ch{chapter}] {title} [{quality}] @{suffix}{ext}"
                logger.info(f"No format_template for user {user_id}, using default: {new_template}")

            original_ext = os.path.splitext(file_name)[1].lower() or ('.mkv' if media_type == "video" else '.mp3' if media_type == "audio" else '.file')
            template_ext_match = re.search(r'\.([a-zA-Z0-9]+)$', new_template, re.IGNORECASE)
            template_ext = f".{template_ext_match.group(1).lower()}" if template_ext_match else original_ext

            if '{ext}' in new_template:
                new_template = new_template.replace('{ext}', '')
                target_ext = template_ext if template_ext_match else original_ext
            elif template_ext_match:
                new_template = re.sub(r'\.[a-zA-Z0-9]+$', '', new_template, flags=re.IGNORECASE)
                target_ext = template_ext
            else:
                target_ext = original_ext

            replacements = {
                '{volume}': volume,
                '{chapter}': chapter,
                '{season}': season,
                '{episode}': episode,
                '{quality}': quality,
                '{title}': title,
                '{suffix}': custom_suffix,
                'Volume': volume,
                'Chapter': chapter,
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
                new_filename = f"[AS] [Vol01-Ch01] Unknown_Title [720P] @{custom_suffix}"

            full_filename = f"{new_filename}{target_ext}"
            if len(full_filename) > 255:
                full_filename = full_filename[:255 - len(target_ext)] + target_ext

            download_path = f"downloads/{user_id}/{file_id}_{full_filename}"
            metadata_path = f"metadata/{user_id}/{file_id}_{full_filename}"
            convert_path = f"convert/{user_id}/{file_id}_{full_filename}" if target_ext != original_ext else None

            os.makedirs(os.path.dirname(download_path), exist_ok=True)
            os.makedirs(os.path.dirname(metadata_path), exist_ok=True)
            if convert_path:
                os.makedirs(os.path.dirname(convert_path), exist_ok=True)

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

            if convert_path and target_ext != original_ext:
                await msg.edit("**Converting file...**")
                if await convert_file(file_path, convert_path, target_ext):
                    if os.path.exists(convert_path):
                        await cleanup_files(file_path)
                        file_path = convert_path
                        logger.info(f"Converted to {convert_path}")
                    else:
                        logger.warning(f"Converted file {convert_path} not found, using {file_path}")
                else:
                    logger.error(f"File conversion failed for {full_filename}")
                    await msg.edit("Error: File conversion failed.")

            metadata_enabled = await attempt_operation(
                lambda: codeflixbots.get_metadata(user_id),
                "get metadata setting"
            ) == "On"
            if metadata_enabled and target_ext in ('.mp4', '.mkv', '.mp3'):
                await msg.edit("**Processing metadata...**")
                if await add_metadata(file_path, metadata_path, user_id):
                    if os.path.exists(metadata_path):
                        await cleanup_files(file_path)
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

            sent_message = None
            await msg.edit("**Uploading...**")
            upload_params = {
                'chat_id': message.chat.id,
                'caption': caption,
                'thumb': thumb_path,
                'progress': progress_for_pyrogram,
                'progress_args': ("Uploading...", msg, time.time())
            }

            if media_type == "document" or target_ext not in ('.mp4', '.mkv', '.mp3'):
                sent_message = await attempt_operation(
                    lambda: client.send_document(document=file_path, **upload_params),
                    "upload document"
                )
            elif media_type == "video" or target_ext in ('.mp4', '.mkv'):
                sent_message = await attempt_operation(
                    lambda: client.send_video(video=file_path, **upload_params),
                    "upload video"
                )
            elif media_type == "audio":
                sent_message = await attempt_operation(
                    lambda: client.send_audio(audio=file_path, **upload_params),
                    "upload audio"
                )

            if sent_message:
                await msg.delete()
                await send_to_dump_channel(client, sent_message, user_id)
                logger.info(f"Completed processing for user {user_id}, file {file_id}")
            else:
                await msg.edit("Error: Upload failed.")
        except Exception as e:
            logger.error(f"Processing failed for user {user_id}, file {file_id}: {e}")
            if 'msg' in locals():
                await msg.edit(f"Error: Processing failed: {e}")
            else:
                await message.reply_text(f"Error: Processing failed: {e}")
        finally:
            await cleanup_files(download_path, metadata_path, convert_path, thumb_path)
            renaming_operations.pop(file_id, None)

    # Spawn processing as a separate task
    asyncio.create_task(run_processing())

# Increase Pyrogram concurrency
client = Client(
    "my_bot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN,
    max_concurrent_transmissions=1000  # Allow more simultaneous downloads/uploads
)
