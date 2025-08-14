# handlers.py
from aiogram import Router, F, types
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from config import ADMINS, MANAGERS
from database import insert_message, get_user_messages
from utils import save_file
import logging

router = Router()
logging.basicConfig(level=logging.INFO)

BACK_TEXT = "⬅ Назад"
BACK_BTN = KeyboardButton(text=BACK_TEXT)
SKIP_TEXT = "❌ Нет"  # Кнопка «Нет» для шага загрузки файла
SKIP_BTN = KeyboardButton(text=SKIP_TEXT)
HELP_TEXT = "❓ Помощь"
HELP_BTN = KeyboardButton(text=HELP_TEXT)


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
            [KeyboardButton(text="📂 Мои обращения")],
            [HELP_BTN],
        ],
        resize_keyboard=True
    )


HELP_MESSAGE = (
    "🆘 *Как пользоваться ботом*\n\n"
    "1) В главном меню выберите нужное действие:\n"
    " • *Задать вопрос руководителю* — появится список имён, выберите получателя.\n"
    " • *Общий вопрос* — обращение без конкретного получателя.\n"
    " • *Написать генеральному директору* — обращение лично директору (анонимность недоступна).\n"
    " • *Предложить идею* — отправьте предложение по улучшению.\n"
    " • *Мои обращения* — посмотрить статусы и ответы по вашим заявкам.\n\n"
    "2) Далее бот попросит указать *имя и должность*, либо вы можете выбрать *«🤐 Анонимно»* (кроме обращения директору).\n"
    "   Если анонимно — кратко укажите причину.\n\n"
    "3) Напишите текст сообщения (до 1000 символов).\n\n"
    "4) Прикрепите файл (по желанию) или нажмите кнопку *«❌ Нет»*.\n\n"
    "5) Нажимайте *«⬅ Назад»*, чтобы вернуться на предыдущий шаг.\n\n"
    "_Если вы отправили произвольный текст вне сценария — бот вернёт вас к нужному шагу и подскажет что делать._"
)


# --- История для «Назад» ---------------------------------------------------
async def push_history(state: FSMContext):
    current = await state.get_state()
    if not current:
        return
    data = await state.get_data()
    history = data.get("history", [])
    if not history or history[-1] != current:
        history.append(current)
        await state.update_data(history=history)


async def pop_previous(state: FSMContext):
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


@router.message(Command("help"))
@router.message(F.text == HELP_TEXT)
async def show_help(message: Message):
    await message.answer(HELP_MESSAGE, parse_mode="Markdown", reply_markup=main_menu())


# Универсальный «Назад»
@router.message(F.text == BACK_TEXT)
async def go_back(message: Message, state: FSMContext):
    prev = await pop_previous(state)
    if not prev:
        await state.clear()
        await state.update_data(history=[])
        await message.answer("Вы вернулись в главное меню.", reply_markup=main_menu())
        return

    await state.set_state(prev)
    state_name = prev.split(":")[-1] if ":" in prev else prev

    if state_name == "choosing_manager":
        buttons = [[KeyboardButton(text=name)] for name in MANAGERS]
        kb = ReplyKeyboardMarkup(keyboard=buttons + [[BACK_BTN]], resize_keyboard=True, one_time_keyboard=True)
        await message.answer("Выберите руководителя:", reply_markup=kb)
    elif state_name == "entering_name":
        # Определим тип, чтобы понять, разрешать ли анонимность
        data = await state.get_data()
        if data.get("type") == "директор":
            kb = ReplyKeyboardMarkup(keyboard=[[BACK_BTN]], resize_keyboard=True, one_time_keyboard=True)
            await message.answer("Введите ваше имя и фамилию:", reply_markup=kb)
        else:
            kb = ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="🤐 Анонимно")], [BACK_BTN]],
                resize_keyboard=True,
                one_time_keyboard=True
            )
            await message.answer("Введите ваше имя и фамилию или нажмите 'Анонимно'.", reply_markup=kb)
    elif state_name == "entering_position":
        await message.answer("Укажите вашу должность:",
                             reply_markup=ReplyKeyboardMarkup(keyboard=[[BACK_BTN]], resize_keyboard=True))
    elif state_name == "anonymous_reason":
        await message.answer("Почему вы хотите остаться анонимным?",
                             reply_markup=ReplyKeyboardMarkup(keyboard=[[BACK_BTN]], resize_keyboard=True))
    elif state_name == "typing_message":
        await message.answer("Введите ваше сообщение (до 1000 символов):",
                             reply_markup=ReplyKeyboardMarkup(keyboard=[[BACK_BTN]], resize_keyboard=True))
    elif state_name == "uploading_file":
        kb = ReplyKeyboardMarkup(keyboard=[[SKIP_BTN], [BACK_BTN]], resize_keyboard=True)
        await message.answer("Если хотите, прикрепите файл (pdf, docx, xls, jpg, png) или нажмите «❌ Нет».",
                             reply_markup=kb)
    else:
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
    await state.update_data(user_id=message.from_user.id, type="руководитель")
    await push_history(state)

    buttons = [[KeyboardButton(text=name)] for name in MANAGERS]
    kb = ReplyKeyboardMarkup(keyboard=buttons + [[BACK_BTN]], resize_keyboard=True, one_time_keyboard=True)
    await message.answer("Выберите руководителя:", reply_markup=kb)
    await state.set_state(Form.choosing_manager)


