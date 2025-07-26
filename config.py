import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
ADMINS = list(map(int, os.getenv("ADMINS", "").split(",")))
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
