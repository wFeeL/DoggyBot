from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, WebAppInfo

from telegram_bot.env import webapp_url


def get_form_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🪪 Заполнить форму", web_app=WebAppInfo(url=webapp_url))]]
    )