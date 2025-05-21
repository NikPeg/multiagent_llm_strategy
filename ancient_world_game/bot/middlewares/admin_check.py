from aiogram import types
from aiogram.dispatcher.middlewares import BaseMiddleware
from aiogram.dispatcher.handler import CancelHandler, current_handler
from aiogram.utils.exceptions import Throttled
import logging

from storage import get_user_by_telegram_id

class AdminCheckMiddleware(BaseMiddleware):
    """
    Middleware для проверки прав администратора

    Проверяет, имеет ли пользователь права администратора для
    выполнения защищенных команд и функций. Блокирует доступ для
    неавторизованных пользователей.
    """

    def __init__(self, admin_ids: list):
        """
        Инициализирует middleware

        Args:
            admin_ids (list): Список Telegram ID администраторов
        """
        super(AdminCheckMiddleware, self).__init__()
        self.admin_ids = admin_ids

        # Логируем информацию о загрузке middleware
        logging.info(f"AdminCheckMiddleware initialized with {len(admin_ids)} admins")

    async def on_pre_process_message(self, message: types.Message, data: dict):
        """
        Проверяет права администратора перед обработкой сообщения

        Args:
            message (types.Message): Входящее сообщение
            data (dict): Данные обработчика
        """
        # Получаем текущий обработчик
        handler = current_handler.get()

        # Если обработчик не задан, просто пропускаем middleware
        if handler is None:
            return

        # Проверяем, требует ли обработчик прав администратора
        requires_admin = getattr(handler, 'requires_admin', False)

        if requires_admin:
            user_id = message.from_user.id

            # Проверяем, является ли пользователь администратором
            if user_id not in self.admin_ids:
                # Проверяем дополнительно в базе данных, возможно права были добавлены динамически
                user = await get_user_by_telegram_id(user_id)
                if not user or not user.get('is_admin', False):
                    # Логируем попытку несанкционированного доступа
                    logging.warning(f"User {user_id} tried to access admin command: {message.text}")

                    # Сообщаем пользователю об отсутствии прав
                    await message.reply(
                        "У вас нет прав администратора для выполнения этой команды."
                    )

                    # Отменяем дальнейшую обработку сообщения
                    raise CancelHandler()
                else:
                    # Добавляем пользователя в список администраторов, если он есть в базе
                    self.admin_ids.append(user_id)
                    logging.info(f"User {user_id} added to admin list from database")

    async def on_pre_process_callback_query(self, callback_query: types.CallbackQuery, data: dict):
        """
        Проверяет права администратора перед обработкой callback-запроса

        Args:
            callback_query (types.CallbackQuery): Входящий callback-запрос
            data (dict): Данные обработчика
        """
        # Получаем текущий обработчик
        handler = current_handler.get()

        # Если обработчик не задан, просто пропускаем middleware
        if handler is None:
            return

        # Проверяем, требует ли обработчик прав администратора
        requires_admin = getattr(handler, 'requires_admin', False)

        if requires_admin:
            user_id = callback_query.from_user.id

            # Проверяем, является ли пользователь администратором
            if user_id not in self.admin_ids:
                # Проверяем дополнительно в базе данных
                user = await get_user_by_telegram_id(user_id)
                if not user or not user.get('is_admin', False):
                    # Логируем попытку несанкционированного доступа
                    logging.warning(f"User {user_id} tried to access admin callback: {callback_query.data}")

                    # Сообщаем пользователю об отсутствии прав
                    await callback_query.answer("У вас нет прав администратора", show_alert=True)

                    # Отменяем дальнейшую обработку callback-запроса
                    raise CancelHandler()
                else:
                    # Добавляем пользователя в список администраторов, если он есть в базе
                    self.admin_ids.append(user_id)
                    logging.info(f"User {user_id} added to admin list from database")

# Декоратор для обозначения функций, требующих права администратора
def admin_required(func):
    """
    Декоратор для функций, требующих права администратора

    Args:
        func: Декорируемая функция

    Returns:
        function: Декорированная функция с установленным флагом requires_admin
    """
    setattr(func, 'requires_admin', True)
    return func
