import motor.motor_asyncio, datetime, pytz
from config import Config
import logging  # Added for logging errors and important information
from .utils import send_log
from pymongo import MongoClient

class Database:
    def __init__(self, uri, database_name):
        try:
            self._client = motor.motor_asyncio.AsyncIOMotorClient(uri)
            self._client.server_info()  # This will raise an exception if the connection fails
            logging.info("Successfully connected to MongoDB")
        except Exception as e:
            logging.error(f"Failed to connect to MongoDB: {e}")
            raise e  # Re-raise the exception after logging it
        self.codeflixbots = self._client[database_name]
        self.col = self.codeflixbots.user

    def new_user(self, id):
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

    async def add_user(self, b, m):
        u = m.from_user
        if not await self.is_user_exist(u.id):
            user = self.new_user(u.id)
            try:
                await self.col.insert_one(user)
                await send_log(b, u)
            except Exception as e:
                logging.error(f"Error adding user {u.id}: {e}")

    async def is_user_exist(self, id):
        try:
            user = await self.col.find_one({"_id": int(id)})
            return bool(user)
        except Exception as e:
            logging.error(f"Error checking if user {id} exists: {e}")
            return False

    async def total_users_count(self):
        try:
            count = await self.col.count_documents({})
            return count
        except Exception as e:
            logging.error(f"Error counting users: {e}")
            return 0

    async def get_all_users(self):
        try:
            all_users = self.col.find({})
            return all_users
        except Exception as e:
            logging.error(f"Error getting all users: {e}")
            return None

    async def delete_user(self, user_id):
        try:
            await self.col.delete_many({"_id": int(user_id)})
        except Exception as e:
            logging.error(f"Error deleting user {user_id}: {e}")

    async def set_thumbnail(self, id, file_id):
        try:
            await self.col.update_one({"_id": int(id)}, {"$set": {"file_id": file_id}})
        except Exception as e:
            logging.error(f"Error setting thumbnail for user {id}: {e}")

    async def get_thumbnail(self, id):
        try:
            user = await self.col.find_one({"_id": int(id)})
            return user.get("file_id", None) if user else None
        except Exception as e:
            logging.error(f"Error getting thumbnail for user {id}: {e}")
            return None

    async def set_caption(self, id, caption):
        try:
            await self.col.update_one({"_id": int(id)}, {"$set": {"caption": caption}})
        except Exception as e:
            logging.error(f"Error setting caption for user {id}: {e}")

    async def get_caption(self, id):
        try:
            user = await self.col.find_one({"_id": int(id)})
            return user.get("caption", None) if user else None
        except Exception as e:
            logging.error(f"Error getting caption for user {id}: {e}")
            return None

    async def set_format_template(self, id, format_template):
        try:
            await self.col.update_one(
                {"_id": int(id)}, {"$set": {"format_template": format_template}}
            )
        except Exception as e:
            logging.error(f"Error setting format template for user {id}: {e}")

    async def get_format_template(self, id):
        try:
            user = await self.col.find_one({"_id": int(id)})
            return user.get("format_template", None) if user else None
        except Exception as e:
            logging.error(f"Error getting format template for user {id}: {e}")
            return None

    async def set_media_preference(self, id, media_type):
        try:
            await self.col.update_one(
                {"_id": int(id)}, {"$set": {"media_type": media_type}}
            )
        except Exception as e:
            logging.error(f"Error setting media preference for user {id}: {e}")

    async def get_media_preference(self, id):
        try:
            user = await self.col.find_one({"_id": int(id)})
            return user.get("media_type", None) if user else None
        except Exception as e:
            logging.error(f"Error getting media preference for user {id}: {e}")
            return None

    async def get_metadata(self, user_id):
        user = await self.col.find_one({'_id': int(user_id)})
        return user.get('metadata', "Off")

    async def set_metadata(self, user_id, metadata):
        await self.col.update_one({'_id': int(user_id)}, {'$set': {'metadata': metadata}})

    async def get_title(self, user_id):
        user = await self.col.find_one({'_id': int(user_id)})
        return user.get('title', 'Encoded by @Animes_Cruise')

    async def set_title(self, user_id, title):
        await self.col.update_one({'_id': int(user_id)}, {'$set': {'title': title}})

    async def get_author(self, user_id):
        user = await self.col.find_one({'_id': int(user_id)})
        return user.get('author', '@Animes_Cruise')

    async def set_author(self, user_id, author):
        await self.col.update_one({'_id': int(user_id)}, {'$set': {'author': author}})

    async def get_artist(self, user_id):
        user = await self.col.find_one({'_id': int(user_id)})
        return user.get('artist', '@Animes_Cruise')

    async def set_artist(self, user_id, artist):
        await self.col.update_one({'_id': int(user_id)}, {'$set': {'artist': artist}})

    async def get_audio(self, user_id):
        user = await self.col.find_one({'_id': int(user_id)})
        return user.get('audio', 'By @Animes_Cruise')

    async def set_audio(self, user_id, audio):
        await self.col.update_one({'_id': int(user_id)}, {'$set': {'audio': audio}})

    async def get_subtitle(self, user_id):
        user = await self.col.find_one({'_id': int(user_id)})
        return user.get('subtitle', "By @Animes_Cruise")

    async def set_subtitle(self, user_id, subtitle):
        await self.col.update_one({'_id': int(user_id)}, {'$set': {'subtitle': subtitle}})

    async def get_video(self, user_id):
        user = await self.col.find_one({'_id': int(user_id)})
        return user.get('video', 'Encoded By @Animes_Cruise')

    async def set_video(self, user_id, video):
        await self.col.update_one({'_id': int(user_id)}, {'$set': {'video': video}})


