import os
from telegram_bot import env
from datetime import datetime
from urllib.parse import parse_qs

import psycopg2
import requests
from dotenv import load_dotenv
from flask import Flask, request, jsonify, render_template

app = Flask(__name__, static_folder='static')
load_dotenv()

print(env.webapp_url)
@app.route("/")
def index():
    return render_template('index.html')


# Получение данных пользователя
@app.route("/get_user_data/<telegram_id>", methods=["GET"])
def get_user_data(telegram_id):
    pg_dsn = f"postgres://{os.environ['POSTGRES_USER']}:{os.environ['POSTGRES_PASSWORD']}@{os.environ['POSTGRES_HOST']}:{os.environ['POSTGRES_PORT']}/{os.environ['POSTGRES_DATABASE']}"
    connection = psycopg2.connect(str(pg_dsn))

    with connection as conn:
        with conn.cursor() as cur:
            cur.execute(f"SELECT * FROM user_profile WHERE user_id = '{telegram_id}'ORDER by full_name ASC")
            user_profile = get_dict_fetch(cur, cur.fetchall())[0]
            cur.execute(f"SELECT * FROM pets WHERE user_id = '{telegram_id}' ORDER by name ASC")
            pets = get_dict_fetch(cur, cur.fetchall())
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
