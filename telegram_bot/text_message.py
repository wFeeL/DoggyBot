ABOUT_TEXT = """👋 Вас приветствует сервис <b>Doggy Logy</b>\n
Мы работаем только с <b>проверенными компаниями</b>, которым <b>доверяем сами</b>. Здесь вы можете приобрести нашу <b>программу лояльности</b>\n
<i>Скидки действуют на всех наших партнеров, 1 раз в месяц на каждого партнера</i>\n
<i>Создатель бренда Doggy Logy: Валерия Попова @doggy_logy</i>"""

PROMO_CODE_ENABLED = """<b>🎟️ Ваш промокод</b>: <code>{promo_code}</code>"""

PROMO_CODE_NOT_ENABLED = """<i>🎟️ Получите промокод после заполнения формы.</i>"""

MENU_TEXT = """👋 Вас приветствует сервис <b>Doggy Logy</b>\n
Мы работаем только с <b>проверенными компаниями</b>, которым <b>доверяем сами</b>. Здесь вы можете приобрести нашу <b>программу лояльности</b>\n
<i>Скидки действуют на всех наших партнеров, 1 раз в месяц на каждого партнера</i>\n\n"""

PROFILE_TEXT = """👤 <b>Ваш профиль</b>\n
🎭 <b>О вас:</b>
<b>Полное имя</b>: <code>{full_name}</code>
<b>Номер телефона</b>: <code>{phone_number}</code>
<b>Дата рождения</b>: <code>{birth_date}</code>
<b>Возраст</b>: <code>{age} лет</code>\n
🐶 <b>Ваши питомцы:</b>\n{pets}
🎟️ <b>Ваш промокод:</b> <code>{promo_code}</code>"""

NONE_PROFILE_TEXT = """👤 <b>Ваш профиль</b>\n\n<i>Вы ещё не указали никаких данных!</i>"""

FORM_TEXT = """👇 <b>Для заполнения формы нажмите на кнопку ниже.</b>"""

CONSULTATION_TEXT = """👨‍⚕️ В нашем сервисе можно получить <b>1 бесплатную</b> консультацию врача.
<i>Сформулируйте и отправьте свой вопрос @doggy_logy</i>"""

ADMIN_PANEL_TEXT = """🛡 <b>Админ-панель:</b>"""

USER_BLOCKED_TEXT = """❌ <b>Вы заблокированы, для разблокировки свяжитесь с администрацией.</b>"""

FUNCTION_ERROR_TEXT = """❌ <b>Вам недоступна эта функция.</b>"""

REDEEM_CODE_TEXT = """📇 <b>Списать промокод:</b>"""

CODE_ERROR_TEXT = """⚠ <b>Этот промокод неверный.</b>"""

FORMAT_ERROR_TEXT = """⚠ <b>Введён промокод неверного формата.</b>"""

PROFILE_COMPLETE_TEXT = """<b>Ваш профиль успешно заполнен.</b>"""

PROFILE_ERROR_TEXT = """❌ <b>Предоставлены недействительные данные.</b>"""

CHOOSE_TREATMENT = """🐶 <b>Тип обработки:</b>"""

CHOOSE_MEDICAMENT = """💊 <b>Лекарственный препарат:</b>"""

CHOOSE_PERIOD = """🗓 <b>Период:</b>"""

CHOOSE_SPECIAL_PERIOD = """🗓 <b>Введите период в днях</b>"""

REMINDER_TEXT = """<b>Напоминание:</b>\n
• <b>Тип</b>: <i>{treatment}</i>
• <b>Лекарственный препарат</b>: <i>{medicament}</i> 💊
• <b>Дата начала</b>: <i>{start_date}</i>
• <b>Дата окончания</b>: <i>{end_date}</i>
• <b>Период</b>: <i>{period} дней</i>
"""

NONE_REMINDER_TEXT = """У вас нет напоминаний!"""

ADD_REMINDER_SUCCESSFUL_TEXT = """Вы успешно добавили напоминание!"""

OLD_REDEEMED_PROMO = """🔋 <b>Теперь вы снова можете использовать промокод у партнёра <code>{partner_name}</code>!</b>"""

CHOOSE_START_DATE = """🗓 <b>Выберите дату начала</b>"""

CHOOSE_CATEGORY_TEXT = """🛍 <b>Категории:</b>"""

CATEGORY_NAME = """<b>{category}</b>\n\n"""

PARTNER_CATEGORY_TEXT = """• <a href='{url}'>{name}</a>\n{legacy_text}\n\n"""

PROMO_CODE_REDEEMED_TEXT = """✅ Промокод списан!"""

PROMO_CODE_ALREADY_REDEEMED_TEXT = """⚠ Промокод уже списан у этого партнёра."""

USER_PROMO_CODE_REDEEMED_TEXT = """✅ <b>Ваш промокод списан у партнёра <code>{partner_name}</code></b>"""

STATS_TEXT = """📊 <b>Статистика</b>:\n
Количество пользователей: <code>{users_len}</code>
Количество партнёров: <code>{partners_len}</code>
Подписок за день: <code>{orders_day} / {orders_day_sum}₽</code>
Подписок за месяц: <code>{orders_month} / {orders_month_sum}₽</code>
Подписок за год: <code>{orders_year} / {orders_year_sum}₽</code>"""

PARTNERS_TEXT = """📈 <b>Партнёры:</b>"""

USERS_TEXT = """👥 <b>Пользователи:</b>"""

USER_INFO_TEXT = """👤 <b>{full_name} (ID: {user_id})</b>
<b>Статус:</b> <code>{user_status}</code>"""

PARTNER_INFO_TEXT = """📈 <b>{partner_name} (ID: {partner_id})</b>\n
<b>ТГ партнёра:</b> {full_name} (ID: {user_id})
<b>Категория:</b> <code>{category_name}</code>
<b>Скрыт:</b> <code>{partner_status}</code>\n
{partner_url}"""

ERROR_TEXT = """Something went wrong."""