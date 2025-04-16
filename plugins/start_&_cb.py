import random
import asyncio
from PIL import Image
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from helper.database import *
from config import Config, Txt
import logging
from pyrogram.errors import FloodWait, MessageNotModified, ChatAdminRequired
import os

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize MongoDB (already imported as codeflixbots)
db = codeflixbots

# Start Command Handler
@Client.on_message(filters.private & filters.command("start"))
async def start(client, message: Message):
    user = message.from_user
    await db.add_user(client, message)

    # Initial interactive text and sticker sequence
    m = await message.reply_text("ᴋᴏɴɴɪᴄʜɪᴡᴀ..ɪ'ᴍ ᴋᴀɴᴀᴏ!\nᴡᴀɪᴛ ᴀ ᴍᴏᴍᴇɴᴛ. . .")
    await asyncio.sleep(0.4)
    await m.edit_text("🎊")
    await asyncio.sleep(0.5)
    await m.edit_text("⚡")
    await asyncio.sleep(0.5)
    await m.edit_text("ᴀʀᴀ ᴀʀᴀ!...")
    await asyncio.sleep(0.4)
    await m.delete()

    # Send sticker after the text sequence
    await message.reply_sticker("CAACAgUAAxkBAAECroBmQKMAAQ-Gw4nibWoj_pJou2vP1a4AAlQIAAIzDxlVkNBkTEb1Lc4eBA")

    # Define buttons for the start message
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("• ᴍʏ ᴀʟʟ ᴄᴏᴍᴍᴀɴᴅs •", callback_data='help')
        ],
        [
            InlineKeyboardButton('• ᴜᴘᴅᴀᴛᴇs', url='https://t.me/FILE_SHARINGBOTS'),
            InlineKeyboardButton('sᴜᴘᴘᴏʀᴛ •', url='https://t.me/ahss_help_zone')
        ],
        [
            InlineKeyboardButton('• ᴀʙᴏᴜᴛ• ', callback_data='about')
        ]
    ])

    # Send start message with or without picture
    if Config.START_PIC:
        await message.reply_photo(
            Config.START_PIC,
            caption=Txt.START_TXT.format(user.mention),
            reply_markup=buttons
        )
    else:
        await message.reply_text(
            text=Txt.START_TXT.format(user.mention),
            reply_markup=buttons,
            disable_web_page_preview=True
        )

# Help Command Handler
@Client.on_message(filters.private & filters.command("help"))
async def help_command(client, message):
    bot = await client.get_me()
    mention = bot.mention

    await message.reply_text(
        text=Txt.HELP_TXT.format(mention=mention),
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("• ᴀᴜᴛᴏ ʀᴇɴᴀᴍᴇ ғᴏʀᴍᴀᴛ •", callback_data='file_names')],
            [InlineKeyboardButton('• ᴛʜᴜᴍʙɴᴀɪʟ', callback_data='thumbnail'), InlineKeyboardButton('ᴄᴀᴘᴛɪᴏɴ •', callback_data='caption')],
            [InlineKeyboardButton('• ᴍᴇᴛᴀᴅᴀᴛᴀ', callback_data='meta'), InlineKeyboardButton('ᴅᴏɴᴀᴛᴇ •', callback_data='donate')],
            [InlineKeyboardButton('• ʜᴏᴍᴇ', callback_data='home')]
        ])
    )

# Donation Command Handler
@Client.on_message(filters.command("donate"))
async def donation(client, message):
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton(text="ʙᴀᴄᴋ", callback_data="help"), InlineKeyboardButton(text="ᴏᴡɴᴇʀ", url='https://t.me/proobito')]
    ])
    yt = await message.reply_photo(photo='https://envs.sh/ZsI.png?DpE8x=1', caption=Txt.DONATE_TXT, reply_markup=buttons)
    await asyncio.sleep(300)
    await yt.delete()
    await message.delete()

# Premium Command Handler
@Client.on_message(filters.command("premium"))
async def getpremium(bot, message):
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("ᴏᴡɴᴇʀ", url="https://t.me/proobito"), InlineKeyboardButton("ᴄʟᴏsᴇ", callback_data="close")]
    ])
    yt = await message.reply_photo(photo='https://envs.sh/ZsI.png?DpE8x=1', caption=Txt.PREMIUM_TXT, reply_markup=buttons)
    await asyncio.sleep(300)
    await yt.delete()
    await message.delete()

# Plan Command Handler
@Client.on_message(filters.command("plan"))
async def premium(bot, message):
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("sᴇɴᴅ ss", url="https://t.me/proobito"), InlineKeyboardButton("ᴄʟᴏsᴇ", callback_data="close")]
    ])
    yt = await message.reply_photo(photo='https://envs.sh/ZsI.png?DpE8x=1', caption=Txt.PREPLANS_TXT, reply_markup=buttons)
    await asyncio.sleep(300)
    await yt.delete()
    await message.delete()

