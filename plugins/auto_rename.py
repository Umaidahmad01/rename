#### LAND UNDER LELE MC####
from helper.database import codeflixbots
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery  # Added CallbackQuery
import os
import subprocess
import re
import json

# Supported formats
SUPPORTED_FORMATS = ["mkv", "mp4", "avi", "mov", "pdf"]

# Resolution mapping
RESOLUTION_MAP = {
    "hdrip": "2160p",
    "2160p": "2160p",
    "fhd": "1080p",
    "1080p": "1080p",
    "hd": "720p",
    "720p": "720p",
    "sd": "480p",
    "480p": "480p"
}

# FFmpeg resolution settings
RESOLUTION_SETTINGS = {
    "2160p": "3840:2160",
    "1080p": "1920:1080",
    "720p": "1280:720",
    "480p": "854:480"
}

# Helper functions for FileStorage
def get_storage_data(client, user_id, key, default=None):
    storage_file = client.storage.file_name  # Get the storage file path
    if os.path.exists(storage_file):
        with open(storage_file, 'r') as f:
            data = json.load(f)
            return data.get(f"{user_id}_{key}", default)
    return default

def set_storage_data(client, user_id, key, value):
    storage_file = client.storage.file_name
    data = {}
    if os.path.exists(storage_file):
        with open(storage_file, 'r') as f:
            data = json.load(f)
    data[f"{user_id}_{key}"] = value
    with open(storage_file, 'w') as f:
        json.dump(data, f)

def delete_storage_data(client, user_id, key):
    storage_file = client.storage.file_name
    if os.path.exists(storage_file):
        with open(storage_file, 'r') as f:
            data = json.load(f)
        data.pop(f"{user_id}_{key}", None)
        with open(storage_file, 'w') as f:
            json.dump(data, f)

# /autorename command
@Client.on_message(filters.command("autorename") & filters.private)
async def autorename_command(client, message):
    if len(message.command) < 2:
        await message.reply_text("Usage: /autorename <pattern>\nExample: /autorename MySeries S{season} E{episode} {quality}.mkv")
        return

    pattern = " ".join(message.command[1:])  # Full pattern lena
    user_id = message.from_user.id

    if "{season}" in pattern or "{episode}" in pattern or "{quality}" in pattern:
        set_storage_data(client, user_id, "pattern", pattern)
        await message.reply_text("Please provide the season number (e.g., 01 for S01):")
        set_storage_data(client, user_id, "state", "awaiting_season")
    else:
        await message.reply_text("Pattern must include {season}, {episode}, or {quality} variables!")

# Handle user input for season, episode, and file
@Client.on_message(filters.text & filters.private)
async def handle_text_input(client, message):
    user_id = message.from_user.id
    state = get_storage_data(client, user_id, "state")

    if state == "awaiting_season":
        season = message.text.strip()
        if not re.match(r"^\d+$", season):
            await message.reply_text("Please enter a valid season number (e.g., 01):")
            return
        set_storage_data(client, user_id, "season", f"{int(season):02d}")  # 2-digit format
        set_storage_data(client, user_id, "state", "awaiting_episode")
        await message.reply_text("Please provide the episode number (e.g., 01 for E01):")

    elif state == "awaiting_episode":
        episode = message.text.strip()
        if not re.match(r"^\d+$", episode):
            await message.reply_text("Please enter a valid episode number (e.g., 01):")
            return
        set_storage_data(client, user_id, "episode", f"{int(episode):02d}")  # 2-digit format
        set_storage_data(client, user_id, "state", "awaiting_file")
        pattern = get_storage_data(client, user_id, "pattern")
        await message.reply_text(f"Please send the file to rename using pattern: {pattern}")

