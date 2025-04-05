import asyncio
from datetime import datetime

from flask import Flask, render_template, jsonify

app = Flask(__name__, static_folder='static')
@app.route("/")
def index():
    return render_template('index.html')


# Получение данных пользователя
@app.route("/get_user_data/<telegram_id>", methods=["GET"])
def get_user_data(telegram_id):
    pass
    # user_profile = asyncio.run(db.get_user_profile(user_id=telegram_id))
    # pets = asyncio.run(db.get_pets(user_id=telegram_id, is_multiple=True))

    # if user_profile:
    #     if len(pets) > 0:
    #         pets = list(map(lambda elem: dict(elem), pets))
    #         for pet in pets:
    #             pet['birth_date'] = datetime.fromtimestamp(float(pet["birth_date"])).strftime('%Y-%m-%d')
    #     else:
    #         pets = []
    #
    #     data = {
    #         'full_name': user_profile['full_name'],
    #         'phone_number': user_profile['phone_number'],
    #         'birth_date': datetime.fromtimestamp(user_profile["birth_date"]).strftime('%Y-%m-%d'),
    #         'about_me': user_profile['about_me'],
    #         'pets': pets,
    #     }
    #     return jsonify(data)
    # return jsonify({"data": None})


if __name__ == "__main__":
    app.run(debug=True)

