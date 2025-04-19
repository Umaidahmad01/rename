import random
import asyncio
from PIL import Image
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from helper.database import codeflixbots
from config import Config, Txt
import logging
from pyrogram.errors import FloodWait, MessageNotModified, ChatAdminRequired
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

# Thumbnail Command Handler
@Client.on_message(filters.private & filters.command("setthumbnail"))
async def set_thumbnail(client, message):
    user_id = message.from_user.id
    if not message.reply_to_message or not message.reply_to_message.photo:
        await message.reply_text("Please reply to a photo to set it as your thumbnail.")
        return

    thumbnail_id = message.reply_to_message.photo.file_id
    await codeflixbots.set_thumbnail(user_id, thumbnail_id)
    
    # Log thumbnail setting activity
    log_message = (
        f"**Thumbnail Set**\n"
        f"User: {message.from_user.mention} (`{user_id}`)\n"
        f"Thumbnail ID: {thumbnail_id}"
    )
    try:
        await client.send_message(Config.LOG_CHANNEL, log_message)
        await client.send_photo(Config.DUMP_CHANNEL, thumbnail_id, caption=log_message)
    except Exception as e:
        logger.error(f"Error logging thumbnail for user {user_id}: {e}")

    await message.reply_text("Thumbnail set successfully!")

# Extraction Command Handler
async def get_extraction_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Generate inline keyboard for /extraction with ✅ on selected mode."""
    current_mode = await codeflixbots.get_rename_mode(user_id)
    buttons = [
        [
            InlineKeyboardButton(
                f"Filename {'✅' if current_mode == 'filename' else ''}",
                callback_data="extraction_filename"
            ),
            InlineKeyboardButton(
                f"Caption {'✅' if current_mode == 'caption' else ''}",
                callback_data="extraction_caption"
            )
        ]
    ]
    return InlineKeyboardMarkup(buttons)

@Client.on_message(filters.command("extraction") & filters.private)
async def extraction(client, message):
    user_id = message.from_user.id
    keyboard = await get_extraction_keyboard(user_id)
    await message.reply_text(
        "Select rename mode:",
        reply_markup=keyboard
    )
    logger.info(f"Displayed extraction keyboard for user {user_id}")

@Client.on_callback_query(filters.regex(r"^extraction_"))
async def extraction_callback(client, callback_query):
    user_id = callback_query.from_user.id
    mode = callback_query.data.split("_")[1]  # e.g., "filename" or "caption"
    try:
        await codeflixbots.set_rename_mode(user_id, mode)
        keyboard = await get_extraction_keyboard(user_id)
        await callback_query.message.edit_text(
            f"Selected rename mode: {mode} ✅",
            reply_markup=keyboard
        )
        # Log mode change activity
        log_message = (
            f"**Rename Mode Changed**\n"
            f"User: {callback_query.from_user.mention} (`{user_id}`)\n"
            f"New Mode: {mode}"
        )
        await client.send_message(Config.LOG_CHANNEL, log_message)
        await client.send_message(Config.DUMP_CHANNEL, log_message)
        await callback_query.answer(f"Set to {mode}")
        logger.info(f"User {user_id} set rename_mode to {mode}")
    except Exception as e:
        await callback_query.answer("Error setting mode", show_alert=True)
        logger.error(f"Error setting rename_mode for user {user_id}: {e}")

# Callback Query Handler
@Client.on_callback_query()
async def callback(client, query: CallbackQuery):
    data = query.data
    user_id = query.from_user.id

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
        except:
            await query.message.delete()
