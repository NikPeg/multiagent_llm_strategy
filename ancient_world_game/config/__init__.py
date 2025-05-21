"""
__init__.py для модуля config.

Экспортирует основные конфигурационные компоненты для использования в других модулях.
Позволяет импортировать конфигурацию напрямую из пакета config.
"""

from .config_loader import config, get_config, check_config
from .game_constants import (
    STATS,
    MAX_STAT_VALUE,
    INITIAL_STAT_VALUE,
    INITIAL_STAT_POINTS,
    STAT_EMOJIS,
    EVENT_TYPES,
    EVENT_TYPE_WEIGHTS,
    BOT_COMMANDS,
    ADMIN_COMMANDS
)

# Экспортируем основные настройки из объекта config для обратной совместимости
# Это позволит коду, использующему прямой импорт атрибутов, работать корректно
BOT_TOKEN = config.BOT_TOKEN
ADMIN_IDS = config.ADMIN_IDS
ADMIN_CHAT_ID = config.ADMIN_CHAT_ID
DB_PATH = config.DB_PATH
CHROMA_PERSIST_DIRECTORY = config.CHROMA_PERSIST_DIRECTORY
MODEL_PATH = config.MODEL_PATH
MODEL_MAX_TOKENS = config.MODEL_MAX_TOKENS
MODEL_TEMPERATURE = config.MODEL_TEMPERATURE
MODEL_HOST = config.MODEL_HOST
MODEL_PORT = config.MODEL_PORT
START_GAME_YEAR = config.START_GAME_YEAR
REAL_DAY_TO_GAME_YEAR = config.REAL_DAY_TO_GAME_YEAR
LOG_LEVEL = config.LOG_LEVEL
LOG_FILE = config.LOG_FILE
ENABLE_CONSOLE_LOGS = config.ENABLE_CONSOLE_LOGS
THREADS = config.THREADS
GPU_LAYERS = config.GPU_LAYERS
SCHEDULER_INTERVAL = config.SCHEDULER_INTERVAL
DAILY_UPDATE_TIME = config.DAILY_UPDATE_TIME
DEBUG_MODE = config.DEBUG_MODE
GAME_CHANNEL_URL = config.GAME_CHANNEL_URL
DISABLE_EVENT_GENERATION = config.DISABLE_EVENT_GENERATION

# Обновляем __all__ для включения всех экспортируемых переменных
__all__ = [
    # Из config_loader.py
    'config',
    'get_config',
    'check_config',

    # Прямые экспорты настроек
    'BOT_TOKEN',
    'ADMIN_IDS',
    'ADMIN_CHAT_ID',
    'DB_PATH',
    'CHROMA_PERSIST_DIRECTORY',
    'MODEL_PATH',
    'MODEL_MAX_TOKENS',
    'MODEL_TEMPERATURE',
    'MODEL_HOST',
    'MODEL_PORT',
    'START_GAME_YEAR',
    'REAL_DAY_TO_GAME_YEAR',
    'LOG_LEVEL',
    'LOG_FILE',
    'ENABLE_CONSOLE_LOGS',
    'THREADS',
    'GPU_LAYERS',
    'SCHEDULER_INTERVAL',
    'DAILY_UPDATE_TIME',
    'DEBUG_MODE',
    'GAME_CHANNEL_URL',
    'DISABLE_EVENT_GENERATION',

    # Из game_constants.py
    'STATS',
    'MAX_STAT_VALUE',
    'INITIAL_STAT_VALUE',
    'INITIAL_STAT_POINTS',
    'STAT_EMOJIS',
    'EVENT_TYPES',
    'EVENT_TYPE_WEIGHTS',
    'BOT_COMMANDS',
    'ADMIN_COMMANDS'
]
