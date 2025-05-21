from aiogram import Dispatcher
from .admin_check import AdminCheckMiddleware, admin_required
from .throttling import ThrottlingMiddleware
from .action_logger import ActionLoggerMiddleware
from .user_activity import UserActivityMiddleware

def setup_middlewares(dp: Dispatcher, admin_ids: list):
    """
    Настраивает и регистрирует все middleware в диспетчере

    Args:
        dp (Dispatcher): Диспетчер бота
        admin_ids (list): Список ID администраторов
    """
    # Настройка middleware для проверки прав администратора
    admin_middleware = AdminCheckMiddleware(admin_ids)
    dp.middleware.setup(admin_middleware)

    # Настройка middleware для защиты от спама (троттлинг)
    throttling_middleware = ThrottlingMiddleware(limit=0.5)  # 0.5 секунд между сообщениями
    dp.middleware.setup(throttling_middleware)

# Экспортируем декоратор для удобного импорта
__all__ = [
    'admin_required',
    'setup_middlewares'
]
