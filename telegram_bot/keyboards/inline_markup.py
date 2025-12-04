from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder

from telegram_bot import db, env, text_message
from telegram_bot.env import PERIODS_TO_DAYS
from telegram_bot.helper import CallbackMediaGroupClass


# BUTTONS
def get_menu_button(text="🔙 Главное меню") -> list[InlineKeyboardButton]:
    return [InlineKeyboardButton(text=text, callback_data="menu")]


def get_profile_button(text="👤 Профиль") -> list[InlineKeyboardButton]:
    return [InlineKeyboardButton(text=text, callback_data="profile")]


def get_delete_message_button(text='👀 Скрыть') -> list[InlineKeyboardButton]:
    return [InlineKeyboardButton(text=text, callback_data='delete_message')]


def get_about_button(text="🔑 Запись к специалистам") -> list[InlineKeyboardButton]:
    return [InlineKeyboardButton(text=text, callback_data="about")]


def get_fill_profile_button(text="🪪 Заполнить данные") -> list[InlineKeyboardButton]:
    return [InlineKeyboardButton(text=text, callback_data="form")]


def get_admin_menu_button(text="🛡 Панель админа") -> list[InlineKeyboardButton]:
    return [InlineKeyboardButton(text=text, callback_data="admin_panel")]


def get_consultation_button(text="👩‍⚕️Памятки и контакты") -> list[InlineKeyboardButton]:
    return [InlineKeyboardButton(text=text, callback_data="consultation")]


def get_treatments_calendar_button(text="🗓️ Календарь обработок") -> list[InlineKeyboardButton]:
    return [InlineKeyboardButton(text=text, callback_data="treatments_calendar")]


def get_create_task_button(text='➕ Создать напоминание') -> list[InlineKeyboardButton]:
    return [InlineKeyboardButton(text=text, callback_data='task:create')]


def get_recommend_button(text='🐾 Порекомендовать пэт-бренд') -> list[InlineKeyboardButton]:
    return [InlineKeyboardButton(text=text, callback_data='recommend')]


def get_edit_task_button(page: int, text='✏️ Редактировать') -> list[InlineKeyboardButton]:
    return [InlineKeyboardButton(text=text, callback_data=f"task:edit:{page}")]


def get_delete_task_button(page: int, text='🗑️ Удалить') -> list[InlineKeyboardButton]:
    return [InlineKeyboardButton(text=text, callback_data=f"task:delete:{page}")]


def get_add_reminder_button(text='✅ Сохранить напоминание') -> list[InlineKeyboardButton]:
    return [InlineKeyboardButton(text=text, callback_data='reminder:create')]


def get_magic_button(text='🔮 Волшебная кнопка') -> list[InlineKeyboardButton]:
    return [InlineKeyboardButton(text=text, callback_data='magic:menu')]


# INLINE_MARKUPS
def get_back_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[get_menu_button()])

def get_about_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        get_recommend_button(),
        get_menu_button()
    ])

def get_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(
        *get_profile_button(), *get_treatments_calendar_button(), *get_consultation_button(),
        *get_magic_button(), *get_about_button()
    )
    builder.adjust(2, 1)
    return builder.as_markup()


def get_profile_keyboard(is_profile_fill: bool = False) -> InlineKeyboardMarkup:
    if is_profile_fill:
        return InlineKeyboardMarkup(inline_keyboard=[get_menu_button(), get_fill_profile_button('✏️ Редактировать')])
    else:
        builder = InlineKeyboardBuilder()
        builder.add(*get_fill_profile_button(), *get_menu_button())
        builder.adjust(1, 1)
        return builder.as_markup()


def get_none_task_keyboard() -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup(inline_keyboard=[
        get_create_task_button(), get_menu_button()
    ])
    return markup


