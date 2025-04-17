import logging
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionError, OperationFailure
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

class Database:
    def __init__(obito):
        obito.client = AsyncIOMotorClient(
            Config.DB_URL,
            maxPoolSize=100,
            minPoolSize=10,
            serverSelectionTimeoutMS=5000
        )
        obito.db = obito.client[Config.DB_NAME]
        obito.users = obito.db.users
        logger.info("Database initialized")

    async def add_user(obito, client, message):
        user_id = message.from_user.id
        try:
            async with asyncio.timeout(5):
                user = await obito.users.find_one({"user_id": user_id})
                if not user:
                    await obito.users.insert_one({
                        "user_id": user_id,
                        "rename_mode": "filename",
                        "custom_suffix": None,
                        "format_template": None,
                        "metadata_enabled": "Off",
                        "title": None,
                        "artist": None,
                        "author": None,
                        "video_title": None,
                        "audio_title": None,
                        "subtitle": None,
                        "caption": None,
                        "thumbnail": None
                    })
                    logger.info(f"Added user {user_id} to database")
                else:
                    logger.debug(f"User {user_id} already exists")
        except asyncio.TimeoutError:
            logger.error(f"Timeout adding user {user_id}")
        except Exception as e:
            logger.error(f"Error adding user {user_id}: {e}")

    async def set_user_choice(obito, user_id: int, rename_mode: str):
        max_retries = 3
        for attempt in range(max_retries):
            try:
                async with asyncio.timeout(5):
                    await obito.users.update_one(
                        {"user_id": user_id},
                        {"$set": {"rename_mode": rename_mode}},
                        upsert=True
                    )
                    logger.info(f"Set rename_mode '{rename_mode}' for user {user_id}")
                    return
            except asyncio.TimeoutError:
                logger.warning(f"Timeout setting rename_mode for user {user_id} (attempt {attempt+1}/{max_retries})")
            except ConnectionError:
                logger.warning(f"Connection error setting rename_mode for user {user_id} (attempt {attempt+1}/{max_retries})")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Error setting rename_mode for user {user_id}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
        logger.error(f"Failed to set rename_mode for user {user_id} after {max_retries} attempts")

    async def get_user_choice(obito, user_id: int) -> str:
        max_retries = 3
        for attempt in range(max_retries):
            try:
                async with asyncio.timeout(5):
                    user = await obito.users.find_one({"user_id": user_id})
                    return user.get("rename_mode", "filename") if user else "filename"
            except asyncio.TimeoutError:
                logger.warning(f"Timeout getting rename_mode for user {user_id} (attempt {attempt+1}/{max_retries})")
            except ConnectionError:
                logger.warning(f"Connection error getting rename_mode for user {user_id} (attempt {attempt+1}/{max_retries})")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Error getting rename_mode for user {user_id}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
        logger.error(f"Failed to get rename_mode for user {user_id} after {max_retries} attempts")
        return "filename"

    async def set_custom_suffix(obito, user_id: int, suffix: str):
        max_retries = 3
        for attempt in range(max_retries):
            try:
                async with asyncio.timeout(5):
                    await obito.users.update_one(
                        {"user_id": user_id},
                        {"$set": {"custom_suffix": suffix}},
                        upsert=True
                    )
                    logger.info(f"Set custom_suffix '{suffix}' for user {user_id}")
                    return
            except asyncio.TimeoutError:
                logger.warning(f"Timeout setting custom_suffix for user {user_id} (attempt {attempt+1}/{max_retries})")
            except ConnectionError:
                logger.warning(f"Connection error setting custom_suffix for user {user_id} (attempt {attempt+1}/{max_retries})")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Error setting custom_suffix for user {user_id}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
        logger.error(f"Failed to set custom_suffix for user {user_id} after {max_retries} attempts")

    async def get_custom_suffix(obito, user_id: int) -> str:
        max_retries = 3
        for attempt in range(max_retries):
            try:
                async with asyncio.timeout(5):
                    user = await obito.users.find_one({"user_id": user_id})
                    return user.get("custom_suffix") if user else None
            except asyncio.TimeoutError:
                logger.warning(f"Timeout getting custom_suffix for user {user_id} (attempt {attempt+1}/{max_retries})")
            except ConnectionError:
                logger.warning(f"Connection error getting custom_suffix for user {user_id} (attempt {attempt+1}/{max_retries})")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Error getting custom_suffix for user {user_id}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
        logger.error(f"Failed to get custom_suffix for user {user_id} after {max_retries} attempts")
        return None

    async def set_format_template(obito, user_id: int, template: str):
        max_retries = 3
        for attempt in range(max_retries):
            try:
                async with asyncio.timeout(5):
                    await obito.users.update_one(
                        {"user_id": user_id},
                        {"$set": {"format_template": template}},
                        upsert=True
                    )
                    logger.info(f"Set format_template '{template}' for user {user_id}")
                    return
            except asyncio.TimeoutError:
                logger.warning(f"Timeout setting format_template for user {user_id} (attempt {attempt+1}/{max_retries})")
            except ConnectionError:
                logger.warning(f"Connection error setting format_template for user {user_id} (attempt {attempt+1}/{max_retries})")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Error setting format_template for user {user_id}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
        logger.error(f"Failed to set format_template for user {user_id} after {max_retries} attempts")

    async def get_format_template(obito, user_id: int) -> str:
        max_retries = 3
        for attempt in range(max_retries):
            try:
                async with asyncio.timeout(5):
                    user = await obito.users.find_one({"user_id": user_id})
                    return user.get("format_template") if user else None
            except asyncio.TimeoutError:
                logger.warning(f"Timeout getting format_template for user {user_id} (attempt {attempt+1}/{max_retries})")
            except ConnectionError:
                logger.warning(f"Connection error getting format_template for user {user_id} (attempt {attempt+1}/{max_retries})")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Error getting format_template for user {user_id}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
        logger.error(f"Failed to get format_template for user {user_id} after {max_retries} attempts")
        return None

    async def set_metadata(obito, user_id: int, status: str):
        max_retries = 3
        for attempt in range(max_retries):
            try:
                async with asyncio.timeout(5):
                    await obito.users.update_one(
                        {"user_id": user_id},
                        {"$set": {"metadata_enabled": status}},
                        upsert=True
                    )
                    logger.info(f"Set metadata_enabled '{status}' for user {user_id}")
                    return
            except asyncio.TimeoutError:
                logger.warning(f"Timeout setting metadata_enabled for user {user_id} (attempt {attempt+1}/{max_retries})")
            except ConnectionError:
                logger.warning(f"Connection error setting metadata_enabled for user {user_id} (attempt {attempt+1}/{max_retries})")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Error setting metadata_enabled for user {user_id}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
        logger.error(f"Failed to set metadata_enabled for user {user_id} after {max_retries} attempts")

    async def get_metadata(obito, user_id: int) -> str:
        max_retries = 3
        for attempt in range(max_retries):
            try:
                async with asyncio.timeout(5):
                    user = await obito.users.find_one({"user_id": user_id})
                    return user.get("metadata_enabled", "Off") if user else "Off"
            except asyncio.TimeoutError:
                logger.warning(f"Timeout getting metadata_enabled for user {user_id} (attempt {attempt+1}/{max_retries})")
            except ConnectionError:
                logger.warning(f"Connection error getting metadata_enabled for user {user_id} (attempt {attempt+1}/{max_retries})")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Error getting metadata_enabled for user {user_id}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
        logger.error(f"Failed to get metadata_enabled for user {user_id} after {max_retries} attempts")
        return "Off"

    async def set_title(obito, user_id: int, title: str):
        max_retries = 3
        for attempt in range(max_retries):
            try:
                async with asyncio.timeout(5):
                    await obito.users.update_one(
                        {"user_id": user_id},
                        {"$set": {"title": title}},
                        upsert=True
                    )
                    logger.info(f"Set title '{title}' for user {user_id}")
                    return
            except asyncio.TimeoutError:
                logger.warning(f"Timeout setting title for user {user_id} (attempt {attempt+1}/{max_retries})")
            except ConnectionError:
                logger.warning(f"Connection error setting title for user {user_id} (attempt {attempt+1}/{max_retries})")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Error setting title for user {user_id}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
        logger.error(f"Failed to set title for user {user_id} after {max_retries} attempts")

    async def get_title(obito, user_id: int) -> str:
        max_retries = 3
        for attempt in range(max_retries):
            try:
                async with asyncio.timeout(5):
                    user = await obito.users.find_one({"user_id": user_id})
                    return user.get("title") if user else None
            except asyncio.TimeoutError:
                logger.warning(f"Timeout getting title for user {user_id} (attempt {attempt+1}/{max_retries})")
            except ConnectionError:
                logger.warning(f"Connection error getting title for user {user_id} (attempt {attempt+1}/{max_retries})")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Error getting title for user {user_id}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
        logger.error(f"Failed to get title for user {user_id} after {max_retries} attempts")
        return None

    async def set_artist(obito, user_id: int, artist: str):
        max_retries = 3
        for attempt in range(max_retries):
            try:
                async with asyncio.timeout(5):
                    await obito.users.update_one(
                        {"user_id": user_id},
                        {"$set": {"artist": artist}},
                        upsert=True
                    )
                    logger.info(f"Set artist '{artist}' for user {user_id}")
                    return
            except asyncio.TimeoutError:
                logger.warning(f"Timeout setting artist for user {user_id} (attempt {attempt+1}/{max_retries})")
            except ConnectionError:
                logger.warning(f"Connection error setting artist for user {user_id} (attempt {attempt+1}/{max_retries})")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Error setting artist for user {user_id}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
        logger.error(f"Failed to set artist for user {user_id} after {max_retries} attempts")

    async def get_artist(obito, user_id: int) -> str:
        max_retries = 3
        for attempt in range(max_retries):
            try:
                async with asyncio.timeout(5):
                    user = await obito.users.find_one({"user_id": user_id})
                    return user.get("artist") if user else None
            except asyncio.TimeoutError:
                logger.warning(f"Timeout getting artist for user {user_id} (attempt {attempt+1}/{max_retries})")
            except ConnectionError:
                logger.warning(f"Connection error getting artist for user {user_id} (attempt {attempt+1}/{max_retries})")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Error getting artist for user {user_id}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
        logger.error(f"Failed to get artist for user {user_id} after {max_retries} attempts")
        return None

    async def set_author(obito, user_id: int, author: str):
        max_retries = 3
        for attempt in range(max_retries):
            try:
                async with asyncio.timeout(5):
                    await obito.users.update_one(
                        {"user_id": user_id},
                        {"$set": {"author": author}},
                        upsert=True
                    )
                    logger.info(f"Set author '{author}' for user {user_id}")
                    return
            except asyncio.TimeoutError:
                logger.warning(f"Timeout setting author for user {user_id} (attempt {attempt+1}/{max_retries})")
            except ConnectionError:
                logger.warning(f"Connection error setting author for user {user_id} (attempt {attempt+1}/{max_retries})")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Error setting author for user {user_id}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
        logger.error(f"Failed to set author for user {user_id} after {max_retries} attempts")

    async def get_author(obito, user_id: int) -> str:
        max_retries = 3
        for attempt in range(max_retries):
            try:
                async with asyncio.timeout(5):
                    user = await obito.users.find_one({"user_id": user_id})
                    return user.get("author") if user else None
            except asyncio.TimeoutError:
                logger.warning(f"Timeout getting author for user {user_id} (attempt {attempt+1}/{max_retries})")
            except ConnectionError:
                logger.warning(f"Connection error getting author for user {user_id} (attempt {attempt+1}/{max_retries})")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Error getting author for user {user_id}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
        logger.error(f"Failed to get author for user {user_id} after {max_retries} attempts")
        return None

    async def set_video(obito, user_id: int, video_title: str):
        max_retries = 3
        for attempt in range(max_retries):
            try:
                async with asyncio.timeout(5):
                    await obito.users.update_one(
                        {"user_id": user_id},
                        {"$set": {"video_title": video_title}},
                        upsert=True
                    )
                    logger.info(f"Set video_title '{video_title}' for user {user_id}")
                    return
            except asyncio.TimeoutError:
                logger.warning(f"Timeout setting video_title for user {user_id} (attempt {attempt+1}/{max_retries})")
            except ConnectionError:
                logger.warning(f"Connection error setting video_title for user {user_id} (attempt {attempt+1}/{max_retries})")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Error setting video_title for user {user_id}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
        logger.error(f"Failed to set video_title for user {user_id} after {max_retries} attempts")

    async def get_video(obito, user_id: int) -> str:
        max_retries = 3
        for attempt in range(max_retries):
            try:
                async with asyncio.timeout(5):
                    user = await obito.users.find_one({"user_id": user_id})
                    return user.get("video_title") if user else None
            except asyncio.TimeoutError:
                logger.warning(f"Timeout getting video_title for user {user_id} (attempt {attempt+1}/{max_retries})")
            except ConnectionError:
                logger.warning(f"Connection error getting video_title for user {user_id} (at
