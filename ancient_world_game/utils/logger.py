"""
logger.py - Модуль для настройки и управления логированием в системе.
"""

import logging
import os
from datetime import datetime
from typing import Optional, Union, Dict, Any
import json
import traceback
from functools import wraps
import inspect
import sys

# Настройка базового логгера
logger = logging.getLogger('ancient_world_game')

# Цветовые коды для различных уровней логгирования в консоли
COLORS = {
    'DEBUG': '\033[94m',  # Синий
    'INFO': '\033[92m',   # Зеленый
    'WARNING': '\033[93m', # Желтый
    'ERROR': '\033[91m',  # Красный
    'CRITICAL': '\033[91m\033[1m', # Жирный красный
    'RESET': '\033[0m'    # Сброс цвета
}


class ColoredFormatter(logging.Formatter):
    """Форматтер, добавляющий цвета в логи для консоли."""

    def format(self, record):
        log_message = super().format(record)
        level_name = record.levelname
        if level_name in COLORS:
            return f"{COLORS[level_name]}{log_message}{COLORS['RESET']}"
        return log_message


def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None,
                  enable_console: bool = True) -> None:
    """
    Настраивает систему логирования с выводом в консоль и/или файл.

    Args:
        log_level: Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Путь к файлу для записи логов. Если None, логи в файл не пишутся
        enable_console: Включить вывод логов в консоль
    """
    # Преобразуем строковый уровень в константу logging
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    logger.setLevel(numeric_level)

    # Очистим существующие обработчики
    logger.handlers = []

    # Формат для записи в лог
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'

    # Настройка вывода в консоль, если требуется
    if enable_console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(numeric_level)
        # Используем цветной форматтер для консоли
        colored_formatter = ColoredFormatter(log_format, datefmt=date_format)
        console_handler.setFormatter(colored_formatter)
        logger.addHandler(console_handler)

    # Настройка вывода в файл, если указан путь
    if log_file:
        # Создаем директорию для логов, если она не существует
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)

        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(numeric_level)
        file_formatter = logging.Formatter(log_format, datefmt=date_format)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    logger.info(f"Логирование настроено с уровнем {log_level}")


def log_function_call(func):
    """
    Декоратор для логирования вызовов функций с их аргументами.

    Args:
        func: Декорируемая функция

    Returns:
        Обертка, логирующая вызов функции
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        func_args = inspect.signature(func).bind(*args, **kwargs).arguments
        # Удаляем большие объекты и объекты, которые нельзя сериализовать
        safe_args = {}
        for arg_name, arg_value in func_args.items():
            # Пропускаем self и cls для методов классов
            if arg_name in ('self', 'cls'):
                continue
            try:
                # Проверяем, можно ли сериализовать значение в JSON
                json.dumps(str(arg_value)[:100])
                safe_args[arg_name] = str(arg_value)[:100] + ('...' if len(str(arg_value)) > 100 else '')
            except (TypeError, OverflowError):
                safe_args[arg_name] = f"<non-serializable: {type(arg_value).__name__}>"

        logger.debug(f"Вызов функции {func.__name__} с аргументами: {safe_args}")
        try:
            result = func(*args, **kwargs)
            return result
        except Exception as e:
            logger.error(f"Ошибка в функции {func.__name__}: {str(e)}")
            logger.debug(f"Трейсбек: {traceback.format_exc()}")
            raise
    return wrapper


def log_bot_message(user_id: Union[int, str], message_text: str, is_outgoing: bool = False) -> None:
    """
    Логирует сообщение бота пользователю или наоборот.

    Args:
        user_id: ID пользователя
        message_text: Текст сообщения
        is_outgoing: True если сообщение от бота пользователю, False если от пользователя боту
    """
    direction = "-> пользователю" if is_outgoing else "от пользователя"
    # Обрезаем слишком длинные сообщения в логе
    if len(message_text) > 500:
        message_text = message_text[:500] + "..."

    logger.info(f"Сообщение {direction} {user_id}: {message_text}")


def log_admin_action(admin_id: Union[int, str], action: str, details: Optional[Dict[str, Any]] = None) -> None:
    """
    Логирует действия администратора.

    Args:
        admin_id: ID администратора
        action: Описание действия
        details: Дополнительные детали действия (опционально)
    """
    details_str = ""
    if details:
        try:
            details_str = f", детали: {json.dumps(details, ensure_ascii=False)}"
        except (TypeError, OverflowError):
            details_str = f", детали: {str(details)}"

    logger.info(f"Админ {admin_id}: {action}{details_str}")


def log_game_event(country_name: str, event_type: str, description: str) -> None:
    """
    Логирует игровое событие.

    Args:
        country_name: Название страны
        event_type: Тип события (например, 'war', 'disaster', 'project_completed')
        description: Описание события
    """
    logger.info(f"Игровое событие [{event_type}] в стране {country_name}: {description}")


def log_error(error_message: str, exception: Optional[Exception] = None) -> None:
    """
    Логирует ошибку с опциональным выводом исключения.

    Args:
        error_message: Сообщение об ошибке
        exception: Объект исключения (опционально)
    """
    if exception:
        logger.error(f"{error_message}: {str(exception)}")
        logger.debug(f"Трейсбек: {traceback.format_exc()}")
    else:
        logger.error(error_message)


def log_model_interaction(prompt: str, response: str, model_name: str,
                          duration_ms: Optional[float] = None) -> None:
    """
    Логирует взаимодействие с языковой моделью.

    Args:
        prompt: Запрос к модели
        response: Ответ модели
        model_name: Название используемой модели
        duration_ms: Время выполнения в миллисекундах (опционально)
    """
    # Обрезаем длинные запросы и ответы для логов
    if len(prompt) > 500:
        prompt = prompt[:500] + "..."
    if len(response) > 500:
        response = response[:500] + "..."

    duration_info = f" (заняло {duration_ms:.2f} мс)" if duration_ms is not None else ""

    logger.info(f"Запрос к модели {model_name}{duration_info}")
    logger.debug(f"Запрос: {prompt}")
    logger.debug(f"Ответ: {response}")


def get_logger(name=None):
    """
    Возвращает настроенный логгер.

    Args:
        name (str, optional): Имя логгера. Если не указано, возвращает корневой логгер.

    Returns:
        Настроенный объект логгера
    """
    if name:
        return logging.getLogger(name)
    return logger


# Дополнительные функции для управления логированием

def enable_debug_logging():
    """Включает режим отладочного логирования."""
    for handler in logger.handlers:
        handler.setLevel(logging.DEBUG)
    logger.setLevel(logging.DEBUG)
    logger.debug("Включен режим отладочного логирования")


def disable_debug_logging():
    """Отключает режим отладочного логирования, возвращая уровень INFO."""
    for handler in logger.handlers:
        handler.setLevel(logging.INFO)
    logger.setLevel(logging.INFO)
    logger.info("Отключен режим отладочного логирования")


def log_memory_usage():
    """Логирует текущее использование памяти."""
    try:
        import psutil
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        logger.info(f"Использование памяти: {memory_info.rss / 1024 / 1024:.2f} МБ")
    except ImportError:
        logger.warning("Не удалось импортировать psutil для мониторинга памяти")


# Инициализация логгера при импорте модуля с базовыми настройками
setup_logger = setup_logging
_log_dir = 'logs'
if not os.path.exists(_log_dir):
    os.makedirs(_log_dir)

_default_log_file = os.path.join(_log_dir, f"ancient_world_{datetime.now().strftime('%Y%m%d')}.log")
setup_logging(log_level="INFO", log_file=_default_log_file, enable_console=True)