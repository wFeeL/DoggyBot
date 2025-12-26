import asyncio
import json
import os
import re
from datetime import datetime, timedelta
from urllib.parse import parse_qs

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

from telegram_bot import db
from telegram_bot.env import admins_telegram_id
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


def _is_admin(init_data: str) -> bool:
    tg_user = _tg_user_from_init_data(init_data)
    if not tg_user or not tg_user.get("id"):
        return False
    try:
        uid = int(tg_user["id"])
    except Exception:
        return False
    return uid in (admins_telegram_id or [])


def _send_bot_message(chat_id: int, text: str) -> bool:
    """Отправка сообщения пользователю от бота (без aiogram, через HTTP API)."""

    token = (os.getenv("BOT_TOKEN") or "").strip()
    if not token:
        return False
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": int(chat_id), "text": text, "parse_mode": "HTML"}
        r = requests.post(url, json=payload, timeout=10)
        return r.status_code == 200
    except Exception:
        return False


def _format_dt(ts: float) -> str:
    try:
        from telegram_bot.env import local_timezone

        dt = datetime.fromtimestamp(float(ts), local_timezone)
        wd = ['пн', 'вт', 'ср', 'чт', 'пт', 'сб', 'вс'][dt.weekday()]
        # 23.12.2025 (вт) 10:00
        return dt.strftime('%d.%m.%Y') + f" ({wd}) " + dt.strftime('%H:%M')
    except Exception:
        dt = datetime.fromtimestamp(float(ts))
        wd = ['пн', 'вт', 'ср', 'чт', 'пт', 'сб', 'вс'][dt.weekday()]
        return dt.strftime('%d.%m.%Y') + f" ({wd}) " + dt.strftime('%H:%M')


def _sum_services(service_ids: list[int]) -> tuple[list[dict], int, int]:
    by_id = {int(s["id"]): s for s in _get_all_services()}
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


# --- Booking availability defaults ---

# Период между доступными стартами записи (мин)
BOOKING_STEP_MIN = 30
# Окно записи: показываем только ближайший месяц
BOOKING_HORIZON_DAYS = 30

# Внешняя запись (не из бота) по умолчанию занимает 60 минут и блокирует слот.
EXTERNAL_BOOKING_DURATION_MIN = 60


def _default_slot_hhmm() -> list[str]:
    """Дефолтные стартовые времена записи.

    По умолчанию каждый день полностью доступен с 10:00 до 21:00,
    шаг между стартами — 30 минут.
    """
    out: list[str] = []
    for h in range(10, 21):
        for m in range(0, 60, BOOKING_STEP_MIN):
            # последний старт: 20:30 (рабочий день до 21:00)
            if h == 20 and m > 30:
                continue
            if h == 21:
                continue
            out.append(f"{h:02d}:{m:02d}")
    return out


def _parse_time_hhmm(value: str):
    """Parse time like '10:00' or '10:00:00' -> (hh, mm) or None."""
    s = (value or '').strip()
    if not s:
        return None
    # Accept HH:MM or HH:MM:SS
    m = re.match(r'^(\d{1,2}):(\d{2})(?::(\d{2}))?$', s)
    if not m:
        return None
    try:
        hh = int(m.group(1))
        mm = int(m.group(2))
    except Exception:
        return None
    if not (0 <= hh <= 23 and 0 <= mm <= 59):
        return None
    return hh, mm


def _coerce_slots_list(raw) -> list[str]:
    """Normalize DB slots JSON to list[str] of HH:MM."""
    if raw is None:
        return []
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            return []
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for x in raw:
        t = _parse_time_hhmm(str(x))
        if not t:
            continue
        hh, mm = t
        out.append(f"{hh:02d}:{mm:02d}")
    return sorted(set(out))


