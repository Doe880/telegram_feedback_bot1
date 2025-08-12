# handlers.py
from aiogram import Router, F, types
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from config import ADMINS, MANAGERS
from database import insert_message, get_user_messages
from pathlib import Path
import aiofiles
from utils import save_file
import logging

router = Router()
logging.basicConfig(level=logging.INFO)

BACK_TEXT = "⬅ Назад"
BACK_BTN = KeyboardButton(text=BACK_TEXT)


class Form(StatesGroup):
    choosing_manager = State()
    entering_name = State()
    entering_position = State()
    anonymous_reason = State()
    typing_message = State()
    uploading_file = State()


def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👨‍💼 Задать вопрос руководителю")],
            [KeyboardButton(text="📢 Общий вопрос")],
            [KeyboardButton(text="📝 Написать генеральному директору")],
            [KeyboardButton(text="💡 Предложить идею")],
            [KeyboardButton(text="📂 Мои обращения")]
        ],
        resize_keyboard=True
    )


# --- History helpers -------------------------------------------------------
async def push_history(state: FSMContext):
    """Сохранить текущее состояние в стек истории (если оно есть)."""
    current = await state.get_state()  # строка или None
    if not current:
        return
    data = await state.get_data()
    history = data.get("history", [])
    # избегаем подряд одинаковых записей
    if not history or history[-1] != current:
        history.append(current)
        await state.update_data(history=history)


async def pop_previous(state: FSMContext):
    """Взять предыдущее состояние из истории (или None)."""
    data = await state.get_data()
    history = data.get("history", [])
    if not history:
        return None
    prev = history.pop()
    await state.update_data(history=history)
    return prev
# ---------------------------------------------------------------------------


@router.message(Command("chat_id"))
async def chat_id(message: types.Message):
    await message.answer(f"Chat ID: {message.chat.id}")


# Универсальный хендлер "Назад"
@router.message(F.text == BACK_TEXT)
async def go_back(message: Message, state: FSMContext):
    prev = await pop_previous(state)
    if not prev:
        # Если истории нет — вернуться в главное меню
        await state.clear()
        await state.update_data(history=[])
        await message.answer("Вы вернулись в главное меню.", reply_markup=main_menu())
        return

    # Устанавливаем предыдущее состояние
    await state.set_state(prev)
    state_name = prev.split(":")[-1] if ":" in prev else prev

    # Отправляем соответствующий текст и клавиатуру в соответствии с состоянием
    if state_name == "choosing_manager":
        buttons = [[KeyboardButton(text=name)] for name in MANAGERS]
        kb = ReplyKeyboardMarkup(keyboard=buttons + [[BACK_BTN]], resize_keyboard=True, one_time_keyboard=True)
        await message.answer("Выберите руководителя:", reply_markup=kb)
    elif state_name == "entering_name":
        kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🤐 Анонимно")], [BACK_BTN]], resize_keyboard=True, one_time_keyboard=True)
        await message.answer("Введите ваше имя и фамилию или нажмите 'Анонимно'.", reply_markup=kb)
    elif state_name == "entering_position":
        await message.answer("Укажите вашу должность:", reply_markup=ReplyKeyboardMarkup(keyboard=[[BACK_BTN]], resize_keyboard=True))
    elif state_name == "anonymous_reason":
        await message.answer("Почему вы хотите остаться анонимным?", reply_markup=ReplyKeyboardMarkup(keyboard=[[BACK_BTN]], resize_keyboard=True))
    elif state_name == "typing_message":
        await message.answer("Введите ваше сообщение (до 1000 символов):", reply_markup=ReplyKeyboardMarkup(keyboard=[[BACK_BTN]], resize_keyboard=True))
    elif state_name == "uploading_file":
        await message.answer("Если хотите, прикрепите файл (pdf, docx, xls, jpg, png) или введите 'Нет'.", reply_markup=ReplyKeyboardMarkup(keyboard=[[BACK_BTN]], resize_keyboard=True))
    else:
        # На всякий случай — возвращаем в главное
        await state.clear()
        await state.update_data(history=[])
        await message.answer("Вы вернулись в главное меню.", reply_markup=main_menu())


