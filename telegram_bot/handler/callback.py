import pathlib

from aiogram import types, Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile

from telegram_bot import db, text_message
from telegram_bot.env import PartnerForm, bot, img_path
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


@router.callback_query(lambda call: 'category' in call.data)
async def category_handler(callback: CallbackQuery):
    await callback.message.delete()
    category_id = callback.data.split(":")[1]
    category = await db.get_categories(category_id=int(category_id))
    partners = await db.get_partners(partner_category=int(category_id), is_multiple=True)

    answer_text = f'{text_message.CATEGORY_NAME.format(category=category["category_name"])}{category['category_text']}\n\n'

    for partner in partners:
        text = text_message.PARTNER_CATEGORY_TEXT.format(
            name=partner["partner_name"],
            url=partner["partner_url"],
            legacy_text=partner["partner_legacy_text"],
        )

        answer_text += text
    path = f'{img_path}/{category_id}.png'
    if pathlib.Path(path).is_file():
        await bot.send_photo(
            chat_id=callback.message.chat.id, photo=FSInputFile(path=path), caption=answer_text,
            reply_markup=inline_markup.get_back_categories_keyboard()
        )


@router.callback_query(lambda call: 'redeem' in call.data)
async def redeem_promo_code_handler(callback: CallbackQuery):
    if 'already_redeemed' in callback.data:
        await callback.answer(text_message.PROMO_CODE_ALREADY_REDEEMED_TEXT)

    elif 'redeem_promo_code' in callback.data:
        _, partner_id, promo_code = callback.data.split(":")
        partner = await db.get_partners(partner_id=int(partner_id))
        user = await db.get_users(user_id=callback.message.chat.id)
        promo_user = await db.get_users(promocode=promo_code)

        if user["level"] > 1 or partner["owner_user_id"] == callback.message.chat.id:
            await db.redeem_promo(promo_user["user_id"], promo_code, partner_id)
            await callback.answer(text_message.PROMO_CODE_REDEEMED_TEXT)
            await callback.message.delete()
            await bot.send_message(promo_user["user_id"], text_message.USER_PROMO_CODE_REDEEMED_TEXT.format(
                partner_name=partner["partner_name"])
                                   )


@router.callback_query(F.data == 'admin:stats')
async def handle_admin_stats(callback: CallbackQuery) -> None:
    await callback.message.delete()
    partners = await db.get_partners()
    # orders_day = await db.get_subscriptions(start_ts=time.time() - 86400) or []
    # orders_month = await db.get_subscriptions(start_ts=time.time() - 86400 * 31) or []
    # orders_year = await db.get_subscriptions(start_ts=time.time() - 86400 * 365) or []
    orders_day, orders_month, orders_year = [], [], []

    users = await db.get_users(is_multiple=True)

    await callback.message.answer(
        text=text_message.STATS_TEXT.format(
            users_len=len(users), partners_len=len(partners), orders_day=len(orders_day),
            orders_day_sum=sum([order["price"] for order in orders_day]), orders_month=len(orders_month),
            orders_month_sum=sum([order["price"] for order in orders_month]), orders_year=len(orders_year),
            orders_year_sum=sum([order["price"] for order in orders_year])
        ),
        reply_markup=inline_markup.get_back_admin_menu_keyboard()
    )


@router.callback_query(lambda call: 'admin:partner' in call.data)
async def handle_admin_partners(callback: CallbackQuery) -> None:
    await callback.message.delete()
    page = int(callback.data.split(":")[2]) if len(callback.data.split(":")) > 2 else 1
    await callback.message.answer(
        text=text_message.PARTNERS_TEXT, reply_markup=await inline_markup.get_partners_keyboard(page=page)
    )


@router.callback_query(lambda call: 'admin:user' in call.data)
async def handle_admin_users(callback: CallbackQuery) -> None:
    await callback.message.delete()
    page = int(callback.data.split(":")[2]) if len(callback.data.split(":")) > 2 else 1
    await callback.message.answer(text=text_message.USERS_TEXT,
                                  reply_markup=await inline_markup.get_users_keyboard(page=page))