# Bought Command Handler
@Client.on_message(filters.command("bought") & filters.private)
async def bought(client, message):
    msg = await message.reply('Wait im checking...')
    replied = message.reply_to_message

    if not replied:
        await msg.edit("<b>Please reply with the screenshot of your payment for the premium purchase to proceed.\n\nFor example, first upload your screenshot, then reply to it using the '/bought' command</b>")
    elif replied.photo:
        await client.send_photo(
            chat_id=Config.LOG_CHANNEL,
            photo=replied.photo.file_id,
            caption=f'<b>User - {message.from_user.mention}\nUser id - <code>{message.from_user.id}</code>\nUsername - <code>{message.from_user.username}</code>\nName - <code>{message.from_user.first_name}</code></b>',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Close", callback_data="close_data")]
            ])
        )
        await msg.edit_text('<b>Your screenshot has been sent to Admins</b>')

# Extraction Command Handler
@Client.on_message(filters.command("extraction") & filters.private)
async def extraction_command(client: Client, message: Message) -> None:
    try:
        keyboard = [
            [InlineKeyboardButton("Filename", callback_data="filename")],
            [InlineKeyboardButton("Filecaption", callback_data="filecaption")]
        ]
        await message.reply_text(
            "Choose how to rename the file:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        logging.info(f"Sent extraction options to user {message.from_user.id}")
    except ChatAdminRequired:
        logging.error(f"ChatAdminRequired in extraction_command")
        await message.reply_text("Error: Bot lacks admin rights.")
    except Exception as e:
        logging.error(f"Error in extraction_command: {e}")
        await message.reply_text("Error: Failed to send options.")

# Clear Command Handler
user_tasks = {}  # Track user tasks globally
# Callback Query Handler (Merged for all commands)
@Client.on_callback_query()
async def cb_handler(client, query: CallbackQuery):
    data = query.data
    user_id = query.from_user.id

    logging.info(f"Callback data received: {data}")

    # Handle /extraction callbacks
    if data in ["filename", "filecaption"]:
        try:
            choice = data
            updated_keyboard = [
                [InlineKeyboardButton("Filename ✅" if choice == "filename" else "Filename", callback_data="filename")],
                [InlineKeyboardButton("Filecaption ✅" if choice == "filecaption" else "Filecaption", callback_data="filecaption")]
            ]

            try:
                await query.message.edit_reply_markup(InlineKeyboardMarkup(updated_keyboard))
                logging.info(f"Updated keyboard for user {user_id}")
            except MessageNotModified:
                logging.debug(f"Keyboard unchanged for user {user_id}")
            except ChatAdminRequired:
                logging.error(f"ChatAdminRequired for keyboard update")
                await query.message.reply_text("Error: Bot lacks admin rights.")
                await query.answer("Bot needs admin rights!", show_alert=True)
                return
            except Exception as e:
                logging.error(f"Keyboard update failed for user {user_id}: {e}")
                await query.message.reply_text("Error: Couldn't update buttons.")
                return

            success = await db.set_user_choice(user_id, choice)
            if not success:
                logging.error(f"Failed to save choice '{choice}' for user {user_id}")
                await query.message.reply_text("Error: Couldn't save your choice.")
                await query.answer("Database error!", show_alert=True)
                return

            await query.message.reply_text(
                f"Please send the file to rename using its {choice}."
            )
            await query.answer("Option selected!")
        except ChatAdminRequired:
            logging.error(f"ChatAdminRequired in callback")
            await query.message.reply_text("Error: Bot lacks admin rights.")
            await query.answer("Bot needs admin rights!", show_alert=True)
        except Exception as e:
            logging.error(f"Callback error for user {user_id}: {e}")
            await query.message.reply_text("Error: Something went wrong.")
            await query.answer("Error occurred!", show_alert=True)

    # Handle other callbacks (home, help, etc.)
    elif data == "home":
        await query.message.edit_text(
            text=Txt.START_TXT.format(query.from_user.mention),
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("• ᴍʏ ᴀʟʟ ᴄᴏᴍᴍᴀɴᴅs •", callback_data='help')],
                [InlineKeyboardButton('• ᴜᴘᴅᴀᴛᴇs', url='https://t.me/FILE_SHARINGBOTS'), InlineKeyboardButton('sᴜᴘᴘᴏʀᴛ •', url='https://t.me/CodeflixSupport')],
                [InlineKeyboardButton('• ᴀʙᴏᴜᴛ', callback_data='about'), InlineKeyboardButton('sᴏᴜʀᴄᴇ •', callback_data='source')]
            ])
        )
    elif data == "caption":
        await query.message.edit_text(
            text=Txt.CAPTION_TXT,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("• sᴜᴘᴘᴏʀᴛ", url='https://t.me/ahss_help_zone'), InlineKeyboardButton("ʙᴀᴄᴋ •", callback_data="help")]
            ])
        )
    elif data == "help":
        await query.message.edit_text(
            text=Txt.HELP_TXT.format((await client.get_me()).mention),
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("• ᴀᴜᴛᴏ ʀᴇɴᴀᴍᴇ ғᴏʀᴍᴀᴛ •", callback_data='file_names')],
                [InlineKeyboardButton('• ᴛʜᴜᴍʙɴᴀɪʟ', callback_data='thumbnail'), InlineKeyboardButton('ᴄᴀᴘᴛɪᴏɴ •', callback_data='caption')],
                [InlineKeyboardButton('• ᴍᴇᴛᴀᴅᴀᴛᴀ', callback_data='meta'), InlineKeyboardButton('ᴅᴏɴᴀᴛᴇ •', callback_data='donate')],
                [InlineKeyboardButton('• ʜᴏᴍᴇ', callback_data='home')]
            ])
        )
    elif data == "meta":
        await query.message.edit_text(
            text=Txt.SEND_METADATA,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("• ᴄʟᴏsᴇ", callback_data="close"), InlineKeyboardButton("ʙᴀᴄᴋ •", callback_data="help")]
            ])
        )
    elif data == "donate":
        await query.message.edit_text(
            text=Txt.DONATE_TXT,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("• ʙᴀᴄᴋ", callback_data="help"), InlineKeyboardButton("ᴏᴡɴᴇʀ •", url='https://t.me/i_killed_my_clan')]
            ])
        )
    elif data == "file_names":
        format_template = await db.get_format_template(user_id)
        await query.message.edit_text(
            text=Txt.FILE_NAME_TXT.format(format_template=format_template),
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("• ᴄʟᴏsᴇ", callback_data="close"), InlineKeyboardButton("ʙᴀᴄᴋ •", callback_data="help")]
            ])
        )
    elif data == "thumbnail":
        await query.message.edit_caption(
            caption=Txt.THUMBNAIL_TXT,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("• ᴄʟᴏsᴇ", callback_data="close"), InlineKeyboardButton("ʙᴀᴄᴋ •", callback_data="help")]
            ])
        )
    elif data == "metadata":
        await query.message.edit_caption(
            caption=Txt.SEND_METADATA,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("• ᴄʟᴏsᴇ", callback_data="close"), InlineKeyboardButton("ʙᴀᴄᴋ •", callback_data="help")]
            ])
        )
    elif data == "source":
        await query.message.edit_caption(
            caption=Txt.SOURCE_TXT,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("• ᴄʟᴏsᴇ", callback_data="close"), InlineKeyboardButton("ʙᴀᴄᴋ •", callback_data="home")]
            ])
        )
    elif data == "premiumx":
        await query.message.edit_caption(
            caption=Txt.PREMIUM_TXT,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("• ʙᴀᴄᴋ", callback_data="help"), InlineKeyboardButton("ʙᴜʏ ᴘʀᴇᴍɪᴜᴍ •", url='https://t.me/proobito')]
            ])
        )
    elif data == "plans":
        await query.message.edit_caption(
            caption=Txt.PREPLANS_TXT,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("• ᴄʟᴏsᴇ", callback_data="close"), InlineKeyboardButton("ʙᴜʏ ᴘʀᴇᴍɪᴜᴍ •", url='https://t.me/proobito')]
            ])
        )
    elif data == "about":
        await query.message.edit_text(
            text=Txt.ABOUT_TXT,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("• sᴜᴘᴘᴏʀᴛ", url='https://t.me/ahss_help_zone'), InlineKeyboardButton("ᴄᴏᴍᴍᴀɴᴅs •", callback_data="help")],
                [InlineKeyboardButton("• ᴅᴇᴠᴇʟᴏᴘᴇʀ", url='https://t.me/cosmic_awaken'), InlineKeyboardButton("ɴᴇᴛᴡᴏʀᴋ •", url='https://t.me/society_network')],
                [InlineKeyboardButton("• ʙᴀᴄᴋ •", callback_data="home")]
            ])
        )
    elif data == "close":
        try:
            await query.message.delete()
            await query.message.reply_to_message.delete()
            await query.message.continue_propagation()
        except:
            await query.message.delete()
            await query.message.continue_propagation()

