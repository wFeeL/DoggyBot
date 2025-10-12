import asyncio
import json
import os
from datetime import datetime
from urllib.parse import parse_qs

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

from telegram_bot import db
from telegram_bot.helper import str_to_timestamp, get_user_stroke
from telegram_webapp.services_text import SERVICES, SURVEY_FORM_TEXT

app = Flask(__name__, static_folder='static')
load_dotenv()

# Включаем логирование
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


@app.route("/", methods=['GET'])
def index():
    logger.info("GET / - Главная страница")
    return render_template('index.html')


@app.route("/form", methods=['GET'])
def form():
    logger.info("GET /form - Страница анкеты")
    return render_template('form.html')


@app.route("/survey", methods=['GET'])
def survey():
    # Логируем все параметры запроса
    logger.info(f"GET /survey - Параметры: {request.args}")

    # Пробуем разные способы получения ID услуги
    survey_id = None

    # Способ 1: из tgWebAppStartParam (основной)
    if 'tgWebAppStartParam' in request.args:
        survey_id = request.args.get('tgWebAppStartParam')
        logger.info(f"Получен tgWebAppStartParam: {survey_id}")

    # Способ 2: из startapp (резервный)
    if not survey_id and 'startapp' in request.args:
        survey_id = request.args.get('startapp')
        logger.info(f"Получен startapp: {survey_id}")

    # Способ 3: из id (для тестирования)
    if not survey_id and 'id' in request.args:
        survey_id = request.args.get('id')
        logger.info(f"Получен id: {survey_id}")

    if not survey_id:
        logger.error("ID услуги не указан ни в одном параметре")
        return "ID услуги не указан", 400

    try:
        survey_id = int(survey_id)
        service = SERVICES[survey_id]
        logger.info(f"Услуга найдена: {service['name']}")
    except (ValueError, KeyError) as e:
        logger.error(f"Ошибка поиска услуги: {e}")
        return "Услуга не найдена", 404

    global_counter = 1
    formatted_option_groups = []

    for group in service['option_groups']:
        formatted_group = {
            'title': group.get('title'),
            'options': []
        }

        for option in group['options']:
            formatted_option = dict(option)
            formatted_option['formatted_number'] = number_to_emoji(global_counter)
            formatted_option['display_number'] = global_counter
            formatted_group['options'].append(formatted_option)
            global_counter += 1

        formatted_option_groups.append(formatted_group)

    return render_template('survey.html',
                           survey_id=survey_id,
                           service_name=service['name'],
                           service_description=service.get('description'),
                           service_options_title=service.get('options_title'),
                           service_option_groups=formatted_option_groups,
                           service_footer_link=service.get('footer_link'),
                           service_form_note=service.get('form_note'),
                           total_options=global_counter - 1)


@app.route("/get_user_data/<telegram_id>", methods=["GET"])
def get_user_data(telegram_id):
    logger.info(f"GET /get_user_data/{telegram_id}")
    try:
        user_profile = asyncio.run(db.get_user_profile(user_id=telegram_id))
        pets = asyncio.run(db.get_pets(user_id=telegram_id, is_multiple=True))

        if user_profile:
            logger.info(f"Профиль пользователя найден: {user_profile['full_name']}")
            if len(pets) > 0:
                pets = list(map(lambda elem: dict(elem), pets))
                for pet in pets:
                    pet['birth_date'] = datetime.fromtimestamp(float(pet["birth_date"])).strftime('%Y-%m-%d')
                logger.info(f"Найдено питомцев: {len(pets)}")
            else:
                pets = []
                logger.info("Питомцы не найдены")

            data = {
                'full_name': user_profile['full_name'],
                'phone_number': user_profile['phone_number'],
                'birth_date': datetime.fromtimestamp(float(user_profile["birth_date"])).strftime('%Y-%m-%d'),
                'about_me': user_profile['about_me'],
                'pets': pets,
            }
            return jsonify(data)
        else:
            logger.info("Профиль пользователя не найден")
            return jsonify({"data": None})
    except Exception as e:
        logger.error(f"Ошибка в get_user_data: {e}")
        return jsonify({"data": None})