@router.callback_query(lambda call: 'add_partner' in call.data)
async def handle_add_partner(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_text("<b>Введите название нового партнёра:</b>", parse_mode="HTML")
    await state.set_state(PartnerForm.awaiting_partner_name_new)


@router.callback_query(F.data.startswith('user:'))
async def handle_user_info(callback: CallbackQuery) -> None:
    user_id = int(callback.data.split(":")[1])
    user = await db.get_users(user_id=user_id)
    user_status = user["level"]
    user_status_text = "Пользователь" if user_status == 0 else "Партнер" if user_status == 1 else "Администратор" if user_status == 2 else "Заблокирован" if user_status == -1 else "Неизвестно"
    user_info = text_message.USER_INFO_TEXT.format(full_name=user['full_name'], user_id=user['user_id'],
                                                   user_status=user_status_text)
    await callback.message.edit_text(text=user_info, reply_markup=inline_markup.get_user_keyboard(user_id=user_id,
                                                                                                  user_level=user_status))


@router.callback_query(F.data.startswith('partner:'))
async def handle_partner_info(callback: CallbackQuery) -> None:
    partner_id = int(callback.data.split(":")[1])
    partner = await db.get_partners(partner_id=partner_id)
    owner = await db.get_users(user_id=partner["owner_user_id"])
    category = await db.get_categories(category_id=partner["partner_category"])
    partner_status = partner['partner_enabled']
    partner_status_text = "Да" if not partner_status else "Нет"

    partner_url = ''
    if partner["partner_url"]:
        partner_url = f"Ознакомиться с ассортиментом\n{partner["partner_url"]}\n"
    partner_url += f"""<blockquote>{partner["partner_legacy_text"]}</blockquote>"""

    partner_info = text_message.PARTNER_INFO_TEXT.format(
        partner_name=partner['partner_name'], partner_id=partner['partner_id'], full_name=owner['full_name'],
        user_id=owner['user_id'], category_name=category['category_name'], partner_url=partner_url,
        partner_status=partner_status_text
    )

    await callback.message.edit_text(
        text=partner_info, disable_web_page_preview=True,
        reply_markup=inline_markup.get_partner_keyboard(partner_id=partner_id, partner_status=partner_status)
    )


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


@router.callback_query(F.data.startswith('user_action:') or F.data.startswith('partner_action:'))
async def callback_handler(c: CallbackQuery, state: FSMContext):
    message = c.message
    await state.clear()

    if c.data.startswith("user_action:"):
        action, user_id = c.data.split(":")[1:]
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
        elif action == "make_partner":
            await db.update_user(user_id, level=1)
            await c.answer("✅ Пользователь стал партнёром.")
        elif action == "make_admin":
            await db.update_user(user_id, level=2)
            await c.answer("✅ Пользователь стал админом.")
        c_u = c.model_copy(update={"data": f"user:{user_id}"})
        await callback_handler(c_u, state)

    if c.data.startswith("partner_action:"):
        action, partner_id = c.data.split(":")[1:]
        partner_id = int(partner_id)

        control_partner_markup = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="🔙 Назад", callback_data=f"partner:{partner_id}")]
        ])

        if action == "delete":
            await db.delete_partner(partner_id)
            await c.answer("Партнёр удалён.")
            c_u = c.model_copy(update={"data": "admin:partners"})
            await callback_handler(c_u, state)

        elif action == "set_owner":
            await message.edit_text("<b>Введите ID нового владельца партнёра:</b>", parse_mode="HTML",
                                    reply_markup=control_partner_markup)
            await state.update_data(message_to_delete=message)
            await state.update_data(partner_id=partner_id)
            await state.set_state(PartnerForm.awaiting_partner_owner)

        elif action == "edit_text":
            await message.edit_text("<b>Введите новый текст партнёра:</b>", parse_mode="HTML",
                                    reply_markup=control_partner_markup)
            await state.update_data(message_to_delete=message)
            await state.update_data(partner_id=partner_id)
            await state.set_state(PartnerForm.awaiting_partner_text)

        elif action == "edit_name":
            await message.edit_text("<b>Введите новое название партнёра:</b>", parse_mode="HTML",
                                    reply_markup=control_partner_markup)
            await state.update_data(message_to_delete=message)
            await state.update_data(partner_id=partner_id)
            await state.set_state(PartnerForm.awaiting_partner_name)

        elif action == "edit_category":
            categories_text = "\n".join(
                [f"<code>{category['category_id']}</code>: <b>{category['category_name']}</b>" for category in
                 await db.get_categories(is_multiple=True)])
            await message.edit_text(categories_text + "\n\n<b>Введите новую категорию партнёра:</b>", parse_mode="HTML",
                                    reply_markup=control_partner_markup)
            await state.update_data(message_to_delete=message)
            await state.update_data(partner_id=partner_id)
            await state.set_state(PartnerForm.awaiting_partner_category)

        elif action == "edit_url":
            await message.edit_text("<b>Введите новый URL партнёра:</b>", parse_mode="HTML",
                                    reply_markup=control_partner_markup)
            await state.update_data(message_to_delete=message)
            await state.update_data(partner_id=partner_id)
            await state.set_state(PartnerForm.awaiting_partner_url)

        elif action == "hide":
            await db.update_partner(partner_id, partner_enabled=False)
            await c.answer("✅ Партнёр скрыт.")
            c_u = c.model_copy(update={"data": f"partner:{partner_id}"})
            await callback_handler(c_u, state)

        elif action == "show":
            await db.update_partner(partner_id, partner_enabled=True)
            await c.answer("✅ Партнёр показан.")
            c_u = c.model_copy(update={"data": f"partner:{partner_id}"})
            await callback_handler(c_u, state)


