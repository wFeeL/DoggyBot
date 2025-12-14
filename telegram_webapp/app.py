import asyncio
import json
import os
from datetime import datetime
from urllib.parse import parse_qs

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

from telegram_bot import db
from telegram_bot.helper import str_to_timestamp, get_user_stroke, get_pets_stroke
from telegram_webapp.services_text import SERVICES, SURVEY_FORM_TEXT, BOOKING_PROFILE, BOOKING_SERVICES

app = Flask(__name__, static_folder='static')
load_dotenv()

# Включаем логирование
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def _tg_user_from_init_data(init_data: str) -> dict | None:
    try:
        parsed = parse_qs(init_data)
        user_raw = parsed.get('user', [None])[0]
        if not user_raw:
            return None
        return json.loads(user_raw)
    except Exception:
        return None


def _format_dt(ts: float) -> str:
    try:
        from telegram_bot.env import local_timezone

        return datetime.fromtimestamp(float(ts), local_timezone).strftime('%d.%m.%Y %H:%M')
    except Exception:
        return datetime.fromtimestamp(float(ts)).strftime('%d.%m.%Y %H:%M')


def _sum_services(service_ids: list[int]) -> tuple[list[dict], int, int]:
    by_id = {int(s["id"]): s for s in BOOKING_SERVICES}
    chosen = []
    total_price = 0
    total_minutes = 0
    for sid in service_ids:
        if int(sid) not in by_id:
            continue
        s = by_id[int(sid)]
        chosen.append(s)
        total_price += int(s.get("price", 0))
        total_minutes += int(s.get("duration_min", 0))
    return chosen, total_price, total_minutes


def _day_bounds(date_str: str) -> tuple[float, float]:
    from telegram_bot.env import local_timezone

    dt = datetime.strptime(date_str, '%Y-%m-%d').replace(tzinfo=local_timezone)
    day_start = dt.replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
    day_end = dt.replace(hour=23, minute=59, second=59, microsecond=0).timestamp()
    return day_start, day_end


def _work_bounds(date_str: str) -> tuple[float, float]:
    from telegram_bot.env import local_timezone

    dt = datetime.strptime(date_str, '%Y-%m-%d').replace(tzinfo=local_timezone)
    start = dt.replace(hour=10, minute=0, second=0, microsecond=0).timestamp()
    end = dt.replace(hour=21, minute=0, second=0, microsecond=0).timestamp()
    return start, end


try:
    asyncio.run(db.ensure_bookings_table())
except Exception as e:
    logger.warning(f"ensure_bookings_table failed: {e}")


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


# --- Online booking (single profile) ---


@app.route("/booking", methods=["GET"])
def booking_profile_page():
    return render_template(
        "booking_profile.html",
        profile=BOOKING_PROFILE,
        services=BOOKING_SERVICES,
    )


@app.route("/booking/services", methods=["GET"])
def booking_services_page():
    return render_template("booking_services.html", profile=BOOKING_PROFILE)


@app.route("/booking/time", methods=["GET"])
def booking_time_page():
    return render_template("booking_time.html", profile=BOOKING_PROFILE)


@app.route("/booking/comment", methods=["GET"])
def booking_comment_page():
    return render_template("booking_comment.html", profile=BOOKING_PROFILE)


@app.route("/booking/confirm", methods=["GET"])
def booking_confirm_page():
    return render_template("booking_confirm.html", profile=BOOKING_PROFILE)


@app.route("/booking/success", methods=["GET"])
def booking_success_page():
    return render_template("booking_success.html", profile=BOOKING_PROFILE)


@app.route("/client", methods=["GET"])
def client_profile_page():
    return render_template("client_profile.html", profile=BOOKING_PROFILE)


@app.route("/api/auth/ensure_user", methods=["POST"])
def api_ensure_user():
    payload = request.get_json(silent=True) or {}
    init_data = (payload.get("initData") or "").strip()
    tg_user = _tg_user_from_init_data(init_data)
    if not tg_user or not tg_user.get("id"):
        return jsonify({"ok": False, "error": "telegram_user_missing"}), 400

    user_id = int(tg_user["id"])
    username = tg_user.get("username") or ""
    first_name = tg_user.get("first_name") or ""
    last_name = tg_user.get("last_name") or ""

    try:
        exists = asyncio.run(db.get_users(user_id=user_id))
        if not exists:
            asyncio.run(db.add_user(user_id=user_id, username=username, name=first_name, last_name=last_name))
        return jsonify({"ok": True, "user_id": user_id})
    except Exception as e:
        logger.error(f"ensure_user failed: {e}")
        return jsonify({"ok": False, "error": "server_error"}), 500


