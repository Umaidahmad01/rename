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
from config import Config
import plugins.metadata as metadata_module

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

renaming_operations = {}
user_tasks = {}

SEASON_EPISODE_PATTERNS = [
    (re.compile(r'S(\d+)(?:E|EP)(\d+)'), ('season', 'episode')),
    (re.compile(r'S(\d+)[\s-]*(?:E|EP)(\d+)'), ('season', 'episode')),
    (re.compile(r'Season\s*(\d+)\s*Episode\s*(\d+)', re.IGNORECASE), ('season', 'episode')),
    (re.compile(r'\[S(\d+)\]\[E(\d+)\]'), ('season', 'episode')),
    (re.compile(r'S(\d+)[^\d]*(\d+)'), ('season', 'episode')),
    (re.compile(r'(?:E|EP|Episode)\s*(\d+)', re.IGNORECASE), (None, 'episode')),
    (re.compile(r'\b(\d+)\b'), (None, 'episode'))
]

QUALITY_PATTERNS = [
    (re.compile(r'\b(\d{3,4}[pi])\b', re.IGNORECASE), lambda m: m.group(1)),
    (re.compile(r'\b(4k|2160p)\b', re.IGNORECASE), lambda m: "4k"),
    (re.compile(r'\b(2k|1440p)\b', re.IGNORECASE), lambda m: "2k"),
    (re.compile(r'\b(HDRip|HDTV)\b', re.IGNORECASE), lambda m: m.group(1)),
    (re.compile(r'\b(4kX264|4kx265)\b', re.IGNORECASE), lambda m: m.group(1)),
    (re.compile(r'\[(\d{3,4}[pi])\]', re.IGNORECASE), lambda m: m.group(1))
]

def sanitize_filename(filename, user_handle=None):
    if not filename:
        return "unnamed_file"
    clean = filename
    if user_handle:
        clean = re.sub(r'@(?!' + re.escape(user_handle.lstrip('@')) + r'\b)\w+', '', clean)
    clean = re.sub(r'[^a-zA-Z0-9\s\-\[\]\(\)\.@]', '_', clean)
    clean = re.sub(r'\s+', ' ', clean).strip('_ ')
    clean = clean.replace('..', '.').replace('__', '_')
    return clean[:100]

def extract_season_episode(input_text, rename_mode):
    if not input_text:
        logger.warning(f"No input text for rename_mode {rename_mode}")
        return None, None
    for pattern, (season_group, episode_group) in SEASON_EPISODE_PATTERNS:
        match = pattern.search(input_text)
        if match:
            season = match.group(1) if season_group else None
            episode = match.group(2) if episode_group else match.group(1)
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

async def upscale_video(client, message, scale_factor):
    user_id = message.from_user.id
    telegram_handle = await codeflixbots.get_telegram_handle(user_id)
    if user_id not in user_tasks:
        user_tasks[user_id] = []

    if not message.video and not message.document:
        await message.reply_text("Please send a video to upscale.")
        return

    media = message.video or message.document
    file_id = media.file_id
    file_name = media.file_name or "video.mp4"
    download_path = f"downloads/{file_id}.mp4"
    upscale_path = f"upscale/{file_id}_upscaled.mp4"

    try:
        os.makedirs("downloads", exist_ok=True)
        os.makedirs("upscale", exist_ok=True)

        msg = await message.reply_text("**Downloading video...**")
        download_task = asyncio.create_task(client.download_media(
            media,
            file_name=download_path,
            progress=progress_for_pyrogram,
            progress_args=("Downloading...", msg, time.time())
        ))
        user_tasks[user_id].append(download_task)
        file_path = await download_task

        await msg.edit("**Upscaling video...**")
        ffmpeg = shutil.which('ffmpeg')
        if not ffmpeg:
            raise RuntimeError("FFmpeg not found")
        
        cmd = [
            ffmpeg, '-i', file_path, '-vf', f'scale={scale_factor}', '-c:v', 'libx264',
            '-preset', 'fast', '-c:a', 'copy', '-loglevel', 'error', upscale_path
        ]
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0 or not os.path.exists(upscale_path):
            raise RuntimeError(f"Upscale failed: {stderr.decode()}")

        new_filename = sanitize_filename(f"Upscaled_{file_name}", telegram_handle)
        await msg.edit("**Uploading upscaled video...**")
        upload_task = asyncio.create_task(client.send_document(
            chat_id=message.chat.id,
            document=upscale_path,
            caption=f"**Upscaled: {new_filename}**",
            progress=progress_for_pyrogram,
            progress_args=("Uploading...", msg, time.time())
        ))
        user_tasks[user_id].append(upload_task)
        await upload_task
        await msg.delete()
        await codeflixbots.add_upload(user_id, new_filename)

        caption = f"{new_filename} {telegram_handle or ''}"
        await msg.edit("**Sending to dump channel...**")
        await codeflixbots.send_to_dump_channel(client, upscale_path, caption)

    except Exception as e:
        logger.error(f"Upscale error for user {user_id}: {e}")
        await msg.edit(f"Error: {str(e)}")
        await send_log(client, message.from_user, f"Upscale error: {str(e)}")
    finally:
        await cleanup_files(download_path, upscale_path)
        user_tasks[user_id] = [t for t in user_tasks[user_id] if not t.done()]

