import pathlib
import json

from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile

from telegram_bot import db, text_message
from telegram_bot.env import bot, img_path
from telegram_bot.handler import message
from telegram_bot.keyboards import inline_markup
from telegram_bot.states import treatment_calendar

router = Router()

CALLBACK = {
    'send_about': 'about',
    'send_menu': 'menu',
    'send_profile': 'profile',
    'send_form': 'form',
    'send_admin_panel': 'admin_panel',
    'send_categories': 'categories',
    'send_consultation': 'consultation',
    'send_treatments_calendar': 'treatments_calendar',
    'send_selection': 'selection'
}

@router.callback_query(F.web_app_data)
async def process_web_app_callback(callback_query: CallbackQuery):
    try:
        # Получаем данные из WebApp
        data = json.loads(callback_query.web_app_data.data)
        print(data)

        # Теперь ответить на WebAppQuery
        await callback_query.answer_web_app_query(
            url="https://t.me/DoggyLogy_bot"
        )

        # Можешь отправить сообщение пользователю
        await callback_query.message.answer(f"Спасибо! Получили данные.")

    except Exception as e:
        print(f"Ошибка обработки WebApp данных: {e}")
        await callback_query.message.answer("Ошибка при обработке данных")


# Call a function from callback data
async def call_function_from_callback(callback: CallbackQuery, **kwargs) -> None:
    """
    Call function from callback.
    Find name of function in const dict and call with all arguments.
    :param callback: Callback
    """
    for key in list(CALLBACK.keys()):
        if CALLBACK[key] == callback.data:
            func = getattr(message, key)
            await func(callback.message, **kwargs)


# CALLBACKS
# Handle most of callback's (/menu, /tomorrow, /calendar, /homework etc.)
@router.callback_query(lambda call: call.data in list(CALLBACK.values()))
async def handle_callback(callback: CallbackQuery, **kwargs) -> None:
    """
    Handle callback to call function.

    :param callback: Callback
    :param kwargs: Other message options (need for callback function)
    """
    try:
        await callback.message.delete()

    except TelegramBadRequest:
        pass
    await call_function_from_callback(callback, **kwargs)


# Delete message
@router.callback_query(F.data == 'delete_message')
async def delete_message(callback: CallbackQuery) -> None:
    try:
        await callback.message.delete()

    except TelegramBadRequest as error:
        print(error.message)



@router.callback_query(F.data.startswith('form:'))
async def handle_form_request(callback: CallbackQuery) -> None:
    await callback.message.delete()
    user_id = callback.data.split(':')[1]
    user = await db.get_users(user_id=user_id)
    await message.send_form_text(
        callback.message, user_id=user_id, promo_code=user['promocode'],
        reply_markup=inline_markup.get_back_user_id_keyboard(user_id)
    )

@router.callback_query(lambda call: 'admin:user' in call.data)
async def handle_admin_users(callback: CallbackQuery) -> None:
    await callback.message.delete()
    page = int(callback.data.split(":")[2]) if len(callback.data.split(":")) > 2 else 1
    await callback.message.answer(text=text_message.USERS_TEXT,
                                  reply_markup=await inline_markup.get_users_keyboard(page=page))


@router.callback_query(F.data.startswith('user:'))
async def handle_user_info(callback: CallbackQuery) -> None:
    if callback.data.startswith('user:'):
        user_id = int(callback.data.split(":")[1])
    else:
        user_id = int(callback.data.split(":")[2])
    user = await db.get_users(user_id=user_id)
    user_status = user["level"]
    user_status_text = "Пользователь" if user_status == 0 else "Администратор" if user_status == 2 else "Заблокирован" if user_status == -1 else "Неизвестно"
    user_info = text_message.USER_INFO_TEXT.format(full_name=user['full_name'], user_id=user['user_id'],
                                                   user_status=user_status_text)
    await callback.message.edit_text(text=user_info, reply_markup=inline_markup.get_user_keyboard(user_id=user_id,
                                                                                                  user_level=user_status))


