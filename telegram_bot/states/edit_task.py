import pathlib
from datetime import date

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import FSInputFile
from aiogram.types import Message, CallbackQuery
from aiogram_dialog import DialogManager, StartMode

from telegram_bot import db, text_message
from telegram_bot.helper import timestamp_to_str, str_to_timestamp, get_media_group
from telegram_bot.env import bot, img_path
from telegram_bot.keyboards import inline_markup
from telegram_bot.states import calendar


class TaskForm(StatesGroup):
    pet_type = State()
    task_id = State()
    treatment_id = State()
    medicament_id = State()
    medicament_name = State()
    start_date = State()
    period = State()


router = Router()

async def update_edit_data(message: Message, state: FSMContext, task_id: int | str) -> None:
    task = await db.get_reminders(id=task_id, value=int(True))
    data = {
        'task_id': task_id,
        'treatment_id': task['treatment_id'],
        'medicament_id': task['medicament_id'],
        'medicament_name': task['medicament_name'],
        'start_date': task['start_date'],
        'pet_type': task['pet_type'],
        'period': task['period']
    }

    await state.update_data(data)
    await process_edit_task(message, state, is_edited=False)


async def process_edit_task(message: Message, state: FSMContext, is_edited: bool = True) -> None:
    try:
        data = await state.get_data()
        task_id, treatment_id, medicament_id, medicament_name, start_date, pet_type, period = data.values()
        treatment = await db.get_treatments(id=treatment_id)
        pet_type = await db.get_pet_type(id=int(pet_type))
        if int(medicament_id) != 0:
            medicament = await db.get_medicament(id=medicament_id)
            medicament_name = medicament['name']
        task_text = text_message.REMINDER_TEXT_EDIT.format(
            treatment=treatment['name'],
            medicament=medicament_name,
            pet=pet_type['name'],
            period=period,
            start_date=timestamp_to_str(float(start_date)),
        )

        markup = inline_markup.get_edit_task_keyboard(is_edited=is_edited)
        await message.answer(task_text, reply_markup=markup)


    except KeyError:
        await message.answer(text_message.TRY_AGAIN_ERROR,
                             reply_markup=inline_markup.get_delete_message_keyboard())
        await state.clear()


@router.message(TaskForm.medicament_name)
async def process_medicament_name(message: Message, state: FSMContext) -> None:
    try:
        if message.text is None:
            raise TypeError
        await state.update_data(medicament_name=message.text)
        await state.update_data(medicament_id=0)
    except TypeError:
        pass
    finally:
        await state.set_state(TaskForm.task_id)
        await process_edit_task(message, state)


@router.message(TaskForm.period)
async def process_period(message: Message, state: FSMContext) -> None:
    try:
        if message.text.isdigit():
            await state.update_data(period=message.text)
        else:
            raise TypeError

    except ValueError:
        await message.answer(text=text_message.ERROR_TEXT)

    except TypeError:
        await message.answer(text=text_message.NON_FORMAT_TEXT)

    except Exception as error:
        print(f"Error text: {error}")
        await message.delete()
        await message.answer(text=text_message.TRY_AGAIN_ERROR,
                             reply_markup=inline_markup.get_delete_message_keyboard())
    finally:
        await state.set_state(TaskForm.task_id)
        await process_edit_task(message, state)


