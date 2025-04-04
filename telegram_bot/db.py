import json
import random
import re
import string
import time
from datetime import datetime, timedelta
from typing import Any

import psycopg2

from telegram_bot import text_message
from telegram_bot.env import bot, local_timezone, pg_dsn
from telegram_bot.handler import message
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
        print(f'Error with connection to database {error}')
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
        user_id: int = None, username: str = None, full_name: str = None, promocode: str = None, level: int = None,
        consultation: int = None, is_multiple: bool = False
) -> list | dict:
    condition_dict = locals()
    is_multiple = condition_dict.pop('is_multiple')
    condition = create_condition(condition_dict)
    sql_query = f"SELECT * FROM users {condition} ORDER by user_id"
    return await create_request(sql_query, is_multiple=is_multiple)


async def get_partners(
        owner_user_id: int = None, partner_id: int = None, partner_name: str = None, partner_category: int = None,
        partner_goods_url: str = None, partner_url: str = None, partner_unipromo: str = None,
        partner_discount: int = None, partner_legacy_text: str = None, partner_enabled: int = None,
        is_multiple: bool = False
) -> list | dict:
    condition_dict = locals()
    is_multiple = condition_dict.pop('is_multiple')
    condition = create_condition(condition_dict)
    sql_query = f"SELECT * FROM partners {condition} ORDER by partner_name ASC"
    return await create_request(sql_query, is_multiple=is_multiple)


async def get_categories(
        category_id: int = None, category_name: str = None, category_enabled: int = None, is_multiple: bool = False
) -> list | dict:
    condition_dict = locals()
    is_multiple = condition_dict.pop('is_multiple')
    condition = create_condition(condition_dict)
    sql_query = f"SELECT * FROM categories {condition} ORDER by category_name ASC"
    return await create_request(sql_query, is_multiple=is_multiple)


async def get_treatments(id: int = None, name: str = None, value: int = None, is_multiple: bool = False) -> list | dict:
    condition_dict = locals()
    is_multiple = condition_dict.pop('is_multiple')
    condition = create_condition(condition_dict)
    sql_query = f"SELECT * FROM treatments {condition} ORDER by name ASC"
    return await create_request(sql_query, is_multiple=is_multiple)


async def get_medicament(
        id: int = None, name: str = None, treatments_id: int = None, value: int = None, is_multiple: bool = False
) -> list | dict:
    condition_dict = locals()
    is_multiple = condition_dict.pop('is_multiple')
    condition = create_condition(condition_dict)
    sql_query = f"SELECT * FROM medicaments {condition} ORDER by name ASC"
    return await create_request(sql_query, is_multiple=is_multiple)


async def get_redeemed_promo(
        user_id: int = None, promocode: str = None, redeem_date: int = None, is_multiple: bool = False
) -> list | dict:
    condition_dict = locals()
    is_multiple = condition_dict.pop('is_multiple')
    condition = create_condition(condition_dict)
    sql_query = f"SELECT * FROM redeemed_promocodes {condition} ORDER by redeem_date ASC"
    return await create_request(sql_query, is_multiple=is_multiple)


async def check_old_redeemed_promo():
    olds = await get_redeemed_promo(is_multiple=True)
    for old in olds:
        if old['redeem_date'] + (31 * 86400) < time.time():
            partner_id = old['partner_id']
            partner = await get_partners(partner_id=partner_id)
            await bot.send_message(
                chat_id=old["user_id"],
                text=text_message.OLD_REDEEMED_PROMO.format(partner_name=partner["partner_name"])
            )
            await create_request(
                f"DELETE FROM redeemed_promocodes WHERE partner_id = {partner_id} AND promocode = '{old["promocode"]}'",
                is_return=False)


async def redeem_promo(user_id: int, promocode: str, partner_id: int | str):
    await create_request(
        f"INSERT INTO redeemed_promocodes (user_id, promocode, partner_id, redeem_date) VALUES ({user_id}, '{promocode}', {partner_id}, {time.time()})",
        is_return=False)


async def add_user(user_id: int, username: str, name: str, last_name: str | None):
    await create_request(
        f"INSERT INTO users (user_id, username, full_name, promocode) VALUES ({user_id}, '{username}', '{(name + " " + (last_name or "")).rstrip(" ")}', '{generate_promocode()}')",
        is_return=False)

    await create_request(f"INSERT INTO user_profile (user_id) VALUES ({user_id})", is_return=False)


async def add_partner(user_id: int, partner_name: int, partner_category: int):
    await create_request(f"INSERT INTO partners (owner_user_id, partner_name, partner_category) VALUES ({user_id}, '{partner_name}', {partner_category})", is_return=False)


async def add_category(name: str):
    await create_request(f"INSERT INTO categories (category_name) VALUES ('{name}')", is_return=False)


