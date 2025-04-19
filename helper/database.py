import motor.motor_asyncio
from config import Config
from .utils import send_log

class Database:

    def __init__(obito, uri, database_name):
        obito._client = motor.motor_asyncio.AsyncIOMotorClient(uri)
        obito.codeflixbots = obito._client[database_name]
        obito.col = obito.codeflixbots.user

    def new_user(obito, id):
        return dict(
            _id=int(id),                                   
            file_id=None,  # Thumbnail
            caption=None,
            format_template=None,
            media_type=None,
            rename_mode="filename",  # Default rename mode
            metadata="Off",  # Metadata enabled/disabled
            title=None,  # Metadata fields
            author=None,
            artist=None,
            audio=None,
            subtitle=None,
            video=None
        )

    async def add_user(obito, b, m):
        u = m.from_user
        if not await obito.is_user_exist(u.id):
            user = obito.new_user(u.id)
            await obito.col.insert_one(user)            
            await send_log(b, u)

    async def is_user_exist(obito, id):
        user = await obito.col.find_one({'_id': int(id)})
        return bool(user)

    async def total_users_count(obito):
        count = await obito.col.count_documents({})
        return count

    async def get_all_users(obito):
        all_users = obito.col.find({})
        return all_users

    async def delete_user(obito, user_id):
        await obito.col.delete_many({'_id': int(user_id)})
    
    async def set_thumbnail(obito, id, file_id):
        await obito.col.update_one({'_id': int(id)}, {'$set': {'file_id': file_id}})

    async def get_thumbnail(obito, id):
        user = await obito.col.find_one({'_id': int(id)})
        return user.get('file_id', None)

    async def set_caption(obito, id, caption):
        await obito.col.update_one({'_id': int(id)}, {'$set': {'caption': caption}})

    async def get_caption(obito, id):
        user = await obito.col.find_one({'_id': int(id)})
        return user.get('caption', None)

    async def set_format_template(obito, id, format_template):
        await obito.col.update_one({'_id': int(id)}, {'$set': {'format_template': format_template}})

    async def get_format_template(obito, id):
        user = await obito.col.find_one({'_id': int(id)})
        return user.get('format_template', None)
        
    async def set_media_preference(obito, id, media_type):
        await obito.col.update_one({'_id': int(id)}, {'$set': {'media_type': media_type}})
        
    async def get_media_preference(obito, id):
        user = await obito.col.find_one({'_id': int(id)})
        return user.get('media_type', None)

    async def set_rename_mode(obito, id, mode):
        await obito.col.update_one({'_id': int(id)}, {'$set': {'rename_mode': mode}})

    async def get_rename_mode(obito, id):
        user = await obito.col.find_one({'_id': int(id)})
        return user.get('rename_mode', "filename")  # Default to filename

    # Metadata methods
    async def set_metadata(obito, id, metadata):
        await obito.col.update_one({'_id': int(id)}, {'$set': {'metadata': metadata}})

    async def get_metadata(obito, id):
        user = await obito.col.find_one({'_id': int(id)})
        return user.get('metadata', "Off")

    async def set_title(obito, id, title):
        await obito.col.update_one({'_id': int(id)}, {'$set': {'title': title}})

    async def get_title(obito, id):
        user = await obito.col.find_one({'_id': int(id)})
        return user.get('title', None)

    async def set_author(obito, id, author):
        await obito.col.update_one({'_id': int(id)}, {'$set': {'author': author}})

    async def get_author(obito, id):
        user = await obito.col.find_one({'_id': int(id)})
        return user.get('author', None)

    async def set_artist(obito, id, artist):
        await obito.col.update_one({'_id': int(id)}, {'$set': {'artist': artist}})

    async def get_artist(obito, id):
        user = await obito.col.find_one({'_id': int(id)})
        return user.get('artist', None)

    async def set_audio(obito, id, audio):
        await obito.col.update_one({'_id': int(id)}, {'$set': {'audio': audio}})

    async def get_audio(obito, id):
        user = await obito.col.find_one({'_id': int(id)})
        return user.get('audio', None)

    async def set_subtitle(obito, id, subtitle):
        await obito.col.update_one({'_id': int(id)}, {'$set': {'subtitle': subtitle}})

    async def get_subtitle(obito, id):
        user = await obito.col.find_one({'_id': int(id)})
        return user.get('subtitle', None)

    async def set_video(obito, id, video):
        await obito.col.update_one({'_id': int(id)}, {'$set': {'video': video}})

    async def get_video(obito, id):
        user = await obito.col.find_one({'_id': int(id)})
        return user.get('video', None)

codeflixbots = Database(Config.DB_URL, Config.DB_NAME)
