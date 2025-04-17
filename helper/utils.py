import math
import time
import logging
import asyncio
from pyrogram.types import Message
from pyrogram.errors import FloodWait, ChatAdminRequired
from config import Config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

async def progress_for_pyrogram(current, total, ud_type, message, start):
    now = time.time()
    diff = now - start
    if round(diff % 10.00) == 0 or current == total:
        percentage = current * 100 / total
        speed = current / diff if diff > 0 else 0
        elapsed_time = round(diff) * 1000
        time_to_completion = round((total - current) / speed) * 1000 if speed > 0 else 0
        estimated_total_time = elapsed_time + time_to_completion

        elapsed_time = TimeFormatter(milliseconds=elapsed_time)
        estimated_total_time = TimeFormatter(milliseconds=estimated_total_time)

        progress = "[{0}{1}] \n**Percentage**: {2}%\n".format(
            ''.join(["█" for _ in range(math.floor(percentage / 5))]),
            ''.join([" " for _ in range(20 - math.floor(percentage / 5))]),
            round(percentage, 2)
        )

        tmp = progress + "**{0} of {1}**\n**Speed**: {2}/s\n**ETA**: {3}\n".format(
            humanbytes(current),
            humanbytes(total),
            humanbytes(speed),
            estimated_total_time if time_to_completion != 0 else "0 s"
        )
        try:
            await message.edit(f"{ud_type}\n\n{tmp}")
        except Exception as e:
            logger.debug(f"Error updating progress: {e}")

def humanbytes(size):
    if not size:
        return "0 B"
    for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi']:
        if size < 1024.0:
            break
        size /= 1024.0
    return f"{size:.2f} {unit}B"

def TimeFormatter(milliseconds: int) -> str:
    seconds, milliseconds = divmod(int(milliseconds), 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    tmp = (
        ((str(days) + "d, ") if days else "") +
        ((str(hours) + "h, ") if hours else "") +
        ((str(minutes) + "m, ") if minutes else "") +
        ((str(seconds) + "s, ") if seconds else "") +
        ((str(milliseconds) + "ms") if milliseconds else "")
    )
    return tmp.rstrip(", ")

async def send_log(client, user, log_message: str):
    try:
        await client.send_message(
            chat_id=Config.LOG_CHANNEL,
            text=f"**User**: {user.mention} (ID: {user.id})\n**Action**: {log_message}",
            disable_web_page_preview=True
        )
        logger.info(f"Sent log message for user {user.id}: {log_message}")
    except FloodWait as e:
        logger.warning(f"FloodWait during log send: {e.value}s")
        await asyncio.sleep(e.value)
        await send_log(client, user, log_message)
    except ChatAdminRequired:
        logger.error(f"ChatAdminRequired for log channel")
    except Exception as e:
        logger.error(f"Error sending log message for user {user.id}: {e}")

async def add_prefix_suffix(text: str, prefix: str = None, suffix: str = None) -> str:
    try:
        result = text
        if prefix:
            result = f"{prefix}{result}"
        if suffix:
            result = f"{result}{suffix}"
        return result
    except Exception as e:
        logger.error(f"Error adding prefix/suffix: {e}")
        return text