@router.message(PartnerForm.awaiting_partner_owner)
async def set_partner_owner(message: types.Message, state: FSMContext):
    data = await state.get_data()
    partner_id = data["partner_id"]
    new_owner_id = int(message.text)
    await db.update_partner(partner_id, owner_user_id=new_owner_id)
    control_partner_markup = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="🔙 Назад", callback_data=f"partner:{partner_id}")]
    ])
    await data["message_to_delete"].delete()
    await message.answer("✅ <b>ID партнёра указан.</b>", parse_mode="HTML", reply_markup=control_partner_markup)
    await state.clear()


@router.message(PartnerForm.awaiting_partner_text)
async def edit_partner_text(message: types.Message, state: FSMContext):
    data = await state.get_data()
    partner_id = data["partner_id"]
    new_text = message.text
    await db.update_partner(partner_id, partner_legacy_text=new_text)
    control_partner_markup = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="🔙 Назад", callback_data=f"partner:{partner_id}")]
    ])
    await data["message_to_delete"].delete()
    await message.answer("✅ <b>Текст изменён.</b>", parse_mode="HTML", reply_markup=control_partner_markup)
    await state.clear()


@router.message(PartnerForm.awaiting_partner_name)
async def edit_partner_name(message: types.Message, state: FSMContext):
    data = await state.get_data()
    partner_id = data["partner_id"]
    new_name = message.text
    await db.update_partner(partner_id, partner_name=new_name)
    control_partner_markup = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="🔙 Назад", callback_data=f"partner:{partner_id}")]
    ])
    await data["message_to_delete"].delete()
    await message.answer("✅ <b>Название изменено.</b>", parse_mode="HTML", reply_markup=control_partner_markup)
    await state.clear()


@router.message(PartnerForm.awaiting_partner_category)
async def edit_partner_category(message: types.Message, state: FSMContext):
    data = await state.get_data()
    partner_id = data["partner_id"]
    new_category = int(message.text)
    await db.update_partner(partner_id, partner_category=new_category)
    control_partner_markup = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="🔙 Назад", callback_data=f"partner:{partner_id}")]
    ])
    await data["message_to_delete"].delete()
    await message.answer("✅ <b>Категория изменена.</b>", parse_mode="HTML", reply_markup=control_partner_markup)
    await state.clear()


@router.message(PartnerForm.awaiting_partner_url)
async def edit_partner_url(message: types.Message, state: FSMContext):
    data = await state.get_data()
    partner_id = data["partner_id"]
    new_url = message.text
    await db.update_partner(partner_id, partner_url=new_url)
    control_partner_markup = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="🔙 Назад", callback_data=f"partner:{partner_id}")]
    ])
    await data["message_to_delete"].delete()
    await message.answer("✅ <b>URL изменён.</b>", parse_mode="HTML", reply_markup=control_partner_markup)
    await state.clear()


@router.message(PartnerForm.awaiting_partner_name_new)
async def add_partner_handler(message: types.Message, state: FSMContext):
    partner_name = message.text
    await state.update_data(partner_name=partner_name)
    categories_text = "\n".join(
        [f"<code>{category['category_id']}</code>: <b>{category['category_name']}</b>" for category in
         await db.get_categories(is_multiple=True)])
    await message.answer(categories_text + "\n\n<b>Введите категорию партнёра:</b>", parse_mode="HTML")
    await state.set_state(PartnerForm.awaiting_partner_category_new)


@router.message(PartnerForm.awaiting_partner_category_new)
async def add_partner_category_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    partner_name = data["partner_name"]
    partner_category = int(message.text)

    await db.add_partner(user_id=message.from_user.id, partner_name=partner_name, partner_category=partner_category)

    setting_markup = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="🛍 Перейти к партнёрам", callback_data="admin:partners")],
        [types.InlineKeyboardButton(text="🔙 Назад", callback_data="admin:panel")],
    ])

    await message.answer("<b>✅ Партнёр успешно добавлен!</b>", parse_mode="HTML", reply_markup=setting_markup)
    await state.clear()
