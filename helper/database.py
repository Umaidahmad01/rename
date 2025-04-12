import motor.motor_asyncio
import datetime
import pytz
from config import DB_URL, DB_NAME, DUMP_CHANNEL
import logging
from .utils import send_log
from pymongo import MongoClient
from typing import Optional

# Database class with all functionality
class Database:
    def __init__(obito, uri: str = DB_URL, db_name: str = DB_NAME) -> None:
        # Async MongoDB connection
        try:
            obito._async_client = motor.motor_asyncio.AsyncIOMotorClient(uri)
            obito._async_client.server_info()  # Check connection
            logging.info("Successfully connected to async MongoDB")
        except Exception as e:
            logging.error(f"Failed to connect to async MongoDB: {e}")
            raise e
        
        # Sync MongoDB connection
        try:
            obito.client = MongoClient(uri)
            logging.info("Successfully connected to sync MongoDB")
        except Exception as e:
            logging.error(f"Failed to connect to sync MongoDB: {e}")
            raise e

        # Async collections
        obito.codeflixbots = obito._async_client[db_name]
        obito.col = obito.codeflixbots.user

        # Sync collections
        obito.db = obito.client[db_name]
        obito.users = obito.db.users  # Collection for storing user data

        # Store DUMP_CHANNEL for potential use
        obito.dump_channel = DUMP_CHANNEL

    def new_user(obito, id):
        return dict(
            _id=int(id),
            join_date=datetime.date.today().isoformat(),
            file_id=None,
            caption=None,
            metadata=True,
            metadata_code="Telegram : @Codeflix_Bots",
            format_template=None,
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
        user = await obito.col.find_one({'_id': int(user_id)})
        return user.get('metadata', "Off")

    async def set_metadata(obito, user_id, metadata):
        await obito.col.update_one({'_id': int(user_id)}, {'$set': {'metadata': metadata}})

    async def get_title(obito, user_id):
        user = await obito.col.find_one({'_id': int(user_id)})
        return user.get('title', 'Encoded by @Animes_Sub_Society')

    async def set_title(obito, user_id, title):
        await obito.col.update_one({'_id': int(user_id)}, {'$set': {'title': title}})

    async def get_author(obito, user_id):
        user = await obito.col.find_one({'_id': int(user_id)})
        return user.get('author', '@Animes_Sub_Society')

    async def set_author(obito, user_id, author):
        await obito.col.update_one({'_id': int(user_id)}, {'$set': {'author': author}})

    async def get_artist(obito, user_id):
        user = await obito.col.find_one({'_id': int(user_id)})
        return user.get('artist', '@Animes_Sub_Society')

    async def set_artist(obito, user_id, artist):
        await obito.col.update_one({'_id': int(user_id)}, {'$set': {'artist': artist}})

    async def get_audio(obito, user_id):
        user = await obito.col.find_one({'_id': int(user_id)})
        return user.get('audio', 'By @Animes_Sub_Society')

    async def set_audio(obito, user_id, audio):
        await obito.col.update_one({'_id': int(user_id)}, {'$set': {'audio': audio}})

    async def get_subtitle(obito, user_id):
        user = await obito.col.find_one({'_id': int(user_id)})
        return user.get('subtitle', 'By @Animes_Sub_Society')

    async def set_subtitle(obito, user_id, subtitle):
        await obito.col.update_one({'_id': int(user_id)}, {'$set': {'subtitle': subtitle}})

    async def get_video(obito, user_id):
        user = await obito.col.find_one({'_id': int(user_id)})
        return user.get('video', 'Encoded By @Animes_Sub_Society')

    async def set_video(obito, user_id, video):
        await obito.col.update_one({'_id': int(user_id)}, {'$set': {'video': video}})

    # Synchronous methods for rename mode
    def set_user_choice(obito, user_id: int, rename_mode: str) -> bool:
        """
        Save user's rename mode choice and add extra name 'obito' in MongoDB
        """
        try:
            obito.users.update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "rename_mode": rename_mode,
                        "extra_name": "obito",
                        "updated_at": datetime.datetime.utcnow()
                    }
                },
                upsert=True
            )
            return True
        except Exception as e:
            logging.error(f"Error saving user choice: {str(e)}")
            return False

    def get_user_choice(obito, user_id: int) -> Optional[str]:
        """
        Retrieve user's rename mode from MongoDB
        """
        try:
            user: Optional[dict] = obito.users.find_one({"user_id": user_id})
            return user.get("rename_mode") if user else None
        except Exception as e:
            logging.error(f"Error retrieving user choice: {str(e)}")
            return None

    def delete_user_choice(obito, user_id: int) -> bool:
        """
        Delete user's rename mode from MongoDB after processing
        """
        try:
            obito.users.delete_one({"user_id": user_id})
            return True
        except Exception as e:
            logging.error(f"Error deleting user choice: {str(e)}")
            return False

# Initialize the database
codeflixbots = Database(DB_URL, DB_NAME)