def _allowed_hhmm_for_services(date_str: str, service_ids: list[int]) -> list[str]:
    """Allowed start times (HH:MM) for given services on date.

    Logic:
    - If admin did not configure a date for a service -> use default slots.
    - If admin configured empty slots -> day is закрыт for this service.
    - For multiple services -> intersection across services.
    """

    if not service_ids:
        return []

    allowed: set[str] | None = None
    for sid in service_ids:
        row = None
        try:
            row = asyncio.run(db.get_service_availability(service_id=int(sid), date=date_str))
        except Exception as e:
            logger.error(f"get_service_availability failed: {e}")
            row = None

        if row is None:
            slots = _default_slot_hhmm()
        else:
            slots = _coerce_slots_list(row.get('slots'))

        # Empty list means "closed" for this service
        cur = set(slots)
        if allowed is None:
            allowed = cur
        else:
            allowed &= cur

        if not allowed:
            return []

    return sorted(allowed or [])


def _allowed_start_ts_for_services(date_str: str, service_ids: list[int]) -> list[int]:
    """Allowed start timestamps for given services on date in local TZ."""
    from telegram_bot.env import local_timezone

    hhmm_list = _allowed_hhmm_for_services(date_str, service_ids)
    try:
        base = datetime.strptime(date_str, '%Y-%m-%d').replace(tzinfo=local_timezone)
    except Exception:
        return []

    out: list[int] = []
    for t in hhmm_list:
        parsed = _parse_time_hhmm(t)
        if not parsed:
            continue
        hh, mm = parsed
        out.append(int(base.replace(hour=hh, minute=mm, second=0, microsecond=0).timestamp()))
    return out

def _is_date_in_booking_window(date_str: str) -> bool:
    """True if date_str is within [today, today+BOOKING_HORIZON_DAYS] in local TZ."""
    try:
        from telegram_bot.env import local_timezone
        req = datetime.strptime(date_str, '%Y-%m-%d').date()
        base = datetime.now(local_timezone).date()
    except Exception:
        try:
            req = datetime.strptime(date_str, '%Y-%m-%d').date()
        except Exception:
            return False
        base = datetime.now().date()
    return base <= req <= (base + timedelta(days=int(BOOKING_HORIZON_DAYS)))


_BOOKINGS_READY = False


def _ensure_bookings_ready() -> None:
    """Создаём таблицы для онлайн-записи лениво.

    На уровне импорта вызывать asyncio.run() не стоит — Flask reloader
    может инициализировать модуль несколько раз.
    """

    global _BOOKINGS_READY
    if _BOOKINGS_READY:
        return
    try:
        asyncio.run(db.ensure_bookings_table())
        _BOOKINGS_READY = True
    except Exception as e:
        logger.warning(f"ensure_bookings_table failed: {e}")


@app.before_request
def _before_any_request():
    _ensure_bookings_ready()


_SERVICES_CACHE: dict[str, object] = {"ts": 0.0, "services": BOOKING_SERVICES}


