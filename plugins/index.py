# Don't Remove Credit @VJ_Bots
# Subscribe YouTube Channel For Amazing Bot @Tech_VJ
# Ask Doubt on telegram @KingVJ01

import logging, re, asyncio, time
from utils import temp
from info import ADMINS
from pyrogram import Client, filters, enums
from pyrogram.errors import FloodWait, MessageNotModified
from pyrogram.errors.exceptions.bad_request_400 import ChannelInvalid, ChatAdminRequired, UsernameInvalid, UsernameNotModified
from info import INDEX_REQ_CHANNEL as LOG_CHANNEL
from database.ia_filterdb import save_file
from database.users_chats_db import db
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
lock = asyncio.Lock()

@Client.on_callback_query(filters.regex(r'^index'))
async def index_files(bot, query):
    if query.data.startswith('index_cancel'):
        temp.CANCEL = True
        return await query.answer("Cancelling Indexing")
    _, raju, chat, lst_msg_id, from_user = query.data.split("#")
    if raju == 'reject':
        await query.message.delete()
        await bot.send_message(
            int(from_user),
            f'Your Submission for indexing {chat} has been decliened by our moderators.',
            reply_to_message_id=int(lst_msg_id)
        )
        return

    if lock.locked():
        return await query.answer('Wait until previous process complete.', show_alert=True)
    msg = query.message

    await query.answer('Processing...⏳', show_alert=True)
    if int(from_user) not in ADMINS:
        await bot.send_message(
            int(from_user),
            f'Your Submission for indexing {chat} has been accepted by our moderators and will be added soon.',
            reply_to_message_id=int(lst_msg_id)
        )
    await msg.edit(
        "Starting Indexing",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton('Cancel', callback_data='index_cancel')]]
        )
    )
    try:
        chat = int(chat)
    except:
        chat = chat
    await index_files_to_db(int(lst_msg_id), chat, msg, bot)