codeflixbots = Database(Config.DB_URL, Config.DB_NAME)



class Database:
    def __init__(self, mongo_uri="Config.DB_URL, Config.DB_NAME"):
        self.client = MongoClient(mongo_uri)
        self.db = self.client[db_name]
        self.tokens_collection = self.db["tokens"]
        self.settings_collection = self.db["settings"]  # Reward settings ke liye naya collection

    # Token info get karne ke liye
    def get_token_info(self, chat_id):
        token_data = self.tokens_collection.find_one({"chat_id": chat_id})
        if token_data:
            status = "ON" if token_data.get("status", False) else "OFF"
            current_token = token_data.get("token", "Koi token set nahi hai")
            user_tokens = token_data.get("user_tokens", 0)  # User ke tokens
            return {
                "status": status,
                "token": current_token,
                "user_tokens": user_tokens,
                "api": "https://api.example.com",
                "site": "https://example.com"
            }
        return {
            "status": "OFF",
            "token": "Koi token set nahi hai",
            "user_tokens": 0,
            "api": "https://api.example.com",
            "site": "https://example.com"
        }

    # Token set ya update karne ke liye
    def set_token(self, chat_id, token):
        self.tokens_collection.update_one(
            {"chat_id": chat_id},
            {"$set": {"token": token, "status": True}},
            upsert=True
        )

    # Token ON karne ke liye
    def on_token(self, chat_id):
        self.tokens_collection.update_one(
            {"chat_id": chat_id},
            {"$set": {"status": True}},
            upsert=True
        )

    # Token OFF karne ke liye
    def off_token(self, chat_id):
        self.tokens_collection.update_one(
            {"chat_id": chat_id},
            {"$set": {"status": False}},
            upsert=True
        )

    # Token change karne ke liye
    def change_token(self, chat_id, new_token):
        self.set_token(chat_id, new_token)

    # User ko token dene ke liye
    def give_token(self, chat_id, amount):
        self.tokens_collection.update_one(
            {"chat_id": chat_id},
            {"$inc": {"user_tokens": amount}},  # Tokens increment karo
            upsert=True
        )

    # Reward amount set karne ke liye
    def set_reward(self, amount):
        self.settings_collection.update_one(
            {"key": "reward_amount"},
            {"$set": {"value": amount}},
            upsert=True
        )

    # Reward amount get karne ke liye
    def get_reward(self):
        reward_data = self.settings_collection.find_one({"key": "reward_amount"})
        return reward_data["value"] if reward_data else 10  # Default 10 tokens

    # Solve karne pe reward dene ke liye (example function)
    def reward_user(self, chat_id):
        reward_amount = self.get_reward()
        self.give_token(chat_id, reward_amount)
        return reward_amount
