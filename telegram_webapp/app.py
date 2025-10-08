import asyncio
import os
from datetime import datetime
from urllib.parse import parse_qs

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

from telegram_webapp.services_text import SERVICES, SURVEY_FORM_TEXT
from telegram_bot import db
from telegram_bot.helper import str_to_timestamp, get_user_stroke

app = Flask(__name__, static_folder='static')
load_dotenv()

@app.route("/")
def index():
    return render_template('index.html')


@app.route("/get_user_data/<telegram_id>", methods=["GET"])
def get_user_data(telegram_id):
    user_profile = asyncio.run(db.get_user_profile(user_id=telegram_id))
    pets = asyncio.run(db.get_pets(user_id=telegram_id, is_multiple=True))
    if user_profile:
        if len(pets) > 0:
            pets = list(map(lambda elem: dict(elem), pets))
            for pet in pets:
                pet['birth_date'] = datetime.fromtimestamp(float(pet["birth_date"])).strftime('%Y-%m-%d')
        else:
            pets = []

        data = {
            'full_name': user_profile['full_name'],
            'phone_number': user_profile['phone_number'],
            'birth_date': datetime.fromtimestamp(float(user_profile["birth_date"])).strftime('%Y-%m-%d'),
            'about_me': user_profile['about_me'],
            'pets': pets,
        }
        return jsonify(data)
    return jsonify({"data": None})


@app.route("/webapp_data", methods=["POST"])
def handle_webapp_data():
    try:
        content = request.json
        init_data = content.get("initData")
        form_data = content.get("formData")

        if not init_data:
            return jsonify({"ok": False, "error": "initData отсутствует"})

        parsed = parse_qs(init_data)
        query_id = parsed.get("query_id", [None])[0]

        if not query_id:
            return jsonify({"ok": False, "error": "query_id не найден"})

        answer_url = f"https://api.telegram.org/bot{str(os.environ['BOT_TOKEN'])}/sendMessage"

        form_data = asyncio.run(db.validate_user_form_data(form_data))

        user_id = form_data['human']['user_id']
        if form_data:
            human = form_data['human']
            asyncio.run(db.update_user_profile(
                user_id=user_id, birth_date=str_to_timestamp(human["birth_date"]), full_name=human["full_name"],
                phone_number=human["phone_number"], about_me=human["about_me"]
            ))
            asyncio.run(db.update_user(user_id=user_id, form_value=1))
            asyncio.run(db.delete_pets(user_id))
            for pet in form_data["pets"]:
                asyncio.run(db.add_pet(
                    user_id=user_id, birth_date=str_to_timestamp(pet["birth_date"]),
                    approx_weight=pet["weight"],
                    name=pet["name"], gender=pet["gender"], pet_type=pet["type"], pet_breed=pet["breed"]
                ))

        answer_payload = {
            "chat_id": user_id,
            "text": f"Спасибо, {form_data['human']['full_name']}! Мы получили ваши данные.",
            "reply_markup": {"inline_keyboard": [[{"text": "🔙 Главное меню",
                                                   "callback_data": "menu"}]]}
        }

        response = requests.post(answer_url, json=answer_payload)

        if response.status_code == 200:
            return jsonify({"ok": True})
        else:
            return jsonify({"ok": False, "error": response.text})

    except Exception as e:
        print("Ошибка обработки:", e)
        return jsonify({"ok": False, "error": str(e)})


def number_to_emoji(number):
    """Преобразует число в строку с эмодзи-цифрами"""
    emoji_digits = {
        '0': '0️⃣',
        '1': '1️⃣',
        '2': '2️⃣',
        '3': '3️⃣',
        '4': '4️⃣',
        '5': '5️⃣',
        '6': '6️⃣',
        '7': '7️⃣',
        '8': '8️⃣',
        '9': '9️⃣'
    }

    return ''.join(emoji_digits[digit] for digit in str(number))


@app.route("/survey", methods=["GET"])
def survey():
    survey_id = int(request.args.get('id'))
    service = SERVICES[survey_id]

    # Добавляем сквозную нумерацию для всех опций
    global_counter = 1
    formatted_option_groups = []

    for group in service['option_groups']:
        formatted_group = {
            'title': group.get('title'),
            'options': []
        }

        for option in group['options']:
            formatted_option = dict(option)  # Копируем опцию
            formatted_option['formatted_number'] = number_to_emoji(global_counter)
            formatted_option['display_number'] = global_counter
            formatted_group['options'].append(formatted_option)
            global_counter += 1

        formatted_option_groups.append(formatted_group)

    return render_template('survey.html',
                           survey_id=survey_id,
                           service_name=service['name'],
                           service_description=service.get('description'),
                           service_option_groups=formatted_option_groups,
                           service_footer_link=service.get('footer_link'),
                           service_form_note=service.get('form_note'),
                           total_options=global_counter - 1)


@app.route("/survey_data", methods=["POST"])
async def handle_survey_data():
    try:
        content = request.json
        init_data = content.get("initData")
        survey_data = content.get("surveyData")

        if not init_data:
            return jsonify({"ok": False, "error": "initData отсутствует"})

        service_id = survey_data['service_id']
        service_name = SERVICES[service_id]['name']
        user_id = survey_data['user_id']
        user = await db.get_users(user_id=user_id)
        user_profile = await db.get_user_profile(user_id=user_id)
        contact_text = get_user_stroke(user_profile)

        message_text = SURVEY_FORM_TEXT.format(
            service_name=service_name, selected_option=survey_data['selected_option'],
            free_form=survey_data['free_form'], username=user['username'], contact_text=contact_text,
            promo_code=user['promocode']
        )

        # Отправляем сообщение в Telegram
        bot_token = os.environ.get('BOT_TOKEN')
        if not bot_token:
            return jsonify({"ok": False, "error": "BOT_TOKEN not configured"})

        answer_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        answer_payload = {
            "chat_id": survey_data['user_id'],
            "text": message_text,
            "parse_mode": "HTML"
        }

        response = requests.post(answer_url, json=answer_payload)

        if response.status_code == 200:
            return jsonify({"ok": True})
        else:
            return jsonify({"ok": False, "error": response.text})

    except Exception as e:
        print(f"Ошибка обработки survey_data: {e}")
        return jsonify({"ok": False, "error": str(e)})


if __name__ == "__main__":
    app.run(debug=True, port=80)
