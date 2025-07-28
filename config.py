import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
ADMINS = os.getenv("ADMINS")
MANAGERS = [
    "Бенецкая Наталия",
    "Немов Павел",
    "Заславец Егор",
    "Прутникова Елена",
    "Буйнов Сергей",
    "Сивильдина Елена",
    "Асташкин Павел",
    "Сидоров Владислав",
    "Звиденцева Ольга"
]
