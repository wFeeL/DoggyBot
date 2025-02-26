from aiogram.types import Message

from telegram_bot import db, text_message


def check_block_user(func):
    async def wrapper_check_block_user(message: Message, **kwargs) -> None:
        user = await check_user(message)
        if user["level"] < 0:
            await message.answer(text=text_message.USER_BLOCKED_TEXT)
        else:
            await func(message, **kwargs)

    return wrapper_check_block_user


def check_admin(func):
    async def wrapper_check_admin(message: Message, **kwargs) -> None:
        user = await check_user(message)
        if user["level"] == 2:
            await func(message, **kwargs)
    return wrapper_check_admin


async def check_user(message: Message):
    user = await db.get_users(user_id=message.chat.id)
    if user is None:
        await db.add_user(message.chat.id, message.chat.username, message.chat.first_name, message.chat.last_name)
        return await db.get_users(user_id=message.chat.id)
    return user