import math, time
from datetime import datetime
from pytz import timezone
from config import Config, Txt 
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.errors import ChatAdminRequired
import re
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def old_progress_for_pyrogram(current, total, ud_type, message, start):
    now = time.time()
    diff = now - start
    if round(diff % 5.00) == 0 or current == total:        
        percentage = current * 100 / total
        speed = current / diff if diff > 0 else 0
        elapsed_time = round(diff) * 1000
        time_to_completion = round((total - current) / speed) * 1000 if speed > 0 else 0
        estimated_total_time = elapsed_time + time_to_completion

        elapsed_time = TimeFormatter(milliseconds=elapsed_time)
        estimated_total_time = TimeFormatter(milliseconds=estimated_total_time)

        progress = "{0}{1}".format(
            ''.join(["■" for i in range(math.floor(percentage / 5))]),
            ''.join(["□" for i in range(20 - math.floor(percentage / 5))])
        )            
        tmp = Txt.OLD_PROGRESS_BAR.format( 
            round(percentage, 2),
            humanbytes(current),
            humanbytes(total),
            humanbytes(speed),            
            estimated_total_time if estimated_total_time != '' else "0 s"
        )
        try:
            await message.edit(
                text=f"{ud_type}\n\n{tmp}",               
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("• ᴄᴀɴᴄᴇʟ •", callback_data="close")]])                                               
            )
        except ChatAdminRequired as e:
            logger.error(f"ChatAdminRequired in old progress: {e}")
        except Exception as e:
            logger.error(f"Old progress update failed: {e}")
            if "ffmpeg" in str(e).lower():
                logger.error("FFmpeg not found in old progress")
            pass

async def progress_for_pyrogram(current, total, ud_type, message, start):
    now = time.time()
    diff = now - start
    if round(diff % 1.00) == 0 or current == total:
        percentage = current * 100 / total
        speed = current / diff if diff > 0 else 0
        eta = round((total - current) / speed) if speed > 0 else 0

        bars = 8
        filled = math.floor(percentage / (100 / bars))
        progress = f"{'▮' * filled}{'▯' * (bars - filled)}"

        status = "🔄" if percentage < 100 else "✅"
        action = "↑" if "upload" in ud_type.lower() else "↓"

        tmp = Txt.PROGRESS_BAR.format(
            action,
            ud_type,
            status,
            progress,
            round(percentage, 1),
            humanbytes(current),
            humanbytes(total),
            eta
        )

        try:
            await message.edit(
                text=tmp,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⛔ Cancel", callback_data="close")]
                ])
            )
        except ChatAdminRequired as e:
            logger.error(f"ChatAdminRequired in progress: {e}")
        except Exception as e:
            logger.error(f"Progress update failed: {e}")
            if "ffmpeg" in str(e).lower():
                logger.error("FFmpeg not found in progress")
            pass

def humanbytes(size):    
    if not size:
        return ""
    power = 2**10
    n = 0
    Dic_powerN = {0: '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
    while size > power:
        size /= power
        n += 1
    return f"{round(size, 2)} {Dic_powerN[n]}B"

def TimeFormatter(milliseconds: int) -> str:
    seconds, milliseconds = divmod(int(milliseconds), 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    tmp = ((str(hours) + "h ") if hours else "") + \
          ((str(minutes) + "m ") if minutes else "") + \
          ((str(seconds) + "s") if seconds else "")
    return tmp or "0s"

def convert(seconds):
    seconds = seconds % (24 * 3600)
    hour = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60      
    return "%d:%02d:%02d" % (hour, minutes, seconds)

async def send_log(b, u, msg: str = None):
    if Config.LOG_CHANNEL:
        curr = datetime.now(timezone("Asia/Kolkata"))
        date = curr.strftime('%d %B, %Y')
        time = curr.strftime('%I:%M:%S %p')
        log_msg = f"**Log**\n\nUser: {u.mention}\nID: `{u.id}`\nUN: @{u.username}\n\nDate: {date}\nTime: {time}\n"
        if msg:
            log_msg += f"Message: {msg}\n"
        log_msg += f"By: {b.mention}"
        try:
            await b.send_message(
                Config.LOG_CHANNEL,
                log_msg
            )
        except ChatAdminRequired as e:
            logger.error(f"ChatAdminRequired in send_log: {e}")
        except Exception as e:
            logger.error(f"Failed send_log for user {u.id}: {e}")

def add_prefix_suffix(input_string, prefix='', suffix=''):
    pattern = r'(?P<filename>.*?)(\.\w+)?$'
    match = re.search(pattern, input_string)
    if match:
        filename = match.group('filename')
        extension = match.group(2) or ''
        if prefix is None:
            if suffix is None:
                return f"{filename}{extension}"
            return f"{filename} {suffix}{extension}"
        elif suffix is None:
            if prefix is None:
                return f"{filename}{extension}"
            return f"{prefix}{filename}{extension}"
        else:
            return f"{prefix}{filename} {suffix}{extension}"
    return input_string