def _get_all_services(force: bool = False) -> list[dict]:
    """Базовые + кастомные услуги из админки.

    Чтобы не дёргать БД на каждый запрос — держим лёгкий кэш.
    """
    now = datetime.now().timestamp()
    if (not force) and (now - float(_SERVICES_CACHE.get("ts") or 0) < 10):
        return list(_SERVICES_CACHE.get("services") or BOOKING_SERVICES)

    services = list(BOOKING_SERVICES)
    try:
        custom = asyncio.run(db.get_custom_booking_services()) or []
        # psycopg2 -> dict already
        services.extend([dict(x) for x in custom])
    except Exception:
        pass

    # гарантируем уникальность по id
    seen = set()
    uniq: list[dict] = []
    for s in services:
        try:
            sid = int(s.get("id"))
        except Exception:
            continue
        if sid in seen:
            continue
        seen.add(sid)
        uniq.append(s)

    _SERVICES_CACHE["ts"] = now
    _SERVICES_CACHE["services"] = uniq
    return uniq


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
                    if pet.get("birth_date"):
                        pet['birth_date'] = datetime.fromtimestamp(float(pet["birth_date"])).strftime('%Y-%m-%d')
                    else:
                        pet['birth_date'] = ""
                logger.info(f"Найдено питомцев: {len(pets)}")
            else:
                pets = []
                logger.info("Питомцы не найдены")

            birth_date = ""
            if user_profile.get("birth_date"):
                birth_date = datetime.fromtimestamp(float(user_profile["birth_date"])).strftime('%Y-%m-%d')

            data = {
                'full_name': user_profile['full_name'],
                'phone_number': user_profile['phone_number'],
                'birth_date': birth_date,
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
        services=_get_all_services(),
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


# --- Admin panel ---


@app.route("/admin", methods=["GET"])
def admin_panel_page():
    return render_template("admin_panel.html", profile=BOOKING_PROFILE)


@app.route("/api/admin/me", methods=["POST"])
def api_admin_me():
    payload = request.get_json(silent=True) or {}
    init_data = (payload.get("initData") or "").strip()
    tg_user = _tg_user_from_init_data(init_data) or {}
    uid = tg_user.get("id")
    try:
        uid = int(uid) if uid is not None else None
    except Exception:
        uid = None
    return jsonify({"ok": True, "is_admin": bool(uid and uid in (admins_telegram_id or [])), "user_id": uid})


def _admin_or_403() -> tuple[bool, dict | None]:
    payload = request.get_json(silent=True) or {}
    init_data = (payload.get("initData") or "").strip()
    tg_user = _tg_user_from_init_data(init_data)
    if not tg_user or not tg_user.get("id"):
        return False, None
    try:
        uid = int(tg_user["id"])
    except Exception:
        return False, None
    if uid not in (admins_telegram_id or []):
        return False, None
    return True, tg_user


@app.route("/api/admin/bookings/upcoming", methods=["POST"])
def api_admin_bookings_upcoming():
    ok, _tg_user = _admin_or_403()
    if not ok:
        return jsonify({"ok": False, "error": "forbidden"}), 403

    try:
        bookings = asyncio.run(db.get_upcoming_bookings_all(limit=500)) or []
    except Exception as e:
        logger.error(f"admin bookings failed: {e}")
        bookings = []

    out = []
    for b in bookings:
        b = dict(b)
        user_id = b.get("user_id")
        full_name = ""
        try:
            uid_int = int(user_id) if user_id is not None else 0
        except Exception:
            uid_int = 0

        # Внешняя запись (без пользователя)
        if uid_int == 0:
            full_name = "Внешняя запись"
        else:
            try:
                prof = asyncio.run(db.get_user_profile(user_id=uid_int))
                full_name = (prof or {}).get("full_name") or ""
            except Exception:
                full_name = ""

        services = b.get("services") or []
        primary = ""
        try:
            if isinstance(services, list) and services:
                primary = services[0].get("name") or ""
        except Exception:
            primary = ""

        out.append(
            {
                "id": b.get("id"),
                "user_id": user_id,
                "user_name": full_name,
                "start_ts": b.get("start_ts"),
                "start_label": _format_dt(float(b.get("start_ts") or 0)),
                "total_price": b.get("total_price"),
                "primary_service": primary,
                "services": services,
                "services_summary": ", ".join([
                    (s.get("name") or "Услуга") for s in services if isinstance(s, dict)
                ]),
                "comment": b.get("comment") or "",
            }
        )

    return jsonify({"ok": True, "bookings": out})


@app.route("/api/admin/booking/details", methods=["POST"])
def api_admin_booking_details():
    ok, _ = _admin_or_403()
    if not ok:
        return jsonify({"ok": False, "error": "forbidden"}), 403

    payload = request.get_json(silent=True) or {}
    booking_id = payload.get("booking_id")
    try:
        booking_id = int(booking_id)
    except Exception:
        return jsonify({"ok": False, "error": "booking_id_required"}), 400

    booking = asyncio.run(db.get_booking_by_id(booking_id))
    if not booking:
        return jsonify({"ok": False, "error": "not_found"}), 404

    booking = dict(booking)
    user_profile = None
    try:
        uid = int(booking.get("user_id") or 0)
    except Exception:
        uid = 0
    if uid != 0:
        try:
            user_profile = asyncio.run(db.get_user_profile(user_id=uid))
        except Exception:
            user_profile = None

    services_catalog = _get_all_services()
    selected_ids = []
    try:
        for s in (booking.get("services") or []):
            sid = s.get("id")
            if sid is not None:
                selected_ids.append(int(sid))
    except Exception:
        selected_ids = []

    # start date/time for edit form (Moscow TZ)
    from telegram_bot.env import local_timezone
    try:
        _dt = datetime.fromtimestamp(float(booking.get("start_ts") or 0), local_timezone)
        start_date = _dt.strftime("%Y-%m-%d")
        start_time = _dt.strftime("%H:%M")
    except Exception:
        start_date = ""
        start_time = ""

    return jsonify(
        {
            "ok": True,
            "booking": booking,
            "user": user_profile,
            "is_external": bool(uid == 0),
            "services_catalog": services_catalog,
            "selected_service_ids": selected_ids,
            "start_label": _format_dt(float(booking.get("start_ts") or 0)),
            "end_label": _format_dt(float(booking.get("end_ts") or 0)),
            "start_date": start_date,
            "start_time": start_time,
        }
    )


@app.route("/api/admin/booking/create_external", methods=["POST"])
def api_admin_booking_create_external():
    """Создать запись, которая добавлена администратором вручную (без пользователя)."""

    ok, _ = _admin_or_403()
    if not ok:
        return jsonify({"ok": False, "error": "forbidden"}), 403

    payload = request.get_json(silent=True) or {}
    date_str = (payload.get("date") or "").strip()
    time_str = (payload.get("time") or "").strip()
    comment = (payload.get("comment") or "").strip()

    if not date_str or not time_str:
        return jsonify({"ok": False, "error": "date_time_required"}), 400
    if not _is_date_in_booking_window(date_str):
        return jsonify({"ok": False, "error": "outside_booking_window"}), 400
    if time_str not in set(_default_slot_hhmm()):
        return jsonify({"ok": False, "error": "invalid_time"}), 400

    # parse start in local TZ
    from telegram_bot.env import local_timezone
    try:
        dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M").replace(tzinfo=local_timezone)
        start_ts = dt.timestamp()
    except Exception:
        return jsonify({"ok": False, "error": "invalid_datetime"}), 400

    end_ts = start_ts + int(EXTERNAL_BOOKING_DURATION_MIN) * 60

    # keep within working day
    day_start, day_end = _day_bounds(date_str)
    if start_ts < day_start or end_ts > day_end:
        return jsonify({"ok": False, "error": "outside_work_hours"}), 400

    # conflict check
    conflicts = asyncio.run(db.get_bookings_in_range(start_ts, end_ts)) or []
    if conflicts:
        return jsonify({"ok": False, "error": "slot_busy"}), 409

    services = [
        {
            "id": -1,
            "name": "Внешняя запись",
            "duration_min": int(EXTERNAL_BOOKING_DURATION_MIN),
            "price": 0,
        }
    ]

    created = asyncio.run(
        db.add_booking(
            user_id=0,
            start_ts=start_ts,
            end_ts=end_ts,
            services=services,
            total_price=0,
            specialist=str(BOOKING_PROFILE.get("specialist") or ""),
            comment=comment,
            promo_code=None,
        )
    )

    if not created:
        return jsonify({"ok": False, "error": "create_failed"}), 500
    return jsonify({"ok": True, "booking": created})


@app.route("/api/admin/booking/cancel", methods=["POST"])
def api_admin_booking_cancel():
    ok, _ = _admin_or_403()
    if not ok:
        return jsonify({"ok": False, "error": "forbidden"}), 403

    payload = request.get_json(silent=True) or {}
    booking_id = payload.get("booking_id")
    reason = (payload.get("reason") or "").strip()
    if not reason:
        return jsonify({"ok": False, "error": "reason_required"}), 400
    try:
        booking_id = int(booking_id)
    except Exception:
        return jsonify({"ok": False, "error": "booking_id_required"}), 400

    booking = asyncio.run(db.get_booking_by_id(booking_id))
    if not booking:
        return jsonify({"ok": False, "error": "not_found"}), 404

    cancelled = asyncio.run(db.cancel_booking_admin(booking_id))
    if not cancelled:
        return jsonify({"ok": False, "error": "update_failed"}), 500

    cancelled = dict(cancelled)
    user_id = cancelled.get("user_id")
    dt_label = _format_dt(float(cancelled.get("start_ts") or 0))

    services = cancelled.get("services") or []
    if isinstance(services, str):
        try:
            services = json.loads(services)
        except Exception:
            services = []
    services = services if isinstance(services, list) else []
    services_lines = "\n".join([f"• {(s.get('name') or 'Услуга')}" for s in services if isinstance(s, dict)]) or "—"

    msg = (
        "❌ <b>Запись отменена</b>\n\n"
        f"👩‍⚕️ <b>Специалист:</b> {BOOKING_PROFILE.get('specialist')}\n"
        f"🕒 <b>Дата/время:</b> {dt_label}\n"
        f"🧾 <b>Услуги:</b>\n{services_lines}\n\n"
        f"<b>Причина:</b> {reason}\n\n"
        "Приносим извинения за доставленные неудобства 🙏"
    )
    # У внешних записей user_id == 0 — уведомлять некого
    try:
        if user_id is not None and int(user_id) != 0:
            _send_bot_message(int(user_id), msg)
    except Exception:
        pass

    return jsonify({"ok": True, "booking": cancelled})


@app.route("/api/admin/booking/update", methods=["POST"])
def api_admin_booking_update():
    ok, _ = _admin_or_403()
    if not ok:
        return jsonify({"ok": False, "error": "forbidden"}), 403

    payload = request.get_json(silent=True) or {}
    booking_id = payload.get("booking_id")
    date_str = (payload.get("date") or "").strip()
    time_str = (payload.get("time") or "").strip()
    service_ids = payload.get("service_ids") or []

    try:
        booking_id = int(booking_id)
    except Exception:
        return jsonify({"ok": False, "error": "booking_id_required"}), 400

    if not date_str:
        return jsonify({"ok": False, "error": "date_required"}), 400
    hhmm = _parse_time_hhmm(time_str)
    if not hhmm:
        return jsonify({"ok": False, "error": "time_required"}), 400

    try:
        service_ids = [int(x) for x in service_ids]
    except Exception:
        service_ids = []

    chosen, total_price, total_minutes = _sum_services(service_ids)
    if not chosen:
        return jsonify({"ok": False, "error": "services_required"}), 400

    # Build start/end in Moscow TZ to keep consistency
    from telegram_bot.env import local_timezone

    hh, mm = hhmm
    try:
        base = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=local_timezone)
    except Exception:
        return jsonify({"ok": False, "error": "date_invalid"}), 400

    start_ts = base.replace(hour=hh, minute=mm, second=0, microsecond=0).timestamp()
    end_ts = start_ts + max(15, int(total_minutes)) * 60

    work_start, work_end = _work_bounds(date_str)
    if start_ts < work_start or end_ts > work_end:
        return jsonify({"ok": False, "error": "outside_work_hours"}), 400

    # Валидация по расписанию (строго): админ не может поставить время,
    # которое не выбрано в доступности услуги(услуг) на эту дату.
    allowed = set(_allowed_start_ts_for_services(date_str, service_ids))
    if int(start_ts) not in allowed:
        return jsonify({"ok": False, "error": "slot_not_allowed"}), 409

    old = asyncio.run(db.get_booking_by_id(booking_id))
    if not old:
        return jsonify({"ok": False, "error": "not_found"}), 404

    # Conflict check (exclude current booking)
    conflicts = asyncio.run(db.get_bookings_in_range(start_ts, end_ts)) or []
    for c in conflicts:
        try:
            if int(c.get("id")) == int(booking_id):
                continue
        except Exception:
            pass
        return jsonify({"ok": False, "error": "slot_busy"}), 409

    updated = asyncio.run(
        db.reschedule_booking_admin(
            booking_id=booking_id,
            start_ts=start_ts,
            end_ts=end_ts,
            services=chosen,
            total_price=total_price,
        )
    )
    if not updated:
        return jsonify({"ok": False, "error": "update_failed"}), 500

    updated = dict(updated)

    # Notify user
    try:
        user_id = int(updated.get("user_id") or 0)
        # У внешних записей user_id == 0 — уведомлять некого
        if user_id == 0:
            raise RuntimeError("external_booking")
        old_dt = _format_dt(float(old.get("start_ts") or 0))
        new_dt = _format_dt(float(updated.get("start_ts") or 0))
        services_text = ", ".join([s.get("name") or "Услуга" for s in (updated.get("services") or [])])
        msg = (
            "🔔 Ваша запись обновлена\n"
            f"Было: <b>{old_dt}</b>\n"
            f"Стало: <b>{new_dt}</b>\n"
            f"Услуги: {services_text}\n\n"
            "Извините за неудобства, если они возникли 🙏"
        )
        _send_bot_message(user_id, msg)
    except Exception:
        pass

    return jsonify({"ok": True, "booking": updated})


