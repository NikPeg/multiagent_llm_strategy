"""
throttling.py - Middleware для защиты от спама и ограничения частоты запросов.
Предотвращает флуд запросами и обеспечивает стабильную работу бота.
"""

import asyncio
from typing import Dict, Union, Optional
from aiogram import types, Dispatcher
from aiogram.dispatcher.handler import CancelHandler, current_handler
from aiogram.dispatcher.middlewares import BaseMiddleware
from aiogram.utils.exceptions import Throttled

from utils.logger import get_logger

logger = get_logger(__name__)


class ThrottlingMiddleware(BaseMiddleware):
    """
    Middleware для ограничения частоты запросов к боту (anti-flood).

    Позволяет контролировать количество запросов от пользователя в единицу времени,
    блокируя слишком частые запросы и предотвращая спам.
    """

    def __init__(self, limit: float = 0.5, key_prefix: str = 'antiflood_'):
        """
        Инициализирует middleware с указанными параметрами.

        Args:
            limit (float): Минимальный интервал между запросами (в секундах)
            key_prefix (str): Префикс для ключей в хранилище состояний
        """
        self.rate_limit = limit
        self.prefix = key_prefix
        super(ThrottlingMiddleware, self).__init__()

    async def on_process_message(self, message: types.Message, data: Dict):
        """
        Вызывается при обработке сообщения.

        Args:
            message (types.Message): Входящее сообщение
            data (Dict): Данные хендлера
        """
        # Получаем текущий хендлер
        handler = current_handler.get()

        # Получаем диспетчер из контекста
        dispatcher = Dispatcher.get_current()

        # Если хендлер не установлен, используем дефолтный лимит
        if handler:
            limit = getattr(handler, 'throttling_rate_limit', self.rate_limit)
            key = getattr(handler, 'throttling_key', f"{self.prefix}_{handler.__name__}")
        else:
            limit = self.rate_limit
            key = f"{self.prefix}_message"

        # Пытаемся применить троттлинг
        try:
            await dispatcher.throttle(key, rate=limit)
        except Throttled as t:
            # Сообщаем пользователю только при первом превышении лимита
            await self.message_throttled(message, t)

            # Отменяем обработку сообщения
            raise CancelHandler()

    async def on_process_callback_query(self, callback_query: types.CallbackQuery, data: Dict):
        """
        Вызывается при обработке callback запроса.

        Args:
            callback_query (types.CallbackQuery): Входящий callback запрос
            data (Dict): Данные хендлера
        """
        # Получаем текущий хендлер
        handler = current_handler.get()

        # Получаем диспетчер из контекста
        dispatcher = Dispatcher.get_current()

        # Если хендлер не установлен, используем дефолтный лимит
        if handler:
            limit = getattr(handler, 'throttling_rate_limit', self.rate_limit)
            key = getattr(handler, 'throttling_key', f"{self.prefix}_{handler.__name__}")
        else:
            limit = self.rate_limit
            key = f"{self.prefix}_callback"

        # Пытаемся применить троттлинг
        try:
            await dispatcher.throttle(key, rate=limit)
        except Throttled as t:
            # Отвечаем на callback запрос
            await callback_query.answer('Слишком много запросов! Пожалуйста, подождите.', show_alert=True)

            # Логируем информацию о троттлинге
            logger.info(f"Throttled callback {callback_query.data} from user {callback_query.from_user.id}")

            # Отменяем обработку callback запроса
            raise CancelHandler()

    async def message_throttled(self, message: types.Message, throttled: Throttled):
        """
        Уведомляет пользователя о превышении лимита запросов.

        Args:
            message (types.Message): Сообщение, вызвавшее превышение
            throttled (Throttled): Информация о превышении
        """
        # Рассчитываем, сколько времени осталось до снятия ограничения
        delta = throttled.rate - throttled.delta

        # Логируем информацию о троттлинге
        logger.info(f"Throttled message from user {message.from_user.id}, {delta:.2f}s remaining")

        # Отправляем уведомление только один раз при первом превышении
        if throttled.exceeded_count <= 2:
            await message.reply('Слишком много запросов! Пожалуйста, не спамьте.')

        # Делаем паузу на время троттлинга
        await asyncio.sleep(delta)


# Декоратор для настройки ограничения скорости для определенных хендлеров
def rate_limit(limit: float, key: Optional[str] = None):
    """
    Декоратор для установки ограничения частоты вызовов обработчика.

    Args:
        limit (float): Минимальный интервал между вызовами обработчика (в секундах)
        key (Optional[str]): Ключ для хранения состояния троттлинга

    Returns:
        Декоратор, устанавливающий ограничение скорости для обработчика
    """
    def decorator(func):
        setattr(func, 'throttling_rate_limit', limit)
        if key:
            setattr(func, 'throttling_key', key)
        return func
    return decorator
