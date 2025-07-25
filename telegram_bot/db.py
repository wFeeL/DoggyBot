import random
import re
import string
from datetime import datetime, timedelta
from typing import Any

import psycopg2

from telegram_bot.env import bot, local_timezone, pg_dsn
from telegram_bot.handler import message
from telegram_bot.helper import get_dict_fetch, timestamp_to_str
from telegram_bot.keyboards import inline_markup


def generate_promocode():
    return "DL" + ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(6))


# Return condition for sql queries
def create_condition(args: dict, exception=None) -> str | None:
    """
    Create condition for sql query. Take column's args from table.
    Use them to create 'WHERE' and 'AND' form for creating sql query.
    :param args: column's args from table.
    :param exception: list of exceptions which create request with '<@' element (not '=' element).
    :return: Stroke with condition
    """
    if exception is None:
        exception = []
    if not list(args.values()) == [None] * len(args):
        args_list = list(filter(lambda elem: args[elem] is not None, args))
        condition = 'WHERE ' + ' AND '.join(list(map(
            lambda elem: f"{elem} = '{args[elem]}'" if elem not in exception else "'{%s}' <@ %s" % (args[elem], elem),
            args_list))
        )
        return condition
    return ''


# Create connection to database by pg_dsn
def create_connection():
    try:
        keepalive_kwargs = {
            "keepalives": 1,
            "keepalives_idle": 30,
            "keepalives_interval": 5,
            "keepalives_count": 5,
        }
        connection = psycopg2.connect(str(pg_dsn), **keepalive_kwargs)
        return connection

    except psycopg2.Error as error:
        print(f"Error with connection to database {error}")
        return None


# Return database data from sql request
async def create_request(sql_query: str, is_return: bool = True, is_multiple: bool = True) -> list[dict[Any, Any]] | \
                                                                                              dict[Any, Any] | None:
    conn = create_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(sql_query)
                if is_return:
                    if is_multiple:
                        return get_dict_fetch(cur, cur.fetchall())
                    else:
                        return get_dict_fetch(cur, [cur.fetchone()])[0]
                else:
                    conn.commit()
    except Exception as e:
        print(f"Error fetching sql request data from database: {e}")
    return None


async def get_users(
        user_id: int | str = None, username: str = None, full_name: str = None, promocode: str = None,
        level: int = None,
        form_value: int = None, is_multiple: bool = False
) -> list | dict:
    condition_dict = locals()
    is_multiple = condition_dict.pop('is_multiple')
    condition = create_condition(condition_dict)
    sql_query = f"SELECT * FROM users {condition} ORDER by user_id"
    return await create_request(sql_query, is_multiple=is_multiple)


async def get_treatments(id: int = None, name: str = None, value: int = None, pet_type: int = None, is_multiple: bool = False) -> list | dict:
    condition_dict = locals()
    is_multiple = condition_dict.pop('is_multiple')
    condition = create_condition(condition_dict)
    sql_query = f"SELECT * FROM treatments {condition} ORDER by name ASC"
    return await create_request(sql_query, is_multiple=is_multiple)

async def get_pet_type(id: int = None, name: str = None, type: str = None, value: int = None, is_multiple: bool = False) -> list | dict:
    condition_dict = locals()
    is_multiple = condition_dict.pop('is_multiple')
    condition = create_condition(condition_dict)
    sql_query = f"SELECT * FROM pet_type {condition} ORDER by name ASC"
    return await create_request(sql_query, is_multiple=is_multiple)

async def get_medicament(
        id: int = None, name: str = None, treatments_id: int = None, value: int = None, is_multiple: bool = False
) -> list | dict:
    condition_dict = locals()
    is_multiple = condition_dict.pop('is_multiple')
    condition = create_condition(condition_dict)
    sql_query = f"SELECT * FROM medicaments {condition} ORDER by name ASC"
    return await create_request(sql_query, is_multiple=is_multiple)


async def add_user(user_id: int, username: str, name: str, last_name: str | None):
    await create_request(
        f"INSERT INTO users (user_id, username, full_name, promocode) VALUES ('{user_id}', '{username}', '{(name + ' ' + (last_name or '')).rstrip(' ')}', '{generate_promocode()}')",
        is_return=False)

    await create_request(f"INSERT INTO user_profile (user_id) VALUES ('{user_id}')", is_return=False)


async def get_user_profile(
        user_id: int | str = None, full_name: str = None, birth_date: int = None,
        phone_number: str = None, about_me: str = None, is_multiple: bool = False
) -> list | dict:
    condition_dict = locals()
    is_multiple = condition_dict.pop('is_multiple')
    condition = create_condition(condition_dict)
    sql_query = f"SELECT * FROM user_profile {condition} ORDER by full_name ASC"
    return await create_request(sql_query, is_multiple=is_multiple)


async def get_pets(
        pet_id: int = None, user_id: int = None, approx_weight: int = None, birth_date: int = None,
        name: str = None, gender: int = None, type: str = None, breed: str = None, is_multiple: bool = False
) -> list | dict:
    condition_dict = locals()
    is_multiple = condition_dict.pop('is_multiple')
    condition = create_condition(condition_dict)
    sql_query = f"SELECT * FROM pets {condition} ORDER by name ASC"
    return await create_request(sql_query, is_multiple=is_multiple)


