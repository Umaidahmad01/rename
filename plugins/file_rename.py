import logging
import os
import asyncio
import re
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait
from PIL import Image
import cv2
import zipfile
import ffmpeg
import PyPDF2
from config import Config
from database import codeflixbots

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

METADATA_PATTERNS = [
    (r'S(\d+)(?:E|EP|_|\s)(\d+)', ('season', 'episode')),
    (r'Season\s*(\d+)\s*Episode\s*(\d+)', ('season', 'episode')),
    (r'\[S(\d+)\]\[E(\d+)\]', ('season', 'episode')),
    (r'S(\d+)[^\d]*(\d+)', ('season', 'episode')),
    (r'(?:Vol|Volume|V)\s*(\d+)', ('volume', None)),
    (r'(?:Ch|Chapter|C)\s*(\d+)', (None, 'chapter')),
    (r'V(\d+)[^\d]*C(\d+)', ('volume', 'chapter')),
    (r'Volume\s*(\d+)\s*Chapter\s*(\d+)', ('volume', 'chapter')),
    (r'(?:E|EP|Episode)\s*(\d+)', (None, 'episode')),
    (r'\b(\d+)\b', (None, 'episode'))
]

QUALITY_PATTERNS = [
    (r'\b(\d{3,4}[pi])\b', lambda m: m.group(1).upper()),
    (r'\b(4k|2160p)\b', lambda m: "4K"),
    (r'\b(2k|1440p)\b', lambda m: "2K"),
    (r'\b(HDRip|HDTV|WebRip|BluRay)\b', lambda m: m.group(1).upper()),
    (r'\b(4kX264|4kX265|X264|X265|X26|DD\s*5\.1)\b', lambda m: "X264" if m.group(1).upper() == "X26" else m.group(1).upper()),
    (r'\[(\d{3,4}[pi])\]', lambda m: m.group(1).upper())
]

async def is_authorized(user_id: int) -> bool:
    return user_id in Config.AUTH_USERS

async def extract_metadata(input_text, rename_mode=None):
    if not input_text:
        return None, None, "01", "01", "Unknown_Title"
    input_text = str(input_text)
    
    title_match = re.match(r'^(.*?)(?:S\d+|Season|E\d+|Episode|\d{3,4}[pi]|WebRip|BluRay|Hin\s*Eng|DD\s*5\.1|\[|$)', input_text, re.IGNORECASE)
    title = title_match.group(1).strip().replace('.', ' ').title() if title_match else "Unknown_Title"
    if title:
        title = re.sub(r'\s+', ' ', title).strip()
    
    patterns = [(re.compile(p, re.IGNORECASE), k) for p, k in METADATA_PATTERNS]
    
    if rename_mode:
        for pattern, (key1, key2) in patterns:
            match = pattern.search(rename_mode)
            if match:
                if key1 == 'volume':
                    volume = match.group(1).zfill(2)
                    chapter = match.group(2).zfill(2) if key2 == 'chapter' and len(match.groups()) >= 2 else "01"
                    return volume, chapter, "01", "01", title
                elif key1 == 'season':
                    season = match.group(1).zfill(2)
                    episode = match.group(2).zfill(2) if key2 == 'episode' and len(match.groups()) >= 2 else "01"
                    return None, None, season, episode, title
                elif key2 == 'chapter':
                    chapter = match.group(1).zfill(2)
                    return None, chapter, "01", "01", title
                elif key2 == 'episode':
                    episode = match.group(1).zfill(2)
                    return None, None, "01", episode, title

    for pattern, (key1, key2) in patterns:
        match = pattern.search(input_text)
        if match:
            if key1 == 'volume':
                volume = match.group(1).zfill(2)
                chapter = match.group(2).zfill(2) if key2 == 'chapter' and len(match.groups()) >= 2 else "01"
                return volume, chapter, "01", "01", title
            elif key1 == 'season':
                season = match.group(1).zfill(2)
                episode = match.group(2).zfill(2) if key2 == 'episode' and len(match.groups()) >= 2 else "01"
                return None, None, season, episode, title
            elif key2 == 'chapter':
                chapter = match.group(1).zfill(2)
                return None, chapter, "01", "01", title
            elif key2 == 'episode':
                episode = match.group(1).zfill(2)
                return None, None, "01", episode, title
    return None, None, "01", "01", title