@app.route("/api/admin/services/add", methods=["POST"])
def api_admin_services_add():
    ok, _ = _admin_or_403()
    if not ok:
        return jsonify({"ok": False, "error": "forbidden"}), 403

    payload = request.get_json(silent=True) or {}
    name = (payload.get("name") or "").strip()
    description = (payload.get("description") or "").strip()
    duration_min = payload.get("duration_min")
    price = payload.get("price")

    if not name:
        return jsonify({"ok": False, "error": "name_required"}), 400
    try:
        duration_min = int(duration_min)
        price = int(price)
    except Exception:
        return jsonify({"ok": False, "error": "invalid_numbers"}), 400
    if duration_min < 15:
        return jsonify({"ok": False, "error": "duration_too_small"}), 400
    if price < 0:
        return jsonify({"ok": False, "error": "price_invalid"}), 400

    base_max = 0
    try:
        base_max = max(int(s.get("id")) for s in BOOKING_SERVICES)
    except Exception:
        base_max = 0
    custom_max = 0
    try:
        custom_max = asyncio.run(db.get_custom_services_max_id())
    except Exception:
        custom_max = 0

    new_id = max(base_max, custom_max) + 1
    created = asyncio.run(
        db.add_custom_booking_service(
            service_id=new_id,
            name=name,
            duration_min=duration_min,
            price=price,
            description=description,
        )
    )
    if not created:
        return jsonify({"ok": False, "error": "create_failed"}), 500

    # refresh cache
    _get_all_services(force=True)
    return jsonify({"ok": True, "service": dict(created)})