@router.callback_query(F.data.startswith('task:page'))
async def handle_page_tasks(callback: CallbackQuery) -> None:
    await callback.message.delete()
    page = int(callback.data.split(":")[2])
    await message.send_tasks(callback.message, page)


@router.callback_query(F.data.startswith('task:create'))
async def handle_create_page_tasks(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.delete()
    await treatment_calendar.register_treatment_calendar(callback.message, state)


@router.callback_query(F.data.startswith('task:delete'))
async def handle_create_page_tasks(callback: CallbackQuery) -> None:
    await callback.message.delete()
    page = int(callback.data.split(":")[2])
    tasks = await db.get_reminders(user_id=callback.message.chat.id, value=int(True), is_multiple=True)
    await db.delete_reminder(tasks[page - 1]['id'])
    await callback.message.answer(text=text_message.DELETE_TASK_COMPLETE,
                                  reply_markup=inline_markup.get_back_menu_keyboard())

@router.callback_query(F.data.startswith('cons'))
async def handle_consultation(callback: CallbackQuery) -> None:
    await callback.message.delete()
    callback_data = callback.data.split(':')
    user = await db.get_users(callback.message.chat.id)

    if len(callback_data) == 2:
        if callback_data[1] == 'vip':
            await callback.message.answer(
                text=text_message.CONSULTATION_VIP,
                reply_markup=inline_markup.get_back_consultation_keyboard(),
                disable_web_page_preview=True
            )

        elif callback_data[1] == 'free':
            await callback.message.answer(
                text=text_message.CHOOSE_CONSULTATION_FREE_TEXT,
                reply_markup=inline_markup.get_free_consultation_keyboard()
            )
    else:
        markup = inline_markup.get_back_free_consultation_keyboard()

        if callback_data[2] == 'zoo':
            path = f'{img_path}/consultations/zoo.jpg'
            if pathlib.Path(path).is_file():
                await bot.send_photo(
                    chat_id=callback.message.chat.id, photo=FSInputFile(path=path),
                    caption=text_message.CONSULTATION_ZOO, reply_markup=markup
                )

        elif callback_data[2] == 'help':
            path = f'{img_path}/consultations/help.jpg'
            if pathlib.Path(path).is_file():
                await bot.send_photo(
                    chat_id=callback.message.chat.id, photo=FSInputFile(path=path),
                    caption=text_message.CONSULTATION_HELP, reply_markup=markup
                )

        elif callback_data[2] == 'features':
            pets = await db.get_pets(user_id=callback.message.chat.id, is_multiple=True)
            user = await db.get_users(callback.message.chat.id)
            await callback.message.answer(
                text=text_message.CONSULTATION_FEATURES_TEXT.format(
                    promo_code=user['promocode'],
                    pets=message.get_pets_stroke(pets)
                ),
                reply_markup=markup)
        else:
            await callback.message.answer(
                text=text_message.CONSULTATION_FREE_TEXT.format(promo_code=user['promocode']),
                reply_markup=markup
            )


@router.callback_query(F.data.startswith('user_action:'))
async def callback_handler(c: CallbackQuery, state: FSMContext):
    await state.clear()
    _, action, user_id = c.data.split(":")
    user_id = int(user_id)

    if action == "block":
        await db.update_user(user_id, level=-1)
        await c.answer("✅ Пользователь заблокирован.")
    elif action == "unblock":
        await db.update_user(user_id, level=0)
        await c.answer("✅ Пользователь разблокирован.")
    elif action == "make_user":
        await db.update_user(user_id, level=0)
        await c.answer("✅ Пользователь стал клиентом.")
    elif action == "make_admin":
        await db.update_user(user_id, level=2)
        await c.answer("✅ Пользователь стал админом.")
    await handle_user_info(c)
