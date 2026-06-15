import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
PROXY_URL = os.getenv("PROXY_URL")
ADMINS = [int(x) for x in os.getenv("ADMINS", "").split(",") if x.strip()]
MANAGERS = [
    "Бенецкая Наталия",
    "Немов Павел",
    "Заславец Егор",
    "Прутникова Елена",
    "Буйнов Сергей",
    "Сивильдина Елена",
    "Асташкин Павел",
    "Сидоров Владислав",
    "Звиденцева Ольга",
    "Лукьянчук Татьяна",
    "Курдюмова Мария/Новосельцева Наталья"
]
