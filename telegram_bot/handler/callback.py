import pathlib
import time
from datetime import datetime

from aiogram import types, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from telegram_bot import db
from telegram_bot.env import PartnerForm, bot, oferta_url, webapp_url, support_username
from telegram_bot.handler.message import admin_panel

router = Router()

@router.callback_query()
async def callback_handler(c: CallbackQuery, state: FSMContext):
    message = c.message
    user = await db.get_users(user_id=c.from_user.id, multiple=False)
    await state.clear()

    if user:
        if user["level"] < 0:
            return
    else:
        return

    menu_markup = types.InlineKeyboardMarkup(inline_keyboard=[[
        types.InlineKeyboardButton(text="🔙 Назад", callback_data="menu")
    ]])
    categories_markup = types.InlineKeyboardMarkup(inline_keyboard=[[
        types.InlineKeyboardButton(text="🔙 Назад", callback_data="categories")
    ]])

    if c.data == "about":
        await message.edit_text(text="""👋 Вас приветствует сервис <b>Doggy Logy</b>
        
Мы работаем только с <b>проверенными компаниями</b>, которым <b>доверяем сами</b>. Здесь вы можете приобрести нашу <b>программу лояльности</b>

<i>Скидки действуют на всех наших партнеров, 1 раз в месяц на каждого партнера</i>

<i>Создатель бренда Doggy Logy: Валерия Попова @doggy_logy</i>""", parse_mode="html", reply_markup=menu_markup)

    elif c.data == "menu":
        start_markup = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="👤 Профиль", callback_data="profile"),
             types.InlineKeyboardButton(text="🔋 Подписка", callback_data="subscription")],
            [types.InlineKeyboardButton(text="🛍 Категории", callback_data="categories")],
            [types.InlineKeyboardButton(text="❔ О сервисе", callback_data="about")]
        ])

        subscription = await db.get_subscriptions(user_id=c.from_user.id)
        if subscription:
            subscription = subscription[-1]
            if subscription["end_date"] < time.time():
                subscription = None

        await message.edit_text(f"""👋 Вас приветствует сервис <b>Doggy Logy</b>
        
Мы работаем только с <b>проверенными компаниями</b>, которым <b>доверяем сами</b>. Здесь вы можете приобрести нашу <b>программу лояльности</b>

<i>Скидки действуют на всех наших партнеров, 1 раз в месяц на каждого партнера</i>
{f'\n<b>🔑 Ваш личный промокод:</b> <span class="tg-spoiler">{user["promocode"]}</span>' if subscription else ""}
<b>{"🔋" if subscription else "🪫"} Подписка:</b> {"<code>У вас нет подписки</code>" if not subscription else datetime.fromtimestamp(subscription["end_date"]).strftime('%d %B %H:%M')}
        """, reply_markup=start_markup, parse_mode="html")

    elif c.data == "categories":
        categories = await db.get_categories(category_enabled=True)
        choose_category_keyboard = [[types.InlineKeyboardButton(text=f"{category["category_name"]}",
                                                                callback_data=f"category:{category["category_id"]}")]
                                    for category in categories]
        choose_category_keyboard.append([types.InlineKeyboardButton(text="🔙 Назад", callback_data="menu")])
        choose_category_markup = types.InlineKeyboardMarkup(inline_keyboard=choose_category_keyboard)

        if not message.photo:
            await message.edit_text("""🛍 <b>Категории:</b>""", parse_mode="html", reply_markup=choose_category_markup)
        else:
            await message.delete()
            await bot.send_message(c.from_user.id, """🛍 <b>Категории:</b>""", parse_mode="html",
                                   reply_markup=choose_category_markup)

    elif c.data.startswith("category"):
        category_id = c.data.split(":")[1]
        category = await db.get_categories(category_id=int(category_id))
        partners = await db.get_partners(category_id=int(category_id))

        answer_text = f"<b>{category["category_name"]}</b>"
        multiple = []

        for partner in partners:
            text = f"""

<b>{partner["partner_name"]}</b>
{"Ознакомиться с ассортиментом\n" + partner["partner_url"] + "\n" if partner["partner_url"] else ""}<blockquote>{partner["partner_legacy_text"]}</blockquote>"""
            if (len(answer_text + text) >= 842 and len(multiple) == 0) or (
                    len(answer_text + text) >= 3914 and len(multiple) > 0):
                multiple.append(answer_text)
                answer_text = ""

            answer_text += text

        subscription = await db.get_subscriptions(user_id=c.from_user.id)
        if subscription:
            subscription = subscription[-1]
            if subscription["end_date"] < time.time():
                subscription = None

        if subscription:
            answer_text += """
        
<blockquote><b>ПРОМОКОД ДЛЯ ВСЕХ ПАРТНЕРОВ</b> <code>DoggyLogy</code> 
Партнер может потребовать от Вас ваш индивидуальный промокод из вашего личного кабинета!</blockquote>"""

        multiple.append(answer_text)

        answer_text = multiple[0]
        catigories_markup_ = categories_markup if len(multiple) == 1 else None

        if pathlib.Path(f"img/{category_id}.png").is_file():
            await message.edit_media(
                types.InputMediaPhoto(media=types.FSInputFile(f"img/{category_id}.png", "category_image.png"),
                                      caption=answer_text, parse_mode="html"), reply_markup=catigories_markup_)
        else:
            await message.edit_text(text=answer_text, parse_mode="html", reply_markup=catigories_markup_)

        for answer_text in multiple:
            catigories_markup_ = categories_markup if answer_text == multiple[-1] else None

            await message.answer(text=answer_text, parse_mode="html", reply_markup=catigories_markup_)

    elif c.data == "subscription":
        pass