@Client.on_message(filters.command("clear") & filters.private)
async def clear_tasks(client, message):
    user_id = message.from_user.id
    if user_id not in user_tasks or not user_tasks[user_id]:
        await message.reply_text("No active tasks to clear!")
        return
    
    try:
        for task in user_tasks[user_id]:
            if not task.done():
                task.cancel()
        user_tasks[user_id] = []
        await message.reply_text("All your tasks have been cleared!")
        logger.info(f"Cleared all tasks for user {user_id}")
    except Exception as e:
        logger.error(f"Error clearing tasks for user {user_id}: {e}")
        await message.reply_text(f"Failed to clear tasks: {str(e)}")

@Client.on_message(filters.command("setmedia") & filters.private)
async def set_media(client, message):
    user_id = message.from_user.id
    if len(message.command) < 2:
        return await message.reply_text("Please provide a media type, e.g., /setmedia video, /setmedia audio, /setmedia document")
    media_type = message.command[1].lower()
    valid_types = ['video', 'audio', 'document']
    if media_type not in valid_types:
        return await message.reply_text(f"Invalid media type. Choose from: {', '.join(valid_types)}")
    try:
        await codeflixbots.set_media_preference(user_id, media_type)
        await message.reply_text(f"Media preference set to: {media_type} ✅")
        logger.info(f"Set media preference to {media_type} for user {user_id}")
    except Exception as e:
        logger.error(f"Error setting media preference for user {user_id}: {e}")
        await message.reply_text(f"Error setting media preference: {str(e)}")

