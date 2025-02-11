import asyncio
import locale
from telegram_bot import db
from env import dp, bot
from handler import message, callback

locale.setlocale(locale.LC_ALL, 'ru_RU.UTF-8')

async def main():
    dp.include_routers(message.router, callback.router)
    print((await bot.get_me()).username + " запущен")
    await dp.start_polling(bot, skip_updates=True)
    await db.checker_cycle()

if __name__ == "__main__":
    asyncio.run(main())
