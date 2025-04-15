import random
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from helper.database import *
from config import *
import logging
from typing import List, Optional
from pyrogram.errors import FloodWait, MessageNotModified, ChatAdminRequired
import os
import asyncio

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize MongoDB
db: Database = Database()

# Start Command Handler
@Client.on_message(filters.private & filters.command("start"))
async def start(client, message: Message):
    user = message.from_user
    await codeflixbots.add_user(client, message)

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


# Callback Query Handler
@Client.on_callback_query()
async def cb_handler(client, query: CallbackQuery):
    data = query.data
    user_id = query.from_user.id

    print(f"Callback data received: {data}")  # Debugging line

    if data == "home":
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
            text=Txt.HELP_TXT.format(client.mention),
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("• ᴀᴜᴛᴏ ʀᴇɴᴀᴍᴇ ғᴏʀᴍᴀᴛ •", callback_data='file_names')],
                [InlineKeyboardButton('• ᴛʜᴜᴍʙɴᴀɪʟ', callback_data='thumbnail'), InlineKeyboardButton('ᴄᴀᴘᴛɪᴏɴ •', callback_data='caption')],
                [InlineKeyboardButton('• ᴍᴇᴛᴀᴅᴀᴛᴀ', callback_data='meta'), InlineKeyboardButton('ᴅᴏɴᴀᴛᴇ •', callback_data='donate')],
                [InlineKeyboardButton('• ʜᴏᴍᴇ', callback_data='home')]
            ])
        )

    elif data == "meta":
        await query.message.edit_text(  # Change edit_caption to edit_text
            text=Txt.SEND_METADATA,  # Changed from caption to text
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
        format_template = await codeflixbots.get_format_template(user_id)
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
            chat_id=LOG_CHANNEL,
            photo=replied.photo.file_id,
            caption=f'<b>User - {message.from_user.mention}\nUser id - <code>{message.from_user.id}</code>\nUsername - <code>{message.from_user.username}</code>\nName - <code>{message.from_user.first_name}</code></b>',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Close", callback_data="close_data")]
            ])
        )
        await msg.edit_text('<b>Your screenshot has been sent to Admins</b>')

@Client.on_message(filters.private & filters.command("help"))
async def help_command(client, message):
    # Await get_me to get the bot's user object
    bot = await client.get_me()
    mention = bot.mention

    # Send the help message with inline buttons
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

