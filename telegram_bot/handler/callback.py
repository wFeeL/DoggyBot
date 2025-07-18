import json
import pathlib

from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile

from telegram_bot import db, text_message
from telegram_bot.env import bot, img_path
from telegram_bot.handler import message
from telegram_bot.helper import get_media_group
from telegram_bot.keyboards import inline_markup
from telegram_bot.states import treatment_calendar, edit_task

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
# Handle most of callback's (/menu, /tomorrow, /calendar_reminder, /homework etc.)
@router.callback_query(lambda call: call.data in list(CALLBACK.values()))
async def handle_callback(callback: CallbackQuery, **kwargs) -> None:
    """
    Handle callback to call function.

    :param callback: Callback
    :param kwargs: Other message options (need for callback function)
    """
    if callback.message is not None:
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
    postfix = callback.data.split(':')[2]
    user = await db.get_users(user_id=user_id)
    is_admin, is_form = False, False
    if postfix == "admins":
        is_admin = True
    elif postfix == "forms":
        is_form = True

    await message.send_form_text(
        callback.message, user_id=user_id, promo_code=user['promocode'],
        reply_markup=inline_markup.get_back_user_id_keyboard(user_id, is_admin=is_admin, is_form=is_form)
    )


@router.callback_query(lambda call: call.data.startswith('admin:'))
async def handle_admin_users(callback: CallbackQuery) -> None:
    await callback.message.delete()
    callback_data = callback.data.split(":")
    page = int(callback_data[2]) if len(callback_data) > 2 else 1
    if callback_data[1] == 'users':
        await callback.message.answer(text=text_message.USERS_TEXT,
                                      reply_markup=await inline_markup.get_users_keyboard(page=page))
    elif callback_data[1] == 'admins':
        await callback.message.answer(text=text_message.ADMINS_TEXT,
                                      reply_markup=await inline_markup.get_users_keyboard(page=page, is_admin=True))
    elif callback_data[1] == 'forms':
        await callback.message.answer(text=text_message.LIST_OF_FORMS,
                                      reply_markup=await inline_markup.get_users_keyboard(page=page, is_have_forms=True))


@router.callback_query(lambda call: call.data.startswith('choose_'))
async def handle_user_info(callback: CallbackQuery) -> None:
    is_admin = callback.data.startswith('choose_admin')
    is_form = callback.data.startswith('choose_form')
    if callback.data.startswith('choose_user') or is_admin or is_form:
        user_id = int(callback.data.split(":")[1])
    else:
        user_id = int(callback.data.split(":")[2])
    user = await db.get_users(user_id=user_id)
    user_status = user["level"]
    form_value = user["form_value"]
    user_status_text = "Пользователь" if user_status == 0 else "Администратор" if user_status == 2 else "Заблокирован" if user_status == -1 else "Неизвестно"
    user_info = text_message.USER_INFO_TEXT.format(full_name=user['full_name'], user_id=user['user_id'],
                                                   user_status=user_status_text)
    await callback.message.edit_text(text=user_info, reply_markup=inline_markup.get_user_keyboard(user_id=user_id,
                                                                                                  user_level=user_status, form_value=form_value, is_admin=is_admin, is_form=is_form))


@router.callback_query(F.data.startswith('task:page'))
async def handle_page_tasks(callback: CallbackQuery) -> None:
    await callback.message.delete()
    page = int(callback.data.split(":")[2])
    await message.send_tasks(callback.message, page)


