import json
import os
from telegram_bot import db
from datetime import datetime
from urllib.parse import parse_qs

import asyncio
import requests
from dotenv import load_dotenv
from flask import Flask, request, jsonify, render_template

from telegram_bot.handler.message import str_to_timestamp

app = Flask(__name__, static_folder='static')
load_dotenv()


@app.route("/")
def index():
    return render_template('index.html')


# Получение данных пользователя
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


        # Теперь отправляем ответ через Telegram API
        answer_url = f"https://api.telegram.org/bot{str(os.environ['BOT_TOKEN'])}/answerWebAppQuery"

        form_data = asyncio.run(db.validate_user_form_data(form_data))

        user_id = '416966184'
        if form_data:
            human = form_data['human']
            asyncio.run(db.update_user_profile(
                user_id=user_id, birth_date=str_to_timestamp(human["birth_date"]), full_name=human["full_name"],
                phone_number=human["phone_number"], about_me=human["about_me"]
            ))
            asyncio.run(db.delete_pets(user_id))
            for pet in form_data["pets"]:
                asyncio.run(db.add_pet(
                    user_id=user_id, birth_date=str_to_timestamp(pet["birth_date"]),
                    approx_weight=pet["weight"],
                    name=pet["name"], gender=pet["gender"], pet_type=pet["type"], pet_breed=pet["breed"]
                ))

        answer_payload = {
            "web_app_query_id": query_id,
            "result": {
                "type": "article",
                "id": "id1",
                "title": "Данные получены!",
                "input_message_content": {
                    "message_text": f"Спасибо, {form_data['human']['full_name']}! Мы получили ваши данные."
                }
            }
        }

        response = requests.post(answer_url, json=answer_payload)

        if response.status_code == 200:
            return jsonify({"ok": True})
        else:
            return jsonify({"ok": False, "error": response.text})
    #
    except Exception as e:
        print("Ошибка обработки:", e)
        return jsonify({"ok": False, "error": str(e)})


def get_dict_fetch(cursor, fetch):
    results = []
    columns = list(cursor.description)
    for row in fetch:
        row_dict = {}
        for i, col in enumerate(columns):
            row_dict[col.name] = row[i]
        results.append(row_dict)
    return results


if __name__ == "__main__":
    app.run(debug=True)