async def get_pets_keyboard(is_edit: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    pet_types = await db.get_pet_type(value=int(True), is_multiple=True)
    for pet_type in pet_types:
        if is_edit:
            builder.add(InlineKeyboardButton(text=pet_type['name'], callback_data=f"edit:pet_type:{pet_type['id']}"))
        else:
            builder.add(InlineKeyboardButton(text=pet_type['name'], callback_data=f"pet_type:{pet_type['id']}"))
    if not is_edit:
        builder.add(*get_menu_button())

    builder.adjust(1, 1)
    return builder.as_markup()


async def get_treatments_keyboard(pet_type: int, is_edit: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    treatments = await db.get_treatments(pet_type=pet_type, value=int(True), is_multiple=True)
    for treatment in treatments:
        if is_edit:
            builder.add(InlineKeyboardButton(text=treatment['name'], callback_data=f"edit:treatment:{treatment['id']}"))
        else:
            builder.add(InlineKeyboardButton(text=treatment['name'], callback_data=f"treatment:{treatment['id']}"))

    if not is_edit:
        builder.add(*get_create_task_button(text='⬅️ Назад'))

    builder.adjust(1, 1)
    return builder.as_markup()


async def get_medicament_keyboard(treatments_id: int, pet_type: int, is_edit: bool = False,
                                  media_group: tuple[int, int] = None) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    medicament = await db.get_medicament(treatments_id=treatments_id, value=int(True), is_multiple=True)

    first_message_id = media_group[0] if media_group is not None else 0
    last_message_id = first_message_id + media_group[1] if media_group is not None else 0
    medicament_prefix_callback = 'edit:medic' if is_edit else 'medic'

    for elem in medicament:
        callback = f"{medicament_prefix_callback}:{elem['id']}"
        if media_group is not None:
            callback = str(CallbackMediaGroupClass(callback, first_message_id, last_message_id))
        builder.add(InlineKeyboardButton(text=elem['name'], callback_data=callback))

    callback = f"{medicament_prefix_callback}:choose"
    if media_group is not None:
        callback = str(CallbackMediaGroupClass(callback, first_message_id, last_message_id))
    builder.add(InlineKeyboardButton(text='✏️ Ввести свой вариант', callback_data=callback))

    callback = f'pet_type:{pet_type}'
    if media_group is not None:
        callback = str(CallbackMediaGroupClass(f'pet_type:{pet_type}', first_message_id, last_message_id))

    if not is_edit:
        builder.add(InlineKeyboardButton(text='⬅️ Назад', callback_data=callback))

    builder.adjust(1, 1)
    return builder.as_markup()


async def get_period_keyboard(treatment_id: int, is_edit: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for elem in env.PERIODS_TO_DAYS:
        if is_edit:
            builder.add(InlineKeyboardButton(text=elem, callback_data=f"edit:period:{PERIODS_TO_DAYS[elem]}"))
        else:
            builder.add(InlineKeyboardButton(text=elem, callback_data=f"period:{PERIODS_TO_DAYS[elem]}"))
    builder.adjust(2, 2)
    if is_edit:
        builder.row(InlineKeyboardButton(text='✏️ Ввести период', callback_data='edit:period:choose'))
    else:
        builder.row(InlineKeyboardButton(text='✏️ Ввести период', callback_data='period:choose'))
        builder.row(InlineKeyboardButton(text='⬅️ Назад', callback_data=f"treatment:{treatment_id}"))
    return builder.as_markup()


def get_task_keyboard(page: int, length: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    next_button = InlineKeyboardButton(text='Вперед ➡️', callback_data=f"task:page:{page + 1}")
    back_button = InlineKeyboardButton(text='⬅️ Назад', callback_data=f"task:page:{page - 1}")
    count_button = InlineKeyboardButton(text=f"{page}/{length}", callback_data='None')
    if page == 1 and length == 1:
        builder.add(count_button)

    elif page == 1:
        builder.add(count_button, next_button)

    elif page == length:
        builder.add(back_button, count_button)

    else:
        builder.add(back_button, count_button, next_button)
    builder.adjust(3, 1)
    builder.row(*get_edit_task_button(page), *get_delete_task_button(page))
    builder.row(*get_create_task_button())
    builder.row(*get_menu_button())
    return builder.as_markup()


def get_edit_task_keyboard(is_edited: bool = False) -> InlineKeyboardMarkup:
    keyboard = [[InlineKeyboardButton(text='🪲 Изменить тип', callback_data='edit_treatment'),
                 InlineKeyboardButton(text='💊 Изменить лекарство', callback_data='edit_medicament')],
                [InlineKeyboardButton(text='🗓️ Изменить начало', callback_data='edit_start_date'),
                 InlineKeyboardButton(text='✏️ Изменить период', callback_data='edit_period')]]
    if is_edited:
        keyboard.append([InlineKeyboardButton(text='✅ Сохранить данные', callback_data='edit_data')])
        keyboard.append([InlineKeyboardButton(text='👀 Скрыть', callback_data='stop_state')])
    keyboard.append(get_treatments_calendar_button('⬅️ Назад'))
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    return markup


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


def get_selection_keyboard() -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup(inline_keyboard=[
        get_recommend_button(), get_menu_button()
    ])
    return markup


def get_admin_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Анкеты", callback_data="admin:forms:1")],
        [InlineKeyboardButton(text="👥 Пользователи", callback_data="admin:users:1")],
        [InlineKeyboardButton(text="👮‍ Администраторы", callback_data="admin:admins:1")],
        [InlineKeyboardButton(text="🔎 Поиск анкеты", callback_data="admin:search")],
        get_menu_button()])


def get_back_admin_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[get_admin_menu_button(text='⬅️ Назад')])


async def get_users_keyboard(page, is_admin: bool = False, is_have_forms: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if is_admin:
        users = await db.get_users(is_multiple=True, level=2)
        callback_data_start = 'choose_admin'
        prefix = 'admin:admins'
    elif is_have_forms:
        users = await db.get_users(is_multiple=True, form_value=1)
        callback_data_start = 'choose_forms'
        prefix = 'admin:forms'
    else:
        users = await db.get_users(is_multiple=True)
        callback_data_start = 'choose_user'
        prefix = 'admin:users'

    total_pages = (len(users) + 9) // 10
    users = users[(page - 1) * 10: page * 10]
    for user in users:
        builder.row(InlineKeyboardButton(text=f"{user['full_name']} (ID: {user['user_id']})",
                                         callback_data=f"{callback_data_start}:{user['user_id']}"))
    navigation_buttons = get_page_buttons(page, total_pages, prefix)
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


def get_user_keyboard(user_id: int, user_level: int, form_value: int, is_admin: bool = False,
                      is_form: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    if is_admin:
        back_callback_data = "admin:admins"
        form_postfix = "admins"
    elif is_form:
        back_callback_data = "admin:forms"
        form_postfix = "forms"
    else:
        back_callback_data = "admin:users"
        form_postfix = "users"

    if form_value == 1:
        builder.add(InlineKeyboardButton(text='📝 Анкета', callback_data=f"form:{user_id}:{form_postfix}"))
    if user_level == 2:
        builder.add(InlineKeyboardButton(text="👤 Сделать пользователем",
                                         callback_data=f"user_action:make_user:{user_id}"))
    else:
        if user_level == 0:
            builder.add(InlineKeyboardButton(text="🚫 Заблокировать",
                                             callback_data=f"user_action:block:{user_id}"))
        elif user_level == -1:
            builder.add(InlineKeyboardButton(
                text="⭕ Разблокировать", callback_data=f"user_action:unblock:{user_id}"))
        builder.add(InlineKeyboardButton(text="🛡 Сделать админом", callback_data=f"user_action:make_admin:{user_id}"))
    builder.add(InlineKeyboardButton(text="⬅️ Назад", callback_data=back_callback_data))
    builder.adjust(1, 1)
    return builder.as_markup()


def get_delete_message_keyboard() -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup(inline_keyboard=[get_delete_message_button(), get_menu_button()])
    return markup


def get_consultation_keyboard(is_dog: bool = True) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if is_dog:
        buttons = [
            InlineKeyboardButton(text='📝 Памятка от зооюриста', callback_data='cons:zoo'),
            InlineKeyboardButton(text='🧰 Памятка аптечка первой помощи', callback_data='cons:help'),
            InlineKeyboardButton(text='⚠️ Опасная еда для собак', callback_data='cons:products'),
            InlineKeyboardButton(text='🦴️ Что нужно купить щенку?', callback_data='cons:shopping'),
        ]

    else:
        buttons = [
            InlineKeyboardButton(text='😻 Забота о котиках', callback_data='cons:cats_care'),
            InlineKeyboardButton(text='🎮 Полезные игры с котиком', callback_data='cons:cats_game')
        ]
    builder.add(*buttons)

    builder.add(*get_consultation_button(text='⬅️ Назад'))
    builder.adjust(1, 1)

    return builder.as_markup()

def get_pet_consultation_keyboard() -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text='🐶 Памятки про собачек', callback_data='cons:dog')],
            [InlineKeyboardButton(text='🐈 Памятки про котиков', callback_data='cons:cat')],
            get_menu_button('⬅️ Назад')
        ]
    )
    return markup


