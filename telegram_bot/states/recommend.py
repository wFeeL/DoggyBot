import pathlib
from datetime import date

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import FSInputFile
from aiogram.types import Message, CallbackQuery
from aiogram_dialog import DialogManager, StartMode

from telegram_bot import db, text_message
from telegram_bot.helper import timestamp_to_str, str_to_timestamp, get_media_group
from telegram_bot.env import bot, img_path, admin_telegram_id
from telegram_bot.keyboards import inline_markup
from telegram_bot.states import calendar


class RecommendForm(StatesGroup):
    text = State()


router = Router()


@router.callback_query(F.data.contains('recommend'))
async def handle_recommend(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_text('<b>Напишите пэт-бренд:</b>')
    await state.set_state(RecommendForm.text)


@router.message(RecommendForm.text)
async def process_recommend_text(message: Message) -> None:
    try:
        if message.text is None:
            raise TypeError
        # get chat_id from admins (ENV)
        await bot.send_message(
            chat_id=admin_telegram_id,
            text=text_message.RECOMMENDATION_FROM_USER_TEXT.format(
                name=message.from_user.full_name, username=message.from_user.username, brand=message.text
            ))
        await message.answer(
            text=text_message.RECOMMENDATION_TEXT_SUCCESS, reply_markup=inline_markup.get_back_menu_keyboard()
        )
    except Exception as e:
        print(e)
        await message.answer(text=text_message.ERROR_TEXT)