#         subscription = await db.get_subscriptions(user_id=c.from_user.id)
#         if subscription:
#             subscription = subscription[-1]
#             if subscription["end_date"] < time.time():
#                 subscription = None
#
#         if subscription is None:
#             user_profile = await db.get_user_profile(c.from_user.id)
#
#
#             keyboard = []
#             if user_profile["full_name"]:
#                 keyboard.append([types.InlineKeyboardButton(text="💳 Оформить подписку",
#                                                             callback_data=f"create_invoice:{settings["length"]}:{settings["price"]}")])
#             else:
#                 keyboard.append([types.InlineKeyboardButton(text="🪪 Заполнить данные", callback_data="fill_profile")])
#
#             keyboard.append([types.InlineKeyboardButton(text="🔙 Назад", callback_data=f"menu")])
#
#             buy_subscription_markup = types.InlineKeyboardMarkup(inline_keyboard=keyboard)
#             await message.edit_text(f"""🔋 <b>Подписка</b>
#
# ⏲ <b>Срок действия:</b> <code>{int(settings["length"] / 31)} мес.</code>
# 💰 <b>Стоимость подписки:</b> <code>{settings["price"]}р</code>
#
# <i>Оформляя подписку, вы подтверждаете что вы ознакомились и согласны с <a href="{oferta_url}">условиями оферты</a></i>
# {'\n<blockquote>Перед оформлением подписки обязательно заполните данные о себе и своих питомцах, после этого перезайдите во вкладку "Подписка" и под сообщением появится кнопка для оформления подписки.</blockquote>' if not user_profile["full_name"] else ""}
# """, parse_mode="html", reply_markup=buy_subscription_markup, disable_web_page_preview=True)

    elif c.data.startswith("check_invoice"):
        pass