@app.route("/api/admin/availability/get", methods=["POST"])
def api_admin_availability_get():
    ok, _ = _admin_or_403()
    if not ok:
        return jsonify({"ok": False, "error": "forbidden"}), 403

    payload = request.get_json(silent=True) or {}
    try:
        service_id = int(payload.get("service_id"))
    except Exception:
        return jsonify({"ok": False, "error": "service_id_required"}), 400
    date_str = (payload.get("date") or "").strip()
    if not date_str:
        return jsonify({"ok": False, "error": "date_required"}), 400
    if not _is_date_in_booking_window(date_str):
        return jsonify({"ok": False, "error": "date_out_of_range"}), 400

    row = None
    try:
        row = asyncio.run(db.get_service_availability(service_id=service_id, date=date_str))
    except Exception as e:
        logger.error(f"availability get failed: {e}")

    slots: list[str] = []
    is_default = False
    if row is None:
        # дефолт: полностью свободный день
        slots = _default_slot_hhmm()
        is_default = True
    else:
        s = row.get("slots")
        if isinstance(s, str):
            try:
                s = json.loads(s)
            except Exception:
                s = []
        if isinstance(s, list):
            slots = [f"{hh:02d}:{mm:02d}" for (hh, mm) in filter(None, (_parse_time_hhmm(str(x)) for x in s))]

    return jsonify({"ok": True, "service_id": service_id, "date": date_str, "slots": sorted(set(slots)), "is_default": is_default})