@router.callback_query(F.data.contains('task:create'))
async def handle_create_page_tasks(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.delete()
    await treatment_calendar.register_treatment_calendar(callback.message, state)


@router.callback_query(F.data.startswith('task:edit'))
async def handle_edit_task(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.delete()
    page = int(callback.data.split(":")[2])
    tasks = await db.get_reminders(user_id=callback.message.chat.id, value=int(True), is_multiple=True)
    task_id = tasks[page - 1]['id']
    await edit_task.update_edit_data(callback.message, state, task_id)

@router.callback_query(F.data.startswith('task:delete'))
async def handle_delete_task(callback: CallbackQuery) -> None:
    await callback.message.delete()
    page = int(callback.data.split(":")[2])
    tasks = await db.get_reminders(user_id=callback.message.chat.id, value=int(True), is_multiple=True)
    await db.delete_reminder(tasks[page - 1]['id'])
    await callback.message.answer(text=text_message.DELETE_TASK_COMPLETE,
                                  reply_markup=inline_markup.get_back_menu_keyboard())


@router.callback_query(F.data.contains('cons'))
async def handle_consultation(callback: CallbackQuery, callback_data: str = None) -> None:
    callback_data = callback_data.split(':') if callback_data is not None else callback.data.split(':')
    await callback.message.delete()
    if len(callback_data) == 2:
        if callback_data[1] == 'vip':
            await callback.message.answer(
                text=text_message.CONSULTATION_VIP,
                reply_markup=inline_markup.get_vip_consultation_keyboard(),
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
            media_group = get_media_group(path=f"{img_path}/consultations/zoo/",
                                          first_message_text=text_message.CONSULTATION_ZOO, photos_end=5)
            media_group = await bot.send_media_group(chat_id=callback.message.chat.id, media=media_group)
            media_group_id, media_group_len = media_group[0].message_id, len(media_group)
            markup = inline_markup.get_back_free_consultation_keyboard(media_group=(media_group_id, media_group_len))
            await callback.message.answer(text_message.CHOOSE_ACTION, reply_markup=markup)

        elif callback_data[2] == 'help':
            path = f"{img_path}/consultations/help.jpg"
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
                reply_markup=markup, disable_web_page_preview=True)

        elif callback_data[2] == 'cats_care':
            media_group = get_media_group(path=f"{img_path}/consultations/cats_care/",
                                          first_message_text=text_message.CONSULTATION_CATS_CARE, photos_end=2)
            media_group = await bot.send_media_group(chat_id=callback.message.chat.id, media=media_group)
            media_group_id, media_group_len = media_group[0].message_id, len(media_group)
            markup = inline_markup.get_back_free_consultation_keyboard(media_group=(media_group_id, media_group_len))
            await callback.message.answer(text_message.CHOOSE_ACTION, reply_markup=markup)

        elif callback_data[2] == 'cats_game':
            media_group = get_media_group(path=f"{img_path}/consultations/cats_game/",
                                          first_message_text=text_message.CONSULTATION_CATS_GAME, photos_end=6)
            media_group = await bot.send_media_group(chat_id=callback.message.chat.id, media=media_group)
            media_group_id, media_group_len = media_group[0].message_id, len(media_group)
            markup = inline_markup.get_back_free_consultation_keyboard(media_group=(media_group_id, media_group_len))
            await callback.message.answer(text_message.CHOOSE_ACTION, reply_markup=markup)



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

@router.callback_query(F.data.contains('magic'))
async def handle_magic(callback: CallbackQuery, callback_data: str = None) -> None:
    await callback.message.delete()
    data = callback_data.split(":")[1] if callback_data is not None else callback.data.split(":")[1]

    if data == 'menu':
        await callback.message.answer(text=text_message.MAGIC_TEXT, reply_markup=inline_markup.get_magic_keyboard())
    elif data == 'instruction':
        media_group = get_media_group(path=f"{img_path}/magic_button/",
                                      first_message_text=text_message.MAGIC_INSTRUCTION_TEXT, photos_end=3)
        media_group = await bot.send_media_group(chat_id=callback.message.chat.id, media=media_group)
        media_group_id, media_group_len = media_group[0].message_id, len(media_group)
        markup = inline_markup.get_back_magic_keyboard(media_group=(media_group_id, media_group_len))
        await callback.message.answer(text_message.CHOOSE_ACTION, reply_markup=markup)

    elif data == 'card':
        user = await db.get_users(user_id=callback.message.chat.id)
        markup = inline_markup.get_back_magic_keyboard()
        await callback.message.answer(text=text_message.MAGIC_CARD_TEXT.format(promo_code=user['promocode']), reply_markup=markup)

