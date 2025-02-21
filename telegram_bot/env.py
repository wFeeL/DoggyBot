from aiogram.client.bot import DefaultBotProperties
from aiogram.fsm.state import State, StatesGroup
from aiogram import Bot, Dispatcher

# bot_token = "7281759810:AAHYND_nL0ZbqzVnIWhEIZlUDFQS0a5iUPQ"
bot_token = "7716350005:AAEgZK9gqE26IwfbD5sKy8nqbzetZsKFVB8"

bot = Bot(bot_token, default=DefaultBotProperties(parse_mode='HTML'))
dp: Dispatcher = Dispatcher()

webapp_url = "https://test-webapp-form-23vf7.netlify.app/"
oferta_url = "https://telegra.ph/Dogovor-oferty-12-03-2"
support_username = "OnlyGetC"
super_user = 1305714512

class PartnerForm(StatesGroup):
    awaiting_partner_owner = State()
    awaiting_partner_text = State()
    awaiting_partner_name = State()
    awaiting_partner_name_new = State()
    awaiting_partner_category = State()
    awaiting_partner_category_new = State()
    awaiting_partner_url = State()
    
# Yoomoney authentication
secret_key = "live_P3s2yhfuEK0N4eO2-do0xpM2mt_JSoVJABon9Ya0ezg"
shop_id = 275742