@app.route("/api/admin/availability/dates", methods=["POST"])
def api_admin_availability_dates():
    ok, _ = _admin_or_403()
    if not ok:
        return jsonify({"ok": False, "error": "forbidden"}), 403

    payload = request.get_json(silent=True) or {}
    try:
        service_id = int(payload.get("service_id"))
    except Exception:
        return jsonify({"ok": False, "error": "service_id_required"}), 400

    try:
        dates = asyncio.run(db.list_availability_dates(service_id=service_id)) or []
    except Exception as e:
        logger.error(f"availability dates failed: {e}")
        dates = []

    # Возвращаем только даты в ближайшем окне, чтобы не перегружать UI
    try:
        from telegram_bot.env import local_timezone
        base = datetime.now(local_timezone).date()
    except Exception:
        base = datetime.now().date()
    min_d = base.strftime('%Y-%m-%d')
    max_d = (base + timedelta(days=int(BOOKING_HORIZON_DAYS))).strftime('%Y-%m-%d')
    cleaned = sorted([str(d) for d in dates if isinstance(d, str) and min_d <= str(d) <= max_d])
    return jsonify({"ok": True, "service_id": service_id, "dates": cleaned})


@app.route("/api/admin/availability/set", methods=["POST"])
def api_admin_availability_set():
    ok, _ = _admin_or_403()
    if not ok:
        return jsonify({"ok": False, "error": "forbidden"}), 403

    payload = request.get_json(silent=True) or {}
    try:
        service_id = int(payload.get("service_id"))
    except Exception:
        return jsonify({"ok": False, "error": "service_id_required"}), 400
    date_str = (payload.get("date") or "").strip()
    if not date_str:
        return jsonify({"ok": False, "error": "date_required"}), 400
    if not _is_date_in_booking_window(date_str):
        return jsonify({"ok": False, "error": "date_out_of_range"}), 400
    if not _is_date_in_booking_window(date_str):
        return jsonify({"ok": False, "error": "date_out_of_range"}), 400

    slots_in = payload.get("slots")
    if not isinstance(slots_in, list):
        slots_in = []

    slots: list[str] = []
    for x in slots_in:
        t = _parse_time_hhmm(str(x))
        if not t:
            continue
        hh, mm = t
        # фиксируем шаг записи: 30 минут
        if int(mm) % int(BOOKING_STEP_MIN) != 0:
            continue
        slots.append(f"{hh:02d}:{mm:02d}")
    slots = sorted(set(slots))

    # Пустой список = админ закрыл день по этой услуге
    if not slots:
        try:
            row = asyncio.run(db.upsert_service_availability(service_id=service_id, date=date_str, slots=[]))
        except Exception as e:
            logger.error(f"availability set (close day) failed: {e}")
            return jsonify({"ok": False, "error": "server_error"}), 500
        return jsonify({"ok": True, "availability": dict(row) if row else None, "slots": []})

    try:
        row = asyncio.run(db.upsert_service_availability(service_id=service_id, date=date_str, slots=slots))
    except Exception as e:
        logger.error(f"availability set failed: {e}")
        return jsonify({"ok": False, "error": "server_error"}), 500

    return jsonify({"ok": True, "availability": dict(row) if row else None, "slots": slots})


