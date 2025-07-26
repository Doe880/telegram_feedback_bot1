import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from config import TOKEN, WEBHOOK_URL, WEBHOOK_SECRET
from database import init_db
from handlers import router as user_router
from admin import router as admin_router

bot = Bot(token=TOKEN)
dp = Dispatcher()
dp.include_router(user_router)
dp.include_router(admin_router)
init_db()

async def on_startup(app: web.Application):
    webhook_url = f"{WEBHOOK_URL}/webhook/{WEBHOOK_SECRET}"
    await bot.set_webhook(webhook_url)
    print(f"Webhook установлен: {webhook_url}")

async def on_shutdown(app: web.Application):
    await bot.delete_webhook()
    print("Webhook удалён")

async def healthcheck(request):
    return web.Response(text="OK")

def create_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/health", healthcheck)

    # Настраиваем webhook обработчик
    SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=WEBHOOK_SECRET
    ).register(app, path=f"/webhook/{WEBHOOK_SECRET}")

    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)

    setup_application(app, dp, bot=bot)
    return app

if __name__ == "__main__":
    web.run_app(create_app(), host="0.0.0.0", port=8080)