# File handler
@Client.on_message((filters.document | filters.video) & filters.private)
async def handle_file(client, message):
    user_id = message.from_user.id
    pattern = get_storage_data(client, user_id, "pattern")
    season = get_storage_data(client, user_id, "season")
    episode = get_storage_data(client, user_id, "episode")
    state = get_storage_data(client, user_id, "state")

    if state != "awaiting_file" or not pattern:
        await message.reply_text("Please use /autorename <pattern> first and provide season/episode!")
        return

    # File download karna
    file = message.document or message.video
    original_file_path = await client.download_media(file, file_name=f"downloads/original_{file.file_name}")

    # Pattern se new name generate karna
    new_name = pattern
    if "{season}" in new_name:
        new_name = new_name.replace("{season}", season)
    if "{episode}" in new_name:
        new_name = new_name.replace("{episode}", episode)

    # Quality detection
    quality = None
    for keyword, res in RESOLUTION_MAP.items():
        if keyword in new_name.lower():
            quality = res
            break
    if "{quality}" in new_name and quality:
        new_name = new_name.replace("{quality}", quality)
    elif "{quality}" in new_name:
        new_name = new_name.replace("{quality}", "1080p")  # Default quality

    # File format extract karna from pattern
    file_format = new_name.split('.')[-1].lower() if '.' in new_name else "mp4"
    new_file_path = f"downloads/{new_name}"

    # Ensure downloads directory exists
    os.makedirs("downloads", exist_ok=True)

    # Check if file is already in the desired format
    original_extension = file.file_name.split('.')[-1].lower()

    if file_format == "pdf" or (original_extension == file_format and not quality):
        os.rename(original_file_path, new_file_path)
        await message.reply_text(f"File renamed to: {new_name}")
    else:
        try:
            ffmpeg_cmd = ["ffmpeg", "-i", original_file_path]
            if quality:
                res_value = RESOLUTION_SETTINGS[quality]
                ffmpeg_cmd.extend(["-vf", f"scale={res_value}", "-c:a", "copy"])
            else:
                ffmpeg_cmd.extend(["-c:v", "copy", "-c:a", "copy"])
            ffmpeg_cmd.extend(["-y", new_file_path])
            subprocess.run(ffmpeg_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            if not os.path.exists(new_file_path):
                await message.reply_text("Conversion failed. Please try again.")
                return
            await message.reply_text(f"File renamed and converted to: {new_name}" + 
                                    (f" (Resolution: {quality})" if quality else ""))
        except subprocess.CalledProcessError as e:
            await message.reply_text(f"Error during conversion: {e.stderr.decode()}")
            if os.path.exists(original_file_path):
                os.remove(original_file_path)
            return

    # Renamed file upload karna
    await client.send_document(
        chat_id=message.chat.id,
        document=new_file_path,
        file_name=new_name,
        caption=f"Renamed to {new_name}" + (f" (Resolution: {quality})" if quality else "")
    )

    # Cleanup
    if os.path.exists(original_file_path):
        os.remove(original_file_path)
    if os.path.exists(new_file_path):
        os.remove(new_file_path)

    # Clear storage
    delete_storage_data(client, user_id, "pattern")
    delete_storage_data(client, user_id, "season")
    delete_storage_data(client, user_id, "episode")
    delete_storage_data(client, user_id, "state")
    # Send confirmation message with the template in monospaced font
    await message.reply_text(
        f"**🌟 Fantastic! You're ready to auto-rename your files.**\n\n"
        "📩 Simply send the file(s) you want to rename.\n\n"
        f"**Your saved template:** `{format_template}`\n\n"
        "Remember, it might take some time, but I'll ensure your files are renamed perfectly!✨"
    )


@Client.on_message(filters.private & filters.command("setmedia"))
async def set_media_command(client, message):
    """Initiate media type selection with a sleek inline keyboard."""
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📜 Documents", callback_data="setmedia_document")],
        [InlineKeyboardButton("🎬 Videos", callback_data="setmedia_video")],
        [InlineKeyboardButton("🎵 Audio", callback_data="setmedia_audio")],  # Added audio option
    ])

    await message.reply_text(
        "✨ **Choose Your Media Vibe** ✨\n"
        "Select the type of media you'd like to set as your preference:",
        reply_markup=keyboard,
        quote=True
    )

@Client.on_callback_query(filters.regex(r"^setmedia_"))
async def handle_media_selection(client, callback_query: CallbackQuery):
    """Process the user's media type selection with flair and confirmation."""
    user_id = callback_query.from_user.id
    media_type = callback_query.data.split("_", 1)[1].capitalize()  # Extract and capitalize media type

    try:
        await codeflixbots.set_media_preference(user_id, media_type.lower())

        await callback_query.answer(f"Locked in: {media_type} 🎉")
        await callback_query.message.edit_text(
            f"🎯 **Media Preference Updated** 🎯\n"
            f"Your vibe is now set to: **{media_type}** ✅\n"
            f"Ready to roll with your choice!"
        )
    except Exception as e:
        await callback_query.answer("Oops, something went wrong! 😅")
        await callback_query.message.edit_text(
            f"⚠️ **Error Setting Preference** ⚠️\n"
            f"Couldn’t set {media_type} right now. Try again later!\n"
            f"Details: {str(e)}"
        )
