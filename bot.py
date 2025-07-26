import asyncio
from aiogram import Bot, Dispatcher
from config import TOKEN
from database import init_db
from handlers import router as user_router
from admin import router as admin_router
from aiohttp import web

async def start_bot():
    bot = Bot(token=TOKEN)
    dp = Dispatcher()
    dp.include_router(user_router)
    dp.include_router(admin_router)
    init_db()
    await dp.start_polling(bot)

async def healthcheck(_):
    return web.Response(text="OK")

async def run_webapp():
    app = web.Application()
    app.add_routes([web.get('/health', healthcheck)])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    print("Web server started on port 8080")

async def main():
    # Запускаем одновременно бота и web-сервер
    await asyncio.gather(
        start_bot(),
        run_webapp()
    )

if __name__ == "__main__":
    asyncio.run(main())


