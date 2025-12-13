from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

from telegram_bot import text_message, env
from telegram_bot.keyboards import inline_markup


class SupportForm(StatesGroup):
    text = State()


router = Router()


@router.callback_query(F.data.contains('support'))
async def handle_support(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.delete()
    await callback.message.answer(text_message.SUPPORT_TEXT)
    await state.set_state(SupportForm.text)


@router.message(SupportForm.text)
async def process_support_text(message: Message) -> None:
    try:
        if message.text is None:
            raise TypeError
        for admin_id in env.admins_telegram_id:
            await env.bot.send_message(
                chat_id=str(admin_id),
                text=text_message.SUPPORT_FROM_USER_TEXT.format(
                    name=message.from_user.full_name, username=message.from_user.username, question=message.text
                ))

        await message.answer(
            text=text_message.SUPPORT_TEXT_SUCCESS, reply_markup=inline_markup.get_back_menu_keyboard()
        )
    except Exception as e:
        print(e)
        await message.answer(text=text_message.ERROR_TEXT)
