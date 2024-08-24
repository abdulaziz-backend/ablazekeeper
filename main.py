import logging
import asyncio
import signal
from aiogram import Bot, Dispatcher, types, F, Router
from aiogram.enums import ContentType
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, BotCommand, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import BaseFilter
from aiogram.types import ChatMemberUpdated
from aiogram.enums import ChatMemberStatus

# Create the router for handling commands and messages
router = Router()

# Admin ID and API token
ADMIN_ID = 6236467772
API_TOKEN = '6846608037:AAEQYLvOXyxSTj3bwAk5cZywfs9WebDkzbo'

# Set up logging
logging.basicConfig(level=logging.INFO)

# Dictionaries to manage banned users and bot stats
banned_users = {}
bot_stats = {
    "users": [],
    "chats": set()
}

class IsGroupAdmin(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        chat_member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
        return chat_member.is_chat_admin() or chat_member.status == ChatMemberStatus.OWNER

class IsAdminFilter(BaseFilter):
    def __init__(self, admin_id: int):
        self.admin_id = admin_id

    async def __call__(self, message: Message) -> bool:
        is_admin = message.from_user.id == self.admin_id
        logging.info(f"Is Admin Check: {is_admin}")
        return is_admin

async def delete_system_messages(message: Message):
    await message.delete()

async def ban_user(message: Message):
    if not message.reply_to_message:
        await message.answer("⚠️ Please reply to a user's message to ban them.")
        return
    user_to_ban = message.reply_to_message.from_user
    chat_id = message.chat.id
    logging.info(f"Trying to ban user {user_to_ban.id} in chat {chat_id}")
    try:
        await message.bot.ban_chat_member(chat_id, user_to_ban.id)
        if chat_id not in banned_users:
            banned_users[chat_id] = []
        banned_users[chat_id].append(user_to_ban.id)
        await message.answer(
            f"🚫 {user_to_ban.username} has been banned from the group.\nUser ID: {user_to_ban.id}"
        )
    except Exception as e:
        logging.error(f"Failed to ban user {user_to_ban.id}: {e}")
        await message.answer(f"❌ Failed to ban user {user_to_ban.username}.")

async def spam_user(message: Message, bot: Bot):
    chat_member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
    if not chat_member.is_chat_admin() and chat_member.status != ChatMemberStatus.OWNER:
        await message.answer("⚠️ Only admins or the group owner can use this command.")
        return
    if not message.reply_to_message:
        await message.answer("⚠️ Please reply to a user's message to spam them.")
        return
    user_to_spam = message.reply_to_message.from_user
    spam_message = "🚨 Spam Message 🚨"
    for _ in range(10):
        await bot.send_message(user_to_spam.id, spam_message)
    await message.answer(f"💬 Sent spam messages to {user_to_spam.username}.\nUser ID: {user_to_spam.id}")

@router.message(Command("admin"), IsAdminFilter(ADMIN_ID))
async def admin_broadcast(message: Message):
    if message.reply_to_message:
        content_type = message.reply_to_message.content_type
        logging.info(f"Broadcasting {content_type} to {len(bot_stats['chats'])} chats and {len(bot_stats['users'])} users.")
        try:
            if bot_stats['chats']:
                for chat_id in bot_stats['chats']:
                    logging.info(f"Broadcasting to chat_id {chat_id}")
                    if content_type == ContentType.TEXT:
                        broadcast_content = message.reply_to_message.text
                        await message.bot.send_message(chat_id, broadcast_content)

            if bot_stats['users']:
                for user_id in bot_stats['users']:
                    logging.info(f"Broadcasting to user_id {user_id}")
                    if content_type == ContentType.TEXT:
                        broadcast_content = message.reply_to_message.text
                        await message.bot.send_message(user_id, broadcast_content)
                    # Add handling for other content types if needed

        except Exception as e:
            logging.error(f"Failed to send broadcast: {e}")
            await message.answer("❌ An error occurred while sending the broadcast.")
    else:
        await message.answer("⚠️ Please reply to the message you want to broadcast.")

async def list_banned_users(message: Message):
    chat_id = message.chat.id
    if chat_id not in banned_users or not banned_users[chat_id]:
        await message.answer("🔒 No users are banned in this chat.")
        return
    banned_list = "\n".join([f"• {user_id}" for user_id in banned_users[chat_id]])
    await message.answer(f"🔒 Banned users:\n{banned_list}")

@router.chat_member(ChatMemberUpdated)
async def on_chat_status_change(event: ChatMemberUpdated):
    chat_id = event.chat.id
    if event.new_chat_member.status == ChatMemberStatus.MEMBER:
        if chat_id not in bot_stats['chats']:
            bot_stats['chats'].add(chat_id)
            logging.info(f"Bot added to a new chat: {chat_id}. Total chats: {len(bot_stats['chats'])}")
    elif event.new_chat_member.status in [ChatMemberStatus.KICKED, ChatMemberStatus.LEFT]:
        if chat_id in bot_stats['chats']:
            bot_stats['chats'].remove(chat_id)
            logging.info(f"Bot removed from chat: {chat_id}. Total chats: {len(bot_stats['chats'])}")

@router.message(F.content_type == ContentType.NEW_CHAT_MEMBERS)
async def on_new_chat_members(message: Message):
    num_new_members = len(message.new_chat_members)
    bot_stats['users'] += num_new_members
    logging.info(f"{num_new_members} new users added. Total users: {bot_stats['users']}")

async def on_user_start(message: Message):
    user_id = message.from_user.id
    if user_id not in bot_stats['users']:
        bot_stats['users'].append(user_id)
    inline_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕", url="http://t.me/chat_blazer_bot?startgroup=start"),
            InlineKeyboardButton(text="📢 Join Updates Channel", url="https://t.me/blazer_news")]
        ]
    )
    await message.answer(
        "👋 Welcome! This bot helps to manage your group efficiently.\nClick the button below to join as an admin.",
        reply_markup=inline_keyboard
    )

async def bot_info(message: Message):
    await message.answer(
        f"🤖 Bot is currently being used in:\n\n- {len(bot_stats['users'])} users\n- {len(bot_stats['chats'])} chats"
    )

async def main():
    bot = Bot(token=API_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)

    dp.message.register(on_user_start, CommandStart())
    dp.message.register(ban_user, Command("ban"))
    dp.message.register(spam_user, Command("spam"))
    dp.message.register(bot_info, Command("info"))
    router.message.register(admin_broadcast, Command("admin"), IsAdminFilter(ADMIN_ID))
    dp.message.register(list_banned_users, Command("banned"))
    dp.message.register(delete_system_messages, F.content_type.in_([
        ContentType.NEW_CHAT_MEMBERS,
        ContentType.LEFT_CHAT_MEMBER,
        ContentType.GROUP_CHAT_CREATED,
        ContentType.SUPERGROUP_CHAT_CREATED,
        ContentType.CHANNEL_CHAT_CREATED
    ]))

    await bot.set_my_commands([
        BotCommand(command="/start", description="Start the bot"),
        BotCommand(command="/ban", description="Ban a user"),
        BotCommand(command="/spam", description="Spam a user"),
        BotCommand(command="/info", description="Bot info"),
        BotCommand(command="/admin", description="Admin broadcast"),
        BotCommand(command="/banned", description="List banned users")
    ])

    # Ignore SIGTERM and SIGINT
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    signal.signal(signal.SIGINT, signal.SIG_IGN)

    try:
        await dp.start_polling(bot)
    except Exception as e:
        logging.error(f"Polling interrupted: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