@router.callback_query(F.data == 'edit_treatment')
async def edit_treatment(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.delete()
    data = await state.get_data()
    pet_type = int(data['pet_type'])

    pet_type = await db.get_pet_type(id=pet_type)

    markup = await inline_markup.get_treatments_keyboard(is_edit=True, pet_type=pet_type['id'])

    if pet_type['id'] == 1:
        path = f"{img_path}/treatments/dog/treatments.jpg"
        if pathlib.Path(path).is_file():
            await bot.send_photo(
                chat_id=callback.message.chat.id, photo=FSInputFile(path=path),
                caption=text_message.CHOOSE_TREATMENT, reply_markup=markup
            )
    else:
        await callback.message.answer(text=text_message.CHOOSE_TREATMENT, reply_markup=markup)


@router.callback_query(F.data.startswith('edit:treatment'))
async def process_treatment(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        await callback.message.delete()
        data = callback.data.split(':')
        treatment_id = int(data[2])
        await state.update_data(treatment_id=treatment_id)
        await state.set_state(TaskForm.task_id)
        await process_edit_task(callback.message, state)

    except ValueError:
        await state.clear()


@router.callback_query(F.data == 'edit_medicament')
async def edit_medicament(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.delete()
    data = await state.get_data()
    treatment_id = int(data['treatment_id'])
    pet_type = await db.get_pet_type(id=data['pet_type'])
    pet_type_name = pet_type['type']
    path_folder = f"{img_path}/treatments/{pet_type_name}/"
    markup = await inline_markup.get_medicament_keyboard(treatments_id=treatment_id, is_edit=True, pet_type=pet_type['id'])

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
                                                             pet_type=pet_type['id'], is_edit=True)
        await callback.message.answer(text_message.CHOOSE_ACTION, reply_markup=markup)


@router.callback_query(F.data.contains('edit:medic:choose'))
async def process_medicament_choose(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        await callback.message.delete()
        await callback.message.answer(text=text_message.CHOOSE_SPECIAL_MEDICAMENT)
        await state.set_state(TaskForm.medicament_name)
    except ValueError:
        await state.clear()


@router.callback_query(F.data.contains('edit:medic'))
async def process_medicament(callback: CallbackQuery, state: FSMContext, callback_data: str = None) -> None:
    try:
        await callback.message.delete()
        data = callback_data.split(':') if callback_data is not None else callback.data.split(':')
        medicament_id = int(data[2])

        await state.update_data(medicament_id=medicament_id)
        await state.update_data(medicament_name=None)
        await state.set_state(TaskForm.task_id)
        await process_edit_task(callback.message, state)

    except ValueError:
        await state.clear()


@router.callback_query(F.data == 'edit_period')
async def edit_period(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.delete()
    data = await state.get_data()
    treatment_id = int(data['treatment_id'])
    markup = await inline_markup.get_period_keyboard(is_edit=True, treatment_id=treatment_id)
    await callback.message.answer(text=text_message.CHOOSE_PERIOD, reply_markup=markup)


@router.callback_query(F.data == 'edit_start_date')
async def edit_period(callback: CallbackQuery, dialog_manager: DialogManager) -> None:
    await callback.message.delete()
    await dialog_manager.start(state=calendar.ReminderCalendar.calendar_edit_reminder, mode=StartMode.RESET_STACK)


@router.callback_query(F.data == 'edit:period:choose')
async def process_period_choose(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        await callback.message.delete()
        await callback.message.answer(text=text_message.CHOOSE_SPECIAL_PERIOD)
        await state.set_state(TaskForm.period)
    except ValueError:
        await state.clear()


@router.callback_query(F.data.startswith('edit:period'))
async def process_period(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        await callback.message.delete()
        data = callback.data.split(':')
        period = int(data[2])

        await state.update_data(period=period)
        await state.set_state(TaskForm.task_id)
        await process_edit_task(callback.message, state)

    except ValueError:
        await state.clear()


async def process_edit_date(message: Message, selected_date: date, state: FSMContext) -> None:
    try:
        await message.delete()
        await state.update_data(start_date=str_to_timestamp(selected_date.strftime("%Y-%m-%d")))
        await state.set_state(TaskForm.task_id)
        await process_edit_task(message, state)

    except ValueError:
        await state.clear()


@router.callback_query(F.data == 'edit_data')
async def edit_data(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        data = await state.get_data()
        await db.update_reminder(**data)
        await callback.message.answer(
            text_message.REMINDER_EDIT_COMPLETE, reply_markup=inline_markup.get_reminder_add_complete_keyboard()
        )

    except TypeError or KeyError:
        await callback.message.answer(text_message.TRY_AGAIN_ERROR,
                                      reply_markup=inline_markup.get_delete_message_keyboard())
    finally:
        await state.clear()
        await callback.message.delete()


@router.callback_query(F.data == 'stop_state')
async def stop_state(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.delete()
    await state.clear()