def get_back_consultation_keyboard(pet: str = None, media_group: tuple[int, int] = None) -> InlineKeyboardMarkup:
    if media_group is None:
        button = [InlineKeyboardButton(text='⬅️ Назад', callback_data=f'cons:{pet}')]
    else:
        first_message_id = media_group[0]
        last_message_id = first_message_id + media_group[1]
        button = [InlineKeyboardButton(
            text='⬅️ Назад', callback_data="{" + f"\"act\":\"cons:{pet}\",\"first\":\"{first_message_id}\","
                                                 f"\"last\":\"{last_message_id}\"" + "}"
        )]

    return InlineKeyboardMarkup(inline_keyboard=[button])


def get_back_magic_keyboard(media_group: tuple[int, int] = None) -> InlineKeyboardMarkup:
    if media_group is None:
        keyboard = get_magic_button('⬅️ Назад')
    else:
        first_message_id = media_group[0]
        last_message_id = first_message_id + media_group[1]
        keyboard = [InlineKeyboardButton(
            text='⬅️ Назад', callback_data="{" + f"\"act\":\"magic:menu\",\"first\":\"{first_message_id}\","
                                                 f"\"last\":\"{last_message_id}\"" + "}"
        )]

    return InlineKeyboardMarkup(inline_keyboard=[keyboard])


def get_web_app_keyboard() -> InlineKeyboardMarkup:
    page_url = f'{env.webapp_url}/form'
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🪪 Заполнить форму", web_app=WebAppInfo(url=page_url))]
    ])
    return markup


def get_wrong_promo_code_keyboard() -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text='🔄 Попробовать заново', callback_data='admin:search')],
            get_delete_message_button()
        ]
    )
    return markup


def get_back_user_id_keyboard(user_id: int | str, is_admin: bool = False,
                              is_form: bool = False) -> InlineKeyboardMarkup:
    prefix = 'choose_admin' if is_admin else 'choose_form' if is_form else 'choose_user'
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='⬅️ Назад', callback_data=f"{prefix}:{user_id}")],
    ])


def get_magic_keyboard() -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=text_message.MAGIC_INSTRUCTION_TEXT, callback_data='magic:instruction')],
        [InlineKeyboardButton(text='✨ Натальная карта для питомца', callback_data='magic:card')], get_menu_button()
    ])
    return markup