### /extraction 
@Client.on_message(filters.command("extraction") & filters.private)
async def extraction_command(client: Client, message: Message) -> None:
    keyboard: List[List[InlineKeyboardButton]] = [
        [InlineKeyboardButton("Filename", callback_data="filename")],
        [InlineKeyboardButton("Filecaption", callback_data="filecaption")]
    ]
    await message.reply_text(
        "Choose how you want to rename the file:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

@Client.on_callback_query()
async def handle_callback(client: Client, callback_query: CallbackQuery) -> None:
    try:
        choice: str = callback_query.data
        if not choice or choice not in ["filename", "filecaption"]:
            logging.error(f"Invalid/no callback data for user {callback_query.from_user.id}: {choice}")
            await callback_query.message.reply_text("Error: Invalid option.")
            await callback_query.answer("Invalid selection!")
            return

        user_id: int = callback_query.from_user.id
        logging.info(f"Callback '{choice}' for user {user_id}")

        if not callback_query.message.reply_markup or not hasattr(callback_query.message.reply_markup, 'inline_keyboard'):
            logging.error(f"No keyboard for user {user_id}")
            await callback_query.message.reply_text("Error: Buttons missing.")
            await callback_query.answer("Keyboard error!")
            return

        updated_keyboard = [
            [InlineKeyboardButton("Filename ✅" if choice == "filename" else "Filename", callback_data="filename")],
            [InlineKeyboardButton("Filecaption ✅" if choice == "filecaption" else "Filecaption", callback_data="filecaption")]
        ]
        logging.info(f"Keyboard for user {user_id}: {[[b.text for b in r] for r in updated_keyboard]}")

        for attempt in range(3):
            try:
                await callback_query.message.edit_reply_markup(InlineKeyboardMarkup(updated_keyboard))
                logging.info(f"Keyboard updated for user {user_id}")
                break
            except MessageNotModified:
                logging.warning(f"Keyboard unchanged for user {user_id}, attempt {attempt+1}")
                break
            except ChatAdminRequired as e:
                logging.error(f"ChatAdminRequired for keyboard update, user {user_id}: {e}")
                await callback_query.message.reply_text("Error: Bot lacks admin rights.")
                await callback_query.answer("Admin error!")
                return
            except Exception as e:
                logging.error(f"Keyboard update failed for user {user_id}, attempt {attempt+1}: {e}")
                if attempt == 2:
                    await callback_query.message.reply_text("Error: Couldn't update buttons.")
                    await callback_query.answer("Update failed!")
                    return
                await asyncio.sleep(1)

        try:
            success = await db.set_user_choice(user_id, choice)
            if not success:
                logging.error(f"Failed to save choice '{choice}' for user {user_id}")
                await callback_query.message.reply_text("Error: Couldn't save choice.")
                await callback_query.answer("Database error!")
                return
            await callback_query.message.reply_text(
                f"Please send the file, and I'll rename it using its {choice}."
            )
        except ChatAdminRequired as e:
            logging.error(f"ChatAdminRequired for db save, user {user_id}: {e}")
            await callback_query.message.reply_text("Error: Bot lacks admin rights.")
            await callback_query.answer("Admin error!")
            return

        await callback_query.answer("Option selected!")
    except ChatAdminRequired as e:
        logging.error(f"ChatAdminRequired in callback for user {callback_query.from_user.id}: {e}")
        await callback_query.message.reply_text("Error: Bot lacks admin rights.")
        await callback_query.answer("Admin error!")
    except Exception as e:
        logging.error(f"Callback error for user {callback_query.from_user.id}: {e}")
        await callback_query.message.reply_text("Error: Something went wrong.")
        await callback_query.answer("Error!")

@Client.on_message(filters.document & filters.private)
async def handle_file(client: Client, message: Message) -> None:
    user_id: int = message.from_user.id
    rename_mode: Optional[str] = await db.get_user_choice(user_id)

    if not rename_mode:
        await message.reply_text("Use /extraction to choose a rename mode.")
        return

    file = message.document
    new_name: str = ""

    try:
        logging.info(f"Processing file for user {user_id}, mode {rename_mode}")
        if rename_mode == "filename":
            new_name = file.file_name or f"unnamed_{user_id}.bin"
            await message.reply_text(f"Renaming using filename: {new_name}")

        elif rename_mode == "filecaption":
            caption: Optional[str] = message.caption
            if caption:
                extension: str = file.file_name.split('.')[-1] if '.' in file.file_name else 'bin'
                new_name = f"{caption}.{extension}"
                await message.reply_text(f"Renaming using caption: {new_name}")
            else:
                new_name = file.file_name or f"unnamed_{user_id}.bin"
                await message.reply_text("No caption, using filename: {new_name}")

        logging.info(f"Downloading {file.file_name} for user {user_id}")
        try:
            file_path: str = await client.download_media(file)
        except ChatAdminRequired as e:
            logging.error(f"ChatAdminRequired during download for user {user_id}: {e}")
            await message.reply_text("Error: Bot lacks admin rights.")
            return
        except Exception as e:
            logging.error(f"Download error for user {user_id}: {e}")
            await message.reply_text(f"Error downloading: {e}")
            return

        renamed_file_path: str = f"downloads/{new_name}"
        logging.info(f"Renaming to {renamed_file_path}")
        os.makedirs("downloads", exist_ok=True)
        os.rename(file_path, renamed_file_path)

        logging.info(f"Uploading {new_name} for user {user_id}")
        try:
            await client.send_document(
                chat_id=message.chat.id,
                document=renamed_file_path,
                file_name=new_name
            )
        except ChatAdminRequired as e:
            logging.error(f"ChatAdminRequired during upload for user {user_id}: {e}")
            await message.reply_text("Error: Bot lacks admin rights.")
            return
        except Exception as e:
            logging.error(f"Upload error for user {user_id}: {e}")
            await message.reply_text(f"Error uploading: {e}")
            return

        os.remove(renamed_file_path)
        await db.delete_user_choice(user_id)
        logging.info(f"File processed, choice deleted for user {user_id}")

    except ChatAdminRequired as e:
        logging.error(f"ChatAdminRequired in file processing for user {user_id}: {e}")
        await message.reply_text("Error: Bot lacks admin rights.")
    except Exception as e:
        logging.error(f"Processing error for user {user_id}: {e}")
        if "ffmpeg" in str(e).lower():
            await message.reply_text("Error: FFmpeg not installed. Contact admin.")
        else:
            await message.reply_text(f"Error processing file: {e}")

                
