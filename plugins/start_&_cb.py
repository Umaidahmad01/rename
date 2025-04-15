import random
import asyncio
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
@Client.on_message(filters.command("clear") & filters.private)
async def clear_tasks(client: Client, message: Message) -> None:
    user_id = message.from_user.id
    logging.info(f"Clearing tasks for user {user_id}")
    try:
        if user_id in user_tasks:
            tasks = user_tasks[user_id]
            for task in tasks:
                if not task.done():
                    task.cancel()
            user_tasks[user_id] = []
            logging.info(f"Cleared {len(tasks)} tasks for user {user_id}")

        await db.delete_user_choice(user_id)
        await message.reply_text("All ongoing tasks and settings cleared!")
    except ChatAdminRequired:
        logging.error(f"ChatAdminRequired in clear")
        await message.reply_text("Error: Bot lacks admin rights.")
    except Exception as e:
        logging.error(f"Error clearing tasks for user {user_id}: {e}")
        await message.reply_text("Error: Couldn't clear tasks.")

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
    elif data == "metadatax":
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


@Client.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message) -> None:
    user_id = message.from_user.id
    try:
        await message.reply_text(
            Config.START_MESSAGE.format(
                first_name=message.from_user.first_name,
                username=message.from_user.username or "None",
                mention=message.from_user.mention,
                id=user_id
            ),
            disable_web_page_preview=True
        )
        await codeflixbots.add_user(client, message)
        logger.info(f"Start command by user {user_id}")
        await send_log(client, message.from_user, "Started bot")
    except Exception as e:
        logger.error(f"Error in start_command: {e}")
        await message.reply_text("Error: Failed to start.")
        await send_log(client, message.from_user, f"Start error: {str(e)}")

