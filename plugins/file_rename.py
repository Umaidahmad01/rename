import os
import re
import asyncio
import logging
import time
from pyrogram import Client
from pyrogram.types import Message
from config import Config
from helper.database import codeflixbots
from helper.utils import send_log, progress
from PIL import Image, ImageEnhance
from hachoir.metadata import extractMetadata
from hachoir.parser import createParser

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Global semaphore for overall bot concurrency
global_semaphore = asyncio.Semaphore(50)

# Per-user task queues and semaphores
user_task_queues = {}
user_semaphores = {}
user_tasks = {}  # Track tasks for cancellation

async def extract_season_episode(filename: str) -> tuple:
    """Extract season and episode from filename or caption."""
    pattern = r'(?i)S(\d{1,2})E(\d{1,2})|Season\s*(\d{1,2})\s*Episode\s*(\d{1,2})'
    match = re.search(pattern, filename)
    if match:
        groups = match.groups()
        season = groups[0] or groups[2]
        episode = groups[1] or groups[3]
        return f"S{int(season):02d}", f"E{int(episode):02d}"
    return "SUNKNOWN", "EUNKNOWN"

async def extract_thumbnail(file_path: str, output_path: str) -> bool:
    """Extract thumbnail from video file using FFmpeg."""
    cmd = ["ffmpeg", "-i", file_path, "-vframes", "1", "-an", "-s", "1280x720", output_path]
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        if process.returncode == 0:
            logger.info(f"Extracted thumbnail: {output_path}")
            return True
        logger.error(f"FFmpeg thumbnail extraction error: {stderr.decode()}")
        return False
    except Exception as e:
        logger.error(f"Error extracting thumbnail: {e}")
        return False

async def convert_to_format(file_path: str, target_ext: str, convert_to_mkv: bool) -> str:
    """Convert file to target extension (or MKV if enabled) using FFmpeg with stream copying."""
    if convert_to_mkv and file_path.lower().endswith(".mp4"):
        target_ext = "mkv"
    if file_path.lower().endswith(f".{target_ext}"):
        return file_path  # No conversion needed
    output_path = file_path.rsplit(".", 1)[0] + f".{target_ext}"
    cmd = ["ffmpeg", "-i", file_path, "-c:v", "copy", "-c:a", "copy", output_path]
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        if process.returncode == 0:
            os.remove(file_path)
            logger.info(f"Converted {file_path} to {output_path}")
            return output_path
        logger.error(f"FFmpeg conversion error: {stderr.decode()}")
        return file_path
    except Exception as e:
        logger.error(f"Error converting to {target_ext}: {e}")
        return file_path

async def add_metadata(file_path: str, metadata: dict, thumbnail_path: str = None) -> str:
    """Add metadata and thumbnail to the file using FFmpeg."""
    output_path = file_path.rsplit(".", 1)[0] + "_metadata." + file_path.rsplit(".", 1)[1]
    cmd = ["ffmpeg", "-i", file_path, "-c", "copy", "-map", "0"]
    if thumbnail_path and os.path.exists(thumbnail_path):
        cmd.extend(["-disposition:v:1", "attached_pic", "-i", thumbnail_path, "-map", "1"])
    for key, value in metadata.items():
        if value:
            cmd.extend([f"-metadata", f"{key}={value}"])
    cmd.append(output_path)
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        if process.returncode == 0:
            os.remove(file_path)
            return output_path
        logger.error(f"FFmpeg error for {file_path}: {stderr.decode()}")
        return file_path
    except Exception as e:
        logger.error(f"Error adding metadata to {file_path}: {e}")
        return file_path

async def upscale_image(file_path: str, output_path: str) -> bool:
    """Enhance image quality using PIL."""
    try:
        with Image.open(file_path) as img:
            # Enhance sharpness and contrast
            img = ImageEnhance.Sharpness(img).enhance(2.0)
            img = ImageEnhance.Contrast(img).enhance(1.5)
            img.save(output_path, quality=95)
        logger.info(f"Upscaled image: {output_path}")
        return True
    except Exception as e:
        logger.error(f"Error upscaling image: {e}")
        return False

