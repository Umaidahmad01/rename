import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram import Updater, CommandHandler, CallbackQueryHandler
from database import *
from config import * # ADMIN_IDS bhi import karo

# Database initialize
db = Database()

# Token info ko format karne ke liye
def format_token_info(token_info):
    return f"Token Status: {token_info['status']}\nCurrent Token: {token_info['token']}\nYour Tokens: {token_info['user_tokens']}\nAPI: {token_info['api']}\nSite: {token_info['site']}"

# Restart message bhejne ke liye
def send_restart_message(context):
    context.bot.send_message(chat_id=OWNER_ID, text="Bhai, bot restart ho gaya hai! Sab set hai ab.")

# Admin ya owner check karne ke liye helper function
def is_authorized(chat_id):
    return chat_id == OWNER_ID or chat_id in ADMIN_IDS

# Start command
def start(update, context):
    chat_id = update.message.chat_id
    token_info = db.get_token_info(chat_id)
    text = format_token_info(token_info)
    
    keyboard = [
        [InlineKeyboardButton("Set Token", callback_data='set_token')],
        [InlineKeyboardButton("ON Token", callback_data='on_token'),
         InlineKeyboardButton("OFF Token", callback_data='off_token')],
        [InlineKeyboardButton("Change Token", callback_data='change_token')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.message.reply_text(f"Welcome to Token Bot!\n\n{text}", reply_markup=reply_markup)

# Button handler
def button(update, context):
    query = update.callback_query
    chat_id = query.message.chat_id
    query.answer()

    if query.data == "set_token":
        query.edit_message_text("Naya token daal do: /settoken <token>")
    elif query.data == "on_token":
        db.on_token(chat_id)
        token_info = db.get_token_info(chat_id)
        text = format_token_info(token_info)
        keyboard = [
            [InlineKeyboardButton("Set Token", callback_data='set_token')],
            [InlineKeyboardButton("ON Token", callback_data='on_token'),
             InlineKeyboardButton("OFF Token", callback_data='off_token')],
            [InlineKeyboardButton("Change Token", callback_data='change_token')]
        ]
        query.edit_message_text(f"Token ON kar diya!\n\n{text}", reply_markup=InlineKeyboardMarkup(keyboard))
    elif query.data == "off_token":
        db.off_token(chat_id)
        token_info = db.get_token_info(chat_id)
        text = format_token_info(token_info)
        keyboard = [
            [InlineKeyboardButton("Set Token", callback_data='set_token')],
            [InlineKeyboardButton("ON Token", callback_data='on_token'),
             InlineKeyboardButton("OFF Token", callback_data='off_token')],
            [InlineKeyboardButton("Change Token", callback_data='change_token')]
        ]
        query.edit_message_text(f"Token OFF kar diya!\n\n{text}", reply_markup=InlineKeyboardMarkup(keyboard))
    elif query.data == "change_token":
        query.edit_message_text("Naya token daal do: /settoken <token>")

# Set token command
def set_token(update, context):
    chat_id = update.message.chat_id
    if len(context.args) == 0:
        update.message.reply_text("Token daal do bhai, jaise: /settoken abc123")
        return
    
    new_token = context.args[0]
    db.set_token(chat_id, new_token)
    token_info = db.get_token_info(chat_id)
    text = format_token_info(token_info)
    
    keyboard = [
        [InlineKeyboardButton("Set Token", callback_data='set_token')],
        [InlineKeyboardButton("ON Token", callback_data='on_token'),
         InlineKeyboardButton("OFF Token", callback_data='off_token')],
        [InlineKeyboardButton("Change Token", callback_data='change_token')]
    ]
    update.message.reply_text(f"Token set kar diya!\n\n{text}", reply_markup=InlineKeyboardMarkup(keyboard))

# Give token command (owner ya admin ke liye)
def give_token(update, context):
    chat_id = update.message.chat_id
    if not is_authorized(chat_id):
        update.message.reply_text("Bhai, yeh command sirf owner ya admin ke liye hai!")
        return
    
    if len(context.args) < 2:
        update.message.reply_text("Command galat hai! Use karo: /give_token <user_id> <amount>")
        return
    
    try:
        target_chat_id = int(context.args[0])
        amount = int(context.args[1])
        db.give_token(target_chat_id, amount)
        update.message.reply_text(f"{target_chat_id} ko {amount} tokens de diye!")
        context.bot.send_message(target_chat_id, f"Bhai, tujhe {amount} tokens mil gaye hai!")
    except ValueError:
        update.message.reply_text("User ID ya amount number hona chahiye!")

# Set reward command (owner ya admin ke liye)
def set_reward(update, context):
    chat_id = update.message.chat_id
    if not is_authorized(chat_id):
        update.message.reply_text("Bhai, yeh command sirf owner ya admin ke liye hai!")
        return
    
    if len(context.args) == 0:
        update.message.reply_text("Reward amount daal do: /set_reward <amount>")
        return
    
    try:
        amount = int(context.args[0])
        db.set_reward(amount)
        update.message.reply_text(f"Reward set kar diya! Ab ek solve pe {amount} tokens milenge.")
    except ValueError:
        update.message.reply_text("Amount number hona chahiye!")

# Example solve command (testing ke liye)
def solve(update, context):
    chat_id = update.message.chat_id
    reward = db.reward_user(chat_id)
    token_info = db.get_token_info(chat_id)
    text = format_token_info(token_info)
    update.message.reply_text(f"Solve kar diya! Tujhe {reward} tokens mile.\n\n{text}")

# Main function
def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    # Handlers
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("settoken", set_token))
    dp.add_handler(CommandHandler("give_token", give_token))
    dp.add_handler(CommandHandler("set_reward", set_reward))
    dp.add_handler(CommandHandler("solve", solve))
    dp.add_handler(CallbackQueryHandler(button))

    # Restart message
    updater.job_queue.run_once(send_restart_message, 1)

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