async def extract_thumbnail(client, message, timestamp):
    user_id = message.from_user.id
    telegram_handle = await codeflixbots.get_telegram_handle(user_id)
    if user_id not in user_tasks:
        user_tasks[user_id] = []

    if not message.video and not message.document:
        await message.reply_text("Please send a video to extract thumbnail.")
        return

    media = message.video or message.document
    file_id = media.file_id
    file_name = media.file_name or "video.mp4"
    download_path = f"downloads/{file_id}.mp4"
    thumb_path = f"thumbs/{file_id}_thumb.jpg"

    try:
        os.makedirs("downloads", exist_ok=True)
        os.makedirs("thumbs", exist_ok=True)

        msg = await message.reply_text("**Downloading video...**")
        download_task = asyncio.create_task(client.download_media(
            media,
            file_name=download_path,
            progress=progress_for_pyrogram,
            progress_args=("Downloading...", msg, time.time())
        ))
        user_tasks[user_id].append(download_task)
        file_path = await download_task

        await msg.edit("**Extracting thumbnail...**")
        ffmpeg = shutil.which('ffmpeg')
        if not ffmpeg:
            raise RuntimeError("FFmpeg not found")
        
        cmd = [
            ffmpeg, '-i', file_path, '-ss', str(timestamp), '-vframes', '1',
            '-q:v', '2', '-loglevel', 'error', thumb_path
        ]
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0 or not os.path.exists(thumb_path):
            raise RuntimeError(f"Thumbnail extraction failed: {stderr.decode()}")

        new_filename = sanitize_filename(f"Thumb_{os.path.splitext(file_name)[0]}.jpg", telegram_handle)
        await msg.edit("**Uploading thumbnail...**")
        upload_task = asyncio.create_task(client.send_photo(
            chat_id=message.chat.id,
            photo=thumb_path,
            caption=f"**Thumbnail: {new_filename}**"
        ))
        user_tasks[user_id].append(upload_task)
        await upload_task
        await msg.delete()
        await codeflixbots.add_upload(user_id, new_filename)

        caption = f"{new_filename} {telegram_handle or ''}"
        await msg.edit("**Sending to dump channel...**")
        await codeflixbots.send_to_dump_channel(client, thumb_path, caption)

    except Exception as e:
        logger.error(f"Thumbnail error for user {user_id}: {e}")
        await msg.edit(f"Error: {str(e)}")
        await send_log(client, message.from_user, f"Thumbnail error: {str(e)}")
    finally:
        await cleanup_files(download_path, thumb_path)
        user_tasks[user_id] = [t for t in user_tasks[user_id] if not t.done()]

async def process_file(client, message):
    user_id = message.from_user.id
    format_template = await codeflixbots.get_format_template(user_id)
    rename_mode = await codeflixbots.get_user_choice(user_id)
    telegram_handle = await codeflixbots.get_telegram_handle(user_id)

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
                'QUALITY': quality,
                '{telegram_handle}': telegram_handle or ''
            }
            
            new_template = format_template
            for placeholder, value in replacements.items():
                new_template = new_template.replace(placeholder, str(value))
            
            if not new_template.strip():
                new_template = f"file_{user_id}"
            
            ext = os.path.splitext(file_name)[1] or ('.mp4' if media_type == "video" else '.mp3')
            new_filename = sanitize_filename(f"{new_template}{ext}", telegram_handle)
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
                    if await metadata_module.add_metadata(file_path, metadata_path, user_id):
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
                await codeflixbots.add_upload(user_id, new_filename)
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

            await msg.edit("**Sending to dump channel...**")
            caption = f"{new_filename} {telegram_handle or ''}"
            try:
                if os.path.exists(file_path):
                    await codeflixbots.send_to_dump_channel(client, file_path, caption)
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

            if telegram_handle:
                base_name += f" {telegram_handle}"

            extension = file.file_name.split('.')[-1] if '.' in file.file_name else 'bin'
            new_name = sanitize_filename(f"{base_name}.{extension}", telegram_handle)
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
                await codeflixbots.add_upload(user_id, new_name)
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

            logger.info(f"Sending {new_name} to dump
