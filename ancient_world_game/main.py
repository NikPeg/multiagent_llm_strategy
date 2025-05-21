import asyncio
import logging
import sys
from aiogram import executor
import os
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

# Настраиваем логирование
from utils.logger import setup_logger
setup_logger()
logger = logging.getLogger(__name__)

# Импортируем конфигурацию и экземпляр бота
from config import (
    BOT_TOKEN,
    WEBHOOK_URL,
    WEBHOOK_PATH,
    WEBAPP_HOST,
    WEBAPP_PORT
)
from bot.bot_instance import setup_bot, on_startup, on_shutdown

def main():
    """
    Основная функция для запуска бота
    """
    logger.info("Starting Ancient World Game Bot")

    # Проверяем наличие токена
    if not BOT_TOKEN:
        logger.critical("No bot token provided. Please set BOT_TOKEN in .env file")
        return

    # Получаем экземпляры бота и диспетчера
    bot, dp = setup_bot()

    try:
        # Определяем режим запуска (webhook или polling)
        if WEBHOOK_URL:
            logger.info(f"Starting bot in webhook mode at {WEBHOOK_URL}")
            # Запускаем бота в режиме webhook
            executor.start_webhook(
                dispatcher=dp,
                webhook_path=WEBHOOK_PATH,
                on_startup=on_startup,
                on_shutdown=on_shutdown,
                skip_updates=True,
                host=WEBAPP_HOST,
                port=WEBAPP_PORT,
            )
        else:
            logger.info("Starting bot in polling mode")
            # Запускаем бота в режиме polling
            executor.start_polling(
                dispatcher=dp,
                skip_updates=True,
                on_startup=on_startup,
                on_shutdown=on_shutdown
            )
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped by user request")
    except Exception as e:
        logger.critical(f"Critical error: {e}", exc_info=True)
    finally:
        logger.info("Bot shutdown complete")

async def setup_async():
    """
    Асинхронная инициализация необходимых компонентов
    """
    try:
        # Инициализация базы данных
        from db import setup_database, create_tables
        await setup_database()
        await create_tables()
        logger.info("Database initialized successfully")

        # Инициализация ChromaDB
        from utils.chroma_manager import setup_chroma
        await setup_chroma()
        logger.info("ChromaDB initialized successfully")

        # Инициализация LLM
        from ai import setup_llm_engine
        await setup_llm_engine()
        logger.info("LLM engine initialized successfully")

        return True
    except Exception as e:
        logger.critical(f"Failed to setup async components: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    # Запускаем асинхронную инициализацию
    loop = asyncio.get_event_loop()
    setup_success = loop.run_until_complete(setup_async())

    if setup_success:
        # Запускаем бота
        main()
    else:
        logger.critical("Setup failed, bot cannot start")
        sys.exit(1)
