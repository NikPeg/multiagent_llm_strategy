"""
events_generator.py - Модуль для генерации случайных игровых событий.
Отвечает за создание и применение различных событий к странам.
"""

from typing import Dict, List, Any, Optional, Tuple, Union
import random
from datetime import datetime, timedelta
import uuid

from config import config, EVENT_TYPES, EVENT_TYPE_WEIGHTS
from utils import logger, log_function_call, get_current_game_year
from storage import db, chroma
from ai import model, rag_system, response_parser
from ai import get_generate_event_prompt


class EventGenerator:
    """
    Класс для генерации случайных событий для стран.
    Предоставляет методы для создания и применения различных типов событий.
    """

    @staticmethod
    @log_function_call
    def generate_random_event(user_id: int, country_name: str) -> Dict[str, Any]:
        """
        Генерирует случайное событие для страны, выбирая тип события
        на основе заданных весов.

        Args:
            user_id: ID пользователя
            country_name: Название страны

        Returns:
            Dict[str, Any]: Информация о сгенерированном событии
        """
        # Выбираем тип события на основе весов
        event_type = EventGenerator._select_random_event_type()

        # Генерируем событие указанного типа
        return EventGenerator.generate_event(user_id, country_name, event_type)

    @staticmethod
    @log_function_call
    def _select_random_event_type() -> str:
        """
        Выбирает случайный тип события на основе заданных весов.

        Returns:
            str: Тип события
        """
        # Создаем список типов событий с учетом весов
        weighted_types = []
        for event_type in EVENT_TYPES:
            weight = EVENT_TYPE_WEIGHTS.get(event_type, 1)
            weighted_types.extend([event_type] * weight)

        # Выбираем случайный тип
        return random.choice(weighted_types)

    @staticmethod
    @log_function_call
    def generate_event(user_id: int, country_name: str, event_type: str) -> Dict[str, Any]:
        """
        Генерирует событие указанного типа для страны.

        Args:
            user_id: ID пользователя
            country_name: Название страны
            event_type: Тип события (очень плохую, плохую, нейтральную, хорошую, очень хорошую)

        Returns:
            Dict[str, Any]: Информация о сгенерированном событии
        """
        # Генерируем событие через RAG-систему
        event = rag_system.generate_event_with_context(user_id, country_name, event_type)

        # Сохраняем событие в базе данных
        event_id = EventGenerator._save_event(user_id, event)

        # Обновляем информацию о событии
        event['id'] = event_id
        event['timestamp'] = datetime.now().isoformat()

        return event

    @staticmethod
    @log_function_call
    def _save_event(user_id: int, event: Dict[str, Any]) -> str:
        """
        Сохраняет информацию о событии в базе данных.

        Args:
            user_id: ID пользователя
            event: Информация о событии

        Returns:
            str: ID события
        """
        # Генерируем уникальный ID события
        event_id = str(uuid.uuid4())

        # Добавляем ID и временную метку
        event['id'] = event_id
        event['timestamp'] = datetime.now().isoformat()

        # Сохраняем в Chroma
        chroma.save_event(user_id, event)

        return event_id

    @staticmethod
    @log_function_call
    def apply_event(user_id: int, country_name: str, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Применяет событие к стране, обновляя соответствующие аспекты.

        Args:
            user_id: ID пользователя
            country_name: Название страны
            event: Информация о событии

        Returns:
            Dict[str, Any]: Результаты применения события
        """
        # Получаем затронутые аспекты
        affected_aspects = event.get("affected_aspects", {})

        # Обновляем каждый затронутый аспект
        for aspect, impact in affected_aspects.items():
            # Нормализуем название аспекта
            aspect = aspect.lower().strip()

            # Получаем текущее описание аспекта
            current_description = db.get_country_state(user_id, aspect).get(aspect, "")

            # Генерируем обновленное описание
            updated_description = rag_system.update_aspect_state(
                user_id,
                country_name,
                aspect,
                current_description,
                impact
            )

            # Сохраняем обновленное описание
            db.save_country_state(user_id, aspect, updated_description)

        return {
            "event_id": event.get("id", ""),
            "affected_aspects": list(affected_aspects.keys()),
            "applied_at": datetime.now().isoformat()
        }

    @staticmethod
    @log_function_call
    def should_generate_event(user_id: int, last_event_time: Optional[datetime] = None) -> bool:
        """
        Определяет, нужно ли генерировать новое событие для страны,
        на основе времени последнего события и активности игрока.

        Args:
            user_id: ID пользователя
            last_event_time: Время последнего события (опционально)

        Returns:
            bool: True, если нужно генерировать новое событие, иначе False
        """
        # Если время последнего события не предоставлено, пытаемся загрузить его
        if not last_event_time:
            last_event = EventGenerator._get_last_event(user_id)
            if last_event:
                last_event_time = datetime.fromisoformat(last_event.get('timestamp', ''))

        # Если нет информации о последнем событии, генерируем новое
        if not last_event_time:
            return True

        # Получаем время последней активности игрока
        player_info = db.get_player_info(user_id)
        if not player_info:
            return False

        last_active = datetime.fromisoformat(player_info.get('last_active', ''))

        # Определяем интервал на основе активности игрока
        # Чем чаще игрок активен, тем чаще генерируем события
        if (datetime.now() - last_active).total_seconds() < 3600:  # Активен в последний час
            min_interval = timedelta(hours=1)
        elif (datetime.now() - last_active).total_seconds() < 86400:  # Активен в последние сутки
            min_interval = timedelta(days=1)
        else:  # Активен реже
            min_interval = timedelta(days=3)

        # Проверяем, прошло ли достаточно времени с последнего события
        time_since_last_event = datetime.now() - last_event_time

        # Добавляем небольшую случайность
        jitter = random.uniform(0.8, 1.2)
        adjusted_interval = min_interval * jitter

        return time_since_last_event >= adjusted_interval

    @staticmethod
    @log_function_call
    def _get_last_event(user_id: int) -> Optional[Dict[str, Any]]:
        """
        Получает информацию о последнем событии страны.

        Args:
            user_id: ID пользователя

        Returns:
            Optional[Dict[str, Any]]: Информация о последнем событии или None
        """
        # Получаем данные о стране из Chroma
        country_data = chroma.get_all_country_data(user_id)

        # Извлекаем события
        events = country_data.get('events', [])

        # Если есть события, возвращаем последнее
        if events:
            # Сортируем по времени (от новых к старым)
            events.sort(key=lambda e: e.get('metadata', {}).get('timestamp', ''), reverse=True)
            return events[0]

        return None

    @staticmethod
    @log_function_call
    def get_recent_events(user_id: int, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Получает список недавних событий страны.

        Args:
            user_id: ID пользователя
            limit: Максимальное количество событий для возврата

        Returns:
            List[Dict[str, Any]]: Список недавних событий
        """
        # Получаем данные о стране из Chroma
        country_data = chroma.get_all_country_data(user_id)

        # Извлекаем события
        events = country_data.get('events', [])

        # Сортируем по времени (от новых к старым)
        events.sort(key=lambda e: e.get('metadata', {}).get('timestamp', ''), reverse=True)

        # Ограничиваем количество
        events = events[:limit]

        # Форматируем для удобства
        formatted_events = []
        for event in events:
            metadata = event.get('metadata', {})
            formatted_events.append({
                'id': metadata.get('event_id', ''),
                'type': metadata.get('type', 'нейтральное'),
                'title': event.get('title', 'Событие'),
                'description': event.get('description', ''),
                'timestamp': metadata.get('timestamp', '')
            })

        return formatted_events

    @staticmethod
    @log_function_call
    def generate_global_event(country_ids: List[int]) -> Dict[str, Any]:
        """
        Генерирует глобальное событие, затрагивающее несколько стран.

        Args:
            country_ids: Список ID пользователей стран

        Returns:
            Dict[str, Any]: Информация о глобальном событии
        """
        # Выбираем тип события (для глобальных преимущественно негативные или нейтральные)
        global_event_types = ["очень плохую", "плохую", "плохую", "нейтральную", "нейтральную", "хорошую"]
        event_type = random.choice(global_event_types)

        # Получаем информацию о странах
        countries_info = []
        for user_id in country_ids:
            player_info = db.get_player_info(user_id)
            if player_info:
                countries_info.append({
                    'user_id': user_id,
                    'country_name': player_info.get('country_name', '')
                })

        # Если нет стран, прекращаем генерацию
        if not countries_info:
            return {"error": "Нет доступных стран для глобального события"}

        # Формируем промпт для LLM
        prompt = f"""Ты - летописец древнего мира, описывающий глобальные события.

В мире существуют следующие государства:
{", ".join([country['country_name'] for country in countries_info if country['country_name']])}

Создай {event_type} новость, которая затронет все эти государства. 
Это должно быть значимое событие, которое повлияет на весь известный мир.
Примеры возможных событий: природные катаклизмы, солнечные затмения, кометы, эпидемии, 
миграции народов, появление новых религий, технологические открытия.

Ответь в следующем формате:
ЗАГОЛОВОК: [краткий заголовок события]
СОБЫТИЕ: [подробное описание события]
ПОСЛЕДСТВИЯ: [как это событие повлияет на мир в целом]
ВЛИЯНИЕ НА СТРАНЫ:
- [название страны]: [как именно затронута эта страна]"""

        # Получаем ответ LLM
        response = model.generate_response(prompt, max_tokens=1000, temperature=0.8)

        # Парсим результат
        global_event = {
            "title": "",
            "description": "",
            "consequences": "",
            "country_effects": {}
        }

        # Извлекаем заголовок
        title_match = re.search(r"ЗАГОЛОВОК:\s*(.+?)(?=\nСОБЫТИЕ:|\n\n|$)", response, re.DOTALL)
        if title_match:
            global_event["title"] = title_match.group(1).strip()

        # Извлекаем описание события
        description_match = re.search(r"СОБЫТИЕ:\s*(.+?)(?=\nПОСЛЕДСТВИЯ:|\n\n|$)", response, re.DOTALL)
        if description_match:
            global_event["description"] = description_match.group(1).strip()

        # Извлекаем последствия
        consequences_match = re.search(r"ПОСЛЕДСТВИЯ:\s*(.+?)(?=\nВЛИЯНИЕ НА СТРАНЫ:|\n\n|$)", response, re.DOTALL)
        if consequences_match:
            global_event["consequences"] = consequences_match.group(1).strip()

        # Извлекаем влияние на страны
        country_effects_section = ""
        if "ВЛИЯНИЕ НА СТРАНЫ:" in response:
            country_effects_section = response.split("ВЛИЯНИЕ НА СТРАНЫ:", 1)[1].strip()

        if country_effects_section:
            # Ищем строки вида "- страна: влияние"
            country_pattern = r"-\s*([^:]+):\s*(.+?)(?=\n-|\n\n|$)"
            country_matches = re.findall(country_pattern, country_effects_section, re.DOTALL)

            for country_name, effect in country_matches:
                country_name = country_name.strip()
                effect = effect.strip()

                # Находим соответствующий user_id
                for country_info in countries_info:
                    if country_info['country_name'].lower() == country_name.lower():
                        global_event["country_effects"][country_info['user_id']] = {
                            "country_name": country_name,
                            "effect": effect
                        }
                        break

        # Добавляем метаданные
        global_event["id"] = str(uuid.uuid4())
        global_event["type"] = event_type
        global_event["timestamp"] = datetime.now().isoformat()
        global_event["year"] = get_current_game_year()

        # Применяем событие к каждой стране
        for user_id, effect_info in global_event["country_effects"].items():
            country_name = effect_info["country_name"]
            effect = effect_info["effect"]

            # Формируем событие для конкретной страны
            country_event = {
                "title": global_event["title"],
                "description": f"{global_event['description']}\n\nВлияние на {country_name}: {effect}",
                "consequences": global_event["consequences"],
                "affected_aspects": {},  # Это будет дополнено ниже
                "type": event_type,
                "is_global": True,
                "global_event_id": global_event["id"]
            }

            # Генерируем влияние на аспекты страны
            country_event = EventGenerator._enrich_country_event(user_id, country_name, country_event, effect)

            # Сохраняем и применяем событие
            EventGenerator._save_event(user_id, country_event)
            EventGenerator.apply_event(user_id, country_name, country_event)

        return global_event

    @staticmethod
    @log_function_call
    def _enrich_country_event(user_id: int, country_name: str,
                              event: Dict[str, Any], effect: str) -> Dict[str, Any]:
        """
        Дополняет событие страны информацией о влиянии на аспекты.

        Args:
            user_id: ID пользователя
            country_name: Название страны
            event: Базовое событие
            effect: Описание влияния

        Returns:
            Dict[str, Any]: Дополненное событие
        """
        # Формируем промпт для определения влияния на аспекты
        prompt = f"""Ты - аналитик древнего мира, оценивающий влияние событий на различные аспекты государства.

Событие: {event.get("title", "")}
Описание: {event.get("description", "")}

Влияние на государство {country_name}:
{effect}

Определи, как это событие повлияет на различные аспекты государства.
Ответь в следующем формате:
АСПЕКТЫ:
- экономика: [описание влияния]
- военное дело: [описание влияния]
- религия и культура: [описание влияния]
- управление и право: [описание влияния]
- строительство и инфраструктура: [описание влияния]
- внешняя политика: [описание влияния]
- общественные отношения: [описание влияния]
- территория: [описание влияния]
- технологичность: [описание влияния]

Указывай только те аспекты, на которые действительно повлияет событие."""

        # Получаем ответ LLM
        response = model.generate_response(prompt, max_tokens=600, temperature=0.7)

        # Извлекаем влияние на аспекты
        aspects_section = ""
        if "АСПЕКТЫ:" in response:
            aspects_section = response.split("АСПЕКТЫ:", 1)[1].strip()

        affected_aspects = {}

        if aspects_section:
            # Ищем строки вида "- аспект: влияние"
            aspect_pattern = r"-\s*([^:]+):\s*(.+?)(?=\n-|\n\n|$)"
            aspect_matches = re.findall(aspect_pattern, aspects_section, re.DOTALL)

            for aspect, impact in aspect_matches:
                aspect = aspect.strip().lower()
                impact = impact.strip()

                if impact:  # Добавляем только непустые влияния
                    affected_aspects[aspect] = impact

        # Обновляем событие
        event["affected_aspects"] = affected_aspects

        return event


# Экспортируем функции для удобного доступа
generate_random_event = EventGenerator.generate_random_event
generate_event = EventGenerator.generate_event
apply_event = EventGenerator.apply_event
should_generate_event = EventGenerator.should_generate_event
get_recent_events = EventGenerator.get_recent_events
generate_global_event = EventGenerator.generate_global_event
