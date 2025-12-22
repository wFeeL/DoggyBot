import asyncio
import random
import re
import string
from datetime import datetime, timedelta
from typing import Any

import psycopg2

from telegram_bot.env import bot, local_timezone, pg_dsn
from telegram_bot.helper import get_dict_fetch, timestamp_to_str

# Включаем логирование
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


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
            # Не даём процессу зависать, если Postgres временно недоступен
            "connect_timeout": 5,
        }
        connection = psycopg2.connect(str(pg_dsn), **keepalive_kwargs)
        return connection

    except psycopg2.Error as error:
        print(f"Error with connection to database {error}")
        return None


# Return database data from sql request
async def create_request(
        sql_query: str,
        is_return: bool = True,
        is_multiple: bool = True,
        params: tuple | list | None = None,
) -> list[dict[Any, Any]] | dict[Any, Any] | None:
    """Единая точка выполнения SQL.

    - Всегда закрывает соединение.
    - Поддерживает параметризованные запросы (cur.execute(sql, params)).
    - Не падает при временной недоступности БД.
    """

    conn = create_connection()
    if conn is None:
        logger.error("DB connection is None")
        return None

    try:
        with conn:
            with conn.cursor() as cur:
                if params is None:
                    cur.execute(sql_query)
                else:
                    cur.execute(sql_query, params)

                if not is_return:
                    conn.commit()
                    return None

                if is_multiple:
                    return get_dict_fetch(cur, cur.fetchall())

                row = cur.fetchone()
                if row is None:
                    return None
                return get_dict_fetch(cur, [row])[0]
    except Exception:
        logger.exception("Error fetching sql request data from database")
        return None
    finally:
        try:
            conn.close()
        except Exception:
            pass


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
    """Создать пользователя при /start.

    Пользователь может нажимать /start многократно — поэтому делаем UPSERT.
    """

    full_name = (name + ' ' + (last_name or '')).rstrip(' ')
    uid = str(user_id)

    # users: обновляем username/full_name, но не затираем существующий promocode
    await create_request(
        """
        INSERT INTO users (user_id, username, full_name, promocode)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (user_id)
        DO UPDATE SET
            username = EXCLUDED.username,
            full_name = EXCLUDED.full_name
        """,
        is_return=False,
        params=(uid, username, full_name, generate_promocode()),
    )

    # user_profile: если уже есть — ничего не делаем
    await create_request(
        "INSERT INTO user_profile (user_id) VALUES (%s) ON CONFLICT (user_id) DO NOTHING",
        is_return=False,
        params=(uid,),
    )


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

    try:
        human = web_app_data['human']
        if not validate_full_name(human['full_name']):
            logger.error("Невалидное полное имя")
            return False
        if not validate_phone_number(human['phone_number']):
            logger.error("Невалидный номер телефона")
            return False
        if not validate_birth_date(human['birth_date']):
            logger.error("Невалидная дата рождения")
            return False

        pets = web_app_data['pets']
        if not pets or len(pets) < 1:
            logger.error("Нет питомцев")
            return False

        for pet in pets:
            if not validate_pet(pet):
                logger.error(f"Невалидные данные питомца: {pet}")
                return False

        # Если все проверки пройдены, возвращаем исходные данные
        return web_app_data
    except KeyError as e:
        logger.error(f"Отсутствует обязательное поле: {e}")
        return False
    except Exception as e:
        logger.error(f"Ошибка валидации: {e}")
        return False


async def delete_reminder(id: int):
    await create_request(f"DELETE FROM reminders WHERE id = {id}", is_return=False)


async def is_user_have_form(user_id: int) -> bool:
    user = await get_user_profile(user_id=user_id)
    return bool(user and user.get('full_name'))


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
    # Важно: webapp импортирует telegram_bot.db, но ему не нужны aiogram-хендлеры.
    # Поэтому подтягиваем их только в той функции, где они реально используются.
    from telegram_bot.handler import message
    from telegram_bot.keyboards import inline_markup

    if bot is None:
        return

    tasks = await get_reminders(value=int(True), is_multiple=True)
    now_timestamp = datetime.now().timestamp()
    for task in tasks:
        if now_timestamp > float(task['end_date']):
            end_date = datetime.fromtimestamp(now_timestamp, local_timezone) + timedelta(days=int(task['period']))
            await create_request(f"UPDATE reminders SET end_date = '{end_date.timestamp()}' WHERE id = {task['id']}",
                                 is_return=False)
            await bot.send_message(chat_id=task['user_id'], text=await message.get_task_text(task),
                                   reply_markup=inline_markup.get_delete_message_keyboard())


