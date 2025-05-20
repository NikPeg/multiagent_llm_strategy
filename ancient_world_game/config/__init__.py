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

__all__ = [
    # Из config_loader.py
    'config',
    'get_config',
    'check_config',

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
