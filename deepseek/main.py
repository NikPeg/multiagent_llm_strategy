import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from handlers import register_handlers

def main():
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(levelname)s %(name)s: %(message)s'
    )
    logger = logging.getLogger(__name__)

    # Создаём бота и диспетчер с новым способом установки parse_mode
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties()
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Регистрируем все хендлеры
    register_handlers(dp)

    logger.info("Бот запущен")
    asyncio.run(dp.start_polling(bot))


if __name__ == "__main__":
    main()
