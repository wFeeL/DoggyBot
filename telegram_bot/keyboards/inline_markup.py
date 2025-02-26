from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from telegram_bot import db, env
from telegram_bot.env import PERIODS_TO_DAYS


# BUTTONS
def get_menu_button(text="🔙 Главное меню") -> list[InlineKeyboardButton]:
    return [InlineKeyboardButton(text=text, callback_data="menu")]


def get_profile_button(text="👤 Профиль") -> list[InlineKeyboardButton]:
    return [InlineKeyboardButton(text=text, callback_data="profile")]


def get_delete_message_button(text='👀 Скрыть') -> list[InlineKeyboardButton]:
    return [InlineKeyboardButton(text=text, callback_data='delete_message')]


def get_categories_button(text="🛍 Категории") -> list[InlineKeyboardButton]:
    return [InlineKeyboardButton(text=text, callback_data="categories")]


def get_about_button(text="❔ О сервисе") -> list[InlineKeyboardButton]:
    return [InlineKeyboardButton(text=text, callback_data="about")]


def get_fill_profile_button(text="🪪 Заполнить данные") -> list[InlineKeyboardButton]:
    return [InlineKeyboardButton(text=text, callback_data="form")]


def get_admin_menu_button(text="🛡 Панель админа") -> list[InlineKeyboardButton]:
    return [InlineKeyboardButton(text=text, callback_data="admin_panel")]


def get_consultation_button(text="👨‍⚕️Консультация") -> list[InlineKeyboardButton]:
    return [InlineKeyboardButton(text=text, callback_data="consultation")]


def get_selection_button(text="🐶 Подборка для щенков ") -> list[InlineKeyboardButton]:
    return [InlineKeyboardButton(text=text, callback_data="selection")]


def get_treatments_calendar_button(text="🗓️ Календарь обработок") -> list[InlineKeyboardButton]:
    return [InlineKeyboardButton(text=text, callback_data="treatments_calendar")]


def get_create_task_button(text='➕ Создать напоминание') -> list[InlineKeyboardButton]:
    return [InlineKeyboardButton(text=text, callback_data='task:create')]


def get_delete_task_button(page: int, text='🗑️ Удалить напоминание') -> list[InlineKeyboardButton]:
    return [InlineKeyboardButton(text=text, callback_data=f'task:delete:{page}')]


def get_add_reminder_button(text='➕ Добавить напоминание') -> list[InlineKeyboardButton]:
    return [InlineKeyboardButton(text=text, callback_data='reminder:create')]


# INLINE_MARKUPS
def get_back_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[get_menu_button()])


def get_back_categories_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[get_categories_button(text='⬅️ Назад')])


def get_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(*get_profile_button(), *get_categories_button(), *get_treatments_calendar_button(),
                *get_selection_button(),
                *get_consultation_button(), *get_about_button())
    builder.adjust(2, 1)
    return builder.as_markup()


def get_profile_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(*get_fill_profile_button(), *get_menu_button())
    builder.adjust(1, 1)
    return builder.as_markup()


def get_none_task_keyboard() -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup(inline_keyboard=[
        get_create_task_button(), get_menu_button()
    ])
    return markup


async def get_treatments_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    treatments = await db.get_treatments(value=int(True), is_multiple=True)
    for treatment in treatments:
        builder.add(InlineKeyboardButton(text=treatment['name'], callback_data=f'treatment:{treatment['id']}'))
    builder.add(*get_menu_button())
    builder.adjust(1, 1)
    return builder.as_markup()


