import pathlib
from datetime import date, datetime, timedelta
from select import select

from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InputMediaPhoto, FSInputFile
from telegram_bot.env import bot
from telegram_bot import text_message, db
from telegram_bot.keyboards import inline_markup
from telegram_bot.states import calendar
from aiogram_dialog import DialogManager, setup_dialogs, StartMode


class TreatmentCalendarForm(StatesGroup):
    none_state = State()
    treatment_id = State()
    medicament_id = State()
    period = State()
    start_date = State()


router = Router()
router.include_router(calendar.dialog)  # Include calendar router (dialog window from aiogram_dialog)
setup_dialogs(router)  # Setup router's dialog


async def register_treatment_calendar(message: Message, state: FSMContext) -> None:
    markup = await inline_markup.get_treatments_keyboard()
    path = "img/treatments/treatments.jpg"
    if pathlib.Path(path).is_file():
        await bot.send_photo(
            chat_id=message.chat.id, photo=FSInputFile(path=path),
            caption=text_message.CHOOSE_TREATMENT, reply_markup=markup
        )
    await state.set_state(TreatmentCalendarForm.none_state)


@router.callback_query(F.data.startswith('treatment:'))
async def process_treatment(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        await callback.message.delete()
        data = callback.data.split(':')
        treatment_id = int(data[1])

        await state.update_data(treatment_id=treatment_id)

        markup = await inline_markup.get_medicament_keyboard(treatments_id=treatment_id)
        if pathlib.Path(f"img/treatments/{treatment_id}.jpg").is_file():
            await bot.send_photo(
                chat_id=callback.message.chat.id, photo=FSInputFile(path=f"img/treatments/{treatment_id}.jpg"),
                caption=text_message.CHOOSE_MEDICAMENT, reply_markup=markup
            )

    except ValueError:
        await state.clear()


@router.callback_query(F.data.startswith('medicament:'))
async def process_medicament(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        await callback.message.delete()
        data = callback.data.split(':')
        medicament_id = int(data[1])

        await state.update_data(medicament_id=medicament_id)
        state_data = await state.get_data()
        treatment_id = state_data['treatment_id']
        markup = await inline_markup.get_period_keyboard(treatment_id=treatment_id)
        await callback.message.answer(text=text_message.CHOOSE_PERIOD, reply_markup=markup)

    except ValueError:
        await state.clear()


@router.callback_query(F.data == 'period:choose')
async def process_period_choose(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        await callback.message.delete()
        await callback.message.answer(text=text_message.CHOOSE_SPECIAL_PERIOD)
        await state.set_state(TreatmentCalendarForm.period)
    except ValueError:
        await state.clear()


@router.message(TreatmentCalendarForm.period)
async def process_period(message: Message, state: FSMContext, dialog_manager: DialogManager) -> None:
    try:
        if message.text.isdigit():
            await state.update_data(period=message.text)
            await dialog_manager.start(state=calendar.ReminderCalendar.calendar, mode=StartMode.RESET_STACK)
        else:
            raise TypeError

    except ValueError:
        await message.answer(text=text_message.ERROR_TEXT)
        await state.clear()

    except TypeError:
        await message.answer(text=text_message.NON_FORMAT_TEXT)
        await state.clear()


@router.callback_query(F.data.startswith('period:'))
async def process_period(callback: CallbackQuery, state: FSMContext, dialog_manager: DialogManager) -> None:
    try:
        await callback.message.delete()
        data = callback.data.split(':')
        period = int(data[1])
        await state.update_data(period=period)
        await dialog_manager.start(state=calendar.ReminderCalendar.calendar, mode=StartMode.RESET_STACK)

    except ValueError:
        await state.clear()


async def process_start_date(callback: CallbackQuery, selected_date: date, state: FSMContext) -> None:
    data = await state.get_data()
    end_date = selected_date + timedelta(days=int(data['period']))
    start_date = selected_date.strftime("%d.%m.%Y")

    await state.update_data(start_date=start_date)
    treatment_id, medicament_id, period = data['treatment_id'], data['medicament_id'], data['period']
    treatment, medicament = await db.get_treatments(id=treatment_id), await db.get_medicament(id=medicament_id)
    await callback.message.delete()
    await callback.message.answer(text=text_message.REMINDER_TEXT.format(
        treatment=treatment['name'],
        medicament=medicament['name'],
        period=period,
        start_date=start_date,
        end_date=end_date.strftime("%d.%m.%Y")
    ), reply_markup=inline_markup.get_reminder_keyboard())

@router.callback_query(F.data.startswith('reminder:create'))
async def process_reminder(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.delete()
    data = await state.get_data()
    treatment_id, medicament_id, start_date, period = data['treatment_id'], data['medicament_id'], data['start_date'], data['period']

    try:
        await db.add_reminder(
            user_id=callback.message.chat.id,
            treatment_id=treatment_id,
            medicament_id=medicament_id,
            start_date=start_date,
            period=period
        )

    except KeyError:
        await callback.message.answer(text=text_message.ERROR_TEXT)
    except Exception as e:
        print(f'Error text: {e}')
    finally:
        await state.clear()


    await callback.message.answer(text=text_message.ADD_REMINDER_SUCCESSFUL_TEXT,
                                  reply_markup=inline_markup.get_reminder_add_complete_keyboard())
