"""
config.py - Конфигурационный модуль, загружающий настройки из .env файла
"""

import os
from pathlib import Path
from typing import List
from dotenv import load_dotenv
import logging

# Определяем путь к файлу .env
BASE_DIR = Path(__file__).parent.absolute()
ENV_PATH = BASE_DIR / '.env'

# Загружаем переменные из .env файла
load_dotenv(dotenv_path=ENV_PATH)

# Настройки Telegram бота
BOT_TOKEN = os.getenv('BOT_TOKEN')

# Администраторы бота
ADMIN_IDS_STR = os.getenv('ADMIN_IDS', '')
ADMIN_IDS = [int(admin_id.strip()) for admin_id in ADMIN_IDS_STR.split(',') if admin_id.strip()]
ADMIN_CHAT_ID = int(os.getenv('ADMIN_CHAT_ID', '0')) or None

# Настройки базы данных
DB_PATH = os.getenv('DB_PATH', 'game_data.db')
CHROMA_PERSIST_DIRECTORY = os.getenv('CHROMA_PERSIST_DIRECTORY', './chroma_db')

# Настройки LLM модели
MODEL_PATH = os.getenv('MODEL_PATH', '')
MODEL_MAX_TOKENS = int(os.getenv('MODEL_MAX_TOKENS', '2048'))
MODEL_TEMPERATURE = float(os.getenv('MODEL_TEMPERATURE', '0.7'))
MODEL_HOST = os.getenv('MODEL_HOST', 'localhost')
MODEL_PORT = int(os.getenv('MODEL_PORT', '8000'))

# Настройки игровой логики
START_GAME_YEAR = int(os.getenv('START_GAME_YEAR', '-3000'))
REAL_DAY_TO_GAME_YEAR = int(os.getenv('REAL_DAY_TO_GAME_YEAR', '1'))
MAX_STAT_VALUE = int(os.getenv('MAX_STAT_VALUE', '5'))
INITIAL_POINTS = int(os.getenv('INITIAL_POINTS', '15'))

# Настройки логирования
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = os.getenv('LOG_FILE', 'logs/ancient_world.log')
ENABLE_CONSOLE_LOGS = os.getenv('ENABLE_CONSOLE_LOGS', 'true').lower() == 'true'

# Настройки API
TELEGRAM_API_ID = int(os.getenv('TELEGRAM_API_ID', '0')) or None
TELEGRAM_API_HASH = os.getenv('TELEGRAM_API_HASH')

# Настройки производительности
THREADS = int(os.getenv('THREADS', '4'))
GPU_LAYERS = int(os.getenv('GPU_LAYERS', '32'))

# Настройки планировщика задач
SCHEDULER_INTERVAL = int(os.getenv('SCHEDULER_INTERVAL', '60'))
DAILY_UPDATE_TIME = os.getenv('DAILY_UPDATE_TIME', '12:00')

# Дополнительные настройки
DEBUG_MODE = os.getenv('DEBUG_MODE', 'false').lower() == 'true'
GAME_CHANNEL_URL = os.getenv('GAME_CHANNEL_URL', '')
DISABLE_EVENT_GENERATION = os.getenv('DISABLE_EVENT_GENERATION', 'false').lower() == 'true'

# Игровые константы
STATS = [
    "экономика",
    "военное дело",
    "религия и культура",
    "управление и право",
    "строительство и инфраструктура",
    "внешняя политика",
    "общественные отношения",
    "территория",
    "технологичность"
]

# Настройка логирования
def setup_logging():
    """
    Настраивает систему логирования на основе конфигурации.
    """
    log_level_name = LOG_LEVEL.upper()
    log_level = getattr(logging, log_level_name, logging.INFO)

    # Создаем директорию для логов, если она не существует
    log_dir = os.path.dirname(LOG_FILE)
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
    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Консольный обработчик, если включен
    if ENABLE_CONSOLE_LOGS:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    logging.info(f"Логирование настроено с уровнем {LOG_LEVEL}")

# Проверка конфигурации
def validate_config() -> List[str]:
    """
    Проверяет корректность настроек и возвращает список ошибок.

    Returns:
        Список ошибок в настройках или пустой список, если ошибок нет
    """
    errors = []

    # Проверка критических настроек
    if not BOT_TOKEN:
        errors.append("BOT_TOKEN не задан в .env файле")

    if not MODEL_PATH and not (MODEL_HOST and MODEL_PORT):
        errors.append("MODEL_PATH или MODEL_HOST+MODEL_PORT должны быть заданы в .env файле")

    # Проверка согласованности настроек
    if MAX_STAT_VALUE < 1:
        errors.append(f"MAX_STAT_VALUE должен быть положительным числом (текущее значение: {MAX_STAT_VALUE})")

    if INITIAL_POINTS < MAX_STAT_VALUE:
        errors.append(f"INITIAL_POINTS ({INITIAL_POINTS}) должен быть не меньше MAX_STAT_VALUE ({MAX_STAT_VALUE})")

    return errors

# Инициализация логгера при импорте модуля
setup_logging()

# Вывод предупреждений о проблемах конфигурации
config_errors = validate_config()
if config_errors:
    for error in config_errors:
        logging.warning(f"Ошибка конфигурации: {error}")
