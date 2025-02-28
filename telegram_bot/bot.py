import asyncio
import locale
import pprint
from telegram_bot import text_message
from telegram_bot.keyboards import inline_markup
from telegram_bot.env import dp, bot
from telegram_bot.handler import message, callback
from telegram_bot.states import treatment_calendar, calendar
from telegram_bot.scheduler import start_scheduler
from aiogram_dialog import DialogManager, setup_dialogs, StartMode, ShowMode
from aiogram.filters import ExceptionTypeFilter
from aiogram_dialog.api.exceptions import UnknownIntent

locale.setlocale(locale.LC_ALL, 'ru_RU.UTF-8')

async def on_unknown_intent(event, dialog_manager: DialogManager):
    # Example of handling UnknownIntent Error and starting new dialog.
    print("Restarting dialog: %s", event.exception)
    callback_query = event.update.callback_query
    await callback_query.message.edit_text(text=text_message.TRY_AGAIN_ERROR, reply_markup=inline_markup.get_delete_message_keyboard())
    # await message.send_menu(message=callback_query.message, state=dialog_manager.__dict__['_data']['state'])

async def main():
    dp.include_routers(message.router, treatment_calendar.router, callback.router, calendar.dialog)
    setup_dialogs(dp)
    start_scheduler()

    dp.errors.register(
        on_unknown_intent,
        ExceptionTypeFilter(UnknownIntent),
    )

    print((await bot.get_me()).username + " запущен")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
