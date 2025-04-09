import pathlib
from datetime import date, timedelta

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram_dialog import DialogManager, StartMode

from telegram_bot import text_message, db
from telegram_bot.env import bot, img_path
from telegram_bot import handler
from telegram_bot.keyboards import inline_markup
from telegram_bot.states import calendar


class SearchForm(StatesGroup):
    promo_code = State()


router = Router()


@router.callback_query(lambda call: 'admin:search' in call.data)
async def handle_admin_search(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.delete()
    await state.set_state(SearchForm.promo_code)
    await callback.message.answer(text=text_message.CHOOSE_PROMO_CODE_ADMIN)


@router.message(SearchForm.promo_code)
async def handle_promo_code(message: Message, state: FSMContext) -> None:
    promo_code = str(message.text)
    if promo_code is None or not (promo_code.startswith("DL") and len(promo_code) == 8):
       await state.set_state(SearchForm.promo_code)
       await message.answer(
           text=text_message.WRONG_PROMO_CODE, reply_markup=inline_markup.get_wrong_promo_code_keyboard()
       )
       await state.clear()
    else:
        user = await db.get_users(promocode=promo_code)
        user_id = user['user_id']
        user_profile = await db.get_user_profile(user_id=user_id)
        pets = await db.get_pets(user_id=user_id, is_multiple=True)
        data = {
            'user': handler.message.get_user_stroke(user_profile),
            'pets': handler.message.get_pets_stroke(pets),
            'promo_code': promo_code,
        }
        await message.answer(
            text=text_message.USER_FORM_TEXT.format(**data), reply_markup=inline_markup.get_back_admin_menu_keyboard()
        )