from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from config import TOKEN, WEBHOOK_URL, WEBHOOK_SECRET
from database import init_db
from handlers import router as user_router
from admin import router as admin_router

# Проверка необходимых переменных окружения
if not all([TOKEN, WEBHOOK_URL, WEBHOOK_SECRET]):
    raise ValueError("❌ Не заданы необходимые переменные окружения: BOT_TOKEN, WEBHOOK_URL, WEBHOOK_SECRET")

# Инициализация бота и диспетчера
bot = Bot(token=TOKEN)
dp = Dispatcher()
dp.include_router(user_router)
dp.include_router(admin_router)
init_db()

# Установка webhook при старте
async def on_startup(app: web.Application):
    webhook_url = f"{WEBHOOK_URL}/webhook/{WEBHOOK_SECRET}"
    try:
        await bot.set_webhook(webhook_url)
        print(f"✅ Webhook установлен: {webhook_url}")
    except Exception as e:
        print(f"❌ Ошибка при установке webhook: {e}")

# Удаление webhook при остановке
async def on_shutdown(app: web.Application):
    await bot.delete_webhook()
    print("🔻 Webhook удалён")

# Эндпоинт для healthcheck
async def healthcheck(request):
    return web.Response(text="OK")

# Создание и запуск aiohttp-приложения
def create_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/health", healthcheck)

    # Webhook handler
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
