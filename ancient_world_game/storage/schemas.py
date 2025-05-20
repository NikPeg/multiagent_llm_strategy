"""
schemas.py - Определяет схемы данных и модели для структурированного хранения и валидации.
Используется для организации и типизации данных в приложении.
"""

from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from datetime import datetime
import json


@dataclass
class PlayerStats:
    """Модель для хранения характеристик игрока."""
    economy: int = 1         # Экономика
    military: int = 1        # Военное дело
    religion: int = 1        # Религия и культура
    governance: int = 1      # Управление и право
    construction: int = 1    # Строительство и инфраструктура
    diplomacy: int = 1       # Внешняя политика
    society: int = 1         # Общественные отношения
    territory: int = 1       # Территория
    technology: int = 1      # Технологичность

    @classmethod
    def from_dict(cls, data: Dict[str, int]) -> 'PlayerStats':
        """
        Создает объект из словаря с характеристиками.

        Args:
            data: Словарь с характеристиками

        Returns:
            PlayerStats: Новый объект PlayerStats
        """
        # Маппинг между русскими названиями и полями класса
        mapping = {
            "экономика": "economy",
            "военное дело": "military",
            "религия и культура": "religion",
            "управление и право": "governance",
            "строительство и инфраструктура": "construction",
            "внешняя политика": "diplomacy",
            "общественные отношения": "society",
            "территория": "territory",
            "технологичность": "technology"
        }

        # Создаем словарь с аргументами для конструктора
        kwargs = {}
        for rus_name, value in data.items():
            if rus_name.lower() in mapping:
                field_name = mapping[rus_name.lower()]
                kwargs[field_name] = value

        return cls(**kwargs)

    def to_dict(self) -> Dict[str, int]:
        """
        Преобразует объект в словарь с русскими названиями характеристик.

        Returns:
            Dict[str, int]: Словарь с характеристиками
        """
        # Обратный маппинг
        mapping = {
            "economy": "экономика",
            "military": "военное дело",
            "religion": "религия и культура",
            "governance": "управление и право",
            "construction": "строительство и инфраструктура",
            "diplomacy": "внешняя политика",
            "society": "общественные отношения",
            "territory": "территория",
            "technology": "технологичность"
        }

        result = {}
        for field_name, rus_name in mapping.items():
            result[rus_name] = getattr(self, field_name)

        return result

    def get_average(self) -> float:
        """
        Рассчитывает среднее значение всех характеристик.

        Returns:
            float: Среднее значение
        """
        total = (self.economy + self.military + self.religion +
                 self.governance + self.construction + self.diplomacy +
                 self.society + self.territory + self.technology)
        return total / 9


@dataclass
class CountryState:
    """Модель для хранения состояния страны по различным аспектам."""
    economy: str = ""        # Экономика
    military: str = ""       # Военное дело
    religion: str = ""       # Религия и культура
    governance: str = ""     # Управление и право
    construction: str = ""   # Строительство и инфраструктура
    diplomacy: str = ""      # Внешняя политика
    society: str = ""        # Общественные отношения
    territory: str = ""      # Территория
    technology: str = ""     # Технологичность

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> 'CountryState':
        """
        Создает объект из словаря с описаниями аспектов.

        Args:
            data: Словарь с описаниями аспектов

        Returns:
            CountryState: Новый объект CountryState
        """
        # Маппинг между русскими названиями и полями класса
        mapping = {
            "экономика": "economy",
            "военное дело": "military",
            "религия и культура": "religion",
            "управление и право": "governance",
            "строительство и инфраструктура": "construction",
            "внешняя политика": "diplomacy",
            "общественные отношения": "society",
            "территория": "territory",
            "технологичность": "technology"
        }

        # Создаем словарь с аргументами для конструктора
        kwargs = {}
        for rus_name, description in data.items():
            if rus_name.lower() in mapping:
                field_name = mapping[rus_name.lower()]
                kwargs[field_name] = description

        return cls(**kwargs)

    def to_dict(self) -> Dict[str, str]:
        """
        Преобразует объект в словарь с русскими названиями аспектов.

        Returns:
            Dict[str, str]: Словарь с описаниями аспектов
        """
        # Обратный маппинг
        mapping = {
            "economy": "экономика",
            "military": "военное дело",
            "religion": "религия и культура",
            "governance": "управление и право",
            "construction": "строительство и инфраструктура",
            "diplomacy": "внешняя политика",
            "society": "общественные отношения",
            "territory": "территория",
            "technology": "технологичность"
        }

        result = {}
        for field_name, rus_name in mapping.items():
            value = getattr(self, field_name)
            if value:  # Добавляем только непустые поля
                result[rus_name] = value

        return result