@app.route("/api/admin/availability/delete", methods=["POST"])
def api_admin_availability_delete():
    ok, _ = _admin_or_403()
    if not ok:
        return jsonify({"ok": False, "error": "forbidden"}), 403

    payload = request.get_json(silent=True) or {}
    try:
        service_id = int(payload.get("service_id"))
    except Exception:
        return jsonify({"ok": False, "error": "service_id_required"}), 400
    date_str = (payload.get("date") or "").strip()
    if not date_str:
        return jsonify({"ok": False, "error": "date_required"}), 400
    if not _is_date_in_booking_window(date_str):
        return jsonify({"ok": False, "error": "date_out_of_range"}), 400
    if not _is_date_in_booking_window(date_str):
        return jsonify({"ok": False, "error": "date_out_of_range"}), 400
    if not _is_date_in_booking_window(date_str):
        return jsonify({"ok": False, "error": "date_out_of_range"}), 400

    # «Удалить дату» = закрыть день (слоты = [])
    try:
        asyncio.run(db.upsert_service_availability(service_id=service_id, date=date_str, slots=[]))
    except Exception as e:
        logger.error(f"availability delete (close day) failed: {e}")
        return jsonify({"ok": False, "error": "server_error"}), 500

    return jsonify({"ok": True, "date": date_str, "service_id": service_id})


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
    return jsonify({"ok": True, "services": _get_all_services()})


@app.route("/api/booking/available_dates", methods=["GET"])
def api_booking_available_dates():
    """Available dates for selected services (rolling window).

    По умолчанию каждый день в ближайший месяц доступен целиком (10:00–21:00, шаг 30 минут).
    Если админ настроил конкретный день — применяем его расписание.
    Если админ закрыл день (слоты = []) — день недоступен.
    """

    service_ids_raw = (request.args.get("service_ids") or "").strip()
    try:
        service_ids = [int(x) for x in service_ids_raw.split(",") if x.strip().isdigit()]
    except Exception:
        service_ids = []

    chosen, _, _ = _sum_services(service_ids)
    if not chosen:
        return jsonify({"ok": False, "error": "services_required"}), 400

    try:
        from telegram_bot.env import local_timezone

        base = datetime.now(local_timezone).date()
    except Exception:
        base = datetime.now().date()

    out: list[str] = []
    for i in range(0, int(BOOKING_HORIZON_DAYS) + 1):
        d = (base + timedelta(days=i)).strftime('%Y-%m-%d')
        if _allowed_hhmm_for_services(d, service_ids):
            out.append(d)

    return jsonify({"ok": True, "dates": out})


