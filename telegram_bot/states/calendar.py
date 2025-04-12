from datetime import date
from typing import Dict

from aiogram.filters.state import State, StatesGroup
from aiogram.types import CallbackQuery
from aiogram_dialog import Dialog, Window
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import (
    Calendar, CalendarScope, )
from aiogram_dialog.widgets.kbd import CalendarConfig
from aiogram_dialog.widgets.kbd.calendar_kbd import (
    CalendarDaysView, CalendarMonthView, CalendarScopeView, CalendarYearsView,
)
from aiogram_dialog.widgets.text import Const, Format, Text
from babel.dates import get_month_names

from telegram_bot import text_message
from telegram_bot.states import treatment_calendar, edit_task


async def start_date_selected(callback: CallbackQuery, widget,
                              dialog_manager: DialogManager, selected_date: date) -> None:
    await treatment_calendar.process_start_date(callback, selected_date, state=dialog_manager.middleware_data['state'])
    await dialog_manager.done()


async def start_edit_date(callback: CallbackQuery, widget,
                          dialog_manager: DialogManager, selected_date: date) -> None:
    await edit_task.process_edit_date(callback.message, selected_date, state=dialog_manager.middleware_data['state'])
    await dialog_manager.done()


# ReminderCalendar state (only for calendar_reminder widget)
class ReminderCalendar(StatesGroup):
    calendar_reminder = State()
    calendar_edit_reminder = State()

# Custom month for calendar_reminder
class Month(Text):
    async def _render_text(self, data, manager: DialogManager) -> str:
        selected_date: date = data["date"]
        locale = manager.event.from_user.language_code
        return get_month_names(
            'wide', context='stand-alone', locale=locale,
        )[selected_date.month].title()


# Configurate custom calendar_reminder (create range and buttons)
class CustomCalendar(Calendar):
    def _init_views(self) -> Dict[CalendarScope, CalendarScopeView]:
        return {
            CalendarScope.DAYS: CalendarDaysView(
                self._item_callback_data, self.config,
                header_text='🗓 ' + Month() + Format(' {date:%Y}'),
                next_month_text=Month() + " ▶",
                prev_month_text="◀ " + Month(),
                today_text=Format(">{date:%d}<")
            ),
            CalendarScope.MONTHS: CalendarMonthView(
                self._item_callback_data, self.config,
                month_text=Month(),
                this_month_text='> ' + Month() + ' <',
                next_year_text=Format("{date:%Y}") + " ▶",
                prev_year_text="◀ " + Format("{date:%Y}"),
            ),
            CalendarScope.YEARS: CalendarYearsView(
                self._item_callback_data, self.config,
                this_year_text=Format("> {date:%Y} <"),
                next_page_text=Format("{date:%Y}") + " ▶",
                prev_page_text="◀ " + Format("{date:%Y}"),
            ),
        }


min_date = date.today()
# Create calendar_reminder config with date ranges
calendar_config = CalendarConfig(
    years_columns=1, years_per_page=1, month_columns=1
)

# Create dialog with calendar_reminder widget
dialog = Dialog(
    Window(
        Const(text_message.CHOOSE_START_DATE),
        CustomCalendar(id='reminder_calendar', on_click=start_date_selected, config=calendar_config),
        state=ReminderCalendar.calendar_reminder,
    ),
    Window(
        Const(text_message.CHOOSE_START_DATE),
        CustomCalendar(id='edit_reminder_calendar', on_click=start_edit_date, config=calendar_config),
        state=ReminderCalendar.calendar_edit_reminder,
    )
)
