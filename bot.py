import asyncio
from aiogram import Bot, Dispatcher
from config import TOKEN
from database import init_db
from handlers import router as user_router
from admin import router as admin_router


async def main():
    bot = Bot(token=TOKEN)
    dp = Dispatcher()
    dp.include_router(user_router)
    dp.include_router(admin_router)
    init_db()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