@app.route("/api/profile/has_form/<telegram_id>", methods=["GET"])
def api_has_form(telegram_id):
    try:
        value = asyncio.run(db.is_user_have_form(user_id=telegram_id))
        return jsonify({"ok": True, "has_form": bool(value)})
    except Exception as e:
        logger.error(f"has_form failed: {e}")
        return jsonify({"ok": True, "has_form": False})


@app.route("/api/profile/details/<telegram_id>", methods=["GET"])
def api_profile_details(telegram_id):
    try:
        user_profile = asyncio.run(db.get_user_profile(user_id=telegram_id))
        pets = asyncio.run(db.get_pets(user_id=telegram_id, is_multiple=True)) or []

        if not user_profile:
            return jsonify({"ok": True, "profile": None, "pets": []})

        pets_norm = []
        for pet in pets:
            p = dict(pet)
            if p.get("birth_date"):
                try:
                    p["birth_date"] = datetime.fromtimestamp(float(p["birth_date"])).strftime("%Y-%m-%d")
                except Exception:
                    pass
            pets_norm.append(p)

        profile = dict(user_profile)
        if profile.get("birth_date"):
            try:
                profile["birth_date"] = datetime.fromtimestamp(float(profile["birth_date"])).strftime("%Y-%m-%d")
            except Exception:
                pass

        return jsonify({"ok": True, "profile": profile, "pets": pets_norm})
    except Exception as e:
        logger.error(f"profile_details failed: {e}")
        return jsonify({"ok": False, "error": "server_error"}), 500


@app.route("/api/booking/services", methods=["GET"])
def api_booking_services():
    return jsonify({"ok": True, "services": BOOKING_SERVICES})


@app.route("/api/booking/slots", methods=["GET"])
def api_booking_slots():
    date_str = (request.args.get("date") or "").strip()
    service_ids_raw = (request.args.get("service_ids") or "").strip()

    if not date_str:
        return jsonify({"ok": False, "error": "date_required"}), 400

    try:
        service_ids = [int(x) for x in service_ids_raw.split(",") if x.strip().isdigit()]
    except Exception:
        service_ids = []

    chosen, _, total_minutes = _sum_services(service_ids)
    if not chosen:
        return jsonify({"ok": False, "error": "services_required"}), 400

    duration_sec = max(15, int(total_minutes)) * 60
    work_start, work_end = _work_bounds(date_str)
    now_ts = datetime.now().timestamp()

    day_start, day_end = _day_bounds(date_str)
    try:
        bookings = asyncio.run(db.get_bookings_in_range(day_start, day_end)) or []
    except Exception as e:
        logger.error(f"slots get_bookings_in_range failed: {e}")
        bookings = []

    occupied = []
    for b in bookings:
        try:
            occupied.append((float(b["start_ts"]), float(b["end_ts"])))
        except Exception:
            continue

    step = 15 * 60
    slots = []
    start = int(work_start)
    end_limit = int(work_end - duration_sec)
    for s in range(start, end_limit + 1, step):
        if s < now_ts:
            continue
        e = s + duration_sec
        is_free = True
        for os, oe in occupied:
            if s < oe and e > os:
                is_free = False
                break
        if not is_free:
            continue
        slots.append({"start_ts": float(s), "label": _format_dt(s)})

    return jsonify({"ok": True, "slots": slots, "duration_min": total_minutes})


