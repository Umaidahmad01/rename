from pyrogram import Client, filters
from pyrogram.errors import FloodWait
from pyrogram.types import InputMediaDocument, Message 
from PIL import Image
from datetime import datetime
from hachoir.metadata import extractMetadata
from hachoir.parser import createParser
from helper.utils import progress_for_pyrogram, humanbytes, convert
from helper.database import codeflixbots
from config import Config
import os
import time
import re
import ffmpeg
import shutil
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

renaming_operations = {}

# Pattern 1: S01E02 or S01EP02
pattern1 = re.compile(r'S(\d+)(?:E|EP)(\d+)')
# Pattern 2: S01 E02 or S01 EP02 or S01 - E01 or S01 - EP02
pattern2 = re.compile(r'S(\d+)\s*(?:E|EP|-\s*EP)(\d+)')
# Pattern 3: Episode Number After "E" or "EP"
pattern3 = re.compile(r'(?:[([<{]?\s*(?:E|EP)\s*(\d+)\s*[)\]>}]?)')
# Pattern 3_2: episode number after - [hyphen]
pattern3_2 = re.compile(r'(?:\s*-\s*(\d+)\s*)')
# Pattern 4: S2 09 ex.
pattern4 = re.compile(r'S(\d+)[^\d]*(\d+)', re.IGNORECASE)
# Pattern 4_2: Standalone Season Number
pattern4_2 = re.compile(r'S(\d+)', re.IGNORECASE)
# Pattern X: Standalone Episode Number
patternX = re.compile(r'(\d+)')
# QUALITY PATTERNS 
# Pattern 5: 3-4 digits before 'p' as quality
pattern5 = re.compile(r'\b(?:.*?(\d{3,4}[^\dp]*p).*?|.*?(\d{3,4}p))\b', re.IGNORECASE)
# Pattern 6: Find 4k in brackets or parentheses
pattern6 = re.commito/pile(r'[([<{]?\s*4k\s*[)\]>}]?', re.IGNORECASE)
# Pattern 7: Find 2k in brackets or parentheses
pattern7 = re.compile(r'[([<{]?\s*2k\s*[)\]>}]?', re.IGNORECASE)
# Pattern 8: Find HdRip without spaces
pattern8 = re.compile(r'[([<{]?\s*HdRip\s*[)\]>}]?|\bHdRip\b', re.IGNORECASE)
# Pattern 9: Find 4kX264 in brackets or parentheses
pattern9 = re.compile(r'[([<{]?\s*4kX264\s*[)\]>}]?', re.IGNORECASE)
# Pattern 10: Find 4kx265 in brackets or parentheses
pattern10 = re.compile(r'[([<{]?\s*4kx265\s*[)\]>}]?', re.IGNORECASE)
# CHAPTER AND VOLUME PATTERNS
pattern_chapter = re.compile(r'(?:Chapter|Ch\.?|C\.?)\s*(\d+)', re.IGNORECASE)
pattern_volume = re.compile(r'(?:Volume|Vol\.?|V\.?)\s*(\d+)', re.IGNORECASE)

def extract_quality(text):
    match5 = re.search(pattern5, text)
    if match5:
        logger.info("Matched Pattern 5")
        return match5.group(1) or match5.group(2)

    match6 = re.search(pattern6, text)
    if match6:
        logger.info("Matched Pattern 6")
        return "4k"

    match7 = re.search(pattern7, text)
    if match7:
        logger.info("Matched Pattern 7")
        return "2k"

    match8 = re.search(pattern8, text)
    if match8:
        logger.info("Matched Pattern 8")
        return "HdRip"

    match9 = re.search(pattern9, text)
    if match9:
        logger.info("Matched Pattern 9")
        return "4kX264"

    match10 = re.search(pattern10, text)
    if match10:
        logger.info("Matched Pattern 10")
        return "4kx265"

    logger.info("Quality: Unknown")
    return "Unknown"