async def get_user_profile(
        user_id: int = None, full_name: str = None, birth_date: int = None,
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
        start_date: str = None, period: str = None, value: int = None, is_multiple: bool = False
) -> list | dict:
    condition_dict = locals()
    is_multiple = condition_dict.pop('is_multiple')
    condition = create_condition(condition_dict)
    sql_query = f"SELECT * FROM reminders {condition} ORDER by start_date ASC"
    return await create_request(sql_query, is_multiple=is_multiple)


async def add_pet(user_id: int, approx_weight: int | float, name: str, birth_date: int | float, gender: str,
                  pet_type: str, pet_breed: str):
    await create_request(f"INSERT INTO pets (user_id, approx_weight, name, birth_date, gender, type, breed) VALUES ({user_id}, {approx_weight}, '{name}', {birth_date}, '{gender}', '{pet_type}', '{pet_breed}')", is_return=False)


async def delete_pets(user_id: int, **kwargs):
    await create_request(f"DELETE FROM pets WHERE user_id = {user_id}", is_return=False)


async def update_user_profile(user_id: int, **kwargs):
    updations = ", ".join(
        [f"{key} = {f'"{value}"' if isinstance(value, str) else value}" for key, value in kwargs.items()])
    await create_request(f"UPDATE user_profile SET {updations} WHERE user_id = {user_id}", is_return=False)


async def update_user(user_id: int, **kwargs):
    updations = ", ".join(
        [f"{key} = {f'"{value}"' if isinstance(value, str) else value}" for key, value in kwargs.items()])

    await create_request(f"UPDATE users SET {updations} WHERE user_id = {user_id}", is_return=False)


async def update_partner(partner_id: int, **kwargs):
    updations = ", ".join(
        [f"{key} = {f'"{value}"' if isinstance(value, str) else value}" for key, value in kwargs.items()])

    await create_request(f"UPDATE partners SET {updations} WHERE partner_id = {partner_id}", is_return=False)


async def validate_user_form_data(web_app_data: str, user_id: int):
    if not web_app_data or (await get_users(user_id=user_id))["level"] < 0:
        return False

    def validate_full_name(full_name):
        pattern = r'^([А-Я][а-я]{1,15}\s){2}[А-Я][а-я]{1,15}$'
        return re.match(pattern, full_name) is not None

    def validate_phone_number(phone_number):
        pattern = r'^\+7 \(\d{3}\) \d{3}-\d{2}-\d{2}$'
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

    try:
        data = json.loads(web_app_data)
    except json.JSONDecodeError:
        return False

    human = data.get('human', {})
    if not validate_full_name(human.get('full_name', '')):
        return False
    if not validate_phone_number(human.get('phone_number', '')):
        return False
    if not validate_birth_date(human.get('birth_date', '')):
        return False

    pets = data.get('pets', [])
    if not pets or len(pets) < 1:
        return False

    for pet in pets:
        if not validate_pet(pet):
            return False

    return data


async def delete_partner(partner_id: int):
    await create_request(f"DELETE FROM partners WHERE partner_id = {partner_id}", is_return=False)


async def delete_reminder(id: int):
    await create_request(f"DELETE FROM reminders WHERE id = {id}", is_return=False)

async def is_user_have_form(user_id: int) -> bool:
    user = await get_user_profile(user_id=user_id)
    return user['full_name'] is not None


async def add_reminder(
        user_id: int = None, treatment_id: int = None, medicament_id: int = None, medicament_name: str = '',
        start_date: str = None, period: str = None, value: int = 1
) -> None:
    start_date = datetime.strptime(start_date, "%d.%m.%Y")
    end_date = start_date + timedelta(days=int(period))
    await create_request(f"INSERT INTO reminders (user_id, treatment_id, medicament_id, medicament_name, start_date, end_date, period, value) VALUES ({user_id}, {treatment_id}, {medicament_id}, '{medicament_name}', '{start_date.timestamp()}', '{end_date.timestamp()}', '{period}', {value})", is_return=False)


async def check_reminders():
    tasks = await get_reminders(value=int(True), is_multiple=True)
    now_timestamp = datetime.now().timestamp()
    for task in tasks:
        if now_timestamp > float(task['end_date']):
            end_date = datetime.fromtimestamp(now_timestamp, local_timezone) + timedelta(days=int(task['period']))
            await create_request(f"UPDATE reminders SET end_date = '{end_date.timestamp()}' WHERE id = {task['id']}", is_return=False)
            await bot.send_message(chat_id=task['user_id'], text=await message.get_task_text(task),
                                   reply_markup=inline_markup.get_delete_message_keyboard())


def get_dict_fetch(cursor, fetch):
    results = []
    columns = list(cursor.description)
    for row in fetch:
        row_dict = {}
        for i, col in enumerate(columns):
            row_dict[col.name] = row[i]
        results.append(row_dict)
    return results
