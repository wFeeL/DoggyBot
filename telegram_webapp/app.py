from datetime import datetime

import psycopg2
from flask import Flask, render_template, jsonify

app = Flask(__name__, static_folder='static')
@app.route("/")
def index():
    return render_template('index.html')


# Получение данных пользователя
@app.route("/get_user_data/<telegram_id>", methods=["GET"])
def get_user_data(telegram_id):
    pg_dsn = "postgres://flask_user:password123@91.239.206.123:29572/flask_db"
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
            'birth_date': datetime.fromtimestamp(user_profile["birth_date"]).strftime('%Y-%m-%d'),
            'about_me': user_profile['about_me'],
            'pets': pets,
        }
        return jsonify(data)
    return jsonify({"data": None})


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
