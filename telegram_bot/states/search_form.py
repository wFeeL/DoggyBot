from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

from telegram_bot import handler
from telegram_bot import text_message, db
from telegram_bot.keyboards import inline_markup


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
        await handler.message.send_form_text(message, user_id=user['user_id'], promo_code=promo_code)