@router.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.clear()
    await state.update_data(history=[])
    await message.answer(
        "👋 Привет! Я бот для обратной связи.\n"
        "Вы можете задать вопрос, поделиться идеей или предложить улучшение.\n"
        "Выберите действие:",
        reply_markup=main_menu()
    )


@router.message(F.text == "👨‍💼 Задать вопрос руководителю")
async def choose_manager(message: Message, state: FSMContext):
    # сохраняем user_id и тип
    await state.update_data(user_id=message.from_user.id, type="руководитель")
    # push_history не добавит ничего, если предыдущего состояния нет
    await push_history(state)

    buttons = [[KeyboardButton(text=name)] for name in MANAGERS]
    kb = ReplyKeyboardMarkup(keyboard=buttons + [[BACK_BTN]], resize_keyboard=True, one_time_keyboard=True)
    await message.answer("Выберите руководителя:", reply_markup=kb)
    await state.set_state(Form.choosing_manager)


@router.message(Form.choosing_manager)
async def manager_chosen(message: Message, state: FSMContext):
    # запоминаем текущее для возможности вернуться
    await push_history(state)
    await state.update_data(recipient=message.text)
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🤐 Анонимно")], [BACK_BTN]], resize_keyboard=True, one_time_keyboard=True)
    await message.answer("Введите ваше имя и фамилию или нажмите 'Анонимно'.", reply_markup=kb)
    await state.set_state(Form.entering_name)


@router.message(F.text.in_({
    "📢 Общий вопрос",
    "📝 Написать генеральному директору",
    "💡 Предложить идею"
}))
async def choose_type(message: Message, state: FSMContext):
    type_map = {
        "📢 Общий вопрос": "общий",
        "📝 Написать генеральному директору": "директор",
        "💡 Предложить идею": "идея"
    }
    await state.update_data(user_id=message.from_user.id, type=type_map[message.text], recipient="")
    await push_history(state)

    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🤐 Анонимно")], [BACK_BTN]], resize_keyboard=True, one_time_keyboard=True)
    await message.answer("Введите ваше имя и фамилию или нажмите 'Анонимно'.", reply_markup=kb)
    await state.set_state(Form.entering_name)


@router.message(Form.entering_name)
async def get_name(message: Message, state: FSMContext):
    await push_history(state)
    text = message.text
    if text == "🤐 Анонимно":
        await state.update_data(is_anonymous=1, name="Аноним", position="Аноним")
        await message.answer("Почему вы хотите остаться анонимным?", reply_markup=ReplyKeyboardMarkup(keyboard=[[BACK_BTN]], resize_keyboard=True))
        await state.set_state(Form.anonymous_reason)
    else:
        await state.update_data(is_anonymous=0, name=text)
        await message.answer("Укажите вашу должность:", reply_markup=ReplyKeyboardMarkup(keyboard=[[BACK_BTN]], resize_keyboard=True))
        await state.set_state(Form.entering_position)


@router.message(Form.entering_position)
async def get_position(message: Message, state: FSMContext):
    await push_history(state)
    await state.update_data(position=message.text, reason="")
    await message.answer("Введите ваше сообщение (до 1000 символов):", reply_markup=ReplyKeyboardMarkup(keyboard=[[BACK_BTN]], resize_keyboard=True))
    await state.set_state(Form.typing_message)


@router.message(Form.anonymous_reason)
async def get_reason(message: Message, state: FSMContext):
    await push_history(state)
    await state.update_data(reason=message.text)
    await message.answer("Введите ваше сообщение (до 1000 символов):", reply_markup=ReplyKeyboardMarkup(keyboard=[[BACK_BTN]], resize_keyboard=True))
    await state.set_state(Form.typing_message)


