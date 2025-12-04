import pathlib

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, InlineKeyboardMarkup, FSInputFile

from telegram_bot import db, text_message
from telegram_bot.env import bot, img_path
from telegram_bot.decorators import check_block_user, check_admin
from telegram_bot.helper import get_user_stroke, get_pets_stroke, get_task_text
from telegram_bot.keyboards import inline_markup

router = Router()


@router.message(Command("about"))
@check_block_user
async def send_about(message: Message, **kwargs):
    path = f'{img_path}/help_spec.jpg'
    if pathlib.Path(path).is_file():
        await bot.send_photo(
            chat_id=message.chat.id,
            photo=FSInputFile(path=path),
            caption=f'{text_message.ABOUT_TEXT}\n\n{text_message.CONTACT_TEXT}',
            reply_markup=inline_markup.get_about_keyboard()
        )


@router.message(Command("menu", "start"))
async def send_menu(message: Message, state: FSMContext, **kwargs):
    user = await db.get_users(user_id=message.chat.id)
    await state.clear()
    if user is None:
        await db.add_user(message.chat.id, message.chat.username, message.chat.first_name, message.chat.last_name)

    promo_code_text = ''
    if not await db.is_user_have_form(message.chat.id):
        promo_code_text = text_message.PROMO_CODE_NOT_ENABLED

    text = text_message.MENU_TEXT.format(promo_code_text=promo_code_text, contact_text=text_message.CONTACT_TEXT)
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
        one_time_keyboard=True, disable_web_page_preview=True
    )


@router.message(Command("consultation"))
@check_block_user
async def send_consultation(message: Message, **kwargs):
    await message.answer(
        text=text_message.SELECTION_TEXT,
        reply_markup=inline_markup.get_pet_consultation_keyboard(),
        disable_web_page_preview=True
    )


@router.message(Command("calendar_reminder"))
@check_block_user
async def send_treatments_calendar(message: Message, **kwargs):
    tasks = await db.get_reminders(user_id=message.chat.id, value=int(True), is_multiple=True)
    if len(tasks) == 0:
        await message.answer(text=text_message.NONE_REMINDER_TEXT, reply_markup=inline_markup.get_none_task_keyboard())
    else:
        await send_tasks(message, 1)


@router.message(Command(commands=["admin", "ap", "panel"]))
@check_admin
async def send_admin_panel(message: Message, **kwargs):
    users = await db.get_users(is_multiple=True)
    forms = await db.get_users(is_multiple=True, form_value=1)
    admins = await db.get_users(level=2, is_multiple=True)
    await message.answer(
        text=text_message.ADMIN_PANEL_TEXT.format(users_len=len(users), form_len=len(forms), admins_len=len(admins)),
        reply_markup=inline_markup.get_admin_menu_keyboard()
    )


async def send_tasks(message: Message, page: int = 1) -> None:
    tasks = await db.get_reminders(user_id=message.chat.id, value=int(True), is_multiple=True)
    task = tasks[page - 1]
    await message.answer(text=await get_task_text(task), reply_markup=inline_markup.get_task_keyboard(page, len(tasks)))


async def send_form_text(message: Message, user_id: int | str, promo_code: str,
                         reply_markup: InlineKeyboardMarkup = None) -> None:
    user_profile = await db.get_user_profile(user_id=user_id)
    pets = await db.get_pets(user_id=user_id, is_multiple=True)
    data = {
        'user': get_user_stroke(user_profile),
        'pets': get_pets_stroke(pets),
        'promo_code': promo_code,
    }
    if reply_markup is None:
        reply_markup = inline_markup.get_back_admin_menu_keyboard()
    await message.answer(
        text=text_message.USER_FORM_TEXT.format(**data), reply_markup=reply_markup
    )
