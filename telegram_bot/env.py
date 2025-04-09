import os
from pathlib import Path

import tzlocal
from aiogram import Bot, Dispatcher
from aiogram.client.bot import DefaultBotProperties
from aiogram.fsm.storage.redis import DefaultKeyBuilder, RedisStorage
from dotenv import load_dotenv
from redis.asyncio.client import Redis

load_dotenv()

bot_token = os.environ['BOT_TOKEN'] # CHANGE BEFORE GIT
storage = RedisStorage(
    Redis(),
    key_builder=DefaultKeyBuilder(with_destiny=True),
)
bot = Bot(bot_token, default=DefaultBotProperties(parse_mode='HTML'), storage=storage)
dp = Dispatcher()


webapp_url = "https://doggybot.onrender.com/"
BASE_DIR = Path(__file__).resolve().parent.parent
pg_dsn = f"postgres://{os.environ['POSTGRES_USER']}:{os.environ['POSTGRES_PASSWORD']}@{os.environ['POSTGRES_HOST']}:{os.environ['POSTGRES_PORT']}/{os.environ['POSTGRES_DATABASE']}"
img_path = f'{os.path.dirname(__file__)}/img'
local_timezone = tzlocal.get_localzone()
PERIODS_TO_DAYS = {
    '1 месяц': '30',
    '35 дней': '35',
    '12 недель': '84',
    '3 месяца': '90',
    '1 год': '365',
}
