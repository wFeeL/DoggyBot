import time
from datetime import datetime

from aiogram import F, types, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from telegram_bot import db, text_message, env
from telegram_bot.keyboards import inline_markup, reply_markup
from telegram_bot.decorators import check_block_user, check_admin
from telegram_bot.text_message import PET_PROFILE_TEXT

router = Router()


@router.message(Command("about"))
@check_block_user
async def send_about(message: Message, **kwargs):
    await message.answer(text=text_message.ABOUT_TEXT, reply_markup=inline_markup.get_back_menu_keyboard(),
                         disable_web_page_preview=True)


@router.message(Command("menu", "start"))
@check_block_user
async def send_menu(message: Message, state: FSMContext, **kwargs):
    user = await db.get_users(user_id=message.chat.id)
    await state.clear()
    if user is None:
        await db.add_user(message.chat.id, message.chat.username, message.chat.first_name, message.chat.last_name)
    user_promo_code = user['promocode']
    text = text_message.MENU_TEXT
    if await db.is_user_have_form(message.chat.id):
        text += text_message.PROMO_CODE_ENABLED.format(promo_code=user_promo_code)
    else:
        text += text_message.PROMO_CODE_NOT_ENABLED

    await message.answer(text=text, reply_markup=inline_markup.get_menu_keyboard())


@router.message(Command("profile"))
@check_block_user
async def send_profile(message: Message, **kwargs):
    user = await db.get_users(message.chat.id)
    user_profile = await db.get_user_profile(user_id=message.chat.id)
    if user_profile is None or user_profile['full_name'] is None:
        await message.answer(
            text=text_message.NONE_PROFILE_TEXT, reply_markup=inline_markup.get_profile_keyboard()
        )
    else:
        pets = await db.get_pets(user_id=message.chat.id, is_multiple=True)
        data = {
            'user': get_user_stroke(user_profile),
            'pets': get_pets_stroke(pets),
            'promo_code': user['promocode']
        }
        await message.answer(
            text=text_message.PROFILE_TEXT.format(**data),
            reply_markup=inline_markup.get_profile_keyboard(is_profile_fill=True)
        )


@router.message(Command("form"))
@check_block_user
async def send_form(message: Message, **kwargs):
    await message.answer(
        text=text_message.FORM_TEXT, reply_markup=inline_markup.get_web_app_keyboard(), resize_keyboard=True,
        one_time_keyboard=True
    )


# @router.message(Command("category"))
# @check_block_user
# async def send_categories(message: Message, **kwargs):
#     await message.answer(text=text_message.CHOOSE_CATEGORY_TEXT,
#                          reply_markup=await inline_markup.get_categories_keyboard())


@router.message(Command("consultation"))
@check_block_user
async def send_consultation(message: Message, **kwargs):
    await message.answer(
        text=text_message.CONSULTATION_TEXT,
        reply_markup=inline_markup.get_consultation_keyboard()
    )


@router.message(Command("calendar"))
@check_block_user
async def send_treatments_calendar(message: Message, **kwargs):
    tasks = await db.get_reminders(user_id=message.chat.id, value=int(True), is_multiple=True)
    if len(tasks) == 0:
        await message.answer(text=text_message.NONE_REMINDER_TEXT, reply_markup=inline_markup.get_none_task_keyboard())
    else:
        await send_tasks(message, 1)


async def send_tasks(message: Message, page: int = 1) -> None:
    tasks = await db.get_reminders(user_id=message.chat.id, value=int(True), is_multiple=True)
    task = tasks[page - 1]
    await message.answer(text=await get_task_text(task), reply_markup=inline_markup.get_task_keyboard(page, len(tasks)))


