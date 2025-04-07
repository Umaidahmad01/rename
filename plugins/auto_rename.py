from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from helper.database import codeflixbots

# Supported formats
SUPPORTED_FORMATS = ["mkv", "mp4", "avi", "mov"]

# /autorename command
@client.on_message(filters.command("autorename") & filters.private)
async def autorename_command(client, message):
    if len(message.command) < 3:
        await message.reply_text("Usage: /autorename <new_name> <format>\nExample: /autorename MyVideo mp4")
        return

    new_name = message.command[1]  # User-specified name
    file_format = message.command[2].lower()  # User-specified format

    if file_format not in SUPPORTED_FORMATS:
        await message.reply_text(f"Unsupported format! Supported formats: {', '.join(SUPPORTED_FORMATS)}")
        return

    # Store the rename details in storage
    client.storage.set(message.from_user.id, "new_name", new_name)
    client.storage.set(message.from_user.id, "file_format", file_format)

    await message.reply_text(f"Please send the file to rename as '{new_name}.{file_format}'.")

# File handler
@client.on_message(filters.document | filters.video & filters.private)
async def handle_file(client, message):
    user_id = message.from_user.id
    new_name = app.storage.get(user_id, "new_name")
    file_format = app.storage.get(user_id, "file_format")

    if not new_name or not file_format:
        await message.reply_text("Please use /autorename <new_name> <format> first.")
        return

    # File download karna
    file = message.document or message.video
    original_file_path = await client.download_media(file, file_name=f"downloads/original_{file.file_name}")

    # New file path with specified name and format
    new_file_path = f"downloads/{new_name}.{file_format}"

    # Ensure downloads directory exists
    os.makedirs("downloads", exist_ok=True)

    try:
        # FFmpeg command to convert file
        subprocess.run([
            "ffmpeg", "-i", original_file_path, "-c:v", "copy", "-c:a", "copy", 
            "-y", new_file_path
        ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # Check if conversion successful
        if os.path.exists(new_file_path):
            await client.send_document(
                chat_id=message.chat.id,
                document=new_file_path,
                file_name=f"{new_name}.{file_format}",
                caption=f"Renamed and converted to {file_format}"
            )
        else:
            await message.reply_text("Conversion failed. Please try again.")

    except subprocess.CalledProcessError as e:
        await message.reply_text(f"Error during conversion: {e.stderr.decode()}")

    # Cleanup
    if os.path.exists(original_file_path):
        os.remove(original_file_path)
    if os.path.exists(new_file_path):
        os.remove(new_file_path)

    # Clear storage
    client.storage.delete(user_id, "new_name")
    client.storage.delete(user_id, "file_format")
    
    format_template = command_parts[1].strip()

    # Save the format template in the database
    await codeflixbots.set_format_template(user_id, format_template)

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
