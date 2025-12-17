import json
import time
from datetime import datetime
from pathlib import Path

from aiogram.types.input_media_photo import InputMediaPhoto

from telegram_bot import db, env, inflector, text_message
from telegram_bot.text_message import PET_PROFILE_TEXT


class CallbackMediaGroupClass:
    def __init__(self, action, first_message_id, last_message_id):
        self.action = action
        self.first_message_id = first_message_id
        self.last_message_id = last_message_id

    def __str__(self):
        return "{" + f"\"act\":\"{self.action}\",\"first\":\"{self.first_message_id}\",\"last\":\"{self.last_message_id}\"" + "}"


async def get_task_text(task: dict) -> str:
    treatment_id, medicament_id, start_date, end_date, period, pet_type = task['treatment_id'], task['medicament_id'], task[
        'start_date'], task['end_date'], task['period'], task['pet_type']
    if int(medicament_id) != 0:
        medicament = await db.get_medicament(id=medicament_id)
        medicament_name = medicament["name"]
    else:
        medicament_name = task["medicament_name"]
    treatment = await db.get_treatments(id=treatment_id)
    pet_type = await db.get_pet_type(id=pet_type)
    text = text_message.REMINDER_TEXT.format(
        treatment=treatment['name'],
        pet=pet_type['name'],
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
    result = []
    for pet in pets_list:
        year_forms = ("год", "лет", "года")
        month_forms = ("месяц", "месяцев", "месяца")
        days_forms = ("день", "дней", "дня")
        years, months, days = 0, 0, 0
        years = round((time.time() - float(pet["birth_date"])) // (86400 * 365))
        days = round((time.time() - float(pet["birth_date"])) // 86400)

        month_now = int(datetime.now().month)
        birth_date_month = int(datetime.fromtimestamp(float(pet["birth_date"]), env.local_timezone).month)

        if month_now > birth_date_month:
            months = month_now - birth_date_month
        elif month_now < birth_date_month:
            months = 12 - birth_date_month + month_now
        years_text = f"{years} {inflector.inflect_with_num(years, year_forms)}"
        month_text = f"{months} {inflector.inflect_with_num(months, month_forms)}"
        days_text = f"{days} {inflector.inflect_with_num(days, days_forms)}"

        if months == 0 and years == 0:
            age_text = days_text
        elif months > 0 and years > 0:
            age_text = f'{years_text} {month_text}'
        elif months == 0:
            age_text = years_text
        elif years == 0:
            age_text = month_text
        else:
            age_text = 'Error!'

        pet_text = PET_PROFILE_TEXT.format(
            count=pets_list.index(pet) + 1, name=pet['name'], approx_weight=pet["approx_weight"],
            emoji='🐶' if pet['type'] == 'dog' else '🐱',
            age=age_text,
            birth_date=datetime.fromtimestamp(float(pet["birth_date"])).strftime('%d %B %Y'),
            type='собака' if pet['type'] == 'dog' else 'кот',
            gender='мальчик' if pet['gender'] == 'male' else 'девочка',
            breed=pet['breed'])
        result.append(pet_text)

    return '\n'.join(result)


def get_user_stroke(user_data) -> str:
    forms = ("год", "лет", "года")

    # Обработка случая, когда birth_date может быть None
    if user_data["birth_date"] is None:
        age = "не указан"
        birth_date_str = "не указана"
    else:
        try:
            age = round((time.time() - float(user_data["birth_date"])) // (86400 * 365))
            age = f"{age} {inflector.inflect_with_num(age, forms)}"
            birth_date_str = datetime.fromtimestamp(float(user_data["birth_date"])).strftime('%d %B %Y')
        except (ValueError, TypeError):
            age = "не указан"
            birth_date_str = "не указана"

    return text_message.USER_PROFILE_TEXT.format(
        full_name=user_data.get('full_name', 'не указано'),
        phone_number=user_data.get('phone_number', 'не указан'),
        birth_date=birth_date_str,
        age=age
    )

def get_dict_fetch(cursor, fetch):
    results = []
    columns = list(cursor.description)
    for row in fetch:
        row_dict = {}
        for i, col in enumerate(columns):
            row_dict[col.name] = row[i]
        results.append(row_dict)
    return results


async def get_photo_id(file_path: str) -> str:
    relative_path = _make_relative_path(file_path)
    await db.ensure_images_table()
    image = await db.get_image(relative_path)
    if image is None:
        raise FileNotFoundError(f"Файл {relative_path} не найден в базе. Используйте /send_images для обновления хранилища.")
    return image["file_id"]


async def get_media_group(path: str, first_message_text: str, photos_end: int, img_format: str = 'jpg', photos_start: int = 1) -> list:
    relative_prefix = _make_relative_path(path)
    file_keys = [f"{relative_prefix}/{i}.{img_format}" for i in range(photos_start, photos_end + 1)]
    photo_ids = [await get_photo_id(file_key) for file_key in file_keys]
    first_photo = [InputMediaPhoto(media=photo_ids[0], caption=first_message_text)]
    media_group = first_photo + [InputMediaPhoto(media=photo_id) for photo_id in photo_ids[1:]]
    return media_group


def is_valid_json(json_str):
    try:
        json.loads(json_str)
        return True
    except json.JSONDecodeError:
        return False


def _make_relative_path(file_path: str) -> str:
    base_path = Path(env.img_path)
    path_obj = Path(file_path)
    try:
        return str(path_obj.relative_to(base_path))
    except ValueError:
        return str(path_obj)


def convert_callback_to_json_data(callback_action: str, first_message_id: int | str, last_message_id: int | str):
    return "{" + f"\"act\":\"{callback_action}\",\"first\":\"{first_message_id}\", \"last\":\"{last_message_id}\"" + "}"