@router.message(Command("usepromo"))
@check_block_user
async def use_promo_handler(message: Message, **kwargs):
    try:
        promo_code = message.text.split(" ")[1]
    except IndexError:
        await message.answer(text_message.ERROR_TEXT)
        return

    user = await db.get_users(user_id=message.chat.id)

    if user["level"] > 1:
        partners = await db.get_partners(is_multiple=True)
    else:
        partners = await db.get_partners(owner_user_id=message.chat.id, is_multiple=True)

    if not partners:
        await message.answer(text_message.FUNCTION_ERROR_TEXT)
        return

    if promo_code.startswith("DL") and len(promo_code) == 8:
        partner_ids = [partner["partner_id"] for partner in partners]

        promo_user = await db.get_users(promocode=promo_code)

        if promo_user:
            redeemed = await db.get_redeemed_promo(promocode=promo_code)
            redeemed_partners = [promo["partner_id"] for promo in redeemed if promo["partner_id"] in partner_ids]

            redeem_promo_keyboard = [
                [types.InlineKeyboardButton(
                    text=f"{"❌" if partner["partner_id"] in redeemed_partners else "✅"} {partner["partner_name"]}",
                    callback_data=f"redeem_promo_code:{partner["partner_id"]}:{promo_code}" if partner[
                                                                                                   "partner_id"] not in redeemed_partners else "already_redeemed")]
                for partner in partners
            ]
            redeem_promo_keyboard.append(inline_markup.get_menu_button())
            redeem_promo_markup = types.InlineKeyboardMarkup(inline_keyboard=redeem_promo_keyboard)

            await message.answer(text_message.REDEEM_CODE_TEXT, reply_markup=redeem_promo_markup)

        else:
            await message.answer(text_message.CODE_ERROR_TEXT)
    else:
        await message.answer(text_message.FORMAT_ERROR_TEXT)


@router.message(Command("selection"))
@check_block_user
async def send_selection(message: Message, **kwargs):
    await message.answer(
        text=text_message.SELECTION_TEXT,
        reply_markup=inline_markup.get_back_menu_keyboard(),
        disable_web_page_preview=True
    )


@router.message(Command(commands=["admin", "ap", "panel"]))
@check_admin
async def send_admin_panel(message: Message, **kwargs):
    await message.answer(text=text_message.ADMIN_PANEL_TEXT, reply_markup=inline_markup.get_admin_menu_keyboard())


@router.message(F.content_type == types.ContentType.WEB_APP_DATA)
@check_block_user
async def webapp_catch(message: Message, **kwargs):
    valid_data = await db.validate_user_form_data(message.web_app_data.data, message.chat.id)
    if valid_data:
        human = valid_data['human']
        await db.update_user_profile(
            user_id=message.chat.id, birth_date=str_to_timestamp(human["birth_date"]), full_name=human["full_name"],
            phone_number=human["phone_number"], about_me=human["about_me"]
        )
        await db.delete_pets(message.chat.id)
        for pet in valid_data["pets"]:
            await db.add_pet(
                user_id=message.chat.id, birth_date=str_to_timestamp(pet["birth_date"]), approx_weight=pet["weight"],
                name=pet["name"], gender=pet["gender"], pet_type=pet["type"], pet_breed=pet["breed"]
            )
        await message.answer(text=text_message.PROFILE_COMPLETE_TEXT,
                             reply_markup=inline_markup.get_back_menu_keyboard())
    else:
        await message.answer(text=text_message.PROFILE_ERROR_TEXT)


async def get_task_text(task: dict) -> str:
    treatment_id, medicament_id, start_date, end_date, period = task['treatment_id'], task['medicament_id'], task[
        'start_date'], task['end_date'], task['period']
    if int(medicament_id) != 0:
        medicament = await db.get_medicament(id=medicament_id)
        medicament_name = medicament["name"]
    else:
        medicament_name = task["medicament_name"]
    treatment = await db.get_treatments(id=treatment_id)
    text = text_message.REMINDER_TEXT.format(
        treatment=treatment['name'],
        medicament=medicament_name,
        start_date=timestamp_to_str(float(start_date)),
        end_date=timestamp_to_str(float(end_date)),
        period=period
    )
    return text


def str_to_timestamp(date_string: str) -> float:
    return datetime.strptime(date_string, "%Y-%m-%d").timestamp()


def timestamp_to_str(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, env.local_timezone).strftime("%d-%m-%Y")


def get_pets_stroke(pets_list) -> str:
    return '\n'.join([
        PET_PROFILE_TEXT.format(
            count=pets_list.index(pet) + 1, name=pet['name'], approx_weight=pet["approx_weight"],
            emoji='🐶' if pet['type'] == 'dog' else '🐱',
            age=round((time.time() - float(pet["birth_date"])) // (86400 * 365)),
            birth_date=datetime.fromtimestamp(float(pet["birth_date"])).strftime('%d %B %Y'),
            type='собака' if pet['type'] == 'dog' else 'кот',
            gender='мальчик' if pet['gender'] == 'male' else 'девочка',
            breed=pet['breed'])
        for pet in pets_list])

def get_user_stroke(user_data) -> str:
    return text_message.USER_PROFILE_TEXT.format(
        full_name=user_data['full_name'], phone_number=user_data['phone_number'],
        birth_date=datetime.fromtimestamp(float(user_data["birth_date"])).strftime('%d %B %Y'),
        age=round((time.time() - float(user_data["birth_date"])) // (86400 * 365))
    )