#         _, invoice_id, summ, length = c.data.split(":")
#         status = check_invoice(invoice_id, summ)
#
#         if status != 0:
#             if status == -1:
#                 await c.answer("❌ Оплата отменена")
#
#             if status == 1:
#                 await c.answer("✅ Оплата прошла успешно!")
#                 await db.add_subscription(c.from_user.id, int(summ), int(length))
#
#             start_markup = types.InlineKeyboardMarkup(inline_keyboard=[
#                 [types.InlineKeyboardButton(text="👤 Профиль", callback_data="profile"),
#                  types.InlineKeyboardButton(text="🔋 Подписка", callback_data="subscription")],
#                 [types.InlineKeyboardButton(text="🛍 Категории", callback_data="categories")],
#                 [types.InlineKeyboardButton(text="❔ О сервисе", callback_data="about")]
#             ])
#
#             subscription = await db.get_subscriptions(user_id=c.from_user.id)
#             if subscription:
#                 subscription = subscription[-1]
#                 if subscription["end_date"] < time.time():
#                     subscription = None
#
#             await message.edit_text(f"""👋 Вас приветствует сервис <b>Doggy Logy</b>
#
# Мы работаем только с <b>проверенными компаниями</b>, которым <b>доверяем сами</b>. Здесь вы можете приобрести нашу <b>программу лояльности</b>
#
# <i>Скидки действуют на всех наших партнеров, 1 раз в месяц на каждого партнера</i>
#
# <b>🔑 Ваш личный промокод:</b> <span class="tg-spoiler">{user["promocode"]}</span>
# <b>{"🔋" if subscription else "🪫"} Подписка:</b> {"<code>У вас нет подписки</code>" if not subscription else datetime.fromtimestamp(subscription["end_date"]).strftime('%d %B %H:%M')}
#             """, reply_markup=start_markup, parse_mode="html")
#
#         elif status == 0:
#             await c.answer("⏳ Счёт ожидает оплату")

    elif c.data.startswith("create_invoice"):
        pass