@app.route("/api/booking/slots", methods=["GET"])
def api_booking_slots():
    date_str = (request.args.get("date") or "").strip()
    service_ids_raw = (request.args.get("service_ids") or "").strip()

    if not date_str:
        return jsonify({"ok": False, "error": "date_required"}), 400
    if not _is_date_in_booking_window(date_str):
        return jsonify({"ok": False, "error": "date_out_of_range"}), 400

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

    slots = []

    # Пользователи видят только разрешённые старты. Если админ не настраивал дату —
    # используется дефолт (10:00–21:00, шаг 30 минут). Если день закрыт — слотов нет.
    candidates = _allowed_start_ts_for_services(date_str, service_ids)

    end_limit = int(work_end - duration_sec)
    for s in sorted(set(int(x) for x in candidates)):
        if s < now_ts:
            continue
        if s < int(work_start) or s > end_limit:
            continue
        e = s + duration_sec
        is_free = True
        for os, oe in occupied:
            if s < oe and e > os:
                is_free = False
                break
        if not is_free:
            continue
        try:
            # Время в таймзоне специалиста (МСК по умолчанию)
            from telegram_bot.env import local_timezone

            hhmm = datetime.fromtimestamp(float(s), local_timezone).strftime('%H:%M')
        except Exception:
            hhmm = ''

        slots.append({"start_ts": float(s), "label": _format_dt(s), "time": hhmm})

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
        # Готовый лейбл времени в таймзоне сервера/специалиста — чтобы UI везде показывал одинаково
        try:
            if out.get('start_ts') is not None:
                out['start_label'] = _format_dt(float(out['start_ts']))
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

    # Строгое расписание: старт должен быть разрешён админом для всех выбранных услуг.
    allowed = set(_allowed_start_ts_for_services(date_str, [int(x) for x in service_ids if str(x).isdigit()]))
    if int(start_ts) not in allowed:
        return jsonify({"ok": False, "error": "slot_not_allowed"}), 409

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

        admin_ids = admins_telegram_id
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

        admin_ids = admins_telegram_id
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

    # Строгое расписание: перенос возможен только на слоты,
    # которые разрешены админом для всех выбранных услуг.
    allowed = set(_allowed_start_ts_for_services(date_str, [int(x) for x in service_ids if str(x).isdigit()]))
    if int(start_ts) not in allowed:
        return jsonify({"ok": False, "error": "slot_not_allowed"}), 409

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

        admin_ids = admins_telegram_id
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
            phone_number=human["phone_number"]
        ))
        asyncio.run(db.update_user(user_id=user_id, form_value=1))

        # Атомарно заменяем питомцев (в одной транзакции).
        # Это защищает от ситуации, когда delete прошёл, а insert упал — и питомцы пропали.
        pets_payload = []
        for pet in validated_data["pets"]:
            pets_payload.append({
                "name": pet.get("name"),
                "weight": pet.get("weight"),
                "birth_date": str_to_timestamp(pet.get("birth_date")),
                "gender": pet.get("gender"),
                "type": pet.get("type"),
                "breed": pet.get("breed", ""),
                "about_pet": pet.get("about_pet", ""),
            })

        ok = asyncio.run(db.replace_pets(user_id, pets_payload))
        if not ok:
            logger.error("Не удалось сохранить питомцев (replace_pets)")
            return jsonify({"ok": False, "error": "Не удалось сохранить питомцев. Попробуйте ещё раз."})

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
        admin_ids = admins_telegram_id
        logger.info(f"Отправка администраторам: {admin_ids}")
        if not admin_ids:
            return jsonify({"ok": False, "error": "Администраторы не настроены"})

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
