"""
__init__.py для модуля storage.

Экспортирует основные компоненты управления хранилищем данных
для использования в других модулях приложения.
"""

from .db_manager import db, get_db, toggle_feature, get_user_by_telegram_id, update_user_subscription_status
from .chroma_manager import chroma, get_chroma
from .schemas import (
    Player,
    PlayerStats,
    CountryState,
    Project,
    Event,
    StatsDict,
    StateDict,
    PlayerDict
)

__all__ = [
    # Менеджеры баз данных
    'db',
    'get_db',
    'chroma',
    'get_chroma',

    # Классы для работы с данными
    'Player',
    'PlayerStats',
    'CountryState',
    'Project',
    'Event',

    # Типы для аннотаций
    'StatsDict',
    'StateDict',
    'PlayerDict',

    'get_user_by_telegram_id',
    'update_user_subscription_status',
    'toggle_feature',
]