@router.message(Form.typing_message)
async def get_message(message: Message, state: FSMContext):
    await push_history(state)
    if len(message.text) > 1000:
        await message.answer("Слишком длинное сообщение. Пожалуйста, сократите до 1000 символов.")
        return
    await state.update_data(message=message.text)
    await message.answer("Если хотите, прикрепите файл (pdf, docx, xls, jpg, png) или введите 'Нет'.",
                         reply_markup=ReplyKeyboardMarkup(keyboard=[[BACK_BTN]], resize_keyboard=True))
    await state.set_state(Form.uploading_file)


@router.message(Form.uploading_file)
async def handle_file_or_skip(message: Message, state: FSMContext):
    file_path = None

    try:
        # Документ (PDF, DOCX, XLSX и т.п.)
        if message.document:
            if message.document.mime_type in [
                "application/pdf",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "image/jpeg",
                "image/png"
            ]:
                file_path = await save_file(message)
            else:
                await message.answer("⛔ Неподдерживаемый тип файла.", reply_markup=ReplyKeyboardMarkup(keyboard=[[BACK_BTN]], resize_keyboard=True))
                return

        # Фото
        elif message.photo:
            largest_photo = message.photo[-1]
            file = await message.bot.get_file(largest_photo.file_id)
            file_bytes = await message.bot.download_file(file.file_path)

            path = Path("uploads") / f"{message.from_user.id}_photo.jpg"
            path.parent.mkdir(exist_ok=True)

            async with aiofiles.open(path, "wb") as f:
                await f.write(file_bytes.getvalue())

            file_path = str(path)

        # Сообщение "Нет"
        elif message.text and message.text.strip().lower() in ["нет", "no"]:
            file_path = None

        else:
            await message.answer("Пожалуйста, прикрепите файл (pdf, docx, xls, jpg, png) или введите 'Нет'.",
                                 reply_markup=ReplyKeyboardMarkup(keyboard=[[BACK_BTN]], resize_keyboard=True))
            return

    except Exception as e:
        logging.error(f"Ошибка при сохранении файла: {e}")
        await message.answer("Произошла ошибка при загрузке файла.", reply_markup=ReplyKeyboardMarkup(keyboard=[[BACK_BTN]], resize_keyboard=True))
        return

    # Сохраняем и очищаем историю (т. к. запрос завершён)
    await state.update_data(file_path=file_path)
    user = await state.get_data()
    msg_id = insert_message(user)

    # Построение текста для админов
    if user.get("is_anonymous"):
        text = (
            f"📩 Анонимное обращение #{msg_id}\n"
            f"Кому: {user.get('recipient','')}\n"
            f"Причина анонимности: {user.get('reason','')}\n"
            f"Тип: {user.get('type','')}\n"
            f"Сообщение:\n{user.get('message','')}"
        )
    else:
        text = (
            f"📩 Обращение #{msg_id} от {user.get('name','')} ({user.get('position','')})\n"
            f"Кому: {user.get('recipient','')}\n"
            f"Тип: {user.get('type','')}\n"
            f"Сообщение:\n{user.get('message','')}"
        )

    # Отправляем админам, но пропускаем чат-источник
    for admin in ADMINS:
        try:
            if admin == message.chat.id:
                logging.debug(f"Пропускаем отправку в тот же чат {admin}")
                continue
            await message.bot.send_message(admin, text)
            if file_path:
                await message.bot.send_document(admin, types.FSInputFile(file_path))
            logging.info(f"Уведомление отправлено админу {admin} для обращения #{msg_id}")
        except Exception as e:
            logging.error(f"Ошибка при отправке админу {admin}: {e}")

    # очистка состояния и истории
    await state.clear()
    await state.update_data(history=[])

    await message.answer("✅ Спасибо! Ваше сообщение отправлено.", reply_markup=main_menu())


@router.message(F.text == "📂 Мои обращения")
async def show_my_requests(message: Message):
    rows = get_user_messages(message.from_user.id)
    if not rows:
        await message.answer("У вас пока нет сохранённых обращений.")
    else:
        result = []
        for r in rows:
            entry = f"🆔#{r[0]} | Тип: {r[1]} | Статус: {r[3]}\n📨 {r[2]}"
            if r[4]:
                entry += f"\n📬 Ответ: {r[4]}"
            result.append(entry)
        await message.answer("\n\n".join(result))