@Client.on_message(filters.command("resetmedia") & filters.private)
async def reset_media(client, message):
    user_id = message.from_user.id
    try:
        await codeflixbots.reset_media_preference(user_id)
        await message.reply_text("Media preference reset to default ✅")
        logger.info(f"Reset media preference for user {user_id}")
    except Exception as e:
        logger.error(f"Error resetting media preference for user {user_id}: {e}")
        await message.reply_text(f"Error resetting media preference: {str(e)}")

@Client.on_message(filters.command("upscale") & filters.private & filters.photo)
async def upscale_image(client, message):
    user_id = message.from_user.id
    try:
        msg = await message.reply_text("**Processing upscale...**")
        photo_path = f"downloads/{user_id}_upscale_{int(time.time())}.jpg"
        await client.download_media(message.photo, file_name=photo_path)

        img = cv2.imread(photo_path)
        scale_factor = await codeflixbots.get_upscale_factor(user_id) or 2.0
        height, width = img.shape[:2]
        new_size = (int(width * scale_factor), int(height * scale_factor))
        upscaled_img = cv2.resize(img, new_size, interpolation=cv2.INTER_CUBIC)

        upscaled_img = cv2.convertScaleAbs(upscaled_img, alpha=1.1, beta=10)
        upscaled_path = f"downloads/{user_id}_upscaled_{int(time.time())}.jpg"
        cv2.imwrite(upscaled_path, upscaled_img)

        await client.send_photo(
            chat_id=message.chat.id,
            photo=upscaled_path,
            caption="Upscaled image ✅"
        )
        await msg.delete()
        os.remove(photo_path)
        os.remove(upscaled_path)
        logger.info(f"Upscaled image for user {user_id}")
    except Exception as e:
        logger.error(f"Error upscaling image for user {user_id}: {e}")
        await msg.edit(f"Error upscaling image: {str(e)}")

@Client.on_message(filters.command("exthum") & filters.private & filters.video)
async def extract_thumbnail(client, message):
    user_id = message.from_user.id
    try:
        msg = await message.reply_text("**Extracting thumbnail...**")
        video_path = f"downloads/{user_id}_video_{int(time.time())}.mp4"
        thumb_path = f"downloads/{user_id}_thumb_{int(time.time())}.jpg"
        await client.download_media(message.video, file_name=video_path)

        ffmpeg_cmd = [
            "ffmpeg", "-i", video_path, "-ss", "00:00:01", "-vframes", "1",
            "-vf", "scale=320:320:force_original_aspect_ratio=decrease",
            thumb_path, "-y"
        ]
        process = await asyncio.create_subprocess_exec(
            *ffmpeg_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            logger.error(f"FFmpeg error extracting thumbnail: {stderr.decode()}")
            raise RuntimeError("Failed to extract thumbnail")

        await client.send_photo(
            chat_id=message.chat.id,
            photo=thumb_path,
            caption="Extracted thumbnail ✅"
        )
        await msg.delete()
        os.remove(video_path)
        os.remove(thumb_path)
        logger.info(f"Extracted thumbnail for user {user_id}")
    except Exception as e:
        logger.error(f"Error extracting thumbnail for user {user_id}: {e}")
        await msg.edit(f"Error extracting thumbnail: {str(e)}")
        