@app.route("/api/booking/list/<telegram_id>", methods=["GET"])
def api_booking_list(telegram_id):
    kind = (request.args.get("kind") or "upcoming").strip()
    if kind not in {"upcoming", "past"}:
        kind = "upcoming"
    try:
        items = asyncio.run(db.get_user_bookings(user_id=telegram_id, kind=kind, limit=100)) or []
    except Exception as e:
        logger.error(f"booking_list failed: {e}")
        items = []

    def _normalize_booking(b: dict) -> dict:
        out = dict(b)
        for k in ("start_ts", "end_ts", "created_at"):
            if k in out and out[k] is not None:
                try:
                    out[k] = float(out[k])
                except Exception:
                    pass
        for k in ("services",):
            if k in out and isinstance(out[k], str):
                try:
                    out[k] = json.loads(out[k])
                except Exception:
                    pass
        return out

    return jsonify({"ok": True, "items": [_normalize_booking(dict(i)) for i in items]})


@app.route("/api/booking/create", methods=["POST"])
def api_booking_create():
    payload = request.get_json(silent=True) or {}
    init_data = (payload.get("initData") or "").strip()
    tg_user = _tg_user_from_init_data(init_data)
    booking = payload.get("booking") or {}

    if not tg_user or not tg_user.get("id"):
        return jsonify({"ok": False, "error": "telegram_user_missing"}), 400

    user_id = int(tg_user["id"])
    service_ids = booking.get("service_ids") or []
    start_ts = booking.get("start_ts")
    comment = booking.get("comment")
    promo_code = booking.get("promo_code")

    if not isinstance(service_ids, list) or not service_ids:
        return jsonify({"ok": False, "error": "services_required"}), 400
    if start_ts is None:
        return jsonify({"ok": False, "error": "start_ts_required"}), 400

    try:
        start_ts = float(start_ts)
    except Exception:
        return jsonify({"ok": False, "error": "start_ts_invalid"}), 400

    try:
        has_form = asyncio.run(db.is_user_have_form(user_id=user_id))
    except Exception:
        has_form = False
    if not has_form:
        return jsonify({"ok": False, "error": "form_required"}), 403

    chosen, total_price, total_minutes = _sum_services([int(x) for x in service_ids if str(x).isdigit()])
    if not chosen:
        return jsonify({"ok": False, "error": "services_required"}), 400

    end_ts = start_ts + (int(total_minutes) * 60)

    date_str = None
    try:
        from telegram_bot.env import local_timezone

        date_str = datetime.fromtimestamp(start_ts, local_timezone).strftime('%Y-%m-%d')
    except Exception:
        date_str = datetime.fromtimestamp(start_ts).strftime('%Y-%m-%d')

    work_start, work_end = _work_bounds(date_str)
    if start_ts < work_start or end_ts > work_end:
        return jsonify({"ok": False, "error": "outside_working_hours"}), 409

    try:
        conflicts = asyncio.run(db.get_bookings_in_range(start_ts, end_ts)) or []
    except Exception:
        conflicts = []
    if conflicts:
        return jsonify({"ok": False, "error": "slot_unavailable"}), 409

    try:
        created = asyncio.run(
            db.add_booking(
                user_id=user_id,
                start_ts=start_ts,
                end_ts=end_ts,
                services=chosen,
                total_price=total_price,
                specialist=BOOKING_PROFILE.get("specialist") or "",
                comment=comment,
                promo_code=promo_code,
            )
        )
    except Exception as e:
        logger.error(f"add_booking failed: {e}")
        return jsonify({"ok": False, "error": "server_error"}), 500

    try:
        user_profile = asyncio.run(db.get_user_profile(user_id=user_id))
        pets = asyncio.run(db.get_pets(user_id=user_id, is_multiple=True)) or []

        services_lines = "\n".join(
            [f"• {s['name']} — {s['duration_min']} мин — {s['price']} ₽" for s in chosen]
        )
        contact_text = get_user_stroke(user_profile) if user_profile else "Анкета не найдена"
        pets_text = get_pets_stroke(pets) if pets else "(нет данных)"

        msg = (
            "📅 <b>Новая запись</b>\n\n"
            f"👩‍⚕️ <b>Специалист:</b> {BOOKING_PROFILE.get('specialist')}\n"
            f"🕒 <b>Дата/время:</b> {_format_dt(start_ts)}\n\n"
            f"🧾 <b>Услуги:</b>\n{services_lines}\n\n"
            f"💳 <b>Итого:</b> {total_price} ₽\n"
            f"💬 <b>Комментарий:</b> {comment or '—'}\n"
            f"🎟️ <b>Промокод:</b> <code>{promo_code or '—'}</code>\n\n"
            f"👤 <b>Пользователь:</b> @{tg_user.get('username') or '—'}\n"
            f"{contact_text}\n\n"
            f"🐾 <b>Питомцы:</b>\n{pets_text}"
        )

        admin_ids = json.loads(os.environ.get("ADMIN_TELEGRAM_ID", "[]"))
        token = os.environ.get("BOT_TOKEN")
        if token and admin_ids:
            for admin_id in admin_ids:
                requests.post(
                    f"https://api.telegram.org/bot{token}/sendMessage",
                    json={
                        "chat_id": admin_id,
                        "text": msg,
                        "parse_mode": "HTML",
                        "disable_web_page_preview": True,
                    },
                    timeout=10,
                )
    except Exception as e:
        logger.warning(f"booking notification failed: {e}")

    return jsonify({"ok": True, "booking": created})





