from aiogram import Router, F, types
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
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

@router.message(Command("chat_id"))
async def chat_id(message: types.Message):
    await message.answer(f"Chat ID: {message.chat.id}")

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


@router.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await message.answer(
        "👋 Привет! Я бот для обратной связи.\n"
        "Вы можете задать вопрос, поделиться идеей или предложить улучшение.\n"
        "Выберите действие:",
        reply_markup=main_menu()
    )
    await state.clear()


@router.message(F.text == "👨‍💼 Задать вопрос руководителю")
async def choose_manager(message: Message, state: FSMContext):
    await state.update_data(user_id=message.from_user.id, type="руководитель")

    buttons = [[KeyboardButton(text=name)] for name in MANAGERS]
    await message.answer(
        "Выберите руководителя:",
        reply_markup=ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)
    )
    await state.set_state(Form.choosing_manager)


@router.message(Form.choosing_manager)
async def manager_chosen(message: Message, state: FSMContext):
    await state.update_data(recipient=message.text)
    await message.answer(
        "Введите ваше имя и фамилию или нажмите 'Анонимно'.",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="🤐 Анонимно")]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
    )
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
    await state.update_data(user_id=message.from_user.id,
                            type=type_map[message.text],
                            recipient="")

    await message.answer(
        "Введите ваше имя и фамилию или нажмите 'Анонимно'.",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="🤐 Анонимно")]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
    )
    await state.set_state(Form.entering_name)


@router.message(Form.entering_name)
async def get_name(message: Message, state: FSMContext):
    if message.text == "🤐 Анонимно":
        await state.update_data(is_anonymous=1, name="Аноним", position="Аноним")
        await message.answer("Почему вы хотите остаться анонимным?")
        await state.set_state(Form.anonymous_reason)
    else:
        await state.update_data(is_anonymous=0, name=message.text)
        await message.answer("Укажите вашу должность:")
        await state.set_state(Form.entering_position)


@router.message(Form.entering_position)
async def get_position(message: Message, state: FSMContext):
    await state.update_data(position=message.text, reason="")
    await message.answer("Введите ваше сообщение (до 1000 символов):", reply_markup=ReplyKeyboardRemove())
    await state.set_state(Form.typing_message)


@router.message(Form.anonymous_reason)
async def get_reason(message: Message, state: FSMContext):
    await state.update_data(reason=message.text)
    await message.answer("Введите ваше сообщение (до 1000 символов):", reply_markup=ReplyKeyboardRemove())
    await state.set_state(Form.typing_message)


@router.message(Form.typing_message)
async def get_message(message: Message, state: FSMContext):
    if len(message.text) > 1000:
        await message.answer("Слишком длинное сообщение. Пожалуйста, сократите до 1000 символов.")
        return
    await state.update_data(message=message.text)
    await message.answer("Если хотите, прикрепите файл (pdf, docx, xls, jpg, png) или введите 'Нет'.")
    await state.set_state(Form.uploading_file)


@router.message(Form.uploading_file)
async def handle_file_or_skip(message: Message, state: FSMContext):
    file_path = None

    try:
        # Документ (PDF, DOCX, XLSX)
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
                await message.answer("⛔ Неподдерживаемый тип файла.")
                return

        # Фото
        elif message.photo:
            largest_photo = message.photo[-1]
            file = await message.bot.get_file(largest_photo.file_id)
            file_bytes = await message.bot.download_file(file.file_path)

            path = Path("uploads") / f"{message.from_user.id}_photo.jpg"
            path.parent.mkdir(exist_ok=True)

            async with aiofiles.open(path, "wb") as f:
                await f.write(file_bytes.read())

            file_path = str(path)

        # Сообщение "Нет"
        elif message.text and message.text.strip().lower() in ["нет", "no"]:
            file_path = None

        else:
            await message.answer("Пожалуйста, прикрепите файл (pdf, docx, xls, jpg, png) или введите 'Нет'.")
            return

    except Exception as e:
        logging.error(f"Ошибка при сохранении файла: {e}")
        await message.answer("Произошла ошибка при загрузке файла.")
        return

    await state.update_data(file_path=file_path)
    user = await state.get_data()
    msg_id = insert_message(user)

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

    for admin in ADMINS:
        if int(admin) == message.chat.id:
            continue  # Не отправлять в тот же чат, откуда пришло сообщение
        await message.bot.send_message(admin, text)
        if file_path:
            await message.bot.send_document(admin, types.FSInputFile(file_path))

    await message.answer("✅ Спасибо! Ваше сообщение отправлено.", reply_markup=main_menu())
    await state.clear()


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
