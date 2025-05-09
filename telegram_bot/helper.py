import time
from datetime import datetime

from telegram_bot import db, text_message, env, inflector
from telegram_bot.text_message import PET_PROFILE_TEXT


async def get_task_text(task: dict) -> str:
    treatment_id, medicament_id, start_date, end_date, period = task['treatment_id'], task['medicament_id'], task[
        'start_date'], task['end_date'], task['period']
    if int(medicament_id) != 0:
        medicament = await db.get_medicament(id=medicament_id)
        medicament_name = medicament["name"]
    else:
        medicament_name = task["medicament_name"]
    treatment = await db.get_treatments(id=treatment_id)
    text = text_message.REMINDER_TEXT.format(
        treatment=treatment['name'],
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
        years = round((time.time() - float(pet["birth_date"])) // (86400 * 365))
        months = int(datetime.now().month - datetime.fromtimestamp(float(pet["birth_date"]), env.local_timezone).month)
        if months == 0:
            months = ''
        else:
            months = f"{months} {inflector.inflect_with_num(months, month_forms)}"
        years = f"{years} {inflector.inflect_with_num(years, year_forms)}"
        pet_text = PET_PROFILE_TEXT.format(
            count=pets_list.index(pet) + 1, name=pet['name'], approx_weight=pet["approx_weight"],
            emoji='🐶' if pet['type'] == 'dog' else '🐱',
            years=years, months=months,
            birth_date=datetime.fromtimestamp(float(pet["birth_date"])).strftime('%d %B %Y'),
            type='собака' if pet['type'] == 'dog' else 'кот',
            gender='мальчик' if pet['gender'] == 'male' else 'девочка',
            breed=pet['breed'])
        result.append(pet_text)

    return '\n'.join(result)


def get_user_stroke(user_data) -> str:
    forms = ("год", "лет", "года")
    age = round((time.time() - float(user_data["birth_date"])) // (86400 * 365))
    age = f"{age} {inflector.inflect_with_num(age, forms)}"
    return text_message.USER_PROFILE_TEXT.format(
        full_name=user_data['full_name'], phone_number=user_data['phone_number'],
        birth_date=datetime.fromtimestamp(float(user_data["birth_date"])).strftime('%d %B %Y'),
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
