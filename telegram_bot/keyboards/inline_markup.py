from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


# from telegram_bot import callback_text

# BUTTONS
def get_form_button(text='✏️ Заполнить анкету') -> list[InlineKeyboardButton]:
    pass
    # button = [InlineKeyboardButton(text=text, callback_data=callback_text.CALLBACK['send_form'])]
    # return button


def get_menu_button(text="🔙 Главное меню") -> list[InlineKeyboardButton]:
    return [InlineKeyboardButton(text=text, callback_data="menu")]


def get_profile_button(text="👤 Профиль") -> list[InlineKeyboardButton]:
    return [InlineKeyboardButton(text=text, callback_data="profile")]


def get_categories_button(text="🛍 Категории") -> list[InlineKeyboardButton]:
    return [InlineKeyboardButton(text=text, callback_data="categories")]


def get_about_button(text="❔ О сервисе") -> list[InlineKeyboardButton]:
    return [InlineKeyboardButton(text=text, callback_data="about")]


def get_fill_profile_button(text="🪪 Заполнить данные") -> list[InlineKeyboardButton]:
    return [InlineKeyboardButton(text=text, callback_data="form")]


# INLINE_MARKUPS
def get_back_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[get_menu_button()])


def get_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(*get_profile_button(), *get_categories_button(), *get_about_button())
    builder.adjust(2, 1)
    return builder.as_markup()


def get_profile_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(*get_fill_profile_button(), *get_menu_button())
    builder.adjust(1, 1)
    return builder.as_markup()

def get_admin_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin:stats"),
        InlineKeyboardButton(text="📈 Партнёры", callback_data="admin:partners:1")],
        [InlineKeyboardButton(text="👥 Пользователи", callback_data="admin:users:1")],
        [InlineKeyboardButton(text="➕ Добавить партнёра", callback_data="admin:add_partner")],
        get_menu_button()])

