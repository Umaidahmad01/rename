import logging
import os
from motor.motor_asyncio import AsyncIOMotorClient
from config import Config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Database:
    def __init__(self, uri: str = Config.DB_URL, db_name: str = Config.DB_NAME):
        try:
            self._async_client = AsyncIOMotorClient(uri)
            self._async_client.server_info()
            logger.info("Successfully connected to async MongoDB")
        except Exception as e:
            logger.error(f"Failed to connect to async MongoDB: {e}")
            raise e

        self.db = self._async_client[db_name]
        self.users = self.db.users

    async def set_format_template(self, user_id: int, template: str) -> bool:
        try:
            await self.users.update_one(
                {'_id': user_id},
                {'$set': {'format_template': template}},
                upsert=True
            )
            logger.info(f"Set format_template for user {user_id}: {template}")
            return True
        except Exception as e:
            logger.error(f"Error setting format_template for user {user_id}: {e}")
            return False

    async def get_format_template(self, user_id: int) -> str:
        try:
            user = await self.users.find_one({'_id': user_id})
            template = user.get('format_template') if user else None
            logger.info(f"Retrieved format_template for user {user_id}: {template}")
            return template
        except Exception as e:
            logger.error(f"Error getting format_template for user {user_id}: {e}")
            return None

    async def set_custom_suffix(self, user_id: int, suffix: str) -> bool:
        try:
            suffix = suffix.strip() if suffix else None
            await self.users.update_one(
                {'_id': user_id},
                {'$set': {'custom_suffix': suffix}},
                upsert=True
            )
            logger.info(f"Set custom_suffix for user {user_id}: {suffix}")
            return True
        except Exception as e:
            logger.error(f"Error setting custom_suffix for user {user_id}: {e}")
            return False

    async def get_custom_suffix(self, user_id: int) -> str:
        try:
            user = await self.users.find_one({'_id': user_id})
            suffix = user.get('custom_suffix') if user else None
            logger.info(f"Retrieved custom_suffix for user {user_id}: {suffix}")
            return suffix
        except Exception as e:
            logger.error(f"Error getting custom_suffix for user {user_id}: {e}")
            return None

    async def set_metadata_field(self, user_id: int, field: str, value: str) -> bool:
        try:
            await self.users.update_one(
                {'_id': user_id},
                {'$set': {f'metadata.{field}': value}},
                upsert=True
            )
            logger.info(f"Set metadata {field} for user {user_id}: {value}")
            return True
        except Exception as e:
            logger.error(f"Error setting metadata {field} for user {user_id}: {e}")
            return False

    async def get_metadata_field(self, user_id: int, field: str) -> str:
        try:
            user = await self.users.find_one({'_id': user_id})
            value = user.get('metadata', {}).get(field) if user else None
            logger.info(f"Retrieved metadata {field} for user {user_id}: {value}")
            return value
        except Exception as e:
            logger.error(f"Error getting metadata {field} for user {user_id}: {e}")
            return None

    async def set_metadata_enabled(self, user_id: int, enabled: str) -> bool:
        try:
            await self.users.update_one(
                {'_id': user_id},
                {'$set': {'metadata_enabled': enabled}},
                upsert=True
            )
            logger.info(f"Set metadata_enabled for user {user_id}: {enabled}")
            return True
        except Exception as e:
            logger.error(f"Error setting metadata_enabled for user {user_id}: {e}")
            return False

    async def get_metadata_enabled(self, user_id: int) -> str:
        try:
            user = await self.users.find_one({'_id': user_id})
            enabled = user.get('metadata_enabled', 'On') if user else 'On'
            logger.info(f"Retrieved metadata_enabled for user {user_id}: {enabled}")
            return enabled
        except Exception as e:
            logger.error(f"Error getting metadata_enabled for user {user_id}: {e}")
            return 'On'

    async def set_media_preference(self, user_id: int, media_type: str) -> bool:
        try:
            await self.users.update_one(
                {'_id': user_id},
                {'$set': {'media_preference': media_type}},
                upsert=True
            )
            logger.info(f"Set media_preference for user {user_id}: {media_type}")
            return True
        except Exception as e:
            logger.error(f"Error setting media_preference for user {user_id}: {e}")
            return False

    async def get_media_preference(self, user_id: int) -> str:
        try:
            user = await self.users.find_one({'_id': user_id})
            media_type = user.get('media_preference') if user else None
            logger.info(f"Retrieved media_preference for user {user_id}: {media_type}")
            return media_type
        except Exception as e:
            logger.error(f"Error getting media_preference for user {user_id}: {e}")
            return None

    async def set_thumbnail(self, user_id: int, file_id: str) -> bool:
        try:
            await self.users.update_one(
                {'_id': user_id},
                {'$set': {'thumbnail': file_id}},
                upsert=True
            )
            logger.info(f"Set thumbnail for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error setting thumbnail for user {user_id}: {e}")
            return False

    async def get_thumbnail(self, user_id: int) -> str:
        try:
            user = await self.users.find_one({'_id': user_id})
            thumbnail = user.get('thumbnail') if user else None
            logger.info(f"Retrieved thumbnail for user {user_id}: {thumbnail}")
            return thumbnail
        except Exception as e:
            logger.error(f"Error getting thumbnail for user {user_id}: {e}")
            return None

    async def set_upscale_scale(self, user_id: int, scale: str) -> bool:
        try:
            await self.users.update_one(
                {'_id': user_id},
                {'$set': {'upscale_scale': scale}},
                upsert=True
            )
            logger.info(f"Set upscale_scale for user {user_id}: {scale}")
            return True
        except Exception as e:
            logger.error(f"Error setting upscale_scale for user {user_id}: {e}")
            return False

    async def get_upscale_scale(self, user_id: int) -> str:
        try:
            user = await self.users.find_one({'_id': user_id})
            scale = user.get('upscale_scale', '2:2') if user else '2:2'
            logger.info(f"Retrieved upscale_scale for user {user_id}: {scale}")
            return scale
        except Exception as e:
            logger.error(f"Error getting upscale_scale for user {user_id}: {e}")
            return '2:2'

    async def set_exthum_timestamp(self, user_id: int, timestamp: float) -> bool:
        try:
            await self.users.update_one(
                {'_id': user_id},
                {'$set': {'exthum_timestamp': timestamp}},
                upsert=True
            )
            logger.info(f"Set exthum_timestamp for user {user_id}: {timestamp}")
            return True
        except Exception as e:
            logger.error(f"Error setting exthum_timestamp for user {user_id}: {e}")
            return False

    async def get_exthum_timestamp(self, user_id: int) -> float:
        try:
            user = await self.users.find_one({'_id': user_id})
            timestamp = user.get('exthum_timestamp') if user else None
            logger.info(f"Retrieved exthum_timestamp for user {user_id}: {timestamp}")
            return timestamp
        except Exception as e:
            logger.error(f"Error getting exthum_timestamp for user {user_id}: {e}")
            return None

    async def set_user_choice(self, user_id: int, rename_mode: str) -> bool:
        try:
            await self.users.update_one(
                {'_id': user_id},
                {'$set': {'rename_mode': rename_mode}},
                upsert=True
            )
            logger.info(f"Set rename_mode for user {user_id}: {rename_mode}")
            return True
        except Exception as e:
            logger.error(f"Error setting rename_mode for user {user_id}: {e}")
            return False

    async def get_user_choice(self, user_id: int) -> str:
        try:
            user = await self.users.find_one({'_id': user_id})
            rename_mode = user.get('rename_mode') if user else None
            logger.info(f"Retrieved rename_mode for user {user_id}: {rename_mode}")
            return rename_mode
        except Exception as e:
            logger.error(f"Error getting rename_mode for user {user_id}: {e}")
            return None

codeflixbots = Database()
