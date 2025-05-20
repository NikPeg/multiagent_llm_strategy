"""
config_loader.py - Загрузчик конфигурации из .env файла.
Предоставляет центральный доступ ко всем настройкам проекта.
"""

import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Union, Tuple, Set
from dotenv import load_dotenv
import logging
import json


class Config:
    """
    Класс для загрузки и хранения конфигурации приложения.
    Реализует паттерн Singleton для обеспечения единой точки доступа к настройкам.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        # Определяем путь к файлу .env
        self.base_dir = Path(__file__).parent.parent.absolute()
        self.env_path = self.base_dir / '.env'

        # Загружаем переменные из .env файла
        load_dotenv(dotenv_path=self.env_path)

        # Инициализируем настройки
        self._load_config()

        self._initialized = True

    def _load_config(self):
        """
        Загружает все настройки из переменных окружения.
        """
        # Настройки Telegram бота
        self.BOT_TOKEN = os.getenv('BOT_TOKEN')
        self.WEBHOOK_URL = os.getenv('WEBHOOK_URL', None)
        self.WEBHOOK_PATH = os.getenv('WEBHOOK_PATH', '/webhook')
        self.WEBHOOK_HOST = os.getenv('WEBHOOK_HOST', '0.0.0.0')
        self.WEBHOOK_PORT = int(os.getenv('WEBHOOK_PORT', 8443))

        # Администраторы бота
        admin_ids_str = os.getenv('ADMIN_IDS', '')
        self.ADMIN_IDS = [int(admin_id.strip()) for admin_id in admin_ids_str.split(',') if admin_id.strip()]
        self.ADMIN_CHAT_ID = int(os.getenv('ADMIN_CHAT_ID', 0)) or None

        # Настройки базы данных
        self.DB_PATH = os.getenv('DB_PATH', 'game_data.db')
        self.CHROMA_PERSIST_DIRECTORY = os.getenv('CHROMA_PERSIST_DIRECTORY', './chroma_db')

        # Настройки LLM модели
        self.MODEL_PATH = os.getenv('MODEL_PATH', '')
        self.MODEL_MAX_TOKENS = int(os.getenv('MODEL_MAX_TOKENS', 2048))
        self.MODEL_TEMPERATURE = float(os.getenv('MODEL_TEMPERATURE', 0.7))
        self.MODEL_HOST = os.getenv('MODEL_HOST', 'localhost')
        self.MODEL_PORT = int(os.getenv('MODEL_PORT', 8000))

        # Настройки игровой логики
        self.START_GAME_YEAR = int(os.getenv('START_GAME_YEAR', -3000))
        self.REAL_DAY_TO_GAME_YEAR = int(os.getenv('REAL_DAY_TO_GAME_YEAR', 1))
        self.MAX_STAT_VALUE = int(os.getenv('MAX_STAT_VALUE', 5))
        self.INITIAL_POINTS = int(os.getenv('INITIAL_POINTS', 15))

        # Настройки логирования
        self.LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
        self.LOG_FILE = os.getenv('LOG_FILE', 'logs/ancient_world.log')
        self.ENABLE_CONSOLE_LOGS = os.getenv('ENABLE_CONSOLE_LOGS', 'true').lower() == 'true'

        # Настройки производительности
        self.THREADS = int(os.getenv('THREADS', 4))
        self.GPU_LAYERS = int(os.getenv('GPU_LAYERS', 32))

        # Настройки планировщика задач
        self.SCHEDULER_INTERVAL = int(os.getenv('SCHEDULER_INTERVAL', 60))
        self.DAILY_UPDATE_TIME = os.getenv('DAILY_UPDATE_TIME', '12:00')

        # Дополнительные настройки
        self.DEBUG_MODE = os.getenv('DEBUG_MODE', 'false').lower() == 'true'
        self.GAME_CHANNEL_URL = os.getenv('GAME_CHANNEL_URL', '')
        self.DISABLE_EVENT_GENERATION = os.getenv('DISABLE_EVENT_GENERATION', 'false').lower() == 'true'

    def get_as_dict(self) -> Dict[str, Any]:
        """
        Возвращает все настройки в виде словаря.

        Returns:
            Словарь с настройками
        """
        config_dict = {}
        for key, value in self.__dict__.items():
            # Исключаем приватные атрибуты и служебные поля
            if not key.startswith('_') and key != 'base_dir' and key != 'env_path':
                config_dict[key] = value
        return config_dict

    def validate(self) -> List[str]:
        """
        Проверяет корректность настроек и возвращает список ошибок.

        Returns:
            Список ошибок в настройках или пустой список, если ошибок нет
        """
        errors = []

        # Проверка критических настроек
        if not self.BOT_TOKEN:
            errors.append("BOT_TOKEN не задан в .env файле")

        if not self.MODEL_PATH:
            errors.append("MODEL_PATH не задан в .env файле")

        # Проверка согласованности настроек
        if self.MAX_STAT_VALUE < 1:
            errors.append(f"MAX_STAT_VALUE должен быть положительным числом (текущее значение: {self.MAX_STAT_VALUE})")

        if self.INITIAL_POINTS < self.MAX_STAT_VALUE:
            errors.append(f"INITIAL_POINTS ({self.INITIAL_POINTS}) должен быть не меньше MAX_STAT_VALUE ({self.MAX_STAT_VALUE})")

        # Другие проверки согласованности можно добавить здесь

        return errors

    def setup_logging(self):
        """
        Настраивает систему логирования на основе конфигурации.
        """
        log_level = getattr(logging, self.LOG_LEVEL.upper(), logging.INFO)

        # Создаем директорию для логов, если она не существует
        log_dir = os.path.dirname(self.LOG_FILE)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)

        # Настраиваем логгер
        logger = logging.getLogger()
        logger.setLevel(log_level)

        # Очищаем существующие обработчики
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

        # Настраиваем форматирование
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        # Файловый обработчик
        file_handler = logging.FileHandler(self.LOG_FILE)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        # Консольный обработчик, если включен
        if self.ENABLE_CONSOLE_LOGS:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(log_level)
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)

        logging.info(f"Логирование настроено с уровнем {self.LOG_LEVEL}")

    def __str__(self) -> str:
        """
        Возвращает строковое представление конфигурации (для отладки).

        Returns:
            Строка с настройками
        """
        config_dict = self.get_as_dict()
        # Маскируем чувствительные данные
        if 'BOT_TOKEN' in config_dict:
            config_dict['BOT_TOKEN'] = '******' if config_dict['BOT_TOKEN'] else None

        return json.dumps(config_dict, indent=2, ensure_ascii=False)


# Создаем экземпляр конфигурации при импорте модуля
config = Config()


def get_config() -> Config:
    """
    Функция для получения экземпляра конфигурации.

    Returns:
        Экземпляр класса Config
    """
    return config


def check_config() -> bool:
    """
    Проверяет корректность конфигурации.

    Returns:
        True если конфигурация корректна, иначе False
    """
    errors = config.validate()
    if errors:
        for error in errors:
            logging.error(f"Ошибка конфигурации: {error}")
        return False
    return True


# Автоматически настраиваем логирование при импорте
try:
    config.setup_logging()
except Exception as e:
    print(f"Ошибка при настройке логирования: {e}")


# Если этот модуль запускается как скрипт, выводим конфигурацию
if __name__ == "__main__":
    print("Текущая конфигурация:")
    print(config)

    errors = config.validate()
    if errors:
        print("\nОбнаружены ошибки в конфигурации:")
        for error in errors:
            print(f" - {error}")
    else:
        print("\nКонфигурация корректна.")