#         _, length, price = c.data.split(":")
#         invoice_url, invoice_id = create_invoice(price, length)
#
#         pay_subscription_markup = types.InlineKeyboardMarkup(inline_keyboard=[
#             [types.InlineKeyboardButton(text="💳 Оплатить", url=invoice_url),
#              types.InlineKeyboardButton(text="🔄 Проверить",
#                                         callback_data=f"check_invoice:{invoice_id}:{price}:{length}")]
#         ])
#         await message.edit_text(f"""💰 <b>Создан счёт на оплату подписки</b>
#
# 🔋 Подписка - <code>{round(int(length) / 31, 1)} мес | {price}р</code>
#
# <blockquote>После оплаты нажмите на кнопку <b>🔄 Проверить</b> чтобы проверить оплату.
#
# <i>Если возникли какие-либо проблемы писать @{support_username}</i></blockquote>""", parse_mode="html",
#                                 reply_markup=pay_subscription_markup)

    elif c.data.startswith("redeem_promocode"):
        _, partner_id, promocode = c.data.split(":")

        partner = await db.get_partners(int(partner_id))
        user_ = await db.get_users(promocode=promocode)

        if user["level"] > 1 or partner["owner_user_id"] == c.from_user.id:
            await db.redeem_promo(user_["user_id"], promocode, partner_id)
            await c.answer("✅ Промокод списан.")
            await message.delete()
            await bot.send_message(user_["user_id"],
                                   f"✅ <b>Ваш промокод списан у партнёра <code>{partner["partner_name"]}</code></b>",
                                   parse_mode="html")

    elif c.data == "already_redeemed":
        await c.answer(f"⚠ Промокод уже списан у этого партнёра.")

    elif c.data == "fill_profile":
        await message.delete()
        await message.answer("👇 <b>Для заполнения формы нажмите на кнопку ниже.</b>",
                             reply_markup=types.ReplyKeyboardMarkup(keyboard=[
                                 [types.KeyboardButton(text="🪪 Заполнить форму",
                                                       web_app=types.WebAppInfo(url=webapp_url))]
                             ], resize_keyboard=True, one_time_keyboard=True), parse_mode="html")

    elif c.data == "profile":
        user_profile = await db.get_user_profile(c.from_user.id)

        menu_form_markup = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="🪪 Заполнить данные", callback_data="fill_profile")],
            [types.InlineKeyboardButton(text="🔙 Меню", callback_data="menu")]
        ])

        if user_profile["full_name"] is None:
            await message.edit_text(f"""👤 <b>Ваш профиль</b>

<i>Вы ещё не указали никаких данных!</i>""", reply_markup=menu_form_markup, parse_mode="html")

        else:
            await message.edit_text(f"""👤 <b>Ваш профиль</b>

🎭 <b>О вас:</b>
<b>Полное имя</b>: <code>{user_profile["full_name"]}</code>
<b>Номер телефона</b>: <code>{user_profile["phone_number"]}</code>
<b>Дата рождения</b>: <code>{datetime.fromtimestamp(user_profile["birth_date"]).strftime('%d %B %Y')}</code>
<b>Возраст</b>: <code>{round((time.time() - user_profile["birth_date"]) // (86400 * 365))} лет</code>

🐶 <b>Ваши питомцы:</b>
{''.join([f'<b>{pet["name"]}</b>: <code>~{pet["approx_weight"]}кг, {round((time.time() - pet["birth_date"]) // (86400 * 365))} лет</code>\n' for pet in user_profile["pets"]])}""",
                                    parse_mode="html", reply_markup=menu_markup)
    if user["level"] < 2:
        return

    elif c.data.startswith("admin"):
        action = c.data.split(":")[1]
        admin_markup = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="🔙 Назад", callback_data="admin:panel"), ]
        ])

        if action == "panel":
            await admin_panel(message, user)
            return

        elif action == "stats":
            partners = await db.get_partners()
            orders_day = await db.get_subscriptions(start_ts=time.time() - 86400) or []
            orders_month = await db.get_subscriptions(start_ts=time.time() - 86400 * 31) or []
            orders_year = await db.get_subscriptions(start_ts=time.time() - 86400 * 365) or []

            users = await db.get_users()

            await message.edit_text(f"""📊 <b>Статистика</b>:
                                    
Количество пользователей: <code>{len(users)}</code>
Количество партнёров: <code>{len(partners)}</code>
Подписок за день: <code>{len(orders_day)} / {sum([order["price"] for order in orders_day])}₽</code>
Подписок за месяц: <code>{len(orders_month)} / {sum([order["price"] for order in orders_month])}₽</code>
Подписок за год: <code>{len(orders_year)} / {sum([order["price"] for order in orders_year])}₽</code>""",
                                    parse_mode="html", reply_markup=admin_markup)

        elif action == "partners":
            page = int(c.data.split(":")[2]) if len(c.data.split(":")) > 2 else 1
            partners = await db.get_partners()
            total_pages = (len(partners) + 14) // 15
            partners = partners[(page - 1) * 15: page * 15]

            partner_buttons = [
                [types.InlineKeyboardButton(text=f"{partner['partner_name']} (ID: {partner['partner_id']})",
                                            callback_data=f"partner:{partner['partner_id']}")]
                for partner in partners
            ]
            navigation_buttons = []
            if page > 1:
                navigation_buttons.append(
                    types.InlineKeyboardButton(text="⬅️ Назад", callback_data=f"admin:partners:{page - 1}"))
            if page < total_pages:
                navigation_buttons.append(
                    types.InlineKeyboardButton(text="Вперёд ➡️", callback_data=f"admin:partners:{page + 1}"))
            partner_buttons.append(navigation_buttons)
            partner_buttons.append([types.InlineKeyboardButton(text="🔙 Назад", callback_data="admin:panel")])
            partner_markup = types.InlineKeyboardMarkup(inline_keyboard=partner_buttons)

            await message.edit_text("📈 <b>Партнёры:</b>", parse_mode="html", reply_markup=partner_markup)

        elif action == "users":
            page = int(c.data.split(":")[2]) if len(c.data.split(":")) > 2 else 1
            users = await db.get_users()
            total_pages = (len(users) + 9) // 10
            users = users[(page - 1) * 10: page * 10]

            user_buttons = [
                [types.InlineKeyboardButton(text=f"{user['full_name']} (ID: {user['user_id']})",
                                            callback_data=f"user:{user['user_id']}")]
                for user in users
            ]
            navigation_buttons = []
            if page > 1:
                navigation_buttons.append(
                    types.InlineKeyboardButton(text="⬅️ Назад", callback_data=f"admin:users:{page - 1}"))
            if page < total_pages:
                navigation_buttons.append(
                    types.InlineKeyboardButton(text="Вперёд ➡️", callback_data=f"admin:users:{page + 1}"))
            user_buttons.append(navigation_buttons)
            user_buttons.append([types.InlineKeyboardButton(text="🔙 Назад", callback_data="admin:panel")])
            user_markup = types.InlineKeyboardMarkup(inline_keyboard=user_buttons)

            await message.edit_text("👥 <b>Пользователи:</b>", parse_mode="html", reply_markup=user_markup)

        elif action == "add_partner":
            await c.message.edit_text("<b>Введите название нового партнёра:</b>", parse_mode="HTML")
            await state.set_state(PartnerForm.awaiting_partner_name_new)

    elif c.data.startswith("user:"):
        user_id = int(c.data.split(":")[1])
        user = await db.get_users(user_id=user_id, multiple=False)
        subscriptions = await db.get_subscriptions(user_id=user_id) or []
        total_spent = sum(sub["price"] for sub in subscriptions)
        subscription_count = len(subscriptions)
        subscription_status = "Активна" if subscriptions and subscriptions[-1][
            "end_date"] > time.time() else "Не активна"
        user_status = user["level"]

        user_info = f"""
👤 <b>{user['full_name']} (ID: {user['user_id']})</b>
<b>Статус:</b> <code>{"Пользователь" if user_status == 0 else "Партнер" if user_status == 1 else "Администратор" if user_status == 2 else "Заблокирован" if user_status == -1 else "Неизвестно"}</code>
<b>Подписка:</b> <code>{subscription_status}</code>
<b>Кол-во покупок подписки:</b> <code>{subscription_count}</code>
<b>На сумму:</b> <code>{total_spent}₽</code>
        """

        user_actions = [
            [types.InlineKeyboardButton(text="🚫 Заблокировать", callback_data=f"user_action:block:{user_id}") if user[
                                                                                                                     "level"] >= 0 else types.InlineKeyboardButton(
                text="⭕ Разблокировать", callback_data=f"user_action:unblock:{user_id}")],
            [types.InlineKeyboardButton(text="🔋 Выдать подписку",
                                        callback_data=f"user_action:give_subscription:{user_id}") if subscription_status == "Не активна" else types.InlineKeyboardButton(
                text="🪫 Забрать подписку", callback_data=f"user_action:remove_subscription:{user_id}")],
            [types.InlineKeyboardButton(text="👤 Сделать пользователем",
                                        callback_data=f"user_action:make_user:{user_id}")],
            [types.InlineKeyboardButton(text="🛍 Сделать партнёром",
                                        callback_data=f"user_action:make_partner:{user_id}")],
            [types.InlineKeyboardButton(text="🛡 Сделать админом", callback_data=f"user_action:make_admin:{user_id}")],
            [types.InlineKeyboardButton(text="🔙 Назад", callback_data="admin:users")]
        ]
        user_markup = types.InlineKeyboardMarkup(inline_keyboard=user_actions)

        await message.edit_text(user_info, parse_mode="html", reply_markup=user_markup)

    elif c.data.startswith("partner:"):
        partner_id = int(c.data.split(":")[1])
        partner = await db.get_partners(partner_id=partner_id)
        owner = await db.get_users(user_id=partner["owner_user_id"], multiple=False)

        partner_info = f"""
📈 <b>{partner['partner_name']} (ID: {partner['partner_id']})</b>
<b>ТГ партнёра:</b> {owner['full_name']} (ID: {owner['user_id']})
<b>Категория:</b> <code>{partner["category"]['category_name']} {partner["category"]['category_name']}</code>
<b>Скрыт:</b> <code>{"Да" if not partner['partner_enabled'] else "Нет"}</code>

{"Ознакомиться с ассортиментом\n" + partner["partner_url"] + "\n" if partner["partner_url"] else ""}<blockquote>{partner["partner_legacy_text"]}</blockquote>
        """

        partner_actions = [
            [types.InlineKeyboardButton(text="🗑 Удалить", callback_data=f"partner_action:delete:{partner_id}")],
            [types.InlineKeyboardButton(text="🆔 Указать ID партнёра",
                                        callback_data=f"partner_action:set_owner:{partner_id}")],
            [types.InlineKeyboardButton(text="👁 Скрыть", callback_data=f"partner_action:hide:{partner_id}") if partner[
                'partner_enabled'] else types.InlineKeyboardButton(text="👁 Показать",
                                                                   callback_data=f"partner_action:show:{partner_id}")],
            [types.InlineKeyboardButton(text="✏ Изменить текст",
                                        callback_data=f"partner_action:edit_text:{partner_id}")],
            [types.InlineKeyboardButton(text="✏ Изменить название",
                                        callback_data=f"partner_action:edit_name:{partner_id}")],
            [types.InlineKeyboardButton(text="✏ Изменить категорию",
                                        callback_data=f"partner_action:edit_category:{partner_id}")],
            [types.InlineKeyboardButton(text="✏ Изменить URL партнёра",
                                        callback_data=f"partner_action:edit_url:{partner_id}")],
            [types.InlineKeyboardButton(text="🔙 Назад", callback_data="admin:partners")]
        ]
        partner_markup = types.InlineKeyboardMarkup(inline_keyboard=partner_actions)

        await message.edit_text(partner_info, parse_mode="html", reply_markup=partner_markup,
                                disable_web_page_preview=True)

    elif c.data.startswith("user_action:"):
        action, user_id = c.data.split(":")[1:]
        user_id = int(user_id)

        if action == "block":
            await db.update_user(user_id, level=-1)
            await c.answer("✅ Пользователь заблокирован.")
        elif action == "unblock":
            await db.update_user(user_id, level=0)
            await c.answer("✅ Пользователь разблокирован.")
        elif action == "give_subscription":
            await db.add_subscription(user_id, price=0, length=30)
            await c.answer("✅ Подписка выдана.")
        elif action == "remove_subscription":
            await db.remove_subscription(user_id)
            await c.answer("✅ Подписка удалена.")
        elif action == "make_user":
            await db.update_user(user_id, level=0)
            await c.answer("✅ Пользователь стал клиентом.")
        elif action == "make_partner":
            await db.update_user(user_id, level=1)
            await c.answer("✅ Пользователь стал партнёром.")
        elif action == "make_admin":
            await db.update_user(user_id, level=2)
            await c.answer("✅ Пользователь стал админом.")
        c_u = c.model_copy(update={"data": f"user:{user_id}"})
        await callback_handler(c_u, state)

    if c.data.startswith("partner_action:"):
        action, partner_id = c.data.split(":")[1:]
        partner_id = int(partner_id)

        control_partner_markup = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="🔙 Назад", callback_data=f"partner:{partner_id}")]
        ])

        if action == "delete":
            await db.delete_partner(partner_id)
            await c.answer("Партнёр удалён.")
            c_u = c.model_copy(update={"data": "admin:partners"})
            await callback_handler(c_u, state)

        elif action == "set_owner":
            await message.edit_text("<b>Введите ID нового владельца партнёра:</b>", parse_mode="HTML",
                                    reply_markup=control_partner_markup)
            await state.update_data(message_to_delete=message)
            await state.update_data(partner_id=partner_id)
            await state.set_state(PartnerForm.awaiting_partner_owner)

        elif action == "edit_text":
            await message.edit_text("<b>Введите новый текст партнёра:</b>", parse_mode="HTML",
                                    reply_markup=control_partner_markup)
            await state.update_data(message_to_delete=message)
            await state.update_data(partner_id=partner_id)
            await state.set_state(PartnerForm.awaiting_partner_text)

        elif action == "edit_name":
            await message.edit_text("<b>Введите новое название партнёра:</b>", parse_mode="HTML",
                                    reply_markup=control_partner_markup)
            await state.update_data(message_to_delete=message)
            await state.update_data(partner_id=partner_id)
            await state.set_state(PartnerForm.awaiting_partner_name)

        elif action == "edit_category":
            categories_text = "\n".join(
                [f"<code>{category['category_id']}</code>: <b>{category['category_name']}</b>" for category in
                 await db.get_categories()])
            await message.edit_text(categories_text + "\n\n<b>Введите новую категорию партнёра:</b>", parse_mode="HTML",
                                    reply_markup=control_partner_markup)
            await state.update_data(message_to_delete=message)
            await state.update_data(partner_id=partner_id)
            await state.set_state(PartnerForm.awaiting_partner_category)

        elif action == "edit_url":
            await message.edit_text("<b>Введите новый URL партнёра:</b>", parse_mode="HTML",
                                    reply_markup=control_partner_markup)
            await state.update_data(message_to_delete=message)
            await state.update_data(partner_id=partner_id)
            await state.set_state(PartnerForm.awaiting_partner_url)

        elif action == "hide":
            await db.update_partner(partner_id, partner_enabled=False)
            await c.answer("✅ Партнёр скрыт.")
            c_u = c.model_copy(update={"data": f"partner:{partner_id}"})
            await callback_handler(c_u, state)

        elif action == "show":
            await db.update_partner(partner_id, partner_enabled=True)
            await c.answer("✅ Партнёр показан.")
            c_u = c.model_copy(update={"data": f"partner:{partner_id}"})
            await callback_handler(c_u, state)

