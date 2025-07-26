import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")

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