@Client.on_message(filters.private & filters.command('index'))
async def send_for_index(bot, message):
    vj = await bot.ask(message.chat.id, "**Now Send Me Your Channel Last Post Link Or Forward A Last Message From Your Index Channel.\n\nAnd You Can Set Skip Number By - /setskip yourskipnumber**")
    if vj.forward_from_chat and vj.forward_from_chat.type == enums.ChatType.CHANNEL:
        last_msg_id = vj.forward_from_message_id
        chat_id = vj.forward_from_chat.username or vj.forward_from_chat.id
    elif vj.text:
        regex = re.compile("(https://)?(t\.me/|telegram\.me/|telegram\.dog/)(c/)?(\d+|[a-zA-Z_0-9]+)/(\d+)$")
        match = regex.match(vj.text)
        if not match:
            return await vj.reply('Invalid link\n\nTry again by /index')
        chat_id = match.group(4)
        last_msg_id = int(match.group(5))
        if chat_id.isnumeric():
            chat_id  = int(("-100" + chat_id))
    else:
        return
    try:
        await bot.get_chat(chat_id)
    except ChannelInvalid:
        return await vj.reply('This may be a private channel / group. Make me an admin over there to index the files.')
    except (UsernameInvalid, UsernameNotModified):
        return await vj.reply('Invalid Link specified.')
    except Exception as e:
        logger.exception(e)
        return await vj.reply(f'Errors - {e}')
    try:
        k = await bot.get_messages(chat_id, last_msg_id)
    except:
        return await message.reply('Make Sure That Iam An Admin In The Channel, if channel is private')
    if k.empty:
        return await message.reply('This may be group and iam not a admin of the group.')

    if message.from_user.id in ADMINS:
        buttons = [[
            InlineKeyboardButton('Yes', callback_data=f'index#accept#{chat_id}#{last_msg_id}#{message.from_user.id}')
        ],[
            InlineKeyboardButton('close', callback_data='close_data')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        return await message.reply(
            f'Do you Want To Index This Channel/ Group ?\n\nChat ID/ Username: <code>{chat_id}</code>\nLast Message ID: <code>{last_msg_id}</code>',
            reply_markup=reply_markup
        )

    if type(chat_id) is int:
        try:
            link = (await bot.create_chat_invite_link(chat_id)).invite_link
        except ChatAdminRequired:
            return await message.reply('Make sure iam an admin in the chat and have permission to invite users.')
    else:
        link = f"@{message.forward_from_chat.username}"
    buttons = [[
        InlineKeyboardButton('Accept Index', callback_data=f'index#accept#{chat_id}#{last_msg_id}#{message.from_user.id}')
    ],[
        InlineKeyboardButton('Reject Index', callback_data=f'index#reject#{chat_id}#{message.id}#{message.from_user.id}'),
    ]]
    reply_markup = InlineKeyboardMarkup(buttons)
    await bot.send_message(
        LOG_CHANNEL,
        f'#IndexRequest\n\nBy : {message.from_user.mention} (<code>{message.from_user.id}</code>)\nChat ID/ Username - <code> {chat_id}</code>\nLast Message ID - <code>{last_msg_id}</code>\nInviteLink - {link}',
        reply_markup=reply_markup
    )
    await message.reply('ThankYou For the Contribution, Wait For My Moderators to verify the files.')


@Client.on_message(filters.command('setskip') & filters.user(ADMINS))
async def set_skip_number(bot, message):
    if ' ' in message.text:
        _, skip = message.text.split(" ")
        try:
            skip = int(skip)
        except:
            return await message.reply("Skip number should be an integer.")
        await message.reply(f"Successfully set SKIP number as {skip}")
        temp.CURRENT = int(skip)
    else:
        await message.reply("Give me a skip number")


async def index_files_to_db(lst_msg_id, chat, msg, bot):
    total_files = 0
    duplicate = 0
    errors = 0
    deleted = 0
    no_media = 0
    unsupported = 0
    async with lock:
        try:
            current = temp.CURRENT
            saved = await db.get_index_progress(chat)
            if saved and saved.get('lst_msg_id') == lst_msg_id:
                current = saved.get('current', current)
                total_files = saved.get('total_files', 0)
                duplicate = saved.get('duplicate', 0)
                errors = saved.get('errors', 0)
                deleted = saved.get('deleted', 0)
                no_media = saved.get('no_media', 0)
                unsupported = saved.get('unsupported', 0)
                try:
                    await msg.edit_text(f"📥 Resuming a previous indexing run for this chat from message <code>{current}</code> (saved automatically after it last stopped)...")
                except Exception:
                    pass
            temp.CANCEL = False
            iterator = bot.iter_messages(chat, lst_msg_id, current).__aiter__()
            last_ui_update = 0.0
            ui_cooldown_until = 0.0
            while True:
                try:
                    message = await iterator.__anext__()
                except StopAsyncIteration:
                    break
                except FloodWait as e:
                    wait_for = e.value + 5
                    logger.warning(f"Indexing hit FloodWait, sleeping {wait_for}s (resuming from message {current})")
                    await db.save_index_progress(chat, lst_msg_id, current, total_files, duplicate, errors, deleted, no_media, unsupported)
                    try:
                        await msg.edit_text(
                            f"⏳ Telegram rate limit hit. Waiting <code>{wait_for}</code>s before continuing...\n\n"
                            f"Progress so far:\nTotal messages fetched: <code>{current}</code>\nTotal messages saved: <code>{total_files}</code>"
                        )
                    except Exception:
                        pass
                    await asyncio.sleep(wait_for)
                    continue

                if temp.CANCEL:
                    await db.save_index_progress(chat, lst_msg_id, current, total_files, duplicate, errors, deleted, no_media, unsupported)
                    await msg.edit(f"Successfully Cancelled!!\n\nSaved <code>{total_files}</code> files to dataBase!\nDuplicate Files Skipped: <code>{duplicate}</code>\nDeleted Messages Skipped: <code>{deleted}</code>\nNon-Media messages skipped: <code>{no_media + unsupported}</code>(Unsupported Media - `{unsupported}` )\nErrors Occurred: <code>{errors}</code>\n\n<i>Progress saved — run /index again with the same link to resume from here.</i>")
                    break
                current += 1
                if current % 30 == 0:
                    # Save progress to the DB every 30 messages regardless —
                    # it's a local write, not subject to Telegram's limits,
                    # and is what makes auto-resume work after a restart.
                    await db.save_index_progress(chat, lst_msg_id, current, total_files, duplicate, errors, deleted, no_media, unsupported)

                    # But only actually EDIT the Telegram status message at
                    # most once every 15 seconds. Editing a message on every
                    # 30-file tick (as often as many times a second on a
                    # huge, fast channel) is what trips Telegram's message-
                    # edit rate limit — and that limit, once tripped, blocks
                    # editing ANY message bot-wide for hours, breaking
                    # unrelated features like search results elsewhere in
                    # the bot. Time-based throttling here, not count-based,
                    # is what actually prevents that.
                    now = time.time()
                    if now >= ui_cooldown_until and now - last_ui_update >= 15:
                        can = [[InlineKeyboardButton('Cancel', callback_data='index_cancel')]]
                        reply = InlineKeyboardMarkup(can)
                        try:
                            await msg.edit_text(
                                text=f"Total messages fetched: <code>{current}</code>\nTotal messages saved: <code>{total_files}</code>\nDuplicate Files Skipped: <code>{duplicate}</code>\nDeleted Messages Skipped: <code>{deleted}</code>\nNon-Media messages skipped: <code>{no_media + unsupported}</code>(Unsupported Media - `{unsupported}` )\nErrors Occurred: <code>{errors}</code>",
                                reply_markup=reply
                            )
                            last_ui_update = now
                        except MessageNotModified:
                            last_ui_update = now
                        except FloodWait as e:
                            # Do NOT block real indexing work waiting this
                            # out — that could be hours for a cosmetic
                            # counter. Just stop trying to update the status
                            # message until the cooldown passes, and keep
                            # indexing in the background the whole time.
                            logger.warning(f"Status message edit flood-waited for {e.value}s — pausing status updates only, indexing continues.")
                            ui_cooldown_until = now + e.value + 5
                        except Exception as e:
                            logger.error(f"Status message edit failed (non-fatal, indexing continues): {e}")
                            last_ui_update = now
                if message.empty:
                    deleted += 1
                    continue
                elif not message.media:
                    no_media += 1
                    continue
                elif message.media not in [enums.MessageMediaType.VIDEO, enums.MessageMediaType.AUDIO, enums.MessageMediaType.DOCUMENT]:
                    unsupported += 1
                    continue
                media = getattr(message, message.media.value, None)
                if not media:
                    unsupported += 1
                    continue
                media.caption = message.caption
                try:
                    aynav, vnay = await save_file(media)
                except FloodWait as e:
                    await asyncio.sleep(e.value + 2)
                    aynav, vnay = await save_file(media)
                if aynav:
                    total_files += 1
                elif vnay == 0:
                    duplicate += 1
                elif vnay == 2:
                    errors += 1
        except Exception as e:
            logger.exception(e)
            await db.save_index_progress(chat, lst_msg_id, current, total_files, duplicate, errors, deleted, no_media, unsupported)
            k = await msg.edit(f'Error: {e}')
            await k.reply_text(f'Succesfully saved <code>{total_files}</code> to dataBase!\nDuplicate Files Skipped: <code>{duplicate}</code>\nDeleted Messages Skipped: <code>{deleted}</code>\nNon-Media messages skipped: <code>{no_media + unsupported}</code>(Unsupported Media - `{unsupported}` )\nErrors Occurred: <code>{errors}</code>')
            await k.reply_text("<b>Progress has been saved automatically — just run /index again with the same channel link and it will resume from here on its own.</b>\n\n**If You Get Message Not Modified Error Then Skip Your Saved File Then Index Again**")
        else:
            await db.clear_index_progress(chat)
            await msg.edit(f'Succesfully saved <code>{total_files}</code> to dataBase!\nDuplicate Files Skipped: <code>{duplicate}</code>\nDeleted Messages Skipped: <code>{deleted}</code>\nNon-Media messages skipped: <code>{no_media + unsupported}</code>(Unsupported Media - `{unsupported}` )\nErrors Occurred: <code>{errors}</code>')
