import os
from pathlib import Path
import tzlocal
from aiogram import Bot, Dispatcher
from aiogram.client.bot import DefaultBotProperties
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.redis import DefaultKeyBuilder, RedisStorage
from redis.asyncio.client import Redis


class PartnerForm(StatesGroup):
    awaiting_partner_owner = State()
    awaiting_partner_text = State()
    awaiting_partner_name = State()
    awaiting_partner_name_new = State()
    awaiting_partner_category = State()
    awaiting_partner_category_new = State()
    awaiting_partner_url = State()


bot_token = "7671505604:AAE-WPWaorO3Bbfhk0Z_2ac62PVJXd__574" # CHANGE BEFORE GIT
storage = RedisStorage(
    Redis(),
    key_builder=DefaultKeyBuilder(with_destiny=True),
)
bot = Bot(bot_token, default=DefaultBotProperties(parse_mode='HTML'), storage=storage)
dp = Dispatcher()


webapp_url = "https://doggybot.onrender.com/"
super_user = 1305714512
BASE_DIR = Path(__file__).resolve().parent.parent
pg_dsn = "postgres://flask_user:password123@localhost:5432/flask_db"
# database_path = str(BASE_DIR / "data" / "database.db")
img_path = f'{os.path.dirname(__file__)}/img'
local_timezone = tzlocal.get_localzone()
PERIODS_TO_DAYS = {
    '1 месяц': '30',
    '35 дней': '35',
    '12 недель': '84',
    '3 месяца': '90',
    '1 год': '365',
}
