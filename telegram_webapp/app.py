import asyncio
import traceback
import json
import os
from datetime import datetime
from urllib.parse import parse_qs

import requests
from dotenv import load_dotenv
from flask import Flask, request, jsonify, render_template

from telegram_bot import db
from telegram_bot.helper import str_to_timestamp

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


@app.route("/survey")
def survey():
    return render_template('survey.html')


@app.route("/survey_data", methods=["POST"])
def handle_survey_data():
    try:
        print("=== SURVEY DATA RECEIVED ===")  # Логирование
        content = request.json
        print(f"Content: {content}")  # Логирование полученных данных

        if not content:
            print("No content received")
            return jsonify({"ok": False, "error": "No data received"})

        init_data = content.get("initData")
        survey_data = content.get("surveyData")

        if not init_data:
            print("No initData found")
            return jsonify({"ok": False, "error": "initData отсутствует"})

        # Парсим initData для получения user_id
        parsed = parse_qs(init_data)
        print(f"Parsed init data: {parsed}")  # Логирование

        user_id = parsed.get("user", [{}])[0]
        if isinstance(user_id, str) and user_id.startswith('{"id":'):
            user_dict = json.loads(user_id)
            user_id = user_dict.get('id')

        if not user_id:
            # Альтернативный способ получения user_id
            user_json = parsed.get("user", [None])[0]
            if user_json:
                user_data = json.loads(user_json)
                user_id = user_data.get('id')
            else:
                user_id = survey_data.get('user_id')

        print(f"User ID: {user_id}")  # Логирование

        # Формируем сообщение для отправки в Telegram
        message_text = f"📊 Новые ответы на анкету: {survey_data.get('service_name', 'Неизвестная услуга')}\n"
        message_text += f"👤 User ID: {user_id}\n\n"

        answers = survey_data.get('answers', {})
        for i, (question_key, answer) in enumerate(answers.items(), 1):
            message_text += f"❓ Вопрос {i}:\n{answer}\n\n"

        # Отправляем сообщение в Telegram
        bot_token = os.environ.get('BOT_TOKEN')
        if not bot_token:
            print("BOT_TOKEN not found in environment")
            return jsonify({"ok": False, "error": "BOT_TOKEN not configured"})

        answer_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        answer_payload = {
            "chat_id": user_id,
            "text": message_text,
            "parse_mode": "HTML"
        }

        print(f"Sending to Telegram: {answer_payload}")  # Логирование
        response = requests.post(answer_url, json=answer_payload)
        print(f"Telegram API response: {response.status_code} - {response.text}")  # Логирование

        if response.status_code == 200:
            return jsonify({"ok": True})
        else:
            error_msg = f"Telegram API error: {response.status_code} - {response.text}"
            print(error_msg)
            return jsonify({"ok": False, "error": error_msg})

    except Exception as e:
        error_msg = f"Exception in handle_survey_data: {str(e)}"
        print(error_msg)

        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({"ok": False, "error": error_msg})


if __name__ == "__main__":
    app.run(debug=True)
