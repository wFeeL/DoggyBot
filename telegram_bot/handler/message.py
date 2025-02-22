import time
from datetime import datetime

from aiogram import F, types, Router
from aiogram.filters import Command
from aiogram.types import Message

from telegram_bot import db, text_message
from telegram_bot.keyboards import inline_markup, reply_markup
from telegram_bot.decorators import check_block_user, check_admin

router = Router()


@router.message(Command("about"))
@check_block_user
async def send_about(message: Message):
    await message.answer(text=text_message.ABOUT_TEXT, reply_markup=inline_markup.get_back_menu_keyboard())


@router.message(Command("menu", "start"))
@check_block_user
async def send_menu(message: Message):
    user = await db.get_users(message.chat.id, multiple=False)
    if user is None:
        await db.add_user(message.chat.id, message.chat.username, message.chat.first_name, message.chat.last_name)

    if user["level"] < 0:
        await message.answer(text=text_message.USER_BLOCKED_TEXT)
        return
    await message.answer(text=text_message.MENU_TEXT, reply_markup=inline_markup.get_menu_keyboard())


@router.message(Command("profile"))
@check_block_user
async def send_profile(message: Message):
    user_profile = await db.get_user_profile(message.chat.id)
    if user_profile is None or user_profile['full_name'] is None:
        await message.answer(
            text=text_message.NONE_PROFILE_TEXT, reply_markup=inline_markup.get_profile_keyboard()
        )
    else:
        data = {
            'full_name': user_profile['full_name'],
            'phone_number': user_profile['phone_number'],
            'birth_date': datetime.fromtimestamp(user_profile["birth_date"]).strftime('%d %B %Y'),
            'age': round((time.time() - user_profile["birth_date"]) // (86400 * 365)),
            'pets': ''.join([
                f'<b>{pet["name"]}</b>: <code>~{pet["approx_weight"]}кг, {round((time.time() - pet["birth_date"]) // (86400 * 365))} лет</code>\n'
                for pet in user_profile["pets"]])
        }
        await message.answer(
            text=text_message.PROFILE_TEXT.format(**data), reply_markup=inline_markup.get_back_menu_keyboard()
        )


@router.message(Command("form"))
@check_block_user
async def send_form(message: Message):
    await message.answer(
        text=text_message.FORM_TEXT, reply_markup=reply_markup.get_form_keyboard(), resize_keyboard=True,
        one_time_keyboard=True
    )


@router.message(Command("category"))
@check_block_user
async def send_categories(message: Message):
    await message.answer(text=text_message.CHOOSE_CATEGORY_TEXT,
                         reply_markup=await inline_markup.get_categories_keyboard())



@router.message(Command("usepromo"))
@check_block_user
async def use_promo_handler(message: Message):
    try:
        promo_code = message.text.split(" ")[1]
    except IndexError:
        await message.answer(text_message.ERROR_TEXT)
        return

    user = await db.get_users(message.chat.id)

    if user["level"] > 1:
        partners = await db.get_partners()
    else:
        partners = await db.get_partners(owner_id=message.chat.id)

    if not partners:
        await message.answer(text_message.FUNCTION_ERROR_TEXT)
        return

    if promo_code.startswith("DL") and len(promo_code) == 8:
        partner_ids = [partner["partner_id"] for partner in partners]

        promo_user = await db.get_users(promocode=promo_code)

        if promo_user:
            redeemed = await db.get_redeemed_promo(promo_code)
            redeemed_partners = [promo["partner_id"] for promo in redeemed if promo["partner_id"] in partner_ids]

            redeem_promo_keyboard = [
                [types.InlineKeyboardButton(
                    text=f"{"❌" if partner["partner_id"] in redeemed_partners else "✅"} {partner["partner_name"]}",
                    callback_data=f"redeem_promo_code:{partner["partner_id"]}:{promo_code}" if partner["partner_id"] not in redeemed_partners else "already_redeemed")]
                for partner in partners
            ]
            redeem_promo_keyboard.append(inline_markup.get_menu_button())
            redeem_promo_markup = types.InlineKeyboardMarkup(inline_keyboard=redeem_promo_keyboard)

            await message.answer(text_message.REDEEM_CODE_TEXT, reply_markup=redeem_promo_markup)

        else:
            await message.answer(text_message.CODE_ERROR_TEXT)
    else:
        await message.answer(text_message.FORMAT_ERROR_TEXT)


@router.message(Command(commands=["admin", "ap", "panel"]))
@check_admin
async def send_admin_panel(message: Message):
    user = await db.get_users(message.chat.id)
    if user["level"] > 2:
        return
    await message.answer(text=text_message.ADMIN_PANEL_TEXT, reply_markup=inline_markup.get_admin_menu_keyboard())


@router.message(F.content_type == types.ContentType.WEB_APP_DATA)
@check_block_user
async def webapp_catch(message: Message):
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
        await message.answer(text=text_message.PROFILE_COMPLETE_TEXT, reply_markup=inline_markup.get_back_menu_keyboard())
    else:
        await message.answer(text=text_message.PROFILE_ERROR_TEXT)


def str_to_timestamp(date_string: str) -> float:
    return datetime.strptime(date_string, "%Y-%m-%d").timestamp()