@router.message(PartnerForm.awaiting_partner_owner)
async def set_partner_owner(message: types.Message, state: FSMContext):
    data = await state.get_data()
    partner_id = data["partner_id"]
    new_owner_id = int(message.text)
    await db.update_partner(partner_id, owner_user_id=new_owner_id)
    control_partner_markup = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="🔙 Назад", callback_data=f"partner:{partner_id}")]
    ])
    await data["message_to_delete"].delete()
    await message.answer("✅ <b>ID партнёра указан.</b>", parse_mode="HTML", reply_markup=control_partner_markup)
    await state.clear()

@router.message(PartnerForm.awaiting_partner_text)
async def edit_partner_text(message: types.Message, state: FSMContext):
    data = await state.get_data()
    partner_id = data["partner_id"]
    new_text = message.text
    await db.update_partner(partner_id, partner_legacy_text=new_text)
    control_partner_markup = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="🔙 Назад", callback_data=f"partner:{partner_id}")]
    ])
    await data["message_to_delete"].delete()
    await message.answer("✅ <b>Текст изменён.</b>", parse_mode="HTML", reply_markup=control_partner_markup)
    await state.clear()

@router.message(PartnerForm.awaiting_partner_name)
async def edit_partner_name(message: types.Message, state: FSMContext):
    data = await state.get_data()
    partner_id = data["partner_id"]
    new_name = message.text
    await db.update_partner(partner_id, partner_name=new_name)
    control_partner_markup = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="🔙 Назад", callback_data=f"partner:{partner_id}")]
    ])
    await data["message_to_delete"].delete()
    await message.answer("✅ <b>Название изменено.</b>", parse_mode="HTML", reply_markup=control_partner_markup)
    await state.clear()