async def get_reminders(
        id: int = None, user_id: int = None, treatment_id: int = None, medicament_id: int = None,
        start_date: str = None, period: str = None, value: int = None, pet_type: int = None, is_multiple: bool = False
) -> list | dict:
    condition_dict = locals()
    is_multiple = condition_dict.pop('is_multiple')
    condition = create_condition(condition_dict)
    sql_query = f"SELECT * FROM reminders {condition} ORDER by start_date ASC"
    return await create_request(sql_query, is_multiple=is_multiple)


async def add_pet(user_id: int | str, approx_weight: int | float, name: str, birth_date: int | float, gender: str,
                  pet_type: str, pet_breed: str):
    await create_request(
        f"INSERT INTO pets (user_id, approx_weight, name, birth_date, gender, type, breed) VALUES ('{user_id}', {approx_weight}, '{name}', '{birth_date}', '{gender}', '{pet_type}', '{pet_breed}')",
        is_return=False)


async def delete_pets(user_id: int | str, **kwargs):
    await create_request(f"DELETE FROM pets WHERE user_id = '{user_id}'", is_return=False)


async def update_user_profile(user_id: int | str, **kwargs):
    result = []
    for key, value in kwargs.items():
        if isinstance(value, str):
            result.append(f"{key} = '{value}'")
        else:
            result.append(f"{key} = {value}")
    updations = ', '.join(result)
    await create_request(f"UPDATE user_profile SET {updations} WHERE user_id = '{user_id}'", is_return=False)


async def update_user(user_id: int, **kwargs):
    result = []
    for key, value in kwargs.items():
        if isinstance(value, str):
            result.append(f"{key} = '{value}'")
        else:
            result.append(f"{key} = {value}")
    updations = ', '.join(result)
    await create_request(f"UPDATE users SET {updations} WHERE user_id = '{user_id}'", is_return=False)


async def validate_user_form_data(web_app_data):
    if not web_app_data:
        return False

    def validate_full_name(full_name):
        return bool(re.match(r'^[^\d]+$', full_name))

    def validate_phone_number(phone_number):
        pattern = r'^\+7 \d{3} \d{3} \d{2} \d{2}$'
        return re.match(pattern, phone_number) is not None

    def validate_birth_date(birth_date):
        try:
            date_obj = datetime.strptime(birth_date, '%Y-%m-%d')
            return date_obj < datetime.now()
        except ValueError:
            return False

    def validate_breed(breed):
        return bool(re.match(r'^[^\d]+$', breed))

    def validate_pet(pet):
        if not isinstance(pet['name'], str) or not pet['name']:
            return False
        if not isinstance(pet['weight'], (int, float)) or not (0 <= pet['weight'] <= 100):
            return False
        if not validate_birth_date(pet['birth_date']):
            return False
        if pet['gender'] not in ['male', 'female']:
            return False
        if pet['type'] not in ['dog', 'cat']:
            return False
        if not validate_breed(pet['breed']):
            return False
        return True

    human = web_app_data['human']
    if not validate_full_name(human['full_name']):
        return False
    if not validate_phone_number(human['phone_number']):
        return False
    if not validate_birth_date(human['birth_date']):
        return False

    pets = web_app_data['pets']
    if not pets or len(pets) < 1:
        return False

    for pet in pets:
        if not validate_pet(pet):
            return False

    return web_app_data


async def delete_reminder(id: int):
    await create_request(f"DELETE FROM reminders WHERE id = {id}", is_return=False)


async def is_user_have_form(user_id: int) -> bool:
    user = await get_user_profile(user_id=user_id)
    return user['full_name'] is not None


async def add_reminder(
        user_id: int = None, treatment_id: int = None, medicament_id: int = None, medicament_name: str = '',
        start_date: str = None, period: str = None, pet_type: int = None, value: int = 1
) -> None:
    start_date = datetime.strptime(start_date, "%d.%m.%Y")
    end_date = start_date + timedelta(days=int(period))
    await create_request(
        f"INSERT INTO reminders (user_id, treatment_id, medicament_id, medicament_name, start_date, end_date, period, value, pet_type) VALUES ('{user_id}', {treatment_id}, {medicament_id}, '{medicament_name}', '{start_date.timestamp()}', '{end_date.timestamp()}', '{period}', {value}, '{pet_type}')",
        is_return=False)


async def update_reminder(task_id: int, treatment_id: int = None, medicament_id: int = None,
                          medicament_name: str = '',
                          start_date: str = None, period: str = None, **kwargs
                          ) -> None:
    start_date = datetime.strptime(timestamp_to_str(float(start_date)), "%d-%m-%Y")
    end_date = start_date + timedelta(days=int(period))

    await create_request(
        f"UPDATE reminders SET treatment_id = {treatment_id}, medicament_id = {medicament_id}, medicament_name = '{medicament_name}', start_date = '{start_date.timestamp()}', end_date = '{end_date.timestamp()}', period = '{period}' WHERE id = {task_id}",
        is_return=False)


async def check_reminders():
    tasks = await get_reminders(value=int(True), is_multiple=True)
    now_timestamp = datetime.now().timestamp()
    for task in tasks:
        if now_timestamp > float(task['end_date']):
            end_date = datetime.fromtimestamp(now_timestamp, local_timezone) + timedelta(days=int(task['period']))
            await create_request(f"UPDATE reminders SET end_date = '{end_date.timestamp()}' WHERE id = {task['id']}",
                                 is_return=False)
            await bot.send_message(chat_id=task['user_id'], text=await message.get_task_text(task),
                                   reply_markup=inline_markup.get_delete_message_keyboard())