# --- Online booking (single profile) ---


async def ensure_bookings_table() -> None:
    await create_request(
        """
        CREATE TABLE IF NOT EXISTS bookings (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            start_ts DOUBLE PRECISION NOT NULL,
            end_ts DOUBLE PRECISION NOT NULL,
            services JSONB NOT NULL,
            total_price INTEGER NOT NULL,
            comment TEXT,
            promo_code TEXT,
            specialist TEXT NOT NULL,
            created_at DOUBLE PRECISION NOT NULL,
            status TEXT NOT NULL DEFAULT 'confirmed'
        );
        """,
        is_return=False,
    )
    await create_request("CREATE INDEX IF NOT EXISTS bookings_user_id_idx ON bookings(user_id);", is_return=False)
    await create_request("CREATE INDEX IF NOT EXISTS bookings_start_ts_idx ON bookings(start_ts);", is_return=False)
    await create_request(
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS reminder_24_sent BOOLEAN NOT NULL DEFAULT FALSE;",
        is_return=False,
    )
    await create_request(
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS reminder_3_sent BOOLEAN NOT NULL DEFAULT FALSE;",
        is_return=False,
    )
    await create_request(
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS followup_sent BOOLEAN NOT NULL DEFAULT FALSE;",
        is_return=False,
    )

    # --- Admin config tables ---
    await create_request(
        """
        CREATE TABLE IF NOT EXISTS booking_services_custom (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            duration_min INTEGER NOT NULL,
            price INTEGER NOT NULL,
            created_at DOUBLE PRECISION NOT NULL
        );
        """,
        is_return=False,
    )
    await create_request(
        "CREATE INDEX IF NOT EXISTS booking_services_custom_id_idx ON booking_services_custom(id);",
        is_return=False,
    )
    await create_request(
        """
        CREATE TABLE IF NOT EXISTS booking_service_availability (
            service_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            slots JSONB NOT NULL,
            updated_at DOUBLE PRECISION NOT NULL,
            PRIMARY KEY (service_id, date)
        );
        """,
        is_return=False,
    )
    await create_request(
        "CREATE INDEX IF NOT EXISTS booking_service_availability_date_idx ON booking_service_availability(date);",
        is_return=False,
    )


def _escape_sql_text(value: str | None) -> str:
    return (value or "").replace("'", "''")


async def add_booking(
        user_id: int | str,
        start_ts: float,
        end_ts: float,
        services: list[dict],
        total_price: int,
        specialist: str,
        comment: str | None = None,
        promo_code: str | None = None,
) -> dict | None:
    import json

    services_json = _escape_sql_text(json.dumps(services, ensure_ascii=False))
    comment = _escape_sql_text(comment)
    promo_code = _escape_sql_text(promo_code)
    specialist = _escape_sql_text(specialist)
    created_at = datetime.now().timestamp()

    sql = (
        "INSERT INTO bookings (user_id, start_ts, end_ts, services, total_price, comment, promo_code, specialist, created_at) "
        f"VALUES ('{user_id}', {float(start_ts)}, {float(end_ts)}, '{services_json}'::jsonb, {int(total_price)}, "
        f"'{comment}', '{promo_code}', '{specialist}', {float(created_at)}) "
        "RETURNING *;"
    )
    return await create_request(sql, is_multiple=False)


async def get_user_bookings(user_id: int | str, kind: str = "upcoming", limit: int = 50) -> list:
    now_ts = datetime.now().timestamp()
    status_cond = "status = 'confirmed'"
    if kind == "past":
        cond = f"user_id = '{user_id}' AND {status_cond} AND start_ts < {now_ts}"
        order = "start_ts DESC"
    else:
        cond = f"user_id = '{user_id}' AND {status_cond} AND start_ts >= {now_ts}"
        order = "start_ts ASC"
    sql = f"SELECT * FROM bookings WHERE {cond} ORDER BY {order} LIMIT {int(limit)}"
    return await create_request(sql, is_multiple=True) or []