def extract_episode_number(text):
    match = re.search(pattern1, text)
    if match:
        logger.info("Matched Pattern 1")
        return match.group(2)
    
    match = re.search(pattern2, text)
    if match:
        logger.info("Matched Pattern 2")
        return match.group(2)

    match = re.search(pattern3, text)
    if match:
        logger.info("Matched Pattern 3")
        return match.group(1)

    match = re.search(pattern3_2, text)
    if match:
        logger.info("Matched Pattern 3_2")
        return match.group(1)
        
    match = re.search(pattern4, text)
    if match:
        logger.info("Matched Pattern 4")
        return match.group(2)

    match = re.search(patternX, text)
    if match:
        logger.info("Matched Pattern X")
        return match.group(1)
        
    return None

def extract_season_number(text):
    match = re.search(pattern1, text)
    if match:
        logger.info("Matched Pattern 1 for Season")
        return match.group(1)
    
    match = re.search(pattern2, text)
    if match:
        logger.info("Matched Pattern 2 for Season")
        return match.group(1)

    match = re.search(pattern4, text)
    if match:
        logger.info("Matched Pattern 4 for Season")
        return match.group(1)

    match = re.search(pattern4_2, text)
    if match:
        logger.info("Matched Pattern 4_2 for Season")
        return match.group(1)
        
    return None

def extract_chapter_number(text):
    match = re.search(pattern_chapter, text)
    if match:
        logger.info("Matched Chapter Pattern")
        return match.group(1)
    return None

def extract_volume_number(text):
    match = re.search(pattern_volume, text)
    if match:
        logger.info("Matched Volume Pattern")
        return match.group(1)
    return None

def convert_file(input_path, output_path, output_ext):
    """Convert file to the specified format (MKV, MP4, PDF, CBZ)."""
    input_ext = os.path.splitext(input_path)[1].lower()
    output_ext = output_ext.lower()

    if input_ext == output_ext:
        shutil.copy(input_path, output_path)
        return output_path

    if output_ext in [".mkv", ".mp4"]:
        try:
            stream = ffmpeg.input(input_path)
            stream = ffmpeg.output(stream, output_path, c="copy", f=output_ext[1:])
            ffmpeg.run(stream)
            return output_path
        except Exception as e:
            logger.error(f"FFmpeg conversion error: {e}")
            raise Exception(f"Failed to convert to {output_ext}: {e}")

    elif output_ext == ".pdf":
        if input_ext in [".jpg", ".jpeg", ".png"]:
            try:
                with open(output_path, "wb") as f:
                    f.write(img2pdf.convert(input_path))
                return output_path
            except Exception as e:
                logger.error(f"PDF conversion error: {e}")
                raise Exception(f"Failed to convert to PDF: {e}")
        else:
            raise Exception("PDF conversion only supported for images")

    elif output_ext == ".cbz":
        if input_ext in [".jpg", ".jpeg", ".png"]:
            try:
                with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
                    zf.write(input_path, os.path.basename(input_path))
                return output_path
            except Exception as e:
                logger.error(f"CBZ conversion error: {e}")
                raise Exception(f"Failed to convert to CBZ: {e}")
        else:
            raise Exception("CBZ conversion only supported for images")

    raise Exception(f"Unsupported conversion from {input_ext} to {output_ext}")

async def apply_metadata(file_path, user_id, client):
    """Apply metadata to the file if enabled."""
    metadata_enabled = await codeflixbots.get_metadata(user_id)
    if metadata_enabled != "On":
        return file_path

    metadata = {
        'title': await codeflixbots.get_title(user_id),
        'author': await codeflixbots.get_author(user_id),
        'artist': await codeflixbots.get_artist(user_id),
        'audio': await codeflixbots.get_audio(user_id),
        'subtitle': await codeflixbots.get_subtitle(user_id),
        'video': await codeflixbots.get_video(user_id)
    }

    output_path = file_path.replace(".mkv", "_meta.mkv").replace(".mp4", "_meta.mp4")
    try:
        stream = ffmpeg.input(file_path)
        ffmpeg_args = {}
        for key, value in metadata.items():
            if value:
                ffmpeg_args[f"metadata:{key}"] = value
        stream = ffmpeg.output(stream, output_path, **ffmpeg_args, c="copy")
        ffmpeg.run(stream)
        os.remove(file_path)
        return output_path
    except Exception as e:
        logger.error(f"Metadata application error: {e}")
        return file_path