@router.message(Form.choosing_manager)
async def manager_chosen(message: Message, state: FSMContext):
    # Проверяем, что выбран из списка
    if message.text not in MANAGERS:
        buttons = [[KeyboardButton(text=name)] for name in MANAGERS]
        kb = ReplyKeyboardMarkup(keyboard=buttons + [[BACK_BTN]], resize_keyboard=True, one_time_keyboard=True)
        await message.answer("Пожалуйста, выберите руководителя из списка кнопок ниже.", reply_markup=kb)
        return

    await push_history(state)
    await state.update_data(recipient=message.text)

    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🤐 Анонимно")], [BACK_BTN]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer("Введите ваше имя и фамилию или нажмите 'Анонимно'.", reply_markup=kb)
    await state.set_state(Form.entering_name)


@router.message(F.text.in_({"📢 Общий вопрос", "📝 Написать генеральному директору", "💡 Предложить идею"}))
async def choose_type(message: Message, state: FSMContext):
    type_map = {
        "📢 Общий вопрос": "общий",
        "📝 Написать генеральному директору": "директор",
        "💡 Предложить идею": "идея"
    }
    msg_type = type_map[message.text]
    await state.update_data(user_id=message.from_user.id, type=msg_type, recipient="")
    await push_history(state)

    if msg_type == "директор":
        # Без анонимности
        kb = ReplyKeyboardMarkup(keyboard=[[BACK_BTN]], resize_keyboard=True, one_time_keyboard=True)
        await message.answer("Введите ваше имя и фамилию:", reply_markup=kb)
    else:
        kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="🤐 Анонимно")], [BACK_BTN]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        await message.answer("Введите ваше имя и фамилию или нажмите 'Анонимно'.", reply_markup=kb)

    await state.set_state(Form.entering_name)


@router.message(Form.entering_name)
async def get_name(message: Message, state: FSMContext):
    await push_history(state)
    text = message.text

    data = await state.get_data()
    msg_type = data.get("type")

    # Если выбрали «директор», а пользователь пытается нажать «Анонимно» — запрещаем
    if msg_type == "директор" and text == "🤐 Анонимно":
        kb = ReplyKeyboardMarkup(keyboard=[[BACK_BTN]], resize_keyboard=True, one_time_keyboard=True)
        await message.answer("Анонимность недоступна для обращения к генеральному директору. Введите имя и фамилию:",
                             reply_markup=kb)
        return

    if text == "🤐 Анонимно":
        await state.update_data(is_anonymous=1, name="Аноним", position="Аноним")
        await message.answer("Почему вы хотите остаться анонимным?",
                             reply_markup=ReplyKeyboardMarkup(keyboard=[[BACK_BTN]], resize_keyboard=True))
        await state.set_state(Form.anonymous_reason)
    else:
        await state.update_data(is_anonymous=0, name=text)
        await message.answer("Укажите вашу должность:",
                             reply_markup=ReplyKeyboardMarkup(keyboard=[[BACK_BTN]], resize_keyboard=True))
        await state.set_state(Form.entering_position)


@router.message(Form.entering_position)
async def get_position(message: Message, state: FSMContext):
    await push_history(state)
    await state.update_data(position=message.text, reason="")
    await message.answer("Введите ваше сообщение (до 1000 символов):",
                         reply_markup=ReplyKeyboardMarkup(keyboard=[[BACK_BTN]], resize_keyboard=True))
    await state.set_state(Form.typing_message)


@router.message(Form.anonymous_reason)
async def get_reason(message: Message, state: FSMContext):
    await push_history(state)
    await state.update_data(reason=message.text)
    await message.answer("Введите ваше сообщение (до 1000 символов):",
                         reply_markup=ReplyKeyboardMarkup(keyboard=[[BACK_BTN]], resize_keyboard=True))
    await state.set_state(Form.typing_message)


