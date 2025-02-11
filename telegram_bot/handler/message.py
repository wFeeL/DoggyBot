import time
from datetime import datetime

from aiogram import F, types, Router
from aiogram.filters import Command
from aiogram.types import Message

from telegram_bot import db, env

router = Router()

@router.message(Command("start"))
async def start(message: Message):
    user = await db.get_users(message.from_user.id, multiple=False)
    
    if user is None:
        await db.add_user(message.from_user.id, message.from_user.username, message.from_user.first_name, message.from_user.last_name)
        answer_text = """👋 Вас приветствует сервис <b>Doggy Logy</b>
        
Мы работаем только с <b>проверенными компаниями</b>, которым <b>доверяем сами</b>. Здесь вы можете приобрести нашу <b>программу лояльности</b>

<i>Скидки действуют на всех наших партнеров, 1 раз в месяц на каждого партнера</i>
        """
    
    else:
        if user["level"] < 0:
            await message.answer("❌ <b>Вы заблокированы, для разблокировки свяжитесь с администрацией</b>", parse_mode="html")
            return
                
        subscription = await db.get_subscriptions(user_id=message.from_user.id)
        if subscription:
            subscription = subscription[-1]
            if subscription["end_date"] < time.time():
                subscription = None
            
        answer_text = f"""👋 Вас приветствует сервис <b>Doggy Logy</b>
        
Мы работаем только с <b>проверенными компаниями</b>, которым <b>доверяем сами</b>. Здесь вы можете приобрести нашу <b>программу лояльности</b>

<i>Скидки действуют на всех наших партнеров, 1 раз в месяц на каждого партнера</i>
{f'\n<b>🔑 Ваш личный промокод:</b> <span class="tg-spoiler">{user["promocode"]}</span>' if subscription else ""}
<b>{"🔋" if subscription else "🪫"} Подписка:</b> {"<code>У вас нет подписки</code>" if not subscription else datetime.fromtimestamp(subscription["end_date"]).strftime('%d %B %H:%M')}
        """
        
    start_markup = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="👤 Профиль", callback_data="profile"),
        types.InlineKeyboardButton(text="🔋 Подписка", callback_data="subscription")],
        [types.InlineKeyboardButton(text="🛍 Категории", callback_data="categories")],
        [types.InlineKeyboardButton(text="❔ О сервисе", callback_data="about")]
    ])
    
    await message.answer(answer_text, parse_mode="html", reply_markup=start_markup)

@router.message(Command("usepromo"))
async def use_promo_handler(message: Message):
    promocode = message.text.split(" ")[1]
    
    user = await db.get_users(message.from_user.id)
    if user["level"] < 0:
        return

    if user["level"] > 1:
        partners = await db.get_partners()
    else:
        partners = await db.get_partners(owner_id=message.from_user.id)
    
    if not partners:
        await message.answer(f"❌ <b>Вам недоступна эта функция.</b>", parse_mode="html")
        return

    if promocode.startswith("DL") and len(promocode) == 8:
        partner_ids = [partner["partner_id"] for partner in partners]
        
        promo_user = await db.get_users(promocode=promocode)
        
        if promo_user:
            redeemed = await db.get_redeemed_promo(promocode)
            redeemed_partners = [promo["partner_id"] for promo in redeemed if promo["partner_id"] in partner_ids]

            redeem_promo_keyboard = [
                [types.InlineKeyboardButton(text=f"{"❌" if partner["partner_id"] in redeemed_partners else "✅"} {partner["partner_name"]}", callback_data=f"redeem_promocode:{partner["partner_id"]}:{promocode}" if partner["partner_id"] not in redeemed_partners else "already_redeemed")] for partner in partners
            ]
            redeem_promo_keyboard.append([types.InlineKeyboardButton(text="🔙 Меню", callback_data="menu")])
            redeem_promo_markup = types.InlineKeyboardMarkup(inline_keyboard=redeem_promo_keyboard)

            await message.answer(f"📇 <b>Списать промокод:</b>", parse_mode="html", reply_markup=redeem_promo_markup)
        
        else:
            await message.answer(f"⚠ <b>Этот промокод неверный.</b>", parse_mode="html")
    else:
        await message.answer(f"⚠ <b>Введён промокод неверного формата.</b>", parse_mode="html")

@router.message(Command(commands=["admin", "ap", "panel"]))
async def admin_panel_handler(message: Message):
    user = await db.get_users(message.from_user.id)
    if user["level"] > 2:
        return
    
    await admin_panel(message, user, False)
    
async def admin_panel(message: Message, user: dict, edit: bool = True):
    if user["level"] > 2:
        return

    admin_panel_keyboard = [
        [types.InlineKeyboardButton(text="📊 Статистика", callback_data="admin:stats"),
        types.InlineKeyboardButton(text="📈 Партнёры", callback_data="admin:partners:1")],
        [types.InlineKeyboardButton(text="👥 Пользователи", callback_data="admin:users:1")],
        [types.InlineKeyboardButton(text="➕ Добавить партнёра", callback_data="admin:add_partner")],
        [types.InlineKeyboardButton(text="🔙 Меню", callback_data="menu")]
    ]

    admin_panel_markup = types.InlineKeyboardMarkup(inline_keyboard=admin_panel_keyboard)

    if edit:
        try:
            await message.edit_text(text=f"""🛡 <b>Админ-панель:</b>""", parse_mode="html", reply_markup=admin_panel_markup)
        except:
            await message.delete()
        else:
            return
        
    await message.answer(text=f"""🛡 <b>Админ-панель:</b>""", parse_mode="html", reply_markup=admin_panel_markup)

@router.message(F.content_type == types.ContentType.WEB_APP_DATA)
async def webapp_catch(message: Message):
    profile = await db.get_user_profile(message.from_user.id)
    if profile["full_name"] is None:
        valid_data = await db.validate_user_form_data(message.web_app_data.data, message.from_user.id)
    else:
        return
    
    profile_markup = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="🔋 Подписка", callback_data="subscription")],
        [types.InlineKeyboardButton(text="👤 Профиль", callback_data="profile")],
        [types.InlineKeyboardButton(text="🔙 Меню", callback_data="menu")],
    ])

    if valid_data:
        await db.update_user_profile(message.from_user.id, full_name=valid_data["human"]["full_name"], birth_date=datetime.strptime(valid_data["human"]["birth_date"], "%Y-%m-%d").timestamp(), phone_number=valid_data["human"]["phone_number"], about_me=valid_data["human"]["about_me"])
        for pet in valid_data["pets"]:
            await db.add_pet(message.from_user.id, pet["weight"], pet["name"], datetime.strptime(pet["birth_date"], "%Y-%m-%d").timestamp(), pet["gender"], pet["type"], pet["breed"])
        await env.bot.send_message(message.chat.id, f"✅ <b>Ваш профиль успешно заполнен.</b>", parse_mode="html", reply_markup=profile_markup)
    else:
        await message.answer("❌ <b>Предоставлены недействительные данные.</b>", parse_mode="html")
