"""
__init__.py для модуля validators.

Экспортирует функции валидации контента на соответствие историческому периоду
и другие валидаторы для использования в других модулях приложения.
"""

from .era_validator import (
    validator as era_validator,
    is_era_compatible,
    suggest_alternative
)

__all__ = [
    # Экспортируем валидатор эпохи
    'era_validator',

    # Экспортируем основные функции для проверки
    'is_era_compatible',
    'suggest_alternative'
]
