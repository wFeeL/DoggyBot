from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram_bot import db

scheduler = AsyncIOScheduler()

def start_scheduler():
    scheduler.add_job(db.check_reminders, 'interval', hours=3)
    scheduler.start()