async def get_bookings_in_range(start_ts: float, end_ts: float) -> list:
    sql = (
        "SELECT * FROM bookings "
        f"WHERE status = 'confirmed' AND start_ts < {float(end_ts)} AND end_ts > {float(start_ts)} "
        "ORDER BY start_ts ASC"
    )
    return await create_request(sql, is_multiple=True) or []


# --- Booking services (custom) & availability (admin-configured) ---


async def get_custom_booking_services() -> list:
    sql = "SELECT * FROM booking_services_custom ORDER BY id ASC"
    return await create_request(sql, is_multiple=True) or []


async def get_custom_services_max_id() -> int:
    row = await create_request("SELECT MAX(id) AS max_id FROM booking_services_custom", is_multiple=False)
    try:
        return int(row.get('max_id') or 0) if row else 0
    except Exception:
        return 0


async def add_custom_booking_service(
        service_id: int,
        name: str,
        duration_min: int,
        price: int,
        description: str | None = None,
) -> dict | None:
    created_at = datetime.now().timestamp()
    name = _escape_sql_text(name)
    description = _escape_sql_text(description)
    sql = (
        "INSERT INTO booking_services_custom (id, name, description, duration_min, price, created_at) "
        f"VALUES ({int(service_id)}, '{name}', '{description}', {int(duration_min)}, {int(price)}, {float(created_at)}) "
        "RETURNING *;"
    )
    return await create_request(sql, is_multiple=False)


async def get_service_availability(service_id: int, date: str) -> dict | None:
    date = _escape_sql_text(date)
    sql = (
        "SELECT * FROM booking_service_availability "
        f"WHERE service_id = {int(service_id)} AND date = '{date}' LIMIT 1"
    )
    return await create_request(sql, is_multiple=False)


async def upsert_service_availability(service_id: int, date: str, slots: list[str]) -> dict | None:
    import json

    date = _escape_sql_text(date)
    slots_json = _escape_sql_text(json.dumps(slots, ensure_ascii=False))
    updated_at = datetime.now().timestamp()

    sql = (
        "INSERT INTO booking_service_availability (service_id, date, slots, updated_at) "
        f"VALUES ({int(service_id)}, '{date}', '{slots_json}'::jsonb, {float(updated_at)}) "
        "ON CONFLICT (service_id, date) DO UPDATE SET slots = EXCLUDED.slots, updated_at = EXCLUDED.updated_at "
        "RETURNING *;"
    )
    return await create_request(sql, is_multiple=False)


async def delete_service_availability(service_id: int, date: str) -> None:
    date = _escape_sql_text(date)
    await create_request(
        f"DELETE FROM booking_service_availability WHERE service_id = {int(service_id)} AND date = '{date}'",
        is_return=False,
    )


async def list_availability_dates(service_id: int) -> list[str]:
    sql = (
        "SELECT date FROM booking_service_availability "
        f"WHERE service_id = {int(service_id)} ORDER BY date ASC"
    )
    rows = await create_request(sql, is_multiple=True) or []
    out: list[str] = []
    for r in rows:
        d = r.get('date')
        if isinstance(d, str):
            out.append(d)
    return out


# --- Admin bookings helpers ---


async def get_upcoming_bookings_all(limit: int = 500) -> list:
    now_ts = datetime.now().timestamp()
    sql = (
        "SELECT * FROM bookings "
        f"WHERE status = 'confirmed' AND start_ts >= {float(now_ts)} "
        "ORDER BY start_ts ASC "
        f"LIMIT {int(limit)}"
    )
    return await create_request(sql, is_multiple=True) or []


async def cancel_booking_admin(booking_id: int) -> dict | None:
    sql = (
        "UPDATE bookings SET status = 'cancelled' "
        f"WHERE id = {int(booking_id)} RETURNING *;"
    )
    return await create_request(sql, is_multiple=False)


