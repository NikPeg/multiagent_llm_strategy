import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from handlers import register_handlers

# Настройка логов
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    # Создаем бота и диспетчер
    bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
    dp = Dispatcher(storage=MemoryStorage())

    # Регистрируем все хендлеры
    register_handlers(dp)

    # Запуск поллинга
    logger.info("Бот запущен")
    asyncio.run(dp.start_polling(bot))


if __name__ == "__main__":
    main()
