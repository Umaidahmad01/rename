import logging
from motor.motor_asyncio import AsyncIOMotorClient
from config import Config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.client = AsyncIOMotorClient(Config.MONGO_URI)
        self.db = self.client.codeflixbots
        self.users = self.db.users
        logger.info("Database initialized with MongoDB connection")

    async def set_format_template(self, user_id: int, template: str) -> bool:
        """Set the file naming template for a user."""
        try:
            await self.users.update_one(
                {'user_id': user_id},
                {'$set': {'format_template': template}},
                upsert=True
            )
            logger.info(f"Set format_template for user {user_id}: {template}")
            return True
        except Exception as e:
            logger.error(f"Error setting format_template for user {user_id}: {e}")
            return False

    async def get_format_template(self, user_id: int) -> str:
        """Get the file naming template for a user."""
        try:
            user = await self.users.find_one({'user_id': user_id})
            template = user.get('format_template') if user else None
            logger.info(f"Retrieved format_template for user {user_id}: {template}")
            return template
        except Exception as e:
            logger.error(f"Error getting format_template for user {user_id}: {e}")
            return None

    async def set_custom_suffix(self, user_id: int, suffix: str) -> bool:
        """Set the custom suffix for a user."""
        try:
            await self.users.update_one(
                {'user_id': user_id},
                {'$set': {'custom_suffix': suffix}},
                upsert=True
            )
            logger.info(f"Set custom_suffix for user {user_id}: {suffix}")
            return True
        except Exception as e:
            logger.error(f"Error setting custom_suffix for user {user_id}: {e}")
            return False

    async def get_custom_suffix(self, user_id: int) -> str:
        """Get the custom suffix for a user."""
        try:
            user = await self.users.find_one({'user_id': user_id})
            suffix = user.get('custom_suffix') if user else None
            logger.info(f"Retrieved custom_suffix for user {user_id}: {suffix}")
            return suffix
        except Exception as e:
            logger.error(f"Error getting custom_suffix for user {user_id}: {e}")
            return None

    async def set_metadata_field(self, user_id: int, field: str, value: str) -> bool:
        """Set a metadata field for a user."""
        try:
            await self.users.update_one(
                {'user_id': user_id},
                {'$set': {f'metadata.{field}': value}},
                upsert=True
            )
            logger.info(f"Set metadata {field} for user {user_id}: {value}")
            return True
        except Exception as e:
            logger.error(f"Error setting metadata {field} for user {user_id}: {e}")
            return False

    async def get_metadata_field(self, user_id: int, field: str) -> str:
        """Get a metadata field for a user."""
        try:
            user = await self.users.find_one({'user_id': user_id})
            value = user.get('metadata', {}).get(field) if user else None
            logger.info(f"Retrieved metadata {field} for user {user_id}: {value}")
            return value
        except Exception as e:
            logger.error(f"Error getting metadata {field} for user {user_id}: {e}")
            return None

    async def set_media_preference(self, user_id: int, media_type: str) -> bool:
        """Set the media preference for a user."""
        try:
            await self.users.update_one(
                {'user_id': user_id},
                {'$set': {'media_preference': media_type}},
                upsert=True
            )
            logger.info(f"Set media_preference for user {user_id}: {media_type}")
            return True
        except Exception as e:
            logger.error(f"Error setting media_preference for user {user_id}: {e}")
            return False

    async def get_media_preference(self, user_id: int) -> str:
        """Get the media preference for a user."""
        try:
            user = await self.users.find_one({'user_id': user_id})
            media_type = user.get('media_preference') if user else None
            logger.info(f"Retrieved media_preference for user {user_id}: {media_type}")
            return media_type
        except Exception as e:
            logger.error(f"Error getting media_preference for user {user_id}: {e}")
            return None

    async def set_thumbnail(self, user_id: int, thumbnail: str) -> bool:
        """Set the thumbnail for a user."""
        try:
            await self.users.update_one(
                {'user_id': user_id},
                {'$set': {'thumbnail': thumbnail}},
                upsert=True
            )
            logger.info(f"Set thumbnail for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error setting thumbnail for user {user_id}: {e}")
            return False

    async def get_thumbnail(self, user_id: int) -> str:
        """Get the thumbnail for a user."""
        try:
            user = await self.users.find_one({'user_id': user_id})
            thumbnail = user.get('thumbnail') if user else None
            logger.info(f"Retrieved thumbnail for user {user_id}: {thumbnail}")
            return thumbnail
        except Exception as e:
            logger.error(f"Error getting thumbnail for user {user_id}: {e}")
            return None

    async def set_metadata_enabled(self, user_id: int, enabled: str) -> bool:
        """Set whether metadata is enabled for a user."""
        try:
            await self.users.update_one(
                {'user_id': user_id},
                {'$set': {'metadata_enabled': enabled}},
                upsert=True
            )
            logger.info(f"Set metadata_enabled for user {user_id}: {enabled}")
            return True
        except Exception as e:
            logger.error(f"Error setting metadata_enabled for user {user_id}: {e}")
            return False

    async def get_metadata(self, user_id: int) -> str:
        """Get whether metadata is enabled for a user."""
        try:
            user = await self.users.find_one({'user_id': user_id})
            enabled = user.get('metadata_enabled', 'On') if user else 'On'
            logger.info(f"Retrieved metadata_enabled for user {user_id}: {enabled}")
            return enabled
        except Exception as e:
            logger.error(f"Error getting metadata_enabled for user {user_id}: {e}")
            return 'On'

    async def set_user_choice(self, user_id: int, choice: str) -> bool:
        """Set the rename mode choice for a user."""
        try:
            await self.users.update_one(
                {'user_id': user_id},
                {'$set': {'rename_mode': choice}},
                upsert=True
            )
            logger.info(f"Set rename_mode for user {user_id}: {choice}")
            return True
        except Exception as e:
            logger.error(f"Error setting rename_mode for user {user_id}: {e}")
            return False

    async def get_user_choice(self, user_id: int) -> str:
        """Get the rename mode choice for a user."""
        try:
            user = await self.users.find_one({'user_id': user_id})
            choice = user.get('rename_mode') if user else None
            logger.info(f"Retrieved rename_mode for user {user_id}: {choice}")
            return choice
        except Exception as e:
            logger.error(f"Error getting rename_mode for user {user_id}: {e}")
            return None
