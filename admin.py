# admin.py
from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, FSInputFile
from aiogram.filters import Command, CommandStart
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
logger = logging.getLogger(__name__)


class AdminStates(StatesGroup):
    choosing_message = State()
    typing_response = State()


def is_admin(message: Message) -> bool:
    # Важно: ADMINS должен быть списком int в config.py
    return message.from_user and message.from_user.id in ADMINS


# На /start у админа очищаем его админское состояние, чтобы не мешало обычным хендлерам
@router.message(CommandStart())
async def admin_reset_on_start(message: Message, state: FSMContext):
    if not is_admin(message):
        return
    if await state.get_state():
        await state.clear()
        # Ничего не отвечаем — общий /start обработается user-хендлером


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
        logger.error(f"Ошибка экспорта: {e}")
        await message.answer("❌ Ошибка при экспорте.")


# Открыть админ-панель
@router.message(Command("admin"))
async def admin_panel(message: Message, state: FSMContext):
    if not is_admin(message):
        await message.answer("⛔ У вас нет прав.")
        return

    rows = get_all_messages()
    if not rows:
        await message.answer("Пока нет обращений.")
        return

    kb = []
    for r in rows:
        # r: (id, type, message, status)
        label = f"🆔#{r[0]} | {r[1]} | {r[3]}"
        kb.append([KeyboardButton(text=label)])

    await message.answer(
        "Выберите сообщение для ответа:",
        reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    )
    await state.set_state(AdminStates.choosing_message)


# Выбор сообщения для ответа
@router.message(AdminStates.choosing_message)
async def admin_choose_message(message: Message, state: FSMContext):
    # Если прилетела команда (например, /start или /export), не обрабатываем тут
    if message.text and message.text.startswith("/"):
        return

    try:
        # Ожидаем формат кнопки: "🆔#<id> | ..."
        msg_id = int(message.text.split("#")[1].split(" ")[0])
        record = get_message_by_id(msg_id)
        if not record:
            await message.answer("⚠️ Обращение не найдено. Нажмите /admin и выберите из списка.")
            return

        # record: (id, user_id, type, message, name, position, is_anonymous, reason, file_path, status, answer, created_at)
        await state.update_data(selected_id=msg_id, user_id=record[1], is_anonymous=record[6])

        # ВАЖНО: текст обращения — record[3], а не record[2]
        text = f"📨 Сообщение #{msg_id}:\n\n{record[3]}\n\nВведите ответ:"
        await message.answer(text, reply_markup=ReplyKeyboardRemove())
        await state.set_state(AdminStates.typing_response)

    except Exception as e:
        logger.warning(f"Неверный формат выбора в админке: {e}")
        await message.answer("⚠️ Неверный формат. Нажмите /admin и выберите сообщение из списка.")


# Ввод и отправка ответа
@router.message(AdminStates.typing_response)
async def admin_send_response(message: Message, state: FSMContext):
    data = await state.get_data()
    msg_id = data["selected_id"]
    user_id = data["user_id"]
    is_anonymous = data["is_anonymous"]
    response = message.text

    try:
        update_status_and_response(msg_id, "✅ Ответ отправлен", response)

        if not is_anonymous:
            try:
                await message.bot.send_message(
                    chat_id=user_id,
                    text=f"📩 Ответ на ваше обращение (ID: {msg_id}):\n\n{response}"
                )
                await message.answer("✅ Ответ сохранён и отправлен пользователю.")
            except Exception as e:
                logger.error(f"Ошибка отправки пользователю {user_id}: {e}")
                await message.answer("⚠️ Ответ сохранён, но не удалось отправить пользователю.")
        else:
            await message.answer("✅ Ответ сохранён и отправлен пользователю.")

    except Exception as e:
        logger.error(f"Ошибка при сохранении ответа: {e}")
        await message.answer("❌ Не удалось сохранить ответ, попробуйте ещё раз.")

    await state.clear()
