from telegram_bot.env import webapp_url
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, WebAppInfo
from aiogram.utils.keyboard import ReplyKeyboardBuilder



def get_form_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🪪 Заполнить форму", web_app=WebAppInfo(url=webapp_url))]]
    )