async def reschedule_booking_admin(
        booking_id: int,
        start_ts: float,
        end_ts: float,
        services: list[dict] | None = None,
        total_price: int | None = None,
        comment: str | None = None,
        promo_code: str | None = None,
) -> dict | None:
    import json

    updates = [f"start_ts = {float(start_ts)}", f"end_ts = {float(end_ts)}", "status = 'confirmed'"]
    if services is not None:
        services_json = _escape_sql_text(json.dumps(services, ensure_ascii=False))
        updates.append(f"services = '{services_json}'::jsonb")
    if total_price is not None:
        updates.append(f"total_price = {int(total_price)}")
    if comment is not None:
        updates.append(f"comment = '{_escape_sql_text(comment)}'")
    if promo_code is not None:
        updates.append(f"promo_code = '{_escape_sql_text(promo_code)}'")

    sql = (
        "UPDATE bookings SET "
        + ", ".join(updates)
        + f" WHERE id = {int(booking_id)} RETURNING *;"
    )
    return await create_request(sql, is_multiple=False)


def _format_booking_dt(ts: float) -> str:
    try:
        dt = datetime.fromtimestamp(float(ts), local_timezone)
        wd = ['пн', 'вт', 'ср', 'чт', 'пт', 'сб', 'вс'][dt.weekday()]
        return dt.strftime('%d.%m.%Y') + f" ({wd}) " + dt.strftime('%H:%M')
    except Exception:
        return "—"


def _format_booking_services(services: list[dict] | None) -> str:
    if not services:
        return "—"
    lines = []
    for srv in services:
        name = srv.get("name") or "Услуга"
        duration = srv.get("duration_min") or srv.get("duration") or 0
        try:
            duration = int(duration)
        except Exception:
            duration = duration or 0
        price = srv.get("price")
        price_text = f" — {price} ₽" if price is not None else ""
        duration_text = f" — {duration} мин" if duration else ""
        lines.append(f"• {name}{duration_text}{price_text}")
    return "\n".join(lines)


async def _mark_booking_notifications(booking_id: int, **flags) -> None:
    allowed = {"reminder_24_sent", "reminder_3_sent", "followup_sent"}
    updates = [f"{k} = {'TRUE' if v else 'FALSE'}" for k, v in flags.items() if k in allowed]
    if not updates:
        return
    sql = f"UPDATE bookings SET {', '.join(updates)} WHERE id = {int(booking_id)}";
    await create_request(sql, is_return=False)


async def check_booking_reminders() -> None:
    now_ts = datetime.now().timestamp()
    in_24h = now_ts + 24 * 3600
    in_3h = now_ts + 3 * 3600
    followup_threshold = now_ts - 6 * 24 * 3600
    followup_window_start = now_ts - 7 * 24 * 3600

    sql = (
        "SELECT * FROM bookings "
        "WHERE status = 'confirmed' AND ("
        f"(start_ts BETWEEN {now_ts} AND {in_24h} AND reminder_24_sent = FALSE) OR "
        f"(start_ts BETWEEN {now_ts} AND {in_3h} AND reminder_3_sent = FALSE) OR "
        f"(start_ts BETWEEN {followup_window_start} AND {followup_threshold} AND followup_sent = FALSE)"
        ")"
    )
    bookings = await create_request(sql, is_multiple=True) or []

    preparation = (
        "Важно: собака на занятии должна быть голодной. Приготовьте корм/лакомство, привычную амуницию и любимую игрушку."
    )
    followup_link = "https://t.me/DoggyLogy_bot/booking"

    for booking in bookings:
        start_ts = float(booking.get("start_ts") or 0)
        time_to_start = start_ts - now_ts
        services_text = _format_booking_services(booking.get("services"))
        user_id = booking.get("user_id")
        booking_id = booking.get("id")

        if not user_id or not booking_id:
            continue

        if (
            not booking.get("reminder_24_sent")
            and time_to_start <= 24 * 3600
            and time_to_start > 3 * 3600
        ):
            text = (
                "⏰ Напоминание о занятии через 24 часа\n"
                f"• Дата и время: {_format_booking_dt(start_ts)}\n"
                f"• Услуги: {services_text}\n\n"
                f"{preparation}"
            )
            await bot.send_message(chat_id=user_id, text=text)
            await _mark_booking_notifications(booking_id, reminder_24_sent=True)

        if not booking.get("reminder_3_sent") and 0 < time_to_start <= 3 * 3600:
            text = (
                "⏰ Напоминание: занятие через 3 часа\n"
                f"• Дата и время: {_format_booking_dt(start_ts)}\n"
                f"• Услуги: {services_text}\n\n"
                f"{preparation}"
            )
            await bot.send_message(chat_id=user_id, text=text)
            await _mark_booking_notifications(booking_id, reminder_3_sent=True)

        if (
            not booking.get("followup_sent")
            and start_ts > 0
            and 6 * 24 * 3600 <= now_ts - start_ts <= 7 * 24 * 3600
        ):
            text = (
                "Спасибо, что были на занятии! Прошло 6 дней — самое время закрепить результат.\n"
                f"Запишитесь на следующее занятие: {followup_link}"
            )
            await bot.send_message(chat_id=user_id, text=text)
            await _mark_booking_notifications(booking_id, followup_sent=True)


