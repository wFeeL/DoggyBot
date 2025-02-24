import asyncio
import locale
from telegram_bot.env import dp, bot
from telegram_bot.handler import message, callback
from telegram_bot.states import treatment_calendar
from telegram_bot.scheduler import start_scheduler

locale.setlocale(locale.LC_ALL, 'ru_RU.UTF-8')


async def main():
    dp.include_routers(message.router, treatment_calendar.router, callback.router)
    start_scheduler()
    print((await bot.get_me()).username + " запущен")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