@dataclass
class Player:
    """Полная модель игрока, объединяющая все данные о стране."""
    user_id: int
    username: Optional[str] = None
    country_name: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    last_active: datetime = field(default_factory=datetime.now)
    goals_count: int = 0
    stats: PlayerStats = field(default_factory=PlayerStats)
    state: CountryState = field(default_factory=CountryState)
    description: str = ""  # Общее описание страны
    problems: List[str] = field(default_factory=list)  # Текущие проблемы

    @classmethod
    def from_db_dict(cls, data: Dict[str, Any]) -> 'Player':
        """
        Создает объект игрока из словаря из базы данных.

        Args:
            data: Словарь с данными из базы

        Returns:
            Player: Новый объект Player
        """
        # Обработка параметров
        player_data = {
            'user_id': data['user_id'],
            'username': data.get('username'),
            'country_name': data['country_name'],
            'goals_count': data.get('goals_count', 0)
        }

        # Преобразование строковых дат в datetime
        if 'created_at' in data:
            player_data['created_at'] = datetime.fromisoformat(data['created_at'])
        if 'last_active' in data:
            player_data['last_active'] = datetime.fromisoformat(data['last_active'])

        # Создание объекта Player
        player = cls(**player_data)

        # Добавление статов, если они есть
        if 'stats' in data:
            player.stats = PlayerStats.from_dict(data['stats'])

        # Добавление состояний аспектов, если они есть
        if 'state' in data:
            player.state = CountryState.from_dict(data['state'])

        # Дополнительные поля
        if 'description' in data:
            player.description = data['description']
        if 'problems' in data:
            if isinstance(data['problems'], str):
                try:
                    # Если problems хранится как JSON-строка
                    player.problems = json.loads(data['problems'])
                except json.JSONDecodeError:
                    player.problems = [data['problems']]
            elif isinstance(data['problems'], list):
                player.problems = data['problems']

        return player

    def to_dict(self) -> Dict[str, Any]:
        """
        Преобразует объект в словарь для хранения в базе.

        Returns:
            Dict[str, Any]: Словарь с данными игрока
        """
        return {
            'user_id': self.user_id,
            'username': self.username,
            'country_name': self.country_name,
            'created_at': self.created_at.isoformat(),
            'last_active': self.last_active.isoformat(),
            'goals_count': self.goals_count,
            'stats': self.stats.to_dict(),
            'state': self.state.to_dict(),
            'description': self.description,
            'problems': json.dumps(self.problems, ensure_ascii=False)
        }

    def get_aspect_details(self, aspect: str) -> str:
        """
        Получает текстовое описание определенного аспекта страны.

        Args:
            aspect: Название аспекта на русском

        Returns:
            str: Описание аспекта или пустая строка, если аспект не найден
        """
        # Маппинг между русскими названиями и полями класса CountryState
        mapping = {
            "экономика": "economy",
            "военное дело": "military",
            "религия и культура": "religion",
            "управление и право": "governance",
            "строительство и инфраструктура": "construction",
            "внешняя политика": "diplomacy",
            "общественные отношения": "society",
            "территория": "territory",
            "технологичность": "technology"
        }

        if aspect.lower() in mapping:
            field_name = mapping[aspect.lower()]
            return getattr(self.state, field_name)

        return ""


@dataclass
class Project:
    """Модель для долгосрочных проектов."""
    id: Optional[int] = None
    user_id: int = 0
    name: str = ""
    description: str = ""
    start_year: int = 0
    duration: int = 0
    progress: int = 0
    category: str = ""  # Категория проекта (строительство, исследование и т.д.)

    def is_completed(self) -> bool:
        """
        Проверяет, завершен ли проект.

        Returns:
            bool: True если проект завершен
        """
        return self.progress >= 100

    def remaining_years(self) -> int:
        """
        Рассчитывает оставшееся количество лет до завершения.

        Returns:
            int: Количество оставшихся лет
        """
        if self.is_completed():
            return 0

        # Рассчитываем оставшиеся годы на основе прогресса и длительности
        completed_part = self.progress / 100
        completed_years = self.duration * completed_part
        return max(0, round(self.duration - completed_years))


@dataclass
class Event:
    """Модель для игровых событий."""
    id: Optional[int] = None
    user_id: int = 0
    type: str = ""  # Тип события (good, bad, neutral, very_good, very_bad)
    description: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    effects: Dict[str, Any] = field(default_factory=dict)  # Эффекты события на характеристики

    def to_dict(self) -> Dict[str, Any]:
        """
        Преобразует объект в словарь.

        Returns:
            Dict[str, Any]: Словарь с данными события
        """
        return {
            'id': self.id,
            'user_id': self.user_id,
            'type': self.type,
            'description': self.description,
            'timestamp': self.timestamp.isoformat(),
            'effects': json.dumps(self.effects, ensure_ascii=False)
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Event':
        """
        Создает объект из словаря.

        Args:
            data: Словарь с данными

        Returns:
            Event: Новый объект Event
        """
        event_data = {
            'id': data.get('id'),
            'user_id': data['user_id'],
            'type': data['type'],
            'description': data['description']
        }

        # Обработка временной метки
        if 'timestamp' in data:
            event_data['timestamp'] = datetime.fromisoformat(data['timestamp'])

        # Обработка эффектов
        if 'effects' in data:
            if isinstance(data['effects'], str):
                try:
                    event_data['effects'] = json.loads(data['effects'])
                except json.JSONDecodeError:
                    event_data['effects'] = {}
            else:
                event_data['effects'] = data['effects']

        return cls(**event_data)


# Типы для аннотаций
StatsDict = Dict[str, int]
StateDict = Dict[str, str]
PlayerDict = Dict[str, Any]