@Client.on_message(filters.command("extraction") & filters.private)
async def extraction_command(client: Client, message: Message) -> None:
    try:
        keyboard = [
            [InlineKeyboardButton("Filename", callback_data="extract_filename")],
            [InlineKeyboardButton("Filecaption", callback_data="extract_filecaption")]
        ]
        await message.reply_text(
            "Choose how to rename the file:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        logger.info(f"Sent extraction options to user {message.from_user.id}")
        await send_log(client, message.from_user, "Started /extraction command")
    except ChatAdminRequired:
        logger.error(f"ChatAdminRequired in extraction_command")
        await message.reply_text("Error: Bot lacks admin rights.")
        await send_log(client, message.from_user, "Extraction command failed: Bot lacks admin rights")
    except Exception as e:
        logger.error(f"Error in extraction_command: {e}")
        await message.reply_text("Error: Failed to send options.")
        await send_log(client, message.from_user, f"Extraction command error: {str(e)}")

@Client.on_message(filters.command("settings") & filters.private)
async def settings_command(client: Client, message: Message) -> None:
    user_id = message.from_user.id
    try:
        metadata_enabled = await codeflixbots.get_metadata(user_id)
        telegram_handle = await codeflixbots.get_telegram_handle(user_id) or "Not set"
        upscale_scale = await codeflixbots.get_upscale_scale(user_id)
        keyboard = [
            [InlineKeyboardButton(f"Metadata: {'ON' if metadata_enabled else 'OFF'}", callback_data="settings_toggle_metadata")],
            [InlineKeyboardButton("Set Metadata", callback_data="settings_set_metadata")],
            [InlineKeyboardButton(f"Telegram Handle: {telegram_handle}", callback_data="settings_set_handle")],
            [InlineKeyboardButton(f"Upscale Scale: {upscale_scale}", callback_data="settings_set_upscale")],
            [InlineKeyboardButton("My Commands", callback_data="settings_mycmd"),
             InlineKeyboardButton("Owner", callback_data="settings_owner")],
            [InlineKeyboardButton("My Uploads", callback_data="settings_myupload"),
             InlineKeyboardButton("Help", callback_data="settings_help")],
            [InlineKeyboardButton("Premium", callback_data="settings_premium")]
        ]
        await message.reply_text(
            "Bot Settings:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        logger.info(f"Sent settings menu to user {user_id}")
        await send_log(client, message.from_user, "Started /settings command")
    except ChatAdminRequired:
        logger.error(f"ChatAdminRequired in settings_command")
        await message.reply_text("Error: Bot lacks admin rights.")
        await send_log(client, message.from_user, "Settings command failed: Bot lacks admin rights")
    except Exception as e:
        logger.error(f"Error in settings_command: {e}")
        await message.reply_text("Error: Failed to send settings.")
        await send_log(client, message.from_user, f"Settings command error: {str(e)}")

@Client.on_message(filters.command("clear") & filters.private)
async def clear_tasks(client: Client, message: Message) -> None:
    user_id = message.from_user.id
    from plugins.file_rename import user_tasks
    logger.info(f"Clearing tasks for user {user_id}")
    try:
        if user_id in user_tasks:
            tasks = user_tasks[user_id]
            for task in tasks:
                if not task.done():
                    task.cancel()
            user_tasks[user_id] = []
            logger.info(f"Cleared {len(tasks)} tasks for user {user_id}")

        await codeflixbots.delete_user_choice(user_id)
        if user_id in metadata_input:
            del metadata_input[user_id]
        if user_id in telegram_handle_input:
            del telegram_handle_input[user_id]
        if user_id in upscale_input:
            del upscale_input[user_id]
        await message.reply_text("All ongoing tasks and settings cleared!")
        await send_log(client, message.from_user, "Cleared all tasks and settings")
    except ChatAdminRequired:
        logger.error(f"ChatAdminRequired in clear")
        await message.reply_text("Error: Bot lacks admin rights.")
        await send_log(client, message.from_user, "Clear command failed: Bot lacks admin rights")
    except Exception as e:
        logger.error(f"Error clearing tasks for user {user_id}: {e}")
        await message.reply_text("Error: Couldn't clear tasks.")
        await send_log(client, message.from_user, f"Clear command error: {str(e)}")

@Client.on_message(filters.command("upscale") & filters.private)
async def upscale_command(client: Client, message: Message) -> None:
    user_id = message.from_user.id
    from plugins.file_rename import upscale_video
    try:
        scale = await codeflixbots.get_upscale_scale(user_id)
        if message.reply_to_message and (message.reply_to_message.video or message.reply_to_message.document):
            await upscale_video(client, message.reply_to_message, scale)
        else:
            await message.reply_text("Please reply to a video with /upscale.")
        logger.info(f"Started /upscale for user {user_id}")
        await send_log(client, message.from_user, "Started /upscale command")
    except ChatAdminRequired:
        logger.error(f"ChatAdminRequired in upscale_command")
        await message.reply_text("Error: Bot lacks admin rights.")
        await send_log(client, message.from_user, "Upscale command failed: Bot lacks admin rights")
    except Exception as e:
        logger.error(f"Error in upscale_command: {e}")
        await message.reply_text("Error: Failed to process upscale.")
        await send_log(client, message.from_user, f"Upscale command error: {str(e)}")

@Client.on_message(filters.command("exthum") & filters.private)
async def exthum_command(client: Client, message: Message) -> None:
    user_id = message.from_user.id
    from plugins.file_rename import extract_thumbnail
    try:
        timestamp = float(message.text.split()[-1]) if len(message.text.split()) > 1 else 0.0
        await codeflixbots.set_exthum_timestamp(user_id, timestamp)
        if message.reply_to_message and (message.reply_to_message.video or message.reply_to_message.document):
            await extract_thumbnail(client, message.reply_to_message, timestamp)
        else:
            await message.reply_text("Please reply to a video with /exthum [timestamp].")
        logger.info(f"Started /exthum for user {user_id}")
        await send_log(client, message.from_user, "Started /exthum command")
    except ValueError:
        await message.reply_text("Invalid timestamp. Use /exthum [seconds].")
    except ChatAdminRequired:
        logger.error(f"ChatAdminRequired in exthum_command")
        await message.reply_text("Error: Bot lacks admin rights.")
        await send_log(client, message.from_user, "Exthum command failed: Bot lacks admin rights")
    except Exception as e:
        logger.error(f"Error in exthum_command: {e}")
        await message.reply_text("Error: Failed to process thumbnail.")
        await send_log(client, message.from_user, f"Exthum command error: {str(e)}")

@Client.on_message(filters.command("setmetadata") & filters.private)
async def set_metadata_command(client: Client, message: Message) -> None:
    user_id = message.from_user.id
    try:
        keyboard = [
            [InlineKeyboardButton("Title", callback_data="metadata_title"),
             InlineKeyboardButton("Artist", callback_data="metadata_artist")],
            [InlineKeyboardButton("Author", callback_data="metadata_author"),
             InlineKeyboardButton("Video Title", callback_data="metadata_video")],
            [InlineKeyboardButton("Audio Title", callback_data="metadata_audio"),
             InlineKeyboardButton("Subtitle", callback_data="metadata_subtitle")],
            [InlineKeyboardButton("Back", callback_data="settings_main")]
        ]
        await message.reply_text(
            "Select a metadata field to set:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        logger.info(f"Sent metadata menu to user {user_id}")
        await send_log(client, message.from_user, "Started /setmetadata command")
    except ChatAdminRequired:
        logger.error(f"ChatAdminRequired in setmetadata_command")
        await message.reply_text("Error: Bot lacks admin rights.")
        await send_log(client, message.from_user, "Setmetadata command failed: Bot lacks admin rights")
    except Exception as e:
        logger.error(f"Error in setmetadata_command: {e}")
        await message.reply_text("Error: Failed to send metadata options.")
        await send_log(client, message.from_user, f"Setmetadata command error: {str(e)}")

@Client.on_callback_query(filters.regex(r"^extract_"))
async def handle_extraction_callback(client: Client, callback_query: CallbackQuery) -> None:
    user_id = callback_query.from_user.id
    choice = callback_query.data
    logger.info(f"Extraction callback for user {user_id}: '{choice}'")

    try:
        valid_choices = ["extract_filename", "extract_filecaption"]
        choice_map = {
            "extract_filename": "filename",
            "extract_filecaption": "filecaption"
        }

        if choice not in valid_choices:
            logger.error(f"Invalid extraction callback for user {user_id}: '{choice}'")
            keyboard = [
                [InlineKeyboardButton("Filename", callback_data="extract_filename")],
                [InlineKeyboardButton("Filecaption", callback_data="extract_filecaption")]
            ]
            await callback_query.message.edit_reply_markup(InlineKeyboardMarkup(keyboard))
            await callback_query.message.reply_text("Please select a valid option (Filename or Filecaption).")
            await callback_query.answer("Invalid selection, try again!")
            await send_log(client, callback_query.from_user, f"Invalid extraction callback: '{choice}'")
            return

        db_choice = choice_map[choice]

        updated_keyboard = [
            [InlineKeyboardButton(f"Filename {'✅' if db_choice == 'filename' else ''}", callback_data="extract_filename")],
            [InlineKeyboardButton(f"Filecaption {'✅' if db_choice == 'filecaption' else ''}", callback_data="extract_filecaption")]
        ]
        await callback_query.message.edit_reply_markup(InlineKeyboardMarkup(updated_keyboard))
        success = await codeflixbots.set_user_choice(user_id, db_choice)
        if not success:
            logger.error(f"Failed to save choice '{db_choice}' for user {user_id}")
            await callback_query.message.reply_text("Error: Couldn't save choice.")
            await callback_query.answer("Database error!")
            await send_log(client, callback_query.from_user, f"Failed to save choice: {db_choice}")
            return
        await callback_query.message.reply_text(
            f"Please send the file to rename using its {db_choice}."
        )
        await send_log(client, callback_query.from_user, f"Selected rename mode: {db_choice}")
        await callback_query.answer("Option selected!")
    except ChatAdminRequired:
        logger.error(f"ChatAdminRequired in extraction callback")
        await callback_query.message.reply_text("Error: Bot lacks admin rights.")
        await callback_query.answer("Admin error!")
        await send_log(client, callback_query.from_user, "Extraction callback failed: Bot lacks admin rights")
    except Exception as e:
        logger.error(f"Extraction callback error for user {user_id}: {e}")
        await callback_query.message.reply_text("Error: Something went wrong.")
        await callback_query.answer("Error!")
        await send_log(client, callback_query.from_user, f"Extraction callback error: {str(e)}")

@Client.on_callback_query(filters.regex(r"^settings_"))
async def handle_settings_callback(client: Client, callback_query: CallbackQuery) -> None:
    user_id = callback_query.from_user.id
    choice = callback_query.data
    logger.info(f"Settings callback for user {user_id}: '{choice}'")

    try:
        if choice == "settings_toggle_metadata":
            current = await codeflixbots.get_metadata(user_id)
            new_value = not current
            await codeflixbots.set_metadata(user_id, new_value)
            await update_settings_keyboard(client, callback_query, new_value)
            await callback_query.message.reply_text(f"Metadata turned {'ON' if new_value else 'OFF'}")
            await callback_query.answer("Metadata toggled!")
            await send_log(client, callback_query.from_user, f"Metadata set to {new_value}")

        elif choice == "settings_set_metadata":
            await set_metadata_command(client, callback_query.message)
            await callback_query.answer("Metadata menu opened!")

        elif choice == "settings_set_handle":
            telegram_handle_input[user_id] = True
            await callback_query.message.reply_text("Please enter your Telegram handle (e.g., @Animes_sub_society) or send 'none' to remove:")
            await callback_query.answer("Enter Telegram handle!")
            await send_log(client, callback_query.from_user, "Prompted for Telegram handle")

        elif choice == "settings_set_upscale":
            upscale_input[user_id] = True
            await callback_query.message.reply_text("Please enter upscale scale (e.g., 2:2 for 2x, 4:4 for 4x):")
            await callback_query.answer("Enter upscale scale!")
            await send_log(client, callback_query.from_user, "Prompted for upscale scale")

        elif choice == "settings_mycmd":
            await callback_query.message.reply_text("Your commands: /start, /settings, /setmetadata, /extraction, /upscale, /exthum, /clear")
            await callback_query.answer("Commands shown!")
            await send_log(client, callback_query.from_user, "Showed mycmd")

        elif choice == "settings_owner":
            await callback_query.message.reply_text("Owner: @Codeflix_Bots")
            await callback_query.answer("Owner info shown!")
            await send_log(client, callback_query.from_user, "Showed owner")

        elif choice == "settings_myupload":
            uploads = await codeflixbots.get_uploads(user_id)
            text = "Your uploads:\n" + "\n".join([f"- {u['file_name']} ({u['date']})" for u in uploads[:5]]) if uploads else "No uploads found."
            await callback_query.message.reply_text(text)
            await callback_query.answer("Uploads shown!")
            await send_log(client, callback_query.from_user, "Showed myupload")

        elif choice == "settings_help":
            await callback_query.message.reply_text(
                "Help:\n/settings - Manage bot settings\n/setmetadata - Set metadata\n/extraction - Rename files\n/upscale - Upscale videos\n/exthum - Extract thumbnails\n/clear - Clear tasks\nContact @Codeflix_Bots for support."
            )
            await callback_query.answer("Help shown!")
            await send_log(client, callback_query.from_user, "Showed help")

        elif choice == "settings_premium":
            await callback_query.message.reply_text("Premium: Upgrade for more features! Contact @Codeflix_Bots.")
            await callback_query.answer("Premium info shown!")
            await send_log(client, callback_query.from_user, "Showed premium")

        elif choice == "settings_main":
            metadata_enabled = await codeflixbots.get_metadata(user_id)
            await update_settings_keyboard(client, callback_query, metadata_enabled)
            await callback_query.answer("Back to settings!")
            await send_log(client, callback_query.from_user, "Returned to settings")

    except ChatAdminRequired:
        logger.error(f"ChatAdminRequired in settings callback")
        await callback_query.message.reply_text("Error: Bot lacks admin rights.")
        await callback_query.answer("Admin error!")
        await send_log(client, callback_query.from_user, "Settings callback failed: Bot lacks admin rights")
    except Exception as e:
        logger.error(f"Settings callback error for user {user_id}: {e}")
        await callback_query.message.reply_text("Error: Something went wrong.")
        await callback_query.answer("Error!")
        await send_log(client, callback_query.from_user, f"Settings callback error: {str(e)}")

async def update_settings_keyboard(client, callback_query, metadata_enabled):
    user_id = callback_query.from_user.id
    telegram_handle = await codeflixbots.get_telegram_handle(user_id) or "Not set"
    upscale_scale = await codeflixbots.get_upscale_scale(user_id)
    keyboard = [
        [InlineKeyboardButton(f"Metadata: {'ON' if metadata_enabled else 'OFF'}", callback_data="settings_toggle_metadata")],
        [InlineKeyboardButton("Set Metadata", callback_data="settings_set_metadata")],
        [InlineKeyboardButton(f"Telegram Handle: {telegram_handle}", callback_data="settings_set_handle")],
        [InlineKeyboardButton(f"Upscale Scale: {upscale_scale}", callback_data="settings_set_upscale")],
        [InlineKeyboardButton("My Commands", callback_data="settings_mycmd"),
         InlineKeyboardButton("Owner", callback_data="settings_owner")],
        [InlineKeyboardButton("My Uploads", callback_data="settings_myupload"),
         InlineKeyboardButton("Help", callback_data="settings_help")],
        [InlineKeyboardButton("Premium", callback_data="settings_premium")]
    ]
    await callback_query.message.edit_reply_markup(InlineKeyboardMarkup(keyboard))