@Client.on_message(filters.private & (filters.document | filters.video | filters.audio | filters.photo))
async def auto_rename_files(client, message):
    user_id = message.from_user.id
    format_template = await codeflixbots.get_format_template(user_id)
    media_preference = await codeflixbots.get_media_preference(user_id)
    rename_mode = await codeflixbots.get_rename_mode(user_id)

    if not format_template:
        return await message.reply_text("Please Set An Auto Rename Format First Using /autorename")

    # Extract file information
    if message.document:
        file_id = message.document.file_id
        file_name = message.document.file_name
        media_type = media_preference or "document"
        file_size = message.document.file_size
    elif message.video:
        file_id = message.video.file_id
        file_name = message.video.file_name or f"video_{file_id}.mp4"
        media_type = media_preference or "video"
        file_size = message.video.file_size
    elif message.audio:
        file_id = message.audio.file_id
        file_name = message.audio.file_name or f"audio_{file_id}.mp3"
        media_type = media_preference or "audio"
        file_size = message.audio.file_size
    elif message.photo:
        file_id = message.photo.file_id
        file_name = f"photo_{file_id}.jpg"
        media_type = media_preference or "photo"
        file_size = 0  # Photos don't have file_size
    else:
        return await message.reply_text("Unsupported File Type")

    logger.info(f"Processing file: {file_name} for user {user_id}")
    print(f"Original File Name: {file_name}")

    # Check for recent renaming operations
    if file_id in renaming_operations:
        elapsed_time = (datetime.now() - renaming_operations[file_id]).seconds
        if elapsed_time < 10:
            logger.info(f"File {file_id} ignored: recently renamed")
            return

    renaming_operations[file_id] = datetime.now()

    # Determine extraction source (filename or caption)
    source_text = file_name if rename_mode == "filename" else (message.caption or file_name)
    logger.info(f"Extraction Source ({rename_mode}): {source_text}")

    # Extract metadata
    episode_number = extract_episode_number(source_text)
    quality = extract_quality(source_text)
    chapter_number = extract_chapter_number(source_text)
    volume_number = extract_volume_number(source_text)
    season_number = extract_season_number(source_text)

    if quality == "Unknown":
        await message.reply_text("I Was Not Able To Extract The Quality Properly. Renaming As 'Unknown'...")
        del renaming_operations[file_id]
        return

    # Replace placeholders in format template
    format_template = format_template.replace("{episode}", str(episode_number or "Unknown"), 1)
    format_template = format_template.replace("{Episode}", str(episode_number or "Unknown"), 1)
    format_template = format_template.replace("{EPISODE}", str(episode_number or "Unknown"), 1)
    format_template = format_template.replace("{quality}", quality, 1)
    format_template = format_template.replace("{Quality}", quality, 1)
    format_template = format_template.replace("{QUALITY}", quality, 1)
    format_template = format_template.replace("{chapter}", str(chapter_number or "Unknown"), 1)
    format_template = format_template.replace("{Chapter}", str(chapter_number or "Unknown"), 1)
    format_template = format_template.replace("{CHAPTER}", str(chapter_number or "Unknown"), 1)
    format_template = format_template.replace("{volume}", str(volume_number or "Unknown"), 1)
    format_template = format_template.replace("{Volume}", str(volume_number or "Unknown"), 1)
    format_template = format_template.replace("{VOLUME}", str(volume_number or "Unknown"), 1)
    format_template = format_template.replace("{season}", str(season_number or "Unknown"), 1)
    format_template = format_template.replace("{Season}", str(season_number or "Unknown"), 1)
    format_template = format_template.replace("{SEASON}", str(season_number or "Unknown"), 1)

    # Determine output extension from format template
    template_ext = os.path.splitext(format_template)[1].lower()
    if not template_ext:
        template_ext = os.path.splitext(file_name)[1].lower()
    new_file_name = f"{os.path.splitext(format_template)[0]}{template_ext}"
    file_path = f"downloads/{new_file_name}"

    # Download the file
    download_msg = await message.reply_text(text="Trying To Download.....")
    try:
        downloaded_path = await client.download_media(
            message=message,
            file_name=f"downloads/temp_{file_id}{os.path.splitext(file_name)[1]}",
            progress=progress_for_pyrogram,
            progress_args=("Download Started....", download_msg, time.time())
        )
    except Exception as e:
        logger.error(f"Download error for user {user_id}: {e}")
        del renaming_operations[file_id]
        return await download_msg.edit(f"Download Error: {e}")

    # Convert file if necessary
    try:
        converted_path = convert_file(downloaded_path, file_path, template_ext)
    except Exception as e:
        logger.error(f"Conversion error for user {user_id}: {e}")
        os.remove(downloaded_path)
        del renaming_operations[file_id]
        return await download_msg.edit(f"Conversion Error: {e}")

    # Apply metadata if enabled
    final_path = await apply_metadata(converted_path, user_id, client)

    # Extract duration for videos/audios
    duration = 0
    try:
        metadata = extractMetadata(createParser(final_path))
        if metadata and metadata.has("duration"):
            duration = metadata.get("duration").seconds
    except Exception as e:
        logger.error(f"Error getting duration for user {user_id}: {e}")

    # Upload the file
    upload_msg = await download_msg.edit("Trying To Upload.....")
    ph_path = None
    c_caption = await codeflixbots.get_caption(message.chat.id)
    c_thumb = await codeflixbots.get_thumbnail(message.chat.id)

    caption = c_caption.format(
        filename=new_file_name,
        filesize=humanbytes(file_size if file_size else os.path.getsize(final_path)),
        duration=convert(duration)
    ) if c_caption else f"**{new_file_name}**"

    if c_thumb:
        ph_path = await client.download_media(c_thumb)
        logger.info(f"Thumbnail downloaded for user {user_id}: {ph_path}")
    elif media_type == "video" and message.video and message.video.thumbs:
        ph_path = await client.download_media(message.video.thumbs[0].file_id)
    elif media_type == "photo" and message.photo:
        ph_path = await client.download_media(message.photo.file_id)

    if ph_path and template_ext not in [".pdf", ".cbz"]:
        Image.open(ph_path).convert("RGB").save(ph_path)
        img = Image.open(ph_path)
        img.resize((320, 320))
        img.save(ph_path, "JPEG")

    # Log renaming activity
    log_message = (
        f"**File Renamed**\n"
        f"User: {message.from_user.mention} (`{user_id}`)\n"
        f"Original: {file_name}\n"
        f"New: {new_file_name}\n"
        f"Mode: {rename_mode}\n"
        f"Media Type: {media_type}\n"
        f"Size: {humanbytes(file_size if file_size else os.path.getsize(final_path))}"
    )
    try:
        await client.send_message(Config.LOG_CHANNEL, log_message)
        await client.send_message(Config.DUMP_CHANNEL, log_message)
    except Exception as e:
        logger.error(f"Error logging to channels for user {user_id}: {e}")

    try:
        if media_type == "document" or template_ext in [".pdf", ".cbz"]:
            await client.send_document(
                message.chat.id,
                document=final_path,
                thumb=ph_path if template_ext not in [".pdf", ".cbz"] else None,
                caption=caption,
                progress=progress_for_pyrogram,
                progress_args=("Upload Started.....", upload_msg, time.time())
            )
        elif media_type == "video":
            await client.send_video(
                message.chat.id,
                video=final_path,
                caption=caption,
                thumb=ph_path,
                duration=duration,
                progress=progress_for_pyrogram,
                progress_args=("Upload Started.....", upload_msg, time.time())
            )
        elif media_type == "audio":
            await client.send_audio(
                message.chat.id,
                audio=final_path,
                caption=caption,
                thumb=ph_path,
                duration=duration,
                progress=progress_for_pyrogram,
                progress_args=("Upload Started.....", upload_msg, time.time())
            )
        elif media_type == "photo" and template_ext in [".jpg", ".jpeg", ".png"]:
            await client.send_photo(
                message.chat.id,
                photo=final_path,
                caption=caption,
                progress=progress_for_pyrogram,
                progress_args=("Upload Started.....", upload_msg, time.time())
            )
    except Exception as e:
        logger.error(f"Upload error for user {user_id}: {e}")
        os.remove(final_path)
        if ph_path:
            os.remove(ph_path)
        del renaming_operations[file_id]
        return await upload_msg.edit(f"Upload Error: {e}")

    await download_msg.delete()
    os.remove(final_path)
    os.remove(downloaded_path)
    if ph_path:
        os.remove(ph_path)

    del renaming_operations[file_id]
