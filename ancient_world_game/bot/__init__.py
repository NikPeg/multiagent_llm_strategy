"""
Инициализация модуля бота, который централизует доступ ко всем компонентам бота.
Обеспечивает удобный импорт и управление компонентами бота.
"""

from .bot_instance import setup_bot, on_startup, on_shutdown

# Импорт основных компонентов для удобного доступа
from .middlewares import setup_middlewares, admin_required
from .handlers import register_all_handlers

# Функция для инициализации и настройки всего бота
async def initialize_bot(admin_ids=None):
    """
    Инициализирует и настраивает бота и все его компоненты.

    Args:
        admin_ids (list, optional): Список ID администраторов бота. По умолчанию None.

    Returns:
        tuple: (bot, dp) - экземпляры бота и диспетчера
    """
    # Получаем экземпляры бота и диспетчера
    bot, dp = setup_bot()

    # Настраиваем middlewares
    if admin_ids:
        setup_middlewares(dp, admin_ids)

    # Регистрируем все обработчики
    register_all_handlers(dp, admin_ids)

    return bot, dp

# Функции для запуска бота в разных режимах
def start_bot_polling():
    """
    Запускает бота в режиме long polling.
    """
    from aiogram import executor
    from .bot_instance import setup_bot

    # Получаем экземпляры бота и диспетчера
    _, dp = setup_bot()

    # Запускаем long polling
    executor.start_polling(
        dp,
        skip_updates=True,
        on_startup=on_startup,
        on_shutdown=on_shutdown
    )

def start_bot_webhook(webhook_url, webhook_path, webapp_host, webapp_port):
    """
    Запускает бота в режиме webhook.

    Args:
        webhook_url (str): URL для вебхука
        webhook_path (str): Путь для вебхука
        webapp_host (str): Хост для веб-приложения
        webapp_port (int): Порт для веб-приложения
    """
    from aiogram import executor
    from .bot_instance import setup_bot

    # Получаем экземпляры бота и диспетчера
    _, dp = setup_bot()

    # Запускаем webhook
    executor.start_webhook(
        dispatcher=dp,
        webhook_path=webhook_path,
        on_startup=on_startup,
        on_shutdown=on_shutdown,
        skip_updates=True,
        host=webapp_host,
        port=webapp_port,
    )

# Экспортируем основные компоненты для удобного импорта
__all__ = [
    'setup_bot',
    'on_startup',
    'on_shutdown',
    'initialize_bot',
    'start_bot_polling',
    'start_bot_webhook',
    'setup_middlewares',
    'admin_required',
    'register_all_handlers'
]
