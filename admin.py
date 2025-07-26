from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
import logging

from config import ADMINS
from database import (
    get_message_by_id,
    update_status_and_response,
    export_all_messages,
    get_all_messages
)

router = Router()


class AdminStates(StatesGroup):
    choosing_message = State()
    typing_response = State()


# Проверка на администратора
def is_admin(message: Message) -> bool:
    return message.from_user.id in ADMINS


# Экспорт обращений в Excel
@router.message(Command("export"))
async def export_messages(message: Message):
    if not is_admin(message):
        await message.answer("❌ У вас нет доступа.")
        return

    try:
        file_path = export_all_messages()
        file = FSInputFile(file_path)
        await message.answer_document(file, caption="📊 Все обращения экспортированы")
    except Exception as e:
        logging.error(f"Ошибка экспорта: {e}")
        await message.answer("❌ Ошибка при экспорте.")


# Команда для запуска админ-панели
@router.message(Command("admin"))
async def admin_panel(message: Message, state: FSMContext):
    if not is_admin(message):
        await message.answer("⛔ У вас нет прав.")
        return

    rows = get_all_messages()
    if not rows:
        await message.answer("❌ Сообщений нет.")
        return

    kb = []
    for r in rows:
        status = r[3]
        label = f"🆔#{r[0]} | {r[1]} | {status}"
        kb.append([KeyboardButton(text=label)])

    await message.answer(
        "Выберите сообщение для ответа:",
        reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    )
    await state.set_state(AdminStates.choosing_message)


# Админ выбирает сообщение
@router.message(AdminStates.choosing_message)
async def admin_choose_message(message: Message, state: FSMContext):
    try:
        msg_id = int(message.text.split("#")[1].split(" ")[0])
        record = get_message_by_id(msg_id)
        if not record:
            await message.answer("⚠️ Сообщение не найдено.")
            return

        await state.update_data(selected_id=msg_id, user_id=record[1], is_anonymous=record[6])

        text = f"📨 Сообщение #{msg_id}:\n\n{record[2]}\n\nВведите ответ:"
        await message.answer(text, reply_markup=ReplyKeyboardRemove())
        await state.set_state(AdminStates.typing_response)

    except Exception as e:
        logging.error(f"Ошибка выбора сообщения: {e}")
        await message.answer("⚠️ Неверный формат. Попробуйте снова.")


# Админ пишет ответ
@router.message(AdminStates.typing_response)
async def admin_send_response(message: Message, state: FSMContext):
    data = await state.get_data()
    msg_id = data["selected_id"]
    user_id = data["user_id"]
    is_anonymous = data["is_anonymous"]
    response = message.text

    update_status_and_response(msg_id, "✅ Отвечено", response)

    if not is_anonymous:
        try:
            await message.bot.send_message(
                chat_id=user_id,
                text=f"📩 Ответ на ваше обращение (ID: {msg_id}):\n\n{response}"
            )
            await message.answer("✅ Ответ отправлен пользователю.")
        except Exception as e:
            logging.error(f"Ошибка отправки пользователю: {e}")
            await message.answer("⚠️ Ответ сохранён, но не удалось отправить пользователю.")
    else:
        await message.answer("✅ Ответ сохранён. Пользователь анонимен — сообщение не отправлено.")

    await state.clear()