@app.route("/webapp_data", methods=["POST"])
def handle_webapp_data():
    logger.info("POST /webapp_data")
    try:
        content = request.json
        init_data = content.get("initData")
        form_data = content.get("formData")

        logger.info(f"Получены данные формы: {form_data}")

        if not init_data:
            logger.error("initData отсутствует")
            return jsonify({"ok": False, "error": "initData отсутствует"})

        # Валидируем данные формы
        validated_data = asyncio.run(db.validate_user_form_data(form_data))

        # Проверяем результат валидации
        if validated_data is False:
            logger.error("Данные формы не прошли валидацию")
            return jsonify({"ok": False, "error": "Данные формы не прошли валидацию"})

        # Если валидация прошла успешно, используем validated_data
        user_id = validated_data['human']['user_id']
        logger.info(f"Обработка данных пользователя: {user_id}")

        # Обновляем профиль пользователя
        human = validated_data['human']
        asyncio.run(db.update_user_profile(
            user_id=user_id,
            birth_date=str_to_timestamp(human["birth_date"]),
            full_name=human["full_name"],
            phone_number=human["phone_number"],
            about_me=human["about_me"]
        ))
        asyncio.run(db.update_user(user_id=user_id, form_value=1))

        # Удаляем старых питомцев и добавляем новых
        asyncio.run(db.delete_pets(user_id))
        for pet in validated_data["pets"]:
            asyncio.run(db.add_pet(
                user_id=user_id,
                birth_date=str_to_timestamp(pet["birth_date"]),
                approx_weight=pet["weight"],
                name=pet["name"],
                gender=pet["gender"],
                pet_type=pet["type"],
                pet_breed=pet["breed"]
            ))

        # Отправляем сообщение пользователю
        answer_url = f"https://api.telegram.org/bot{str(os.environ['BOT_TOKEN'])}/sendMessage"
        answer_payload = {
            "chat_id": user_id,
            "text": f"Спасибо, {human['full_name']}! Мы получили ваши данные.",
            "reply_markup": {"inline_keyboard": [[{"text": "🔙 Главное меню",
                                                   "callback_data": "menu"}]]}
        }

        logger.info(f"Отправка сообщения пользователю {user_id}")
        response = requests.post(answer_url, json=answer_payload)

        if response.status_code == 200:
            logger.info("Сообщение успешно отправлено")
            return jsonify({"ok": True})
        else:
            logger.error(f"Ошибка отправки сообщения: {response.text}")
            return jsonify({"ok": False, "error": response.text})

    except Exception as e:
        logger.error(f"Ошибка обработки webapp_data: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
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


@app.route("/survey_data", methods=["POST"])
async def handle_survey_data():
    logger.info("POST /survey_data")
    try:
        content = request.json
        init_data = content.get("initData")
        survey_data = content.get("surveyData")

        logger.info(f"Получены данные опроса: {survey_data}")

        if not init_data:
            logger.error("initData отсутствует")
            return jsonify({"ok": False, "error": "initData отсутствует"})

        if not isinstance(init_data, str):
            logger.error("initData должен быть строкой")
            return jsonify({"ok": False, "error": "initData должен быть строкой"})

        try:
            parsed = parse_qs(init_data)
            logger.info(f"Парсинг init_data: {list(parsed.keys())}")
        except Exception as e:
            logger.error(f"Ошибка парсинга init_data: {e}")
            pass

        service_id = survey_data['service_id']
        service_name = SERVICES[service_id]['name']
        user_id = survey_data['user_id']

        logger.info(f"Обработка опроса: услуга {service_id}, пользователь {user_id}")

        # Получаем данные пользователя
        user = await db.get_users(user_id=user_id)
        user_profile = await db.get_user_profile(user_id=user_id)

        # Проверяем, что получили данные пользователя
        if not user_profile:
            logger.error(f"Профиль пользователя {user_id} не найден")
            return jsonify({"ok": False, "error": "Профиль пользователя не найден"})

        contact_text = get_user_stroke(user_profile)

        message_text = SURVEY_FORM_TEXT.format(
            service_name=service_name,
            selected_option=survey_data['selected_option'],
            free_form=survey_data['free_form'],
            username=user['username'] if user else 'не указан',
            contact_text=contact_text,
            promo_code=user['promocode'] if user else 'не указан'
        )

        logger.info(f"Текст сообщения подготовлен, длина: {len(message_text)}")

        # Отправляем сообщение в Telegram
        bot_token = os.environ.get('BOT_TOKEN')
        if not bot_token:
            logger.error("BOT_TOKEN not configured")
            return jsonify({"ok": False, "error": "BOT_TOKEN not configured"})

        # Получаем список администраторов
        try:
            admin_ids = list(json.loads(os.environ['ADMIN_TELEGRAM_ID']))
            logger.info(f"Отправка администраторам: {admin_ids}")
        except Exception as e:
            logger.error(f"Ошибка парсинга ADMIN_TELEGRAM_ID: {e}")
            return jsonify({"ok": False, "error": "Ошибка в конфигурации администраторов"})

        # Отправляем сообщение всем администраторам
        success_count = 0
        errors = []

        for admin_id in admin_ids:
            try:
                answer_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                answer_payload = {
                    "chat_id": admin_id,
                    "text": message_text,
                    "parse_mode": "HTML"
                }

                logger.info(f"Отправка администратору {admin_id}")
                response = requests.post(answer_url, json=answer_payload)
                logger.info(f"Ответ Telegram API для администратора {admin_id}: {response.status_code}")

                if response.status_code == 200:
                    success_count += 1
                else:
                    error_msg = f"Ошибка отправки администратору {admin_id}: {response.status_code} - {response.text}"
                    errors.append(error_msg)
                    logger.error(error_msg)

            except Exception as e:
                error_msg = f"Исключение при отправке администратору {admin_id}: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)

        # Если сообщение отправлено хотя бы одному администратору, считаем успехом
        if success_count > 0:
            logger.info(f"Сообщение успешно отправлено {success_count} администраторам")
            if errors:
                logger.warning(f"Были ошибки при отправке некоторым администраторам: {errors}")
            return jsonify({"ok": True})
        else:
            error_msg = "Не удалось отправить сообщение ни одному администратору: " + "; ".join(errors)
            logger.error(error_msg)
            return jsonify({"ok": False, "error": error_msg})

    except Exception as e:
        error_msg = f"Exception in handle_survey_data: {str(e)}"
        logger.error(error_msg)
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({"ok": False, "error": error_msg})


if __name__ == "__main__":
    app.run(debug=True, port=80)