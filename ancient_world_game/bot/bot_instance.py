import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.contrib.middlewares.logging import LoggingMiddleware

from config.config import BOT_TOKEN, ADMIN_IDS
from .middlewares import setup_middlewares
from .handlers import register_all_handlers
from storage import setup_database, create_tables, check_database_connection
from utils.logger import setup_logger

# Настройка логгера
logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN, parse_mode=types.ParseMode.HTML)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Словарь, сопоставляющий имена функций с их объектами
handler_functions = {}

async def on_startup(dp: Dispatcher):
    """
    Выполняется при запуске бота

    Args:
        dp (Dispatcher): Диспетчер бота
    """
    # Настройка логгера
    setup_logger()
    logger.info("Bot starting...")

    # Настройка базы данных
    try:
        await setup_database()
        await create_tables()
        if await check_database_connection():
            logger.info("Database connection successful")
        else:
            logger.error("Database connection failed")
            return
    except Exception as e:
        logger.error(f"Database initialization error: {str(e)}")
        return

    # Регистрация хендлеров
    register_all_handlers(dp, ADMIN_IDS)
    logger.info("Handlers registered")

    # Настройка middlewares
    setup_middlewares(dp, ADMIN_IDS)
    logger.info("Middlewares set up")

    # Уведомление администраторов о запуске бота
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                "🔄 Бот запущен и готов к работе!\n\n"
                f"Версия: 1.0.0\n"
                f"Время запуска: {asyncio.get_event_loop().time()}"
            )
        except Exception as e:
            logger.error(f"Failed to notify admin {admin_id}: {str(e)}")

    logger.info("Bot started successfully")

async def on_shutdown(dp: Dispatcher):
    """
    Выполняется при завершении работы бота

    Args:
        dp (Dispatcher): Диспетчер бота
    """
    logger.info("Bot shutting down...")

    # Уведомление администраторов о завершении работы бота
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                "🛑 Бот завершает работу. Обслуживание или перезапуск."
            )
        except Exception as e:
            logger.error(f"Failed to notify admin {admin_id} about shutdown: {str(e)}")

    # Закрытие соединений с базой данных и другие операции очистки
    # Здесь должен быть код закрытия соединений

    # Закрытие хранилища состояний
    await dp.storage.close()
    await dp.storage.wait_closed()
    logger.info("Storage closed")

    logger.info("Bot shutdown complete")

def setup_bot():
    """
    Настраивает и возвращает экземпляр бота и диспетчера

    Returns:
        tuple: (Bot, Dispatcher) - настроенные экземпляры бота и диспетчера
    """
    # Добавляем логирующий middleware
    dp.middleware.setup(LoggingMiddleware())

    # Устанавливаем обработчики запуска и остановки
    dp.register_on_startup(on_startup)
    dp.register_on_shutdown(on_shutdown)

    return bot, dp

def start_polling():
    """
    Запускает бота в режиме long polling
    """
    logger.info("Starting bot in polling mode")
    from aiogram import executor

    # Настраиваем бота
    _, dispatcher = setup_bot()

    # Запускаем long polling
    executor.start_polling(
        dispatcher,
        skip_updates=True,
        on_startup=on_startup,
        on_shutdown=on_shutdown
    )


# Если файл запущен как основной, запускаем бота
if __name__ == "__main__":
    # Выбираем режим работы в зависимости от настроек
    start_polling()