async def get_medicament_keyboard(treatments_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    medicament = await db.get_medicament(treatments_id=treatments_id, value=int(True), is_multiple=True)
    for elem in medicament:
        builder.add(InlineKeyboardButton(text=elem['name'], callback_data=f'medicament:{elem['id']}'))
    builder.add(InlineKeyboardButton(text='✏️ Ввести свой вариант', callback_data='medicament:choose'))
    builder.add(*get_treatments_calendar_button(text='⬅️ Назад'))
    builder.adjust(1, 1)
    return builder.as_markup()


async def get_period_keyboard(treatment_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for elem in env.PERIODS_TO_DAYS:
        builder.add(InlineKeyboardButton(text=elem, callback_data=f'period:{PERIODS_TO_DAYS[elem]}'))
    builder.adjust(2, 2)
    builder.row(InlineKeyboardButton(text='✏️ Ввести период', callback_data='period:choose'))
    builder.row(InlineKeyboardButton(text='⬅️ Назад', callback_data=f'treatment:{treatment_id}'))
    return builder.as_markup()


def get_task_keyboard(page: int, length: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    next_button = InlineKeyboardButton(text='Вперед ➡️', callback_data=f'task:page:{page + 1}')
    back_button = InlineKeyboardButton(text='⬅️ Назад', callback_data=f'task:page:{page - 1}')
    count_button = InlineKeyboardButton(text=f'{page}/{length}', callback_data='None')
    if page == 1 and length == 1:
        builder.add(count_button)

    elif page == 1:
        builder.add(count_button, next_button)

    elif page == length:
        builder.add(back_button, count_button)

    else:
        builder.add(back_button, count_button, next_button)
    builder.adjust(3, 1)
    builder.row(*get_delete_task_button(page))
    builder.row(*get_create_task_button())
    builder.row(*get_menu_button())
    return builder.as_markup()


def get_reminder_keyboard() -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup(inline_keyboard=[
        get_add_reminder_button(), get_menu_button()
    ])
    return markup


def get_reminder_add_complete_keyboard() -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup(inline_keyboard=[
        get_create_task_button(), get_treatments_calendar_button(), get_menu_button()
    ])
    return markup


def get_admin_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin:stats"),
         InlineKeyboardButton(text="📈 Партнёры", callback_data="admin:partners:1")],
        [InlineKeyboardButton(text="👥 Пользователи", callback_data="admin:users:1")],
        [InlineKeyboardButton(text="➕ Добавить партнёра", callback_data="admin:add_partner")],
        get_menu_button()])


def get_back_admin_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[get_admin_menu_button(text='⬅️ Назад')])


async def get_categories_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    categories = await db.get_categories(category_enabled=int(True), is_multiple=True)
    for category in categories:
        builder.row(InlineKeyboardButton(
            text=f"{category["category_name"]}", callback_data=f"category:{category["category_id"]}")
        )
    builder.row(*get_menu_button())
    return builder.as_markup()


async def get_partners_keyboard(page) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    partners = await db.get_partners(is_multiple=True)
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
    users = await db.get_users(is_multiple=True)
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
        buttons.append(InlineKeyboardButton(text="Вперед ➡️", callback_data=f"{callback_data_start}:{page + 1}"))
    return buttons


def get_user_keyboard(user_id: int, user_level: int) -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚫 Заблокировать",
                              callback_data=f"user_action:block:{user_id}") if user_level >= 0 else InlineKeyboardButton(
            text="⭕ Разблокировать", callback_data=f"user_action:unblock:{user_id}")],
        [InlineKeyboardButton(text="👤 Сделать пользователем",
                              callback_data=f"user_action:make_user:{user_id}")],
        [InlineKeyboardButton(text="🛍 Сделать партнёром",
                              callback_data=f"user_action:make_partner:{user_id}")],
        [InlineKeyboardButton(text="🛡 Сделать админом", callback_data=f"user_action:make_admin:{user_id}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:users")]
    ])
    return markup


def get_delete_message_keyboard() -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup(inline_keyboard=[get_delete_message_button()])
    return markup


def get_partner_keyboard(partner_id: int, partner_status: int) -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"partner_action:delete:{partner_id}")],
        [InlineKeyboardButton(text="🆔 Указать ID партнёра",
                              callback_data=f"partner_action:set_owner:{partner_id}")],
        [InlineKeyboardButton(text="👁 Скрыть",
                              callback_data=f"partner_action:hide:{partner_id}") if partner_status else InlineKeyboardButton(
            text="👁 Показать",
            callback_data=f"partner_action:show:{partner_id}")],
        [InlineKeyboardButton(text="✏ Изменить текст",
                              callback_data=f"partner_action:edit_text:{partner_id}")],
        [InlineKeyboardButton(text="✏ Изменить название",
                              callback_data=f"partner_action:edit_name:{partner_id}")],
        [InlineKeyboardButton(text="✏ Изменить категорию",
                              callback_data=f"partner_action:edit_category:{partner_id}")],
        [InlineKeyboardButton(text="✏ Изменить URL партнёра",
                              callback_data=f"partner_action:edit_url:{partner_id}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:partners")]
    ])
    return markup
