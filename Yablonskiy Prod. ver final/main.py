import asyncio
import locale

import db
from env import dp, bot
from handler import message, callback

async def main():
    locale.setlocale(locale.LC_ALL, 'ru-RU')

    print((await bot.get_me()).username + " запущен")
    await asyncio.gather(dp.start_polling(bot), db.checker_cycle())

if __name__ == "__main__":
    asyncio.run(main())
