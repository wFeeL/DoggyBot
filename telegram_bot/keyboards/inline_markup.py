from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from telegram_bot import db


# BUTTONS
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


def get_admin_menu_button(text="Панель админа") -> list[InlineKeyboardButton]:
    return [InlineKeyboardButton(text=text, callback_data="admin_panel")]


# INLINE_MARKUPS
def get_back_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[get_menu_button()])


def get_back_categories_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[get_categories_button(text='<- Назад')])


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


def get_back_admin_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[get_admin_menu_button(text='<- Назад')])


async def get_categories_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    categories = await db.get_categories(category_enabled=True)
    for category in categories:
        builder.row(InlineKeyboardButton(
            text=f"{category["category_name"]}", callback_data=f"category:{category["category_id"]}")
        )
    builder.row(*get_menu_button())
    return builder.as_markup()


async def get_partners_keyboard(page) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    partners = await db.get_partners()
    total_pages = (len(partners) + 14) // 15
    partners = partners[(page - 1) * 15: page * 15]
    for partner in partners:
        builder.row(InlineKeyboardButton(text=f"{partner['partner_name']} (ID: {partner['partner_id']})",
                                         callback_data=f"partner:{partner['partner_id']}"))

    navigation_buttons = get_page_buttons(page, total_pages, 'admin:partner')
    builder.row(*navigation_buttons)
    builder.row(*get_admin_menu_button('🔙 Главное меню'))
    return builder.as_markup()

async def get_users_keyboard(page) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    users = await db.get_users()
    total_pages = (len(users) + 9) // 10
    users = users[(page - 1) * 10: page * 10]
    for user in users:
        builder.row(InlineKeyboardButton(text=f"{user['full_name']} (ID: {user['user_id']})",
                                    callback_data=f"user:{user['user_id']}"))
    navigation_buttons = get_page_buttons(page, total_pages, 'admin:users')
    builder.row(*navigation_buttons)
    builder.row(*get_admin_menu_button('🔙 Главное меню'))
    return builder.as_markup()


def get_page_buttons(page: int, total_pages: int, callback_data_start: str):
    buttons = []
    if page > 1:
        buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"{callback_data_start}:{page - 1}"))
    if page < total_pages:
        buttons.append(InlineKeyboardButton(text="Вперёд ➡️", callback_data=f"{callback_data_start}:{page + 1}"))
    return buttons