@app.route("/api/booking/cancel", methods=["POST"])
def api_booking_cancel():
    payload = request.get_json(silent=True) or {}
    init_data = (payload.get("initData") or "").strip()
    tg_user = _tg_user_from_init_data(init_data)
    booking_id = payload.get("booking_id")

    if not tg_user or not tg_user.get("id"):
        return jsonify({"ok": False, "error": "telegram_user_missing"}), 400

    try:
        booking_id = int(booking_id)
    except Exception:
        return jsonify({"ok": False, "error": "booking_id_invalid"}), 400

    user_id = int(tg_user["id"])

    try:
        current = asyncio.run(db.get_booking_by_id(booking_id))
    except Exception as e:
        logger.error(f"get_booking_by_id failed: {e}")
        current = None

    if not current or str(current.get("user_id")) != str(user_id):
        return jsonify({"ok": False, "error": "booking_not_found"}), 404

    # Cancel only upcoming bookings
    try:
        if float(current.get("start_ts") or 0) < datetime.now().timestamp():
            return jsonify({"ok": False, "error": "already_started"}), 409
    except Exception:
        pass

    try:
        updated = asyncio.run(db.cancel_booking(booking_id=booking_id, user_id=user_id))
    except Exception as e:
        logger.error(f"cancel_booking failed: {e}")
        return jsonify({"ok": False, "error": "server_error"}), 500

    if not updated:
        return jsonify({"ok": False, "error": "booking_not_found"}), 404

    try:
        services = current.get("services")
        if isinstance(services, str):
            try:
                services = json.loads(services)
            except Exception:
                services = []
        services = services if isinstance(services, list) else []
        services_lines = "\n".join([f"• {s.get('name')}" for s in services]) or "—"

        msg = (
            "❌ <b>Запись отменена</b>\n\n"
            f"👩‍⚕️ <b>Специалист:</b> {BOOKING_PROFILE.get('specialist')}\n"
            f"🆔 <b>ID:</b> {booking_id}\n"
            f"🕒 <b>Дата/время:</b> {_format_dt(float(current.get('start_ts') or 0))}\n\n"
            f"🧾 <b>Услуги:</b>\n{services_lines}\n\n"
            f"👤 <b>Пользователь:</b> @{tg_user.get('username') or '—'}"
        )

        admin_ids = json.loads(os.environ.get("ADMIN_TELEGRAM_ID", "[]"))
        token = os.environ.get("BOT_TOKEN")
        if token and admin_ids:
            for admin_id in admin_ids:
                requests.post(
                    f"https://api.telegram.org/bot{token}/sendMessage",
                    json={
                        "chat_id": admin_id,
                        "text": msg,
                        "parse_mode": "HTML",
                        "disable_web_page_preview": True,
                    },
                    timeout=10,
                )
    except Exception as e:
        logger.warning(f"cancel notification failed: {e}")

    return jsonify({"ok": True, "booking": updated})