async def enhanced_progress(current: int, total: int, message: Message, action: str, start_time: float):
    """Enhanced progress bar with file size and estimated time."""
    percentage = (current / total) * 100
    elapsed_time = time.time() - start_time
    speed = current / elapsed_time if elapsed_time > 0 else 0
    eta = (total - current) / speed if speed > 0 else 0
    file_size_mb = total / (1024 * 1024)
    progress_bar = "#" * int(percentage // 10) + "-" * (10 - int(percentage // 10))
    text = (
        f"{action} [{progress_bar}] {percentage:.1f}%\n"
        f"Size: {file_size_mb:.2f} MB | Speed: {speed / (1024 * 1024):.2f} MB/s\n"
        f"ETA: {int(eta)}s"
    )
    try:
        await message.edit_text(text)
    except Exception:
        pass

async def process_file(client: Client, message: Message):
    """Process a single file: queue it for the user and handle download/upload."""
    user_id = message.from_user.id
    start_time = time.time()

    # Initialize user queue and semaphore if not exists
    if user_id not in user_task_queues:
        user_task_queues[user_id] = asyncio.PriorityQueue()
        user_semaphores[user_id] = asyncio.Semaphore(2)  # Allow 2 concurrent downloads per user
        user_tasks[user_id] = []

    # Check if user is premium for priority
    is_premium = await codeflixbots.get_metadata(user_id) == "Premium"
    priority = 1 if is_premium else 2  # Lower number = higher priority

    # Add task to user's queue
    task_id = id(message)
    await user_task_queues[user_id].put((priority, message))
    user_tasks[user_id].append(task_id)
    logger.info(f"Added task {task_id} for user {user_id} to queue. Queue size: {user_task_queues[user_id].qsize()}")

    async def process_user_tasks():
        """Process all tasks in the user's queue."""
        while not user_task_queues[user_id].empty():
            async with global_semaphore:
                async with user_semaphores[user_id]:
                    priority, task_message = await user_task_queues[user_id].get()
                    try:
                        await process_single_task(client, task_message)
                    except Exception as e:
                        logger.error(f"Error processing task for user {user_id}: {e}")
                        await send_log(client, f"Error processing file for user {user_id}: {e}")
                    finally:
                        user_task_queues[user_id].task_done()
                        if id(task_message) in user_tasks[user_id]:
                            user_tasks[user_id].remove(id(task_message))
                        logger.info(f"Completed task for user {user_id}. Queue size: {user_task_queues[user_id].qsize()}")

    async def process_single_task(client: Client, message: Message):
        """Process a single task: download, convert, rename, add metadata, and upload."""
        user_id = message.from_user.id
        task_id = id(message)
        media = message.document or message.video or message.audio
        if not media:
            await send_log(client, f"No valid media found for user {user_id}")
            return

        # Fetch user settings from database
        rename_mode = await codeflixbots.get_user_choice(user_id) or "filename"
        custom_suffix = await codeflixbots.get_custom_suffix(user_id) or "Finished_Society"
        format_template = await codeflixbots.get_format_template(user_id)
        metadata_enabled = await codeflixbots.get_metadata(user_id) == "On"
        convert_to_mkv = await codeflixbots.get_convert_to_mkv(user_id)

        # Determine file name and path
        file_name = getattr(media, "file_name", None) or f"media_{user_id}_{int(time.time())}"
        file_path = f"downloads/{user_id}/{file_name}"
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # Download file
        logger.info(f"Downloading file for user {user_id}: {file_name}")
        try:
            await client.download_media(
                message=message,
                file_name=file_path,
                progress=enhanced_progress,
                progress_args=(message, "Downloading", start_time)
            )
        except Exception as e:
            logger.error(f"Download failed for user {user_id}: {e}")
            await send_log(client, f"Download failed for user {user_id}: {e}")
            return

        # Determine target extension
        original_ext = file_path.rsplit(".", 1)[1].lower() if "." in file_path else "mp4"
        target_ext = "mkv" if convert_to_mkv else original_ext

        # Convert to target format
        file_path = await convert_to_format(file_path, target_ext, convert_to_mkv)

        # Extract metadata for renaming
        title = "Unknown_Title"
        season, episode = "SUNKNOWN", "EUNKNOWN"
        quality = "UNKNOWN"

        if rename_mode == "filename":
            title = file_name.rsplit(".", 1)[0]
            season, episode = await extract_season_episode(file_name)
        elif rename_mode == "filecaption" and message.caption:
            title = message.caption
            season, episode = await extract_season_episode(message.caption)

        # Extract quality from file metadata
        parser = createParser(file_path)
        if parser:
            try:
                metadata = extractMetadata(parser)
                if metadata and metadata.has("width"):
                    quality = str(metadata.get("width")) + "p"
            finally:
                parser.close()

        # Generate new file name
        new_name = format_template or f"{title}_{season}{episode}_{quality}_{custom_suffix}"
        new_name = re.sub(r'[^\w\s-@]', '', new_name).replace(' ', '_')  # Sanitize filename
        new_file_path = f"downloads/{user_id}/{new_name}.{target_ext}"

        # Apply metadata and thumbnail if enabled
        if metadata_enabled:
            metadata_dict = {
                "title": await codeflixbots.get_title(user_id),
                "artist": await codeflixbots.get_artist(user_id),
                "author": await codeflixbots.get_author(user_id),
                "video_title": await codeflixbots.get_video(user_id),
                "audio_title": await codeflixbots.get_audio(user_id),
                "subtitle": await codeflixbots.get_subtitle(user_id),
                "caption": await codeflixbots.get_caption(user_id)
            }
            thumbnail_path = await codeflixbots.get_thumbnail(user_id)
            new_file_path = await add_metadata(file_path, metadata_dict, thumbnail_path)
            logger.info(f"Applied metadata for user {user_id}: {new_file_path}")

        # Rename file
        try:
            os.rename(file_path, new_file_path)
        except Exception as e:
            logger.error(f"Error renaming file for user {user_id}: {e}")
            await send_log(client, f"Error renaming file for user {user_id}: {e}")
            return

        # Upload immediately
        logger.info(f"Uploading file for user {user_id}: {new_file_path}")
        try:
            await client.send_document(
                chat_id=user_id,
                document=new_file_path,
                caption=new_name,
                progress=enhanced_progress,
                progress_args=(message, "Uploading", start_time)
            )
            logger.info(f"Uploaded to user {user_id} in {time.time() - start_time:.2f}s")
        except Exception as e:
            logger.error(f"Upload failed for user {user_id}: {e}")
            await send_log(client, f"Upload failed for user {user_id}: {e}")
        finally:
            # Clean up
            if os.path.exists(new_file_path):
                os.remove(new_file_path)
            if os.path.exists(file_path) and file_path != new_file_path:
                os.remove(file_path)
            await send_log(client, f"Processed file for user {user_id}: {new_name}")

    # Start processing user tasks
    asyncio.create_task(process_user_tasks())

async def cancel_tasks(client: Client, message: Message):
    """Cancel all queued tasks for the user."""
    user_id = message.from_user.id
    if user_id in user_task_queues and user_task_queues[user_id].qsize() > 0:
        # Clear queue
        while not user_task_queues[user_id].empty():
            user_task_queues[user_id].get_nowait()
            user_task_queues[user_id].task_done()
        user_tasks[user_id].clear()
        await message.reply_text("All queued tasks have been cancelled.")
        logger.info(f"Cancelled all tasks for user {user_id}")
    else:
        await message.reply_text("No tasks are currently queued.")
        logger.info(f"No tasks to cancel for user {user_id}")

async def extract_thumbnail_command(client: Client, message: Message):
    """Extract thumbnail from a video file."""
    user_id = message.from_user.id
    media = message.document or message.video
    if not media:
        await message.reply_text("Please send a video file to extract thumbnail.")
        return

    file_name = getattr(media, "file_name", None) or f"thumb_{user_id}_{int(time.time())}.jpg"
    file_path = f"downloads/{user_id}/{file_name}"
    thumb_path = f"downloads/{user_id}/thumbnail_{user_id}.jpg"
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    # Download video
    await client.download_media(message=message, file_name=file_path)
    if await extract_thumbnail(file_path, thumb_path):
        await client.send_photo(user_id, thumb_path, caption="Extracted Thumbnail")
        await codeflixbots.set_thumbnail(user_id, thumb_path)
        logger.info(f"Thumbnail extracted and set for user {user_id}")
    else:
        await message.reply_text("Failed to extract thumbnail.")
    if os.path.exists(file_path):
        os.remove(file_path)

async def upscale_image_command(client: Client, message: Message):
    """Upscale photo quality."""
    user_id = message.from_user.id
    media = message.photo
    if not media:
        await message.reply_text("Please send a photo to upscale.")
        return

    file_name = f"photo_{user_id}_{int(time.time())}.jpg"
    file_path = f"downloads/{user_id}/{file_name}"
    upscaled_path = f"downloads/{user_id}/upscaled_{file_name}"
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    # Download photo
    await client.download_media(message=message, file_name=file_path)
    if await upscale_image(file_path, upscaled_path):
        await client.send_photo(user_id, upscaled_path, caption="Upscaled Photo")
        logger.info(f"Upscaled photo for user {user_id}")
    else:
        await message.reply_text("Failed to upscale photo.")
    if os.path.exists(file_path):
        os.remove(file_path)
    if os.path.exists(upscaled_path):
        os.remove(upscaled_path)

async def set_media_command(client: Client, message: Message):
    """Set custom metadata for a user."""
    user_id = message.from_user.id
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply_text("Usage: /setmedia <key>=<value> (e.g., title=MyShow)")
        return

    key_value = args[1].split("=", 1)
    if len(key_value) != 2:
        await message.reply_text("Invalid format. Use: /setmedia key=value")
        return

    key, value = key_value
    valid_keys = ["title", "artist", "author", "video_title", "audio_title", "subtitle", "caption"]
    if key not in valid_keys:
        await message.reply_text(f"Invalid key. Choose from: {', '.join(valid_keys)}")
        return

    try:
        if key == "title":
            await codeflixbots.set_title(user_id, value)
        elif key == "artist":
            await codeflixbots.set_artist(user_id, value)
        elif key == "author":
            await codeflixbots.set_author(user_id, value)
        elif key == "video_title":
            await codeflixbots.set_video(user_id, value)
        elif key == "audio_title":
            await codeflixbots.set_audio(user_id, value)
        elif key == "subtitle":
            await codeflixbots.set_subtitle(user_id, value)
        elif key == "caption":
            await codeflixbots.set_caption(user_id, value)
        await message.reply_text(f"Set {key} to '{value}' for your media.")
        logger.info(f"Set {key}='{value}' for user {user_id}")
    except Exception as e:
        await message.reply_text(f"Error setting {key}: {e}")
        logger.error(f"Error setting {key} for user {user_id}: {e}")

async def toggle_mkv_command(client: Client, message: Message):
    """Toggle MP4 to MKV conversion for a user."""
    user_id = message.from_user.id
    current_status = await codeflixbots.get_convert_to_mkv(user_id)
    new_status = not current_status
    try:
        await codeflixbots.set_convert_to_mkv(user_id, new_status)
        status_text = "enabled" if new_status else "disabled"
        await message.reply_text(f"MP4 to MKV conversion {status_text}.")
        logger.info(f"Set convert_to_mkv to {new_status} for user {user_id}")
    except Exception as e:
        await message.reply_text(f"Error toggling MKV conversion: {e}")
        logger.error(f"Error toggling convert_to_mkv for user {user_id}: {e}")
