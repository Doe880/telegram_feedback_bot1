import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession

from config import TOKEN, PROXY_URL
from database import init_db
from handlers import router as user_router
from admin import router as admin_router


async def main():
    if PROXY_URL:
        session = AiohttpSession(proxy=PROXY_URL)
        bot = Bot(token=TOKEN, session=session)
    else:
        bot = Bot(token=TOKEN)

    dp = Dispatcher()
    dp.include_router(user_router)
    dp.include_router(admin_router)

    init_db()

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
