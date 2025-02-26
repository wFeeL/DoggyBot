import os

import tzlocal
from aiogram import Bot, Dispatcher
from aiogram.client.bot import DefaultBotProperties
from aiogram.fsm.state import State, StatesGroup

bot_token = "7671505604:AAE-WPWaorO3Bbfhk0Z_2ac62PVJXd__574"


bot = Bot(bot_token, default=DefaultBotProperties(parse_mode='HTML'))
dp: Dispatcher = Dispatcher()

webapp_url = "https://test-webapp-form-23vf7.netlify.app/"
oferta_url = "https://telegra.ph/Dogovor-oferty-12-03-2"
support_username = "OnlyGetC"
super_user = 1305714512
database_path = f'{os.path.dirname(__file__)}/database.db'
img_path = f'{os.path.dirname(__file__)}/img'
local_timezone = tzlocal.get_localzone()
PERIODS_TO_DAYS = {
    '1 месяц': '30',
    '35 дней': '35',
    '12 недель': '84',
    '3 месяца': '90',
    '1 год': '365',
}

class PartnerForm(StatesGroup):
    awaiting_partner_owner = State()
    awaiting_partner_text = State()
    awaiting_partner_name = State()
    awaiting_partner_name_new = State()
    awaiting_partner_category = State()
    awaiting_partner_category_new = State()
    awaiting_partner_url = State()
