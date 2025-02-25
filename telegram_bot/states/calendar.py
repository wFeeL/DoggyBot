from datetime import date
from typing import Dict
import pprint
from aiogram.filters.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
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
from telegram_bot.states import treatment_calendar


async def start_date_selected(callback: CallbackQuery, widget,
                                          dialog_manager: DialogManager, selected_date: date) -> None:
    await treatment_calendar.process_start_date(callback, selected_date, state=dialog_manager.middleware_data['state'])
    await dialog_manager.done()


# ReminderCalendar state (only for calendar widget)
class ReminderCalendar(StatesGroup):
    calendar = State()


# Custom month for calendar
class Month(Text):
    async def _render_text(self, data, manager: DialogManager) -> str:
        selected_date: date = data["date"]
        locale = manager.event.from_user.language_code
        return get_month_names(
            'wide', context='stand-alone', locale=locale,
        )[selected_date.month].title()


# Configurate custom calendar (create range and buttons)
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
# Create calendar config with date ranges
calendar_config = CalendarConfig(
    min_date=date(min_date.year, min_date.month, min_date.day),
    years_columns=1, years_per_page=1, month_columns=1
)

# Create dialog with calendar widget
dialog = Dialog(
    Window(
        Const(text_message.CHOOSE_START_DATE),
        CustomCalendar(id='homework_calendar', on_click=start_date_selected, config=calendar_config),
        state=ReminderCalendar.calendar,
    )
)
