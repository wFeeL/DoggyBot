import json
import os
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

"""Shared environment/config.

Этот модуль импортируется и ботом (aiogram), и Flask webapp.
Поэтому здесь нельзя делать тяжёлую инициализацию (Bot/RedisStorage)
на уровне импорта — иначе webapp будет падать, когда BOT_TOKEN/Redis
не настроены.
"""

load_dotenv()


def _json_list_env(name: str, default: list[int] | None = None) -> list[int]:
    """Парсит JSON-массив из env, например: [123, 456]."""

    raw = (os.getenv(name) or "").strip()
    if not raw:
        return list(default or [])
    try:
        value = json.loads(raw)
        if isinstance(value, list):
            out: list[int] = []
            for x in value:
                try:
                    out.append(int(x))
                except Exception:
                    continue
            return out
        # допускаем одиночное число
        try:
            return [int(value)]
        except Exception:
            return list(default or [])
    except Exception:
        return list(default or [])


webapp_url = os.getenv("WEBAPP_URL", "https://doggyform.ru/")
admins_telegram_id = _json_list_env("ADMIN_TELEGRAM_ID", default=[])

BASE_DIR = Path(__file__).resolve().parent.parent
pg_dsn = (
    f"postgres://{os.getenv('POSTGRES_USER','')}:{os.getenv('POSTGRES_PASSWORD','')}@"
    f"{os.getenv('POSTGRES_HOST','')}:{os.getenv('POSTGRES_PORT','')}/{os.getenv('POSTGRES_DATABASE','')}"
)
img_path = f"{os.path.dirname(__file__)}/img"

# Сервер работает в UTC, поэтому явно указываем московский часовой пояс
# чтобы время записей совпадало с ожидаемым для пользователей.
local_timezone = ZoneInfo(os.getenv("LOCAL_TZ", "Europe/Moscow"))

PERIODS_TO_DAYS = {
    '1 месяц': '30',
    '35 дней': '35',
    '12 недель': '84',
    '3 месяца': '90',
    '1 год': '365',
}


def init_bot():
    """Ленивая инициализация aiogram Bot/Dispatcher.

    Использовать только там, где реально нужен бот (telegram_bot/bot.py).
    """

    from aiogram import Bot, Dispatcher
    from aiogram.client.bot import DefaultBotProperties
    from aiogram.fsm.storage.redis import DefaultKeyBuilder, RedisStorage
    from redis.asyncio.client import Redis

    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        raise RuntimeError("BOT_TOKEN is not set in environment")

    storage = RedisStorage(
        Redis(),
        key_builder=DefaultKeyBuilder(with_destiny=True),
    )
    bot = Bot(bot_token, default=DefaultBotProperties(parse_mode='HTML'), storage=storage)
    dp = Dispatcher()
    return bot, dp


# Backward compatible exports
try:
    bot, dp = init_bot()
except Exception:
    # webapp может импортировать этот модуль без BOT_TOKEN/Redis
    bot, dp = None, None
