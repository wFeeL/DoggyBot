import asyncio
import html
import time
from typing import List

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InputMediaPhoto, Message
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter

from telegram_bot import db, text_message
from telegram_bot.env import bot
from telegram_bot.keyboards import inline_markup


class Broadcast(StatesGroup):
    text = State()
    photos = State()
    confirm = State()


router = Router()


# Soft global rate limit for mass-send to avoid flood limits.
# Telegram API limits vary; this is a safe default for a small/medium bot.
BROADCAST_RPS = 20  # ~20 send actions per second
BROADCAST_DELAY = 1.0 / BROADCAST_RPS


async def _remember_msg(state: FSMContext, msg: Message | None) -> None:
    """Remember message ids to cleanup the admin chat after confirm/cancel.

    We store both admin messages (text/photos) and bot messages (prompts/preview).
    Deleting is best-effort: Telegram can refuse some deletes; we ignore errors.
    """

    if msg is None:
        return
    try:
        message_id = int(msg.message_id)
    except Exception:
        return

    data = await state.get_data()
    trail = list(data.get("trail_msg_ids") or [])
    if message_id not in trail:
        trail.append(message_id)
        await state.update_data(trail_msg_ids=trail)


async def _remember_many(state: FSMContext, msgs: list[Message] | None) -> None:
    if not msgs:
        return
    for m in msgs:
        await _remember_msg(state, m)


async def _cleanup_trail(chat_id: int, state: FSMContext) -> None:
    """Delete remembered messages in reverse order."""
    try:
        data = await state.get_data()
        trail = list(data.get("trail_msg_ids") or [])
    except Exception:
        trail = []

    # Reverse order: newest first.
    for mid in reversed(trail):
        try:
            await bot.delete_message(chat_id=chat_id, message_id=int(mid))
        except Exception:
            pass

    try:
        await state.update_data(trail_msg_ids=[])
    except Exception:
        pass


def _format_broadcast_text(raw_text: str) -> str:
    # Allow plain text safely. If admin wants HTML, they can type it,
    # but to avoid broken markup during mass-send we escape.
    safe = html.escape(raw_text).strip()
    return f"📣 <b>Сообщение от администратора</b>\n\n{safe}"


async def start_broadcast(message: Message, state: FSMContext) -> None:
    await state.clear()
    m = await message.answer(text_message.BROADCAST_START, reply_markup=inline_markup.get_broadcast_cancel_keyboard())
    await _remember_msg(state, m)
    await state.set_state(Broadcast.text)


@router.callback_query(F.data == "broadcast:cancel")
async def broadcast_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    # Delete the current inline-keyboard message + everything remembered before it.
    try:
        await _remember_msg(state, callback.message)
    except Exception:
        pass
    try:
        await _cleanup_trail(chat_id=int(callback.from_user.id), state=state)
    except Exception:
        pass
    await state.clear()
    await callback.message.answer(text_message.BROADCAST_CANCELLED, reply_markup=inline_markup.get_back_admin_menu_keyboard())


@router.message(Broadcast.text)
async def broadcast_text(message: Message, state: FSMContext) -> None:
    if not message.text:
        m = await message.answer(text_message.BROADCAST_NEED_TEXT, reply_markup=inline_markup.get_broadcast_cancel_keyboard())
        await _remember_msg(state, m)
        return

    # Remember admin text message too.
    await _remember_msg(state, message)
    await state.update_data(text=message.text, photos=[])
    m = await message.answer(text_message.BROADCAST_ADD_PHOTOS, reply_markup=inline_markup.get_broadcast_photos_keyboard())
    await _remember_msg(state, m)
    await state.set_state(Broadcast.photos)


@router.message(Broadcast.photos, F.photo)
async def broadcast_add_photo(message: Message, state: FSMContext) -> None:
    # Remember admin photo message
    await _remember_msg(state, message)
    data = await state.get_data()
    photos: List[str] = list(data.get("photos") or [])
    if len(photos) >= 10:
        m = await message.answer(
            "ℹ️ Можно прикрепить не более <b>10</b> фото.",
            reply_markup=inline_markup.get_broadcast_photos_keyboard(),
        )
        await _remember_msg(state, m)
        return
    file_id = message.photo[-1].file_id
    photos.append(file_id)
    await state.update_data(photos=photos)
    m = await message.answer(
        f"✅ Добавлено фото: <code>{len(photos)}</code>",
        reply_markup=inline_markup.get_broadcast_photos_keyboard(),
    )
    await _remember_msg(state, m)


@router.message(Broadcast.photos)
async def broadcast_photos_other(message: Message, state: FSMContext) -> None:
    # Любые другие сообщения (текст/стикер/видео...) — подсказываем, что делать дальше
    # Сохраняем подсказку в trail, чтобы после отмены/отправки очистить чат.
    m = await message.answer(
        "Отправьте фото или нажмите <b>Далее</b>/<b>Пропустить</b>.",
        reply_markup=inline_markup.get_broadcast_photos_keyboard(),
    )
    await _remember_msg(state, m)


