ABOUT_TEXT = """<b>🐶 Doggy Logy</b> - это сервис для владельцев собак в Москве.

• @KinoSobaki_bot - подбор собак для съемок
• Гуманная коррекция поведения/обучение командам 
• Помощь с выбором щенка
• Передержка
• Догситтер/выгул
• Разработка рациона 
• Консультации ветеринара
• Страхование здоровья питомца
• Подготовка к выставкам 
• Груминг 
• Зооюрист
• Зоотакси
• Пэт-фотограф 

Мы всегда открыты для обратной связи!
<i>С любовью к собакам и их людям, DoggyLogy ❤️</i>
@manager_DogyLogy
@doggy_logy"""

PROMO_CODE_ENABLED = """• Индивидуальный: <code>{promo_code}</code>"""

PROMO_CODE_NOT_ENABLED = """<i>• Получите индивидуальный промокод после заполнения формы.</i>"""

MENU_TEXT = """👋 Бесплатная подписка на сервис <b>Doggy Logy</b>\n
<b>Здесь можно</b>:
• Вести календарь обработок питомца и ставить напоминания.
• Получить подарки и скидки от партнеров <i>1 раз в месяц на каждого партнера</i>.
• Получить 1 ответ от ветеринара.
• Получить подборку товаров для щенка.\n
<b>🎟 Промокоды:</b>
• Общий - <code>DoggyLogy</code>\n"""


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

SELECTION_TEXT = """🐶 <b>Подборка товаров для щенков</b>:\n
Подборка на OZON: <a href='https://www.ozon.ru/cart?share=jQ3wGX0'>Мелкие</a>, <a href='https://www.ozon.ru/cart?share=yzNnP5V'>средние</a> и <a href='https://www.ozon.ru/cart?share=zV1d6LP'>крупные</a> породы.\n
<i>Запросить подборку на WildBerries: @doggy_logy</i>"""

ADMIN_PANEL_TEXT = """🛡 <b>Админ-панель:</b>"""

USER_BLOCKED_TEXT = """❌ <b>Вы заблокированы, для разблокировки свяжитесь с администрацией.</b>"""

FUNCTION_ERROR_TEXT = """❌ <b>Вам недоступна эта функция.</b>"""

REDEEM_CODE_TEXT = """📇 <b>Списать промокод:</b>"""

CODE_ERROR_TEXT = """⚠ <b>Этот промокод неверный.</b>"""

FORMAT_ERROR_TEXT = """⚠ <b>Введён промокод неверного формата.</b>"""

PROFILE_COMPLETE_TEXT = """<b>✅ Ваш профиль успешно заполнен.</b>"""

PROFILE_ERROR_TEXT = """❌ <b>Предоставлены недействительные данные.</b>"""

CHOOSE_TREATMENT = """🐶 <b>Тип обработки:</b>"""

CHOOSE_MEDICAMENT = """💊 <b>Лекарственный препарат:</b>"""

CHOOSE_PERIOD = """🗓 <b>Период:</b>"""

CHOOSE_SPECIAL_PERIOD = """🗓 <b>Введите период в днях:</b>"""

CHOOSE_SPECIAL_MEDICAMENT = """💊 <b>Введите название лекарственного препарата:</b>"""

REMINDER_TEXT = """❗ <b>Напоминание:</b>\n
• <b>Тип</b>: <i>{treatment}</i>
• <b>Лекарство</b>: <i>{medicament}</i> 💊
• <b>Начало</b>: <i>{start_date}</i>
• <b>Конец</b>: <i>{end_date}</i>
• <b>Период</b>: <i>{period} дней</i>
"""

NONE_REMINDER_TEXT = """<b>У Вас нет активных напоминаний!</b>"""

ADD_REMINDER_SUCCESSFUL_TEXT = """✅ Вы успешно добавили напоминание!"""

OLD_REDEEMED_PROMO = """🔋 <b>Теперь вы снова можете использовать промокод у партнёра <code>{partner_name}</code>!</b>"""

CHOOSE_START_DATE = """🗓 <b>Выберите дату начала:</b>"""

CHOOSE_CATEGORY_TEXT = """🛍 <b>Категории:</b>"""

CATEGORY_NAME = """<b>{category}</b>\n\n"""

PARTNER_CATEGORY_TEXT = """• <b><a href='{url}'>{name}</a></b>\n<i>{legacy_text}</i>\n\n"""

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

ERROR_TEXT = """🚫 Произошла ошибка!"""

TRY_AGAIN_ERROR = """🚫 Произошла ошибка! Попробуйте заново."""

NON_FORMAT_TEXT = """🚫 Вы ввели неверный формат данных!"""

DELETE_TASK_COMPLETE = """✅ Вы успешно удалили напоминание!"""