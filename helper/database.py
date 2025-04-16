import motor.motor_asyncio
import datetime
import pytz
from config import Config
import logging
from .utils import send_log
from pymongo import MongoClient
from typing import Optional
import os
import asyncio

DB_URL = os.getenv("DB_URL", Config.DB_URL)
DB_NAME = os.getenv("DB_NAME", Config.DB_NAME)
DUMP_CHANNEL = os.getenv("DUMP_CHANNEL", getattr(Config, "DUMP_CHANNEL", None))

class Database:
    def __init__(obito, uri: str = DB_URL, db_name: str = DB_NAME) -> None:
        try:
            obito._async_client = motor.motor_asyncio.AsyncIOMotorClient(uri)
            obito._async_client.server_info()
            logging.info("Successfully connected to async MongoDB")
        except Exception as e:
            logging.error(f"Failed to connect to async MongoDB: {e}")
            raise e
        
        try:
            obito.client = MongoClient(uri)
            logging.info("Successfully connected to sync MongoDB")
        except Exception as e:
            logging.error(f"Failed to connect to sync MongoDB: {e}")
            raise e

        obito.codeflixbots = obito._async_client[db_name]
        obito.col = obito.codeflixbots.user
        obito.db = obito.client[db_name]
        obito.users = obito.db.users
        obito.dump_channel = DUMP_CHANNEL
        asyncio.create_task(obito.migrate_metadata())

    async def migrate_metadata(obito):
        try:
            result = await obito.col.update_many(
                {},
                {"$set": {
                    "metadata": False,
                    "title": None,
                    "artist": None,
                    "author": None,
                    "video": None,
                    "audio": None,
                    "subtitle": None,
                    "telegram_handle": None,
                    "upscale_scale": "2:2",
                    "exthum_timestamp": None
                }}
            )
            logging.info(f"Reset metadata for {result.modified_count} users")
        except Exception as e:
            logging.error(f"Error migrating metadata: {e}")

    def new_user(obito, id):
        return dict(
            _id=int(id),
            join_date=datetime.date.today().isoformat(),
            file_id=None,
            caption=None,
            metadata=False,
            metadata_code="Telegram : @Codeflix_Bots",
            format_template=None,
            telegram_handle=None,
            upscale_scale="2:2",
            exthum_timestamp=None,
            uploads=[],
            ban_status=dict(
                is_banned=False,
                ban_duration=0,
                banned_on=datetime.date.max.isoformat(),
                ban_reason=''
            )
        )

    async def add_user(obito, b, m):
        u = m.from_user
        if not await obito.is_user_exist(u.id):
            user = obito.new_user(u.id)
            try:
                await obito.col.insert_one(user)
                await send_log(b, u)
            except Exception as e:
                logging.error(f"Error adding user {u.id}: {e}")

    async def is_user_exist(obito, id):
        try:
            user = await obito.col.find_one({"_id": int(id)})
            return bool(user)
        except Exception as e:
            logging.error(f"Error checking if user {id} exists: {e}")
            return False

    async def total_users_count(obito):
        try:
            count = await obito.col.count_documents({})
            return count
        except Exception as e:
            logging.error(f"Error counting users: {e}")
            return 0

    async def get_all_users(obito):
        try:
            all_users = obito.col.find({})
            return all_users
        except Exception as e:
            logging.error(f"Error getting all users: {e}")
            return None

    async def delete_user(obito, user_id):
        try:
            await obito.col.delete_many({"_id": int(user_id)})
        except Exception as e:
            logging.error(f"Error deleting user {user_id}: {e}")

    async def set_thumbnail(obito, id, file_id):
        try:
            await obito.col.update_one({"_id": int(id)}, {"$set": {"file_id": file_id}})
        except Exception as e:
            logging.error(f"Error setting thumbnail for user {id}: {e}")

    async def get_thumbnail(obito, id):
        try:
            user = await obito.col.find_one({"_id": int(id)})
            return user.get("file_id", None) if user else None
        except Exception as e:
            logging.error(f"Error getting thumbnail for user {id}: {e}")
            return None

    async def set_caption(obito, id, caption):
        try:
            await obito.col.update_one({"_id": int(id)}, {"$set": {"caption": caption}})
        except Exception as e:
            logging.error(f"Error setting caption for user {id}: {e}")

    async def get_caption(obito, id):
        try:
            user = await obito.col.find_one({"_id": int(id)})
            return user.get("caption", None) if user else None
        except Exception as e:
            logging.error(f"Error getting caption for user {id}: {e}")
            return None

    async def set_format_template(obito, id, format_template):
        try:
            await obito.col.update_one(
                {"_id": int(id)}, {"$set": {"format_template": format_template}}
            )
        except Exception as e:
            logging.error(f"Error setting format template for user {id}: {e}")

    async def get_format_template(obito, id):
        try:
            user = await obito.col.find_one({"_id": int(id)})
            return user.get("format_template", None) if user else None
        except Exception as e:
            logging.error(f"Error getting format template for user {id}: {e}")
            return None

    async def set_media_preference(obito, id, media_type):
        try:
            await obito.col.update_one(
                {"_id": int(id)}, {"$set": {"media_type": media_type}}
            )
        except Exception as e:
            logging.error(f"Error setting media preference for user {id}: {e}")

    async def get_media_preference(obito, id):
        try:
            user = await obito.col.find_one({"_id": int(id)})
            return user.get("media_type", None) if user else None
        except Exception as e:
            logging.error(f"Error getting media preference for user {id}: {e}")
            return None

    async def get_metadata(obito, user_id):
        try:
            user = await obito.col.find_one({'_id': int(user_id)})
            return user.get('metadata', False) if user else False
        except Exception as e:
            logging.error(f"Error getting metadata for user {user_id}: {e}")
            return False

    async def set_metadata(obito, user_id, metadata):
        try:
            await obito.col.update_one({'_id': int(user_id)}, {'$set': {'metadata': bool(metadata)}})
            logging.info(f"Set metadata to {metadata} for user {user_id}")
        except Exception as e:
            logging.error(f"Error setting metadata for user {user_id}: {e}")

    async def get_title(obito, user_id):
        try:
            user = await obito.col.find_one({'_id': int(user_id)})
            return user.get('title', None) if user else None
        except Exception as e:
            logging.error(f"Error getting title for user {user_id}: {e}")
            return None

    async def set_title(obito, user_id, title):
        try:
            await obito.col.update_one({'_id': int(user_id)}, {'$set': {'title': title}})
        except Exception as e:
            logging.error(f"Error setting title for user {user_id}: {e}")

    async def get_author(obito, user_id):
        try:
            user = await obito.col.find_one({'_id': int(user_id)})
            return user.get('author', None) if user else None
        except Exception as e:
            logging.error(f"Error getting author for user {user_id}: {e}")
            return None

    async def set_author(obito, user_id, author):
        try:
            await obito.col.update_one({'_id': int(user_id)}, {'$set': {'author': author}})
        except Exception as e:
            logging.error(f"Error setting author for user {user_id}: {e}")

    async def get_artist(obito, user_id):
        try:
            user = await obito.col.find_one({'_id': int(user_id)})
            return user.get('artist', None) if user else None
        except Exception as e:
            logging.error(f"Error getting artist for user {user_id}: {e}")
            return None

    async def set_artist(obito, user_id, artist):
        try:
            await obito.col.update_one({'_id': int(user_id)}, {'$set': {'artist': artist}})
        except Exception as e:
            logging.error(f"Error setting artist for user {user_id}: {e}")

    async def get_audio(obito, user_id):
        try:
            user = await obito.col.find_one({'_id': int(user_id)})
            return user.get('audio', None) if user else None
        except Exception as e:
            logging.error(f"Error getting audio for user {user_id}: {e}")
            return None

    async def set_audio(obito, user_id, audio):
        try:
            await obito.col.update_one({'_id': int(user_id)}, {'$set': {'audio': audio}})
        except Exception as e:
            logging.error(f"Error setting audio for user {user_id}: {e}")

    async def get_subtitle(obito, user_id):
        try:
            user = await obito.col.find_one({'_id': int(user_id)})
            return user.get('subtitle', None) if user else None
        except Exception as e:
            logging.error(f"Error getting subtitle for user {user_id}: {e}")
            return None

    async def set_subtitle(obito, user_id, subtitle):
        try:
            await obito.col.update_one({'_id': int(user_id)}, {'$set': {'subtitle': subtitle}})
        except Exception as e:
            logging.error(f"Error setting subtitle for user {user_id}: {e}")

    async def get_video(obito, user_id):
        try:
            user = await obito.col.find_one({'_id': int(user_id)})
            return user.get('video', None) if user else None
        except Exception as e:
            logging.error(f"Error getting video for user {user_id}: {e}")
            return None

    async def set_video(obito, user_id, video):
        try:
            await obito.col.update_one({'_id': int(user_id)}, {'$set': {'video': video}})
        except Exception as e:
            logging.error(f"Error setting video for user {user_id}: {e}")

    async def set_user_choice(obito, user_id: int, rename_mode: str) -> bool:
        for attempt in range(3):
            try:
                await obito.col.update_one(
                    {"_id": user_id},
                    {
                        "$set": {
                            "rename_mode": rename_mode,
                            "extra_name": "obito",
                            "updated_at": datetime.datetime.utcnow()
                        }
                    },
                    upsert=True
                )
                logging.info(f"Saved rename_mode '{rename_mode}' for user {user_id}")
                return True
            except Exception as e:
                logging.error(f"Error saving user choice for {user_id}, attempt {attempt+1}: {str(e)}")
                if attempt < 2:
                    await asyncio.sleep(1)
                else:
                    return False

    async def get_user_choice(obito, user_id: int) -> Optional[str]:
        try:
            user = await obito.col.find_one({"_id": user_id})
            rename_mode = user.get("rename_mode") if user else None
            logging.info(f"Retrieved rename_mode '{rename_mode}' for user {user_id}")
            return rename_mode
        except Exception as e:
            logging.error(f"Error retrieving user choice for {user_id}: {str(e)}")
            return None

    async def delete_user_choice(obito, user_id: int) -> bool:
        try:
            result = await obito.col.update_one(
                {"_id": user_id},
                {"$unset": {"rename_mode": "", "extra_name": "", "updated_at": ""}}
            )
            logging.info(f"Deleted rename_mode for user {user_id}")
            return result.modified_count > 0
        except Exception as e:
            logging.error(f"Error deleting user choice for {user_id}: {str(e)}")
            return False

    async def add_upload(obito, user_id: int, file_name: str):
        try:
            await obito.col.update_one(
                {"_id": user_id},
                {"$push": {"uploads": {"file_name": file_name, "date": datetime.datetime.utcnow()}}}
            )
            logging.info(f"Added upload '{file_name}' for user {user_id}")
        except Exception as e:
            logging.error(f"Error adding upload for user {user_id}: {e}")

    async def get_uploads(obito, user_id: int):
        try:
            user = await obito.col.find_one({"_id": user_id})
            return user.get("uploads", []) if user else []
        except Exception as e:
            logging.error(f"Error getting uploads for user {user_id}: {e}")
            return []

    async def set_telegram_handle(obito, user_id: int, handle: str):
        try:
            handle = handle.strip() if handle else None
            await obito.col.update_one(
                {"_id": user_id},
                {"$set": {"telegram_handle": handle}}
            )
            logging.info(f"Set telegram_handle '{handle}' for user {user_id}")
        except Exception as e:
            logging.error(f"Error setting telegram_handle for user {user_id}: {e}")

    async def get_telegram_handle(obito, user_id: int):
        try:
            user = await obito.col.find_one({"_id": user_id})
            return user.get("telegram_handle", None) if user else None
        except Exception as e:
            logging.error(f"Error getting telegram_handle for user {user_id}: {e}")
            return None

    async def set_upscale_scale(obito, user_id: int, scale: str):
        try:
            await obito.col.update_one(
                {"_id": user_id},
                {"$set": {"upscale_scale": scale}}
            )
            logging.info(f"Set upscale_scale '{scale}' for user {user_id}")
        except Exception as e:
            logging.error(f"Error setting upscale_scale for user {user_id}: {e}")

    async def get_upscale_scale(obito, user_id: int):
        try:
            user = await obito.col.find_one({"_id": user_id})
            return user.get("upscale_scale", "2:2") if user else "2:2"
        except Exception as e:
            logging.error(f"Error getting upscale_scale for user {user_id}: {e}")
            return "2:2"

    async def set_exthum_timestamp(obito, user_id: int, timestamp: float):
        try:
            await obito.col.update_one(
                {"_id": user_id},
                {"$set": {"exthum_timestamp": timestamp}}
            )
            logging.info(f"Set exthum_timestamp '{timestamp}' for user {user_id}")
        except Exception as e:
            logging.error(f"Error setting exthum_timestamp for user {user_id}: {e}")

    async def get_exthum_timestamp(obito, user_id: int):
        try:
            user = await obito.col.find_one({"_id": user_id})
            return user.get("exthum_timestamp", None) if user else None
        except Exception as e:
            logging.error(f"Error getting exthum_timestamp for user {user_id}: {e}")
            return None

    async def send_to_dump_channel(obito, client, file_path: str, caption: str = None) -> bool:
        if not obito.dump_channel:
            logging.warning("DUMP_CHANNEL not configured")
            return False
        try:
            if not os.path.exists(file_path):
                logging.error(f"File {file_path} does not exist for DUMP_CHANNEL")
                return False
            await client.send_document(
                chat_id=obito.dump_channel,
                document=file_path,
                caption=caption or "Dumped file"
            )
            logging.info(f"Sent file {file_path} to DUMP_CHANNEL {obito.dump_channel}")
            return True
        except Exception as e:
            logging.error(f"Error sending file to DUMP_CHANNEL: {str(e)}")
            return False

    # New method for /clear
    async def clear_user_tasks(obito, user_id: int) -> bool:
        """
        Clears task-related data (uploads) for the user in the database.
        """
        for attempt in range(3):  # Retry for robustness
            try:
                result = await obito.col.update_one(
                    {"_id": int(user_id)},
                    {"$set": {"uploads": []}},
                    upsert=False
                )
                logging.info(f"Cleared uploads for user {user_id}, modified: {result.modified_count}")
                return result.modified_count > 0
            except Exception as e:
                logging.error(f"Error clearing tasks for user {user_id}, attempt {attempt+1}: {e}")
                if attempt < 2:
                    await asyncio.sleep(1)
        return False

    # New helper method for /upscale
    async def get_upscale_factor(obito, user_id: int) -> float:
        """
        Converts upscale_scale (e.g., '2:2') to a float for /upscale command.
        """
        try:
            scale = await obito.get_upscale_scale(user_id)
            if not scale or ":" not in scale:
                logging.warning(f"Invalid upscale_scale '{scale}' for user {user_id}, using default")
                return 2.0
            factor = float(scale.split(":")[0])
            return max(1.0, min(factor, 5.0))  # Clamp between 1x and 5x
        except (ValueError, AttributeError, Exception) as e:
            logging.error(f"Error parsing upscale factor for user {user_id}: {e}")
            return 2.0  # Default to 2x

codeflixbots = Database()
