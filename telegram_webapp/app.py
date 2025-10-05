import asyncio
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
        content = request.json
        print(dict(content))
        init_data = content.get("initData")
        survey_data = content.get("surveyData")

        if not init_data:
            return jsonify({"ok": False, "error": "initData отсутствует"})

        parsed = parse_qs(init_data)
        query_id = parsed.get("query_id", [None])[0]

        if not query_id:
            return jsonify({"ok": False, "error": "query_id не найден"})

        # Формируем текст сообщения с ответами
        message_text = f"📊 Новые ответы на анкету: {survey_data['service_name']}\n"
        message_text += f"👤 Пользователь: {survey_data['user_id']}\n\n"

        answers = survey_data['answers']
        for i, (question_key, answer) in enumerate(answers.items(), 1):
            message_text += f"❓ Вопрос {i}:\n{answer}\n\n"

        # Отправляем сообщение в Telegram
        answer_url = f"https://api.telegram.org/bot{str(os.environ['BOT_TOKEN'])}/sendMessage"
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
        print("Ошибка обработки survey_data:", e)
        return jsonify({"ok": False, "error": str(e)})


if __name__ == "__main__":
    app.run(debug=True)