@router.message(PartnerForm.awaiting_partner_category)
async def edit_partner_category(message: types.Message, state: FSMContext):
    data = await state.get_data()
    partner_id = data["partner_id"]
    new_category = int(message.text)
    await db.update_partner(partner_id, partner_category=new_category)
    control_partner_markup = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="🔙 Назад", callback_data=f"partner:{partner_id}")]
    ])
    await data["message_to_delete"].delete()
    await message.answer("✅ <b>Категория изменена.</b>", parse_mode="HTML", reply_markup=control_partner_markup)
    await state.clear()

@router.message(PartnerForm.awaiting_partner_url)
async def edit_partner_url(message: types.Message, state: FSMContext):
    data = await state.get_data()
    partner_id = data["partner_id"]
    new_url = message.text
    await db.update_partner(partner_id, partner_url=new_url)
    control_partner_markup = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="🔙 Назад", callback_data=f"partner:{partner_id}")]
    ])
    await data["message_to_delete"].delete()
    await message.answer("✅ <b>URL изменён.</b>", parse_mode="HTML", reply_markup=control_partner_markup)
    await state.clear()

@router.message(PartnerForm.awaiting_partner_name_new)
async def add_partner_handler(message: types.Message, state: FSMContext):
    partner_name = message.text
    await state.update_data(partner_name=partner_name)
    categories_text = "\n".join(
        [f"<code>{category['category_id']}</code>: <b>{category['category_name']}</b>" for category in
         await db.get_categories()])
    await message.answer(categories_text + "\n\n<b>Введите категорию партнёра:</b>", parse_mode="HTML")
    await state.set_state(PartnerForm.awaiting_partner_category_new)

@router.message(PartnerForm.awaiting_partner_category_new)
async def add_partner_category_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    partner_name = data["partner_name"]
    partner_category = message.text

    await db.add_partner(user_id=message.from_user.id, partner_name=partner_name, partner_category=partner_category)

    setting_markup = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="🛍 Перейти к партнёрам", callback_data="admin:partners")],
        [types.InlineKeyboardButton(text="🔙 Назад", callback_data="admin:panel")],
    ])

    await message.answer("<b>✅ Партнёр успешно добавлен!</b>", parse_mode="HTML", reply_markup=setting_markup)
    await state.clear()