@router.callback_query(Broadcast.photos, F.data.in_({"broadcast:skip_photos", "broadcast:photos_done"}))
async def broadcast_photos_done(callback: CallbackQuery, state: FSMContext) -> None:
    # Remember the "Далее/Пропустить" message too
    try:
        await _remember_msg(state, callback.message)
    except Exception:
        pass

    data = await state.get_data()
    raw_text = str(data.get("text") or "").strip()
    photos: List[str] = list(data.get("photos") or [])[:10]

    if callback.data == "broadcast:skip_photos":
        photos = []
        await state.update_data(photos=[])

    formatted = _format_broadcast_text(raw_text)

    # Preview
    title_msg = await callback.message.answer(text_message.BROADCAST_PREVIEW_TITLE)
    await _remember_msg(state, title_msg)

    if photos:
        # Caption limit is 1024; if longer — send text separately.
        if len(formatted) > 900:
            m = await callback.message.answer(formatted)
            await _remember_msg(state, m)
            media = [InputMediaPhoto(media=pid) for pid in photos]
        else:
            media = [InputMediaPhoto(media=photos[0], caption=formatted)]
            media.extend(InputMediaPhoto(media=pid) for pid in photos[1:])
        try:
            sent = await bot.send_media_group(chat_id=callback.from_user.id, media=media)
            await _remember_many(state, sent)
        except TelegramBadRequest:
            # fallback: send as separate photos
            m = await callback.message.answer(formatted)
            await _remember_msg(state, m)
            for pid in photos:
                try:
                    pm = await bot.send_photo(chat_id=callback.from_user.id, photo=pid)
                    await _remember_msg(state, pm)
                except Exception:
                    continue
    else:
        m = await callback.message.answer(formatted)
        await _remember_msg(state, m)

    confirm_msg = await callback.message.answer(
        "✅ <b>Подтвердите отправку</b>",
        reply_markup=inline_markup.get_broadcast_confirm_keyboard(),
    )
    await _remember_msg(state, confirm_msg)
    await state.set_state(Broadcast.confirm)


@router.callback_query(Broadcast.confirm, F.data == "broadcast:send")
async def broadcast_send(callback: CallbackQuery, state: FSMContext) -> None:
    # Ensure confirm message is in cleanup trail.
    try:
        await _remember_msg(state, callback.message)
    except Exception:
        pass

    data = await state.get_data()
    raw_text = str(data.get("text") or "").strip()
    photos: List[str] = list(data.get("photos") or [])[:10]
    formatted = _format_broadcast_text(raw_text)

    users = await db.get_users(is_multiple=True)
    # отправляем всем, включая админов, но пропускаем заблокированных в БД
    user_ids = [int(u["user_id"]) for u in users if int(u.get("level", 0)) >= 0]

    ok = 0
    fail = 0

    # Soft rate limiting (token bucket-ish): keep a target delay between send actions.
    next_allowed = time.monotonic()

    async def _soft_wait() -> None:
        nonlocal next_allowed
        now = time.monotonic()
        if now < next_allowed:
            await asyncio.sleep(next_allowed - now)
        # schedule next slot
        next_allowed = max(next_allowed, time.monotonic()) + BROADCAST_DELAY

    async def _send_to(uid: int) -> None:
        nonlocal ok, fail, next_allowed
        try:
            if photos:
                if len(formatted) > 900:
                    await bot.send_message(chat_id=uid, text=formatted)
                    media = [InputMediaPhoto(media=pid) for pid in photos]
                else:
                    media = [InputMediaPhoto(media=photos[0], caption=formatted)]
                    media.extend(InputMediaPhoto(media=pid) for pid in photos[1:])
                await bot.send_media_group(chat_id=uid, media=media)
            else:
                await bot.send_message(chat_id=uid, text=formatted)
            ok += 1
        except TelegramRetryAfter as e:
            # If Telegram asks to slow down, wait and retry once.
            try:
                wait_s = float(getattr(e, "retry_after", 1.0))
            except Exception:
                wait_s = 1.0
            await asyncio.sleep(wait_s + 0.5)
            # Also shift the limiter window forward.
            next_allowed = max(next_allowed, time.monotonic() + wait_s + 0.5)
            try:
                if photos:
                    if len(formatted) > 900:
                        await bot.send_message(chat_id=uid, text=formatted)
                        media = [InputMediaPhoto(media=pid) for pid in photos]
                    else:
                        media = [InputMediaPhoto(media=photos[0], caption=formatted)]
                        media.extend(InputMediaPhoto(media=pid) for pid in photos[1:])
                    await bot.send_media_group(chat_id=uid, media=media)
                else:
                    await bot.send_message(chat_id=uid, text=formatted)
                ok += 1
            except (TelegramForbiddenError, TelegramBadRequest, TelegramRetryAfter, Exception):
                fail += 1
        except (TelegramForbiddenError, TelegramBadRequest):
            fail += 1
        except Exception:
            fail += 1

    # Running sequentially (safer for flood limits). Do not stop on errors.
    for uid in user_ids:
        await _soft_wait()
        await _send_to(uid)

    # Cleanup preview + all steps before it (best-effort), then show result.
    try:
        await _cleanup_trail(chat_id=int(callback.from_user.id), state=state)
    except Exception:
        pass

    await state.clear()
    await callback.message.answer(
        text_message.BROADCAST_SENT_RESULT.format(ok=ok, fail=fail),
        reply_markup=inline_markup.get_back_admin_menu_keyboard(),
    )