async def get_booking_by_id(booking_id: int) -> dict | None:
    return await create_request(f"SELECT * FROM bookings WHERE id = {int(booking_id)} LIMIT 1", is_multiple=False)


async def cancel_booking(booking_id: int, user_id: int | str) -> dict | None:
    sql = (
        "UPDATE bookings SET status = 'cancelled' "
        f"WHERE id = {int(booking_id)} AND user_id = '{user_id}' "
        "RETURNING *;"
    )
    return await create_request(sql, is_multiple=False)


async def reschedule_booking(
        booking_id: int,
        user_id: int | str,
        start_ts: float,
        end_ts: float,
        services: list[dict] | None = None,
        total_price: int | None = None,
        comment: str | None = None,
        promo_code: str | None = None,
) -> dict | None:
    import json

    updates = [f"start_ts = {float(start_ts)}", f"end_ts = {float(end_ts)}", "status = 'confirmed'"]
    if services is not None:
        services_json = _escape_sql_text(json.dumps(services, ensure_ascii=False))
        updates.append(f"services = '{services_json}'::jsonb")
    if total_price is not None:
        updates.append(f"total_price = {int(total_price)}")
    if comment is not None:
        updates.append(f"comment = '{_escape_sql_text(comment)}'")
    if promo_code is not None:
        updates.append(f"promo_code = '{_escape_sql_text(promo_code)}'")

    sql = (
        "UPDATE bookings SET "
        + ", ".join(updates)
        + f" WHERE id = {int(booking_id)} AND user_id = '{user_id}' RETURNING *;"
    )
    return await create_request(sql, is_multiple=False)


# --- Images cache ---


async def ensure_images_table() -> None:
    await create_request(
        """
        CREATE TABLE IF NOT EXISTS bot_images (
            key TEXT PRIMARY KEY,
            file_id TEXT NOT NULL,
            media_type TEXT NOT NULL DEFAULT 'photo'
        );
        """,
        is_return=False,
    )


async def upsert_image(key: str, file_id: str, media_type: str = "photo") -> None:
    key = _escape_sql_text(key)
    file_id = _escape_sql_text(file_id)
    media_type = _escape_sql_text(media_type)
    sql = (
        "INSERT INTO bot_images (key, file_id, media_type) "
        f"VALUES ('{key}', '{file_id}', '{media_type}') "
        "ON CONFLICT (key) DO UPDATE SET file_id = EXCLUDED.file_id, media_type = EXCLUDED.media_type;"
    )
    await create_request(sql, is_return=False)


async def get_image(key: str) -> dict | None:
    key = _escape_sql_text(key)
    sql = f"SELECT * FROM bot_images WHERE key = '{key}'"
    return await create_request(sql, is_multiple=False)


async def get_images_by_prefix(prefix: str) -> list:
    prefix = _escape_sql_text(prefix)
    sql = f"SELECT * FROM bot_images WHERE key LIKE '{prefix}%' ORDER BY key"
    return await create_request(sql, is_multiple=True) or []



# helper function to change phone number format to default
# async def set_format_for_phone_number():
#     non_format_users = await create_request("SELECT full_name, phone_number FROM user_profile WHERE phone_number LIKE '%(%' ORDER BY full_name")
#
#     for user in non_format_users:
#         user_full_name = user['full_name']
#         user_phone_number = user['phone_number']
#         user_phone_number = user_phone_number.replace('(', '').replace(')', '').replace('-', ' ')
#         await create_request(f"UPDATE user_profile SET phone_number = '{user_phone_number}' WHERE full_name = '{user_full_name}'", is_return=False)
