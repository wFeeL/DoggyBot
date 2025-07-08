import pathlib
from datetime import date, timedelta

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram_dialog import DialogManager, StartMode

from telegram_bot import text_message, db
from telegram_bot.env import bot, img_path
from telegram_bot.helper import get_media_group
from telegram_bot.keyboards import inline_markup
from telegram_bot.states import calendar


class TreatmentCalendarForm(StatesGroup):
    none_state = State()
    pet_type = State()
    treatment_id = State()
    medicament_id = State()
    medicament_name = State()
    period = State()
    start_date = State()


router = Router()


async def register_treatment_calendar(message: Message, state: FSMContext):
    markup = await inline_markup.get_pets_keyboard()
    await state.clear()
    await message.answer(text=text_message.CHOOSE_PET_TYPE, reply_markup=markup)
    await state.set_state(TreatmentCalendarForm.none_state)


@router.callback_query(F.data.contains('pet_type:'))
async def process_pet_type(callback: CallbackQuery, state: FSMContext, callback_data: str = None) -> None:
    try:
        await callback.message.delete()
        data = callback_data.split(':') if callback_data is not None else callback.data.split(':')
        pet_type = int(data[1])
        markup = await inline_markup.get_treatments_keyboard(pet_type)
        text = text_message.CHOOSE_TREATMENT
        await state.update_data(pet_type=pet_type)

        if pet_type == 1:
            path = f"{img_path}/treatments/dog/treatments.jpg"
            if pathlib.Path(path).is_file():
                await bot.send_photo(
                    chat_id=callback.message.chat.id, photo=FSInputFile(path=path),
                    caption=text, reply_markup=markup
                )
        elif pet_type == 2:
            await callback.message.answer(text=text, reply_markup=markup)
    except ValueError:
        await state.clear()


