# Don't Remove Credit @VJ_Bots
# Subscribe YouTube Channel For Amazing Bot @Tech_VJ
# Ask Doubt on telegram @KingVJ01

from pyrogram import Client, filters
from info import CHANNELS
from database.ia_filterdb import save_file, clean_file_name
from database.users_chats_db import db

media_filter = filters.document | filters.video

@Client.on_message(filters.chat(CHANNELS) & media_filter)
async def media(bot, message):
    media = getattr(message, message.media.value, None)
    media.caption = message.caption
    result = await save_file(media)
    if result and result[0]:
        await notify_watchlist(bot, media)

async def notify_watchlist(bot, media):
    try:
        file_name = clean_file_name(media.file_name).lower()
    except Exception:
        return
    if not file_name:
        return

    try:
        watchers = await db.get_all_watchlist()
    except Exception as e:
        print(e)
        return

    for item in watchers:
        wl_name = (item.get('name') or '').strip().lower()
        if not wl_name or wl_name not in file_name:
            continue
        try:
            await bot.send_message(
                item['user_id'],
                f"<b>🎉 Gᴏᴏᴅ ɴᴇᴡs! \"{item['name']}\" ꜰʀᴏᴍ ʏᴏᴜʀ ᴡᴀᴛᴄʜʟɪsᴛ ɪs ɴᴏᴡ ᴀᴠᴀɪʟᴀʙʟᴇ. Sᴇᴀʀᴄʜ ꜰᴏʀ ɪᴛ ɴᴏᴡ! ⭐</b>"
            )
        except Exception as e:
            print(e)
        try:
            await db.remove_from_watchlist(item['user_id'], item['_id'])
        except Exception as e:
            print(e)