@app.route("/api/booking/reschedule", methods=["POST"])
def api_booking_reschedule():
    payload = request.get_json(silent=True) or {}
    init_data = (payload.get("initData") or "").strip()
    tg_user = _tg_user_from_init_data(init_data)
    b = payload.get("booking") or {}

    if not tg_user or not tg_user.get("id"):
        return jsonify({"ok": False, "error": "telegram_user_missing"}), 400

    try:
        booking_id = int(b.get("id"))
    except Exception:
        return jsonify({"ok": False, "error": "booking_id_invalid"}), 400

    user_id = int(tg_user["id"])

    try:
        current = asyncio.run(db.get_booking_by_id(booking_id))
    except Exception as e:
        logger.error(f"get_booking_by_id failed: {e}")
        current = None

    if not current or str(current.get("user_id")) != str(user_id):
        return jsonify({"ok": False, "error": "booking_not_found"}), 404

    service_ids = b.get("service_ids") or []
    start_ts = b.get("start_ts")
    comment = b.get("comment")
    promo_code = b.get("promo_code")

    if not isinstance(service_ids, list) or not service_ids:
        return jsonify({"ok": False, "error": "services_required"}), 400
    if start_ts is None:
        return jsonify({"ok": False, "error": "start_ts_required"}), 400

    try:
        start_ts = float(start_ts)
    except Exception:
        return jsonify({"ok": False, "error": "start_ts_invalid"}), 400

    try:
        has_form = asyncio.run(db.is_user_have_form(user_id=user_id))
    except Exception:
        has_form = False
    if not has_form:
        return jsonify({"ok": False, "error": "form_required"}), 403

    chosen, total_price, total_minutes = _sum_services([int(x) for x in service_ids if str(x).isdigit()])
    if not chosen:
        return jsonify({"ok": False, "error": "services_required"}), 400

    end_ts = start_ts + (int(total_minutes) * 60)

    try:
        from telegram_bot.env import local_timezone
        date_str = datetime.fromtimestamp(start_ts, local_timezone).strftime('%Y-%m-%d')
    except Exception:
        date_str = datetime.fromtimestamp(start_ts).strftime('%Y-%m-%d')

    work_start, work_end = _work_bounds(date_str)
    if start_ts < work_start or end_ts > work_end:
        return jsonify({"ok": False, "error": "outside_working_hours"}), 409

    try:
        conflicts = asyncio.run(db.get_bookings_in_range(start_ts, end_ts)) or []
    except Exception:
        conflicts = []

    conflicts = [c for c in conflicts if int(c.get('id') or 0) != booking_id]
    if conflicts:
        return jsonify({"ok": False, "error": "slot_unavailable"}), 409

    try:
        updated = asyncio.run(
            db.reschedule_booking(
                booking_id=booking_id,
                user_id=user_id,
                start_ts=start_ts,
                end_ts=end_ts,
                services=chosen,
                total_price=total_price,
                comment=comment,
                promo_code=promo_code,
            )
        )
    except Exception as e:
        logger.error(f"reschedule_booking failed: {e}")
        return jsonify({"ok": False, "error": "server_error"}), 500

    if not updated:
        return jsonify({"ok": False, "error": "booking_not_found"}), 404

    try:
        old_dt = _format_dt(float(current.get('start_ts') or 0))
        new_dt = _format_dt(start_ts)
        services_lines = "\n".join([f"• {s.get('name')}" for s in chosen]) or "—"

        msg = (
            "🔁 <b>Запись перенесена</b>\n\n"
            f"👩‍⚕️ <b>Специалист:</b> {BOOKING_PROFILE.get('specialist')}\n"
            f"🆔 <b>ID:</b> {booking_id}\n"
            f"🕒 <b>Было:</b> {old_dt}\n"
            f"🕒 <b>Стало:</b> {new_dt}\n\n"
            f"🧾 <b>Услуги:</b>\n{services_lines}\n\n"
            f"👤 <b>Пользователь:</b> @{tg_user.get('username') or '—'}"
        )

        admin_ids = json.loads(os.environ.get("ADMIN_TELEGRAM_ID", "[]"))
        token = os.environ.get("BOT_TOKEN")
        if token and admin_ids:
            for admin_id in admin_ids:
                requests.post(
                    f"https://api.telegram.org/bot{token}/sendMessage",
                    json={
                        "chat_id": admin_id,
                        "text": msg,
                        "parse_mode": "HTML",
                        "disable_web_page_preview": True,
                    },
                    timeout=10,
                )
    except Exception as e:
        logger.warning(f"reschedule notification failed: {e}")

    return jsonify({"ok": True, "booking": updated})
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