async def extract_quality(input_text):
    if not input_text:
        return "720P"
    patterns = [(re.compile(p, re.IGNORECASE), e) for p, e in QUALITY_PATTERNS]
    for pattern, extractor in patterns:
        match = pattern.search(input_text)
        if match:
            return extractor(match)
    return "720P"

async def generate_filename(user_id: int, file_type: str, original_name: str) -> str:
    template = await codeflixbots.get_format_template(user_id)
    rename_mode = await codeflixbots.get_user_choice(user_id)
    if not template:
        template = "[AS] [Vol{volume}-Ch{chapter}] {title} [{quality}]"
    volume, chapter, season, episode, title = await extract_metadata(original_name, rename_mode)
    quality = await extract_quality(original_name)
    
    title = title or "Unknown_Title"
    volume = volume or "01"
    chapter = chapter or "01"
    season = season or "01"
    episode = episode or "01"
    
    ext = {
        "video/mp4": ".mp4",
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "application/zip": ".cbz",
        "application/pdf": ".pdf"
    }.get(file_type, ".pdf")
    
    filename = template.format(
        volume=volume,
        chapter=chapter,
        season=season,
        episode=episode,
        title=title,
        quality=quality
    ) + ext
    return filename[:200]

async def apply_metadata(file_path: str, user_id: int):
    if await codeflixbots.get_metadata_enabled(user_id) != "On":
        return
    metadata = {}
    for field in ["title", "artist", "author"]:
        value = await codeflixbots.get_metadata_field(user_id, field)
        if value:
            metadata[field] = value
    if not metadata:
        metadata["title"] = "Animes_Cruise"
    try:
        if file_path.endswith(".pdf"):
            reader = PyPDF2.PdfReader(file_path)
            writer = PyPDF2.PdfWriter()
            for page in reader.pages:
                writer.add_page(page)
            writer.add_metadata(metadata)
            temp_path = f"temp_{file_path}"
            with open(temp_path, "wb") as f:
                writer.write(f)
            os.rename(temp_path, file_path)
            logger.info(f"Applied metadata to {file_path}: {metadata}")
        elif file_path.endswith(".mp4"):
            stream = ffmpeg.input(file_path)
            for key, value in metadata.items():
                stream = ffmpeg.output(
                    stream, f"temp_{file_path}",
                    **{f"metadata:{key}": value},
                    c="copy"
                )
            ffmpeg.run(stream, overwrite_output=True)
            os.rename(f"temp_{file_path}", file_path)
            logger.info(f"Applied metadata to {file_path}: {metadata}")
    except Exception as e:
        logger.error(f"Error applying metadata to {file_path}: {e}")

async def extract_thumbnail(file_path: str, user_id: int) -> str:
    timestamp = await codeflixbots.get_exthum_timestamp(user_id) or 1.0
    thumb_path = f"downloads/thumb_{user_id}.jpg"
    try:
        os.makedirs("downloads", exist_ok=True)
        if file_path.endswith(".cbz"):
            with zipfile.ZipFile(file_path, 'r') as zf:
                images = [f for f in zf.namelist() if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
                if images:
                    with zf.open(images[0]) as img_file:
                        img = Image.open(img_file)
                        img.thumbnail((200, 200))
                        img.save(thumb_path, "JPEG")
        elif file_path.endswith(".mp4"):
            cap = cv2.VideoCapture(file_path)
            cap.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000)
            ret, frame = cap.read()
            if ret:
                img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                img.thumbnail((200, 200))
                img.save(thumb_path, "JPEG")
            cap.release()
        elif file_path.endswith((".png", ".jpg")):
            img = Image.open(file_path)
            img.thumbnail((200, 200))
            img.save(thumb_path, "JPEG")
        elif file_path.endswith(".pdf"):
            from pdf2image import convert_from_path
            images = convert_from_path(file_path, first_page=1, last_page=1)
            if images:
                img = images[0]
                img.thumbnail((200, 200))
                img.save(thumb_path, "JPEG")
        else:
            return None
        logger.info(f"Extracted thumbnail for user {user_id}: {thumb_path}")
        return thumb_path
    except Exception as e:
        logger.error(f"Error extracting thumbnail for user {user_id}: {e}")
        return None

async def upscale_image(file_path: str, user_id: int) -> str:
    scale = await codeflixbots.get_upscale_scale(user_id)
    factor = float(scale.split(":")[0]) if ":" in scale else 2.0
    output_path = f"downloads/upscaled_{user_id}.png"
    try:
        if file_path.endswith(".pdf"):
            from pdf2image import convert_from_path
            images = convert_from_path(file_path, first_page=1, last_page=1)
            if not images:
                raise ValueError("Failed to extract PDF page")
            img = cv2.cvtColor(np.array(images[0]), cv2.COLOR_RGB2BGR)
        else:
            img = cv2.imread(file_path)
        if img is None:
            raise ValueError("Failed to load image")
        height, width = img.shape[:2]
        new_size = (int(width * factor), int(height * factor))
        upscaled = cv2.resize(img, new_size, interpolation=cv2.INTER_CUBIC)
        cv2.imwrite(output_path, upscaled)
        logger.info(f"Upscaled image for user {user_id}: {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"Error upscaling image for user {user_id}: {e}")
        return None

async def cleanup_files(*paths):
    for path in paths:
        try:
            if path and os.path.exists(path):
                os.remove(path)
        except Exception as e:
            logger.error(f"Error removing {path}: {e}")

@Client.on_message(filters.command("settemplate") & filters.private)
async def set_template(client, message):
    user_id = message.from_user.id
    if not await is_authorized(user_id):
        await message.reply("Unauthorized!")
        return
    if len(message.command) < 2:
        await message.reply("Please provide a template, e.g., /settemplate [AS] [Vol{volume}-Ch{chapter}] {title} [{quality}].pdf")
        return
    template = " ".join(message.command[1:])
    if await codeflixbots.set_format_template(user_id, template):
        await message.reply(f"Template set to: {template}")
    else:
        await message.reply("Failed to set template.")

@Client.on_message((filters.document | filters.video | filters.photo) & filters.private)
async def process_file(client: Client, message: Message):
    user_id = message.from_user.id
    if not await is_authorized(user_id):
        await message.reply("Unauthorized!")
        return

    file = message.document or message.video or message.photo
    file_type = file.mime_type or "application/pdf"
    original_name = file.file_name or f"file_{user_id}"
    file_path = f"downloads/{user_id}_{original_name}"
    os.makedirs("downloads", exist_ok=True)

    msg = await message.reply("**Downloading...**")
    thumb_path = None
    new_file_path = None

    try:
        await message.download(file_path)
        logger.info(f"Downloaded file for user {user_id}: {file_path}")

        media_preference = await codeflixbots.get_media_preference(user_id)
        if media_preference and media_preference not in file_type:
            await msg.edit(f"Your media preference is set to '{media_preference}'. Please upload a {media_preference} file or change it with /setmedia.")
            return
        await apply_metadata(file_path, user_id)

        if await codeflixbots.get_exthum_timestamp(user_id) is not None:
            await msg.edit("**Extracting thumbnail...**")
            thumb_path = await extract_thumbnail(file_path, user_id)

        if file_type in ["image/png", "image/jpeg", "application/pdf"] and await codeflixbots.get_upscale_scale(user_id) != "2:2":
            await msg.edit("**Upscaling image...**")
            file_path = await upscale_image(file_path, user_id) or file_path

        await msg.edit("**Renaming file...**")
        new_filename = await generate_filename(user_id, file_type, original_name)
        new_file_path = f"downloads/{new_filename}"
        os.rename(file_path, new_file_path)

        await msg.edit("**Uploading...**")
        if media_preference == "video":
            await client.send_video(
                chat_id=message.chat.id,
                video=new_file_path,
                caption=new_filename,
                thumb=thumb_path
            )
        elif media_preference == "photo":
            await client.send_photo(
                chat_id=message.chat.id,
                photo=new_file_path,
                caption=new_filename
            )
        else:
            await client.send_document(
                chat_id=message.chat.id,
                document=new_file_path,
                file_name=new_filename,
                caption=new_filename,
                thumb=thumb_path
            )

        logger.info(f"Processed file for user {user_id}: {new_filename}")
        await msg.edit("File processed successfully!")

    except FloodWait as fw:
        logger.warning(f"FloodWait for user {user_id}: {fw.value}s")
        await asyncio.sleep(fw.value)
        await msg.edit("Rate limit hit, please try again later.")
    except Exception as e:
        logger.error(f"Error processing file for user {user_id}: {e}")
        await msg.edit("Failed to process file.")
    finally:
        await cleanup_files(file_path, new_file_path, thumb_path)
