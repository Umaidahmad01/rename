from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from helper.database import TokenDatabase
from config import *
import os

# Bot token from environment variable or default
BOT_TOKEN = os.environ.get("BOT_TOKEN", "7871117577:AAE-5op-GX41uVdceNzOPaj3cncZZZb6Nh8")
# Owner ID from environment variable or default
OWNER_ID = int(os.environ.get("OWNER_ID", "5585016974"))

# Client initialize with bot token
client = Client("my_bot", bot_token=BOT_TOKEN)

# Database initialize with TokenDatabase
db = TokenDatabase(Config.DB_URL, Config.DB_NAME)

# Token info ko format karne ke liye
def format_token_info(token_info):
    return f"Token Status: {token_info['status']}\nCurrent Token: {token_info['token']}\nYour Tokens: {token_info['user_tokens']}\nAPI: {token_info['api']}\nSite: {token_info['site']}"

# Admin ya owner check karne ke liye
def is_authorized(chat_id):
    return chat_id == OWNER_ID or chat_id in ADMIN_IDS

# Start command
@client.on_message(filters.command("start"))
async def start(client, message):
    chat_id = message.chat.id
    token_info = await db.get_token_info(chat_id)
    text = format_token_info(token_info)
    
    keyboard = [
        [InlineKeyboardButton("Set Token", callback_data='set_token')],
        [InlineKeyboardButton("ON Token", callback_data='on_token'),
         InlineKeyboardButton("OFF Token", callback_data='off_token')],
        [InlineKeyboardButton("Change Token", callback_data='change_token')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await message.reply(f"Welcome to Token Bot!\n\n{text}", reply_markup=reply_markup)

# Button handler
@client.on_callback_query()
async def button(client, callback_query):
    chat_id = callback_query.message.chat.id
    data = callback_query.data

    if data == "set_token":
        await callback_query.edit_message_text("Naya token daal do: /settoken <token>")
    elif data == "on_token":
        await db.on_token(chat_id)
        token_info = await db.get_token_info(chat_id)
        text = format_token_info(token_info)
        keyboard = [
            [InlineKeyboardButton("Set Token", callback_data='set_token')],
            [InlineKeyboardButton("ON Token", callback_data='on_token'),
             InlineKeyboardButton("OFF Token", callback_data='off_token')],
            [InlineKeyboardButton("Change Token", callback_data='change_token')]
        ]
        await callback_query.edit_message_text(f"Token ON kar diya!\n\n{text}", reply_markup=InlineKeyboardMarkup(keyboard))
    elif data == "off_token":
        await db.off_token(chat_id)
        token_info = await db.get_token_info(chat_id)
        text = format_token_info(token_info)
        keyboard = [
            [InlineKeyboardButton("Set Token", callback_data='set_token')],
            [InlineKeyboardButton("ON Token", callback_data='on_token'),
             InlineKeyboardButton("OFF Token", callback_data='off_token')],
            [InlineKeyboardButton("Change Token", callback_data='change_token')]
        ]
        await callback_query.edit_message_text(f"Token OFF kar diya!\n\n{text}", reply_markup=InlineKeyboardMarkup(keyboard))
    elif data == "change_token":
        await callback_query.edit_message_text("Naya token daal do: /settoken <token>")

# Set token command
@client.on_message(filters.command("settoken"))
async def set_token(client, message):
    chat_id = message.chat.id
    if len(message.command) < 2:
        await message.reply("Token daal do bhai, jaise: /settoken abc123")
        return
    
    new_token = message.command[1]
    await db.set_token(chat_id, new_token)
    token_info = await db.get_token_info(chat_id)
    text = format_token_info(token_info)
    
    keyboard = [
        [InlineKeyboardButton("Set Token", callback_data='set_token')],
        [InlineKeyboardButton("ON Token", callback_data='on_token'),
         InlineKeyboardButton("OFF Token", callback_data='off_token')],
        [InlineKeyboardButton("Change Token", callback_data='change_token')]
    ]
    await message.reply(f"Token set kar diya!\n\n{text}", reply_markup=InlineKeyboardMarkup(keyboard))

# Give token command (owner ya admin ke liye)
@client.on_message(filters.command("give_token"))
async def give_token(client, message):
    chat_id = message.chat.id
    if not is_authorized(chat_id):
        await message.reply("Bhai, yeh command sirf owner ya admin ke liye hai!")
        return
    
    if len(message.command) < 3:
        await message.reply("Command galat hai! Use karo: /give_token <user_id> <amount>")
        return
    
    try:
        target_chat_id = int(message.command[1])
        amount = int(message.command[2])
        await db.give_token(target_chat_id, amount)
        await message.reply(f"{target_chat_id} ko {amount} tokens de diye!")
        await client.send_message(target_chat_id, f"Bhai, tujhe {amount} tokens mil gaye hai!")
    except ValueError:
        await message.reply("User ID ya amount number hona chahiye!")

# Set reward command (owner ya admin ke liye)
@client.on_message(filters.command("set_reward"))
async def set_reward(client, message):
    chat_id = message.chat.id
    if not is_authorized(chat_id):
        await message.reply("Bhai, yeh command sirf owner ya admin ke liye hai!")
        return
    
    if len(message.command) < 2:
        await message.reply("Reward amount daal do: /set_reward <amount>")
        return
    
    try:
        amount = int(message.command[1])
        await db.set_reward(amount)
        await message.reply(f"Reward set kar diya! Ab ek solve pe {amount} tokens milenge.")
    except ValueError:
        await message.reply("Amount number hona chahiye!")

# Solve command (testing ke liye)
@client.on_message(filters.command("solve"))
async def solve(client, message):
    chat_id = message.chat.id
    reward = await db.reward_user(chat_id)
    token_info = await db.get_token_info(chat_id)
    text = format_token_info(token_info)
    await message.reply(f"Solve kar diya! Tujhe {reward} tokens mile.\n\n{text}")

# Left token command
@client.on_message(filters.command("lefttoken"))
async def left_token(client, message):
    chat_id = message.chat.id
    token_info = await db.get_token_info(chat_id)
    left_tokens = token_info['user_tokens']
    await message.reply(f"Bhai, tere paas {left_tokens} tokens bache hai!")

# Restart message (bot start hone pe)
@client.on_message(filters.private & filters.user(OWNER_ID), group=-1)
async def on_start(client, message):
    await client.send_message(OWNER_ID, "Bhai, bot restart ho gaya hai! Sab set hai ab.")

# Bot ko chalao
if __name__ == "__main__":
    client.run()