@router.callback_query(F.data.startswith('treatment:'))
async def process_treatment(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        await callback.message.delete()
        data = callback.data.split(':')
        treatment_id = int(data[1])
        await state.update_data(treatment_id=treatment_id)
        data = await state.get_data()
        pet_type = await db.get_pet_type(id=data['pet_type'])
        pet_type_name = pet_type['type']
        path_folder = f"{img_path}/treatments/{pet_type_name}/"

        markup = await inline_markup.get_medicament_keyboard(treatments_id=treatment_id, pet_type=pet_type['id'])

        if pet_type_name == 'dog':
            if treatment_id == 3:
                await callback.message.answer(text=text_message.VACCINATION, reply_markup=markup)
            else:
                path = f"{path_folder}/{treatment_id}.jpg"
                if pathlib.Path(path).is_file():
                    await bot.send_photo(
                        chat_id=callback.message.chat.id, photo=FSInputFile(path=path),
                        caption=text_message.CHOOSE_MEDICAMENT, reply_markup=markup
                    )
        elif pet_type_name == 'cat':
            photos_end = 4 if treatment_id == 4 else 6
            photos_start = 5 if treatment_id == 5 else 1

            media_group = get_media_group(path=path_folder, first_message_text=text_message.CHOOSE_MEDICAMENT,
                                          photos_end=photos_end, photos_start=photos_start)
            media_group = await bot.send_media_group(chat_id=callback.message.chat.id, media=media_group)
            media_group_id, media_group_len = media_group[0].message_id, len(media_group)
            markup = await inline_markup.get_medicament_keyboard(treatments_id=treatment_id,
                                                                 media_group=(media_group_id, media_group_len),
                                                                 pet_type=pet_type['id'])
            await callback.message.answer(text_message.CHOOSE_ACTION, reply_markup=markup)


    except ValueError:
        await state.clear()


@router.callback_query(lambda call: 'period:choose' in call.data and 'edit' not in call.data)
async def process_period_choose(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        await callback.message.delete()
        await callback.message.answer(text=text_message.CHOOSE_SPECIAL_PERIOD)
        await state.set_state(TreatmentCalendarForm.period)
    except ValueError:
        await state.clear()


@router.callback_query(lambda call: 'medic:choose' in call.data and 'edit' not in call.data)
async def process_medicament_choose(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        await callback.message.delete()
        await callback.message.answer(text=text_message.CHOOSE_SPECIAL_MEDICAMENT)
        await state.set_state(TreatmentCalendarForm.medicament_name)
    except ValueError:
        await state.clear()


@router.callback_query(lambda call: 'medic:' in call.data and 'edit' not in call.data)
async def process_medicament(callback: CallbackQuery, state: FSMContext, callback_data: str = None) -> None:
    try:
        await callback.message.delete()
        data = callback_data.split(':') if callback_data is not None else callback_data.split(':')
        medicament_id = int(data[1])

        await state.update_data(medicament_id=medicament_id)
        state_data = await state.get_data()
        treatment_id = state_data['treatment_id']
        markup = await inline_markup.get_period_keyboard(treatment_id=treatment_id)
        await callback.message.answer(text=text_message.CHOOSE_PERIOD, reply_markup=markup)

    except ValueError:
        await state.clear()


@router.message(TreatmentCalendarForm.medicament_name)
async def process_medicament_name(message: Message, state: FSMContext) -> None:
    try:
        await state.update_data(medicament_id=0)
        await state.update_data(medicament_name=message.text)
        await state.set_state(TreatmentCalendarForm.period)
        state_data = await state.get_data()
        treatment_id = state_data['treatment_id']

        markup = await inline_markup.get_period_keyboard(treatment_id=treatment_id)
        await message.answer(text=text_message.CHOOSE_PERIOD, reply_markup=markup)
    except ValueError:
        await message.answer(text=text_message.ERROR_TEXT)
        await state.clear()


@router.message(TreatmentCalendarForm.period)
async def process_period(message: Message, state: FSMContext, dialog_manager: DialogManager) -> None:
    try:
        if message.text.isdigit():
            await state.update_data(period=message.text)
            await dialog_manager.start(state=calendar.ReminderCalendar.calendar_reminder, mode=StartMode.RESET_STACK)
        else:
            raise TypeError

    except ValueError:
        await message.answer(text=text_message.ERROR_TEXT)
        await state.clear()

    except TypeError:
        await message.answer(text=text_message.NON_FORMAT_TEXT)
        await state.clear()

    except Exception as error:
        print(f"Error text: {error}")
        await message.delete()
        await message.answer(text=text_message.TRY_AGAIN_ERROR,
                             reply_markup=inline_markup.get_delete_message_keyboard())


@router.callback_query(F.data.startswith('period:'))
async def process_period(callback: CallbackQuery, state: FSMContext, dialog_manager: DialogManager) -> None:
    try:
        await callback.message.delete()
        data = callback.data.split(':')
        period = int(data[1])
        await state.update_data(period=period)
        await dialog_manager.start(state=calendar.ReminderCalendar.calendar_reminder, mode=StartMode.RESET_STACK)

    except ValueError:
        await state.clear()

    except Exception as error:
        print(f"Error text: {error}")
        await callback.message.delete()
        await callback.message.answer(text=text_message.TRY_AGAIN_ERROR,
                                      reply_markup=inline_markup.get_delete_message_keyboard())


async def process_start_date(callback: CallbackQuery, selected_date: date, state: FSMContext) -> None:
    try:
        data = await state.get_data()
        end_date = selected_date + timedelta(days=int(data['period']))
        start_date = selected_date.strftime("%d.%m.%Y")

        await state.update_data(start_date=start_date)
        treatment_id, medicament_id, period, pet_type = data['treatment_id'], data['medicament_id'], data['period'], data['pet_type']
        if int(medicament_id) != 0:
            medicament = await db.get_medicament(id=medicament_id)
            medicament_name = medicament['name']
        else:
            medicament_name = data['medicament_name']

        treatment = await db.get_treatments(id=treatment_id)
        pet = await db.get_pet_type(id=pet_type)
        await callback.message.delete()
        await callback.message.answer(text=text_message.REMINDER_TEXT.format(
            pet=pet['name'],
            treatment=treatment['name'],
            medicament=medicament_name,
            period=period,
            start_date=start_date,
            end_date=end_date.strftime("%d.%m.%Y")
        ), reply_markup=inline_markup.get_reminder_keyboard())

    except Exception as error:
        print(f"Error text: {error}")
        await callback.message.delete()
        await callback.message.answer(text=text_message.TRY_AGAIN_ERROR,
                                      reply_markup=inline_markup.get_delete_message_keyboard())


@router.callback_query(F.data.startswith('reminder:create'))
async def process_reminder(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        await callback.message.delete()
        data = await state.get_data()
        treatment_id, medicament_id, start_date, period, pet_type = data['treatment_id'], data['medicament_id'], data[
            'start_date'], data['period'], data['pet_type']
        medicament_name = None
        if int(medicament_id) == 0:
            medicament_name = data['medicament_name']

        await db.add_reminder(
            user_id=callback.message.chat.id,
            treatment_id=treatment_id,
            medicament_id=medicament_id,
            medicament_name=medicament_name,
            start_date=start_date,
            pet_type=pet_type,
            period=period
        )
        await callback.message.answer(text=text_message.ADD_REMINDER_SUCCESSFUL_TEXT,
                                      reply_markup=inline_markup.get_reminder_add_complete_keyboard())
    except KeyError:
        await callback.message.answer(text=text_message.ERROR_TEXT)
    except Exception as e:
        print(f"Error text: {e}")
    finally:
        await state.clear()