@router.message(Form.typing_message)
async def get_message(message: Message, state: FSMContext):
    await push_history(state)
    if len(message.text) > 1000:
        await message.answer("Слишком длинное сообщение. Пожалуйста, сократите до 1000 символов.")
        return
    await state.update_data(message=message.text)

    # Предлагаем: либо прислать файл, либо нажать «❌ Нет»
    kb = ReplyKeyboardMarkup(keyboard=[[SKIP_BTN], [BACK_BTN]], resize_keyboard=True)
    await message.answer(
        "Если хотите, прикрепите файл (pdf, docx, xls, jpg, png) или нажмите «❌ Нет».",
        reply_markup=kb
    )
    await state.set_state(Form.uploading_file)


@router.message(Form.uploading_file)
async def handle_file_or_skip(message: Message, state: FSMContext):
    file_path = None

    try:
        # Документ или фото — единая функция save_file
        if message.document or message.photo:
            file_path = await save_file(message)
        elif message.text and message.text.strip().lower() in ["нет", "no", SKIP_TEXT.lower(), "❌ нет"]:
            file_path = None
        else:
            kb = ReplyKeyboardMarkup(keyboard=[[SKIP_BTN], [BACK_BTN]], resize_keyboard=True)
            await message.answer(
                "Пожалуйста, прикрепите файл (pdf, docx, xls, jpg, png) или нажмите «❌ Нет».",
                reply_markup=kb
            )
            return
    except Exception as e:
        logging.error(f"Ошибка при сохранении файла: {e}")
        kb = ReplyKeyboardMarkup(keyboard=[[SKIP_BTN], [BACK_BTN]], resize_keyboard=True)
        await message.answer("Произошла ошибка при загрузке файла.", reply_markup=kb)
        return

    await state.update_data(file_path=file_path)
    user = await state.get_data()
    msg_id = insert_message(user)

    # Текст уведомления админам
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

    # Отправляем админам, но не в тот же чат, откуда пришло
    for admin in ADMINS:
        try:
            if admin == message.chat.id:
                continue
            await message.bot.send_message(admin, text)
            if file_path:
                await message.bot.send_document(admin, types.FSInputFile(file_path))
        except Exception as e:
            logging.error(f"Ошибка при отправке админу {admin}: {e}")

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


# --- «Левый» текст: мягко возвращаем в нужный шаг / меню -------------------
@router.message(F.text & ~F.text.startswith("/"))
async def fallback_text(message: Message, state: FSMContext):
    current = await state.get_state()
    if current:
        # Пользователь в сценарии, подскажем что делать дальше
        state_name = current.split(":")[-1]
        if state_name == "choosing_manager":
            buttons = [[KeyboardButton(text=name)] for name in MANAGERS]
            kb = ReplyKeyboardMarkup(keyboard=buttons + [[BACK_BTN]], resize_keyboard=True, one_time_keyboard=True)
            await message.answer("Пожалуйста, выберите руководителя из списка кнопок ниже.", reply_markup=kb)
            return
        elif state_name == "entering_name":
            data = await state.get_data()
            if data.get("type") == "директор":
                kb = ReplyKeyboardMarkup(keyboard=[[BACK_BTN]], resize_keyboard=True, one_time_keyboard=True)
                await message.answer("Введите ваше имя и фамилию (анонимность недоступна):", reply_markup=kb)
            else:
                kb = ReplyKeyboardMarkup(
                    keyboard=[[KeyboardButton(text="🤐 Анонимно")], [BACK_BTN]],
                    resize_keyboard=True,
                    one_time_keyboard=True
                )
                await message.answer("Введите ваше имя и фамилию или нажмите 'Анонимно'.", reply_markup=kb)
            return
        elif state_name == "entering_position":
            kb = ReplyKeyboardMarkup(keyboard=[[BACK_BTN]], resize_keyboard=True)
            await message.answer("Укажите вашу должность:", reply_markup=kb)
            return
        elif state_name == "anonymous_reason":
            kb = ReplyKeyboardMarkup(keyboard=[[BACK_BTN]], resize_keyboard=True)
            await message.answer("Почему вы хотите остаться анонимным?", reply_markup=kb)
            return
        elif state_name == "typing_message":
            kb = ReplyKeyboardMarkup(keyboard=[[BACK_BTN]], resize_keyboard=True)
            await message.answer("Введите ваше сообщение (до 1000 символов):", reply_markup=kb)
            return
        elif state_name == "uploading_file":
            kb = ReplyKeyboardMarkup(keyboard=[[SKIP_BTN], [BACK_BTN]], resize_keyboard=True)
            await message.answer(
                "Прикрепите файл (pdf, docx, xls, jpg, png) или нажмите «❌ Нет».",
                reply_markup=kb
            )
            return

    # Не в сценарии — покажем помощь и меню
    await message.answer(
        "Я не понял сообщение. Пожалуйста, выберите действие в меню или откройте помощь:",
        reply_markup=main_menu()
    )
