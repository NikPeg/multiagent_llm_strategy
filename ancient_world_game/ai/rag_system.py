"""
rag_system.py - Реализация системы Retrieval-Augmented Generation (RAG).
Обеспечивает контекстуализацию запросов к модели через извлечение
релевантной информации из базы знаний.
"""

from typing import Dict, List, Optional, Any, Union, Tuple
import re
from datetime import datetime

from config import config
from utils import logger, log_function_call, measure_execution_time
from storage import chroma
from .model_interface import model


class RAGSystem:
    """
    Класс для реализации системы Retrieval-Augmented Generation.
    Обеспечивает извлечение релевантного контекста и его использование при генерации ответов.
    """

    @staticmethod
    @log_function_call
    def get_country_context(user_id: int, query: str) -> str:
        """
        Извлекает контекст о стране пользователя, релевантный запросу.

        Args:
            user_id: ID пользователя
            query: Запрос или действие пользователя

        Returns:
            str: Релевантный контекст о стране
        """
        return chroma.get_country_context(user_id, query)

    @staticmethod
    @log_function_call
    def get_other_countries_context(user_id: int, query: str) -> str:
        """
        Извлекает контекст о других странах, релевантный запросу.

        Args:
            user_id: ID пользователя
            query: Запрос или действие пользователя

        Returns:
            str: Релевантный контекст о других странах
        """
        return chroma.get_other_countries_context(user_id, query)

    @staticmethod
    @log_function_call
    def process_player_action(user_id: int, country_name: str, action: str) -> Dict[str, Any]:
        """
        Обрабатывает действие игрока с использованием RAG.

        Args:
            user_id: ID пользователя
            country_name: Название страны
            action: Действие игрока

        Returns:
            Dict[str, Any]: Результат обработки действия
        """
        # Извлекаем контекст о стране
        country_context = RAGSystem.get_country_context(user_id, action)

        # Проверяем, требуется ли контекст о других странах
        other_countries_needed = RAGSystem._check_if_other_countries_needed(action)
        other_countries_context = ""

        if other_countries_needed:
            other_countries_context = RAGSystem.get_other_countries_context(user_id, action)
            if other_countries_context:
                country_context += f"\n\nИНФОРМАЦИЯ О ДРУГИХ СТРАНАХ:\n{other_countries_context}"

        # Анализируем действие с помощью модели
        analysis = model.analyze_player_action(user_id, country_name, action, country_context)

        return {
            "action": action,
            "analysis": analysis,
            "country_context": country_context,
            "other_countries_context": other_countries_context if other_countries_needed else None
        }

    @staticmethod
    def _check_if_other_countries_needed(action: str) -> bool:
        """
        Проверяет, требуется ли информация о других странах для обработки действия.

        Args:
            action: Действие игрока

        Returns:
            bool: True если нужна информация о других странах
        """
        # Простая эвристика для определения необходимости информации о других странах
        diplomacy_keywords = [
            "послать", "отправить", "направить", "заключить", "договор", "соглашение",
            "союз", "торговля", "война", "мир", "атаковать", "напасть", "посол",
            "дипломат", "дань", "дар", "подарок", "другая страна", "соседняя"
        ]

        action_lower = action.lower()
        for keyword in diplomacy_keywords:
            if keyword in action_lower:
                return True

        return False

    @staticmethod
    @log_function_call
    def update_aspect_state(user_id: int, country_name: str, aspect: str,
                            current_state: str, action_impact: str) -> str:
        """
        Обновляет состояние аспекта страны на основе воздействия действия.

        Args:
            user_id: ID пользователя
            country_name: Название страны
            aspect: Название аспекта
            current_state: Текущее состояние аспекта
            action_impact: Описание воздействия действия

        Returns:
            str: Обновленное состояние аспекта
        """
        return model.update_country_state(user_id, country_name, aspect, current_state, action_impact)

    @staticmethod
    @log_function_call
    def generate_event_with_context(user_id: int, country_name: str, event_type: str) -> Dict[str, Any]:
        """
        Генерирует событие для страны с использованием контекста из RAG.

        Args:
            user_id: ID пользователя
            country_name: Название страны
            event_type: Тип события

        Returns:
            Dict[str, Any]: Информация о сгенерированном событии
        """
        # Получаем общий контекст о стране
        country_context = chroma.get_country_context(user_id, "общее состояние страны")

        # Генерируем событие
        event = model.generate_event(user_id, country_name, event_type, country_context)

        return event

    @staticmethod
    @log_function_call
    def predict_country_future(user_id: int, country_name: str) -> str:
        """
        Генерирует предсказание о будущем страны на основе текущего контекста.

        Args:
            user_id: ID пользователя
            country_name: Название страны

        Returns:
            str: Предсказание о будущем страны
        """
        # Получаем полный контекст о стране для более точного предсказания
        country_context = chroma.get_country_context(user_id, "будущее страны общее состояние тенденции проблемы")

        # Генерируем предсказание
        prediction = model.predict_future(user_id, country_name, country_context)

        return prediction

    @staticmethod
    @log_function_call
    def update_country_stats(user_id: int, country_name: str) -> Dict[str, int]:
        """
        Обновляет числовые характеристики страны на основе текущих описаний аспектов.

        Args:
            user_id: ID пользователя
            country_name: Название страны

        Returns:
            Dict[str, int]: Обновленные характеристики страны
        """
        # Получаем текущие описания всех аспектов страны
        country_state = chroma.get_all_country_data(user_id).get('aspects', {})

        # Оцениваем характеристики на основе текстовых описаний
        stats = model.evaluate_country_stats(user_id, country_name, country_state)

        return stats

    @staticmethod
    @log_function_call
    def generate_country_problems(user_id: int, country_name: str) -> List[str]:
        """
        Генерирует список текущих проблем страны на основе контекста.

        Args:
            user_id: ID пользователя
            country_name: Название страны

        Returns:
            List[str]: Список проблем
        """
        # Получаем общий контекст о стране
        country_context = chroma.get_country_context(user_id, "проблемы кризис трудности")

        # Генерируем список проблем
        problems = model.generate_country_problems(user_id, country_name, country_context)

        return problems

    @staticmethod
    @log_function_call
    def process_daily_update(user_id: int, country_name: str) -> Dict[str, Any]:
        """
        Обрабатывает ежедневное обновление страны.

        Args:
            user_id: ID пользователя
            country_name: Название страны

        Returns:
            Dict[str, Any]: Результаты обновления
        """
        # Получаем полный контекст о стране
        country_context = chroma.get_country_context(user_id, "общее состояние все аспекты")

        # Формируем промпт для модели
        prompt = f"""Ты - историк-летописец, документирующий развитие страны {country_name} в древнем мире.
        
Вот текущее состояние страны:
{country_context}

Опиши изменения, которые произошли за прошедший год:
1. Как изменились различные аспекты страны?
2. Какие текущие процессы продолжаются?
3. Какие естественные изменения произошли?

Ответь в следующем формате:
ГОД: [текущий год]
ОБЩИЕ ИЗМЕНЕНИЯ: [общее описание изменений за год]
ИЗМЕНЕНИЯ ПО АСПЕКТАМ:
- экономика: [изменения]
- военное дело: [изменения]
- религия и культура: [изменения]
- управление и право: [изменения]
- строительство и инфраструктура: [изменения]
- внешняя политика: [изменения]
- общественные отношения: [изменения]
- территория: [изменения]
- технологичность: [изменения]
"""

        # Получаем ответ модели
        response = model.generate_response(prompt, max_tokens=1000, temperature=0.7)

        # Парсим ответ
        update_results = {
            "year": "",
            "general_changes": "",
            "aspect_changes": {}
        }

        current_section = None
        aspect_changes_section = False

        for line in response.strip().split("\n"):
            line = line.strip()
            if not line:
                continue

            if line.startswith("ГОД:"):
                update_results["year"] = line.split(":", 1)[1].strip()
            elif line.startswith("ОБЩИЕ ИЗМЕНЕНИЯ:"):
                current_section = "general_changes"
                update_results[current_section] = line.split(":", 1)[1].strip()
            elif line.startswith("ИЗМЕНЕНИЯ ПО АСПЕКТАМ:"):
                aspect_changes_section = True
                current_section = None
            elif aspect_changes_section and line.startswith("-"):
                # Парсим изменения в аспектах
                parts = line[1:].strip().split(":", 1)
                if len(parts) == 2:
                    aspect = parts[0].strip()
                    change = parts[1].strip()
                    update_results["aspect_changes"][aspect] = change
            elif current_section:
                # Добавляем текст к текущему разделу
                update_results[current_section] += " " + line

        return update_results

    @staticmethod
    @log_function_call
    def check_projects_progress(user_id: int, country_name: str) -> Dict[str, Any]:
        """
        Проверяет прогресс долгосрочных проектов и обновляет их состояние.

        Args:
            user_id: ID пользователя
            country_name: Название страны

        Returns:
            Dict[str, Any]: Информация об обновленных проектах
        """
        # Получаем информацию о проектах страны
        country_data = chroma.get_all_country_data(user_id)
        projects = country_data.get('projects', [])

        if not projects:
            return {"completed": [], "in_progress": []}

        # Обрабатываем каждый проект
        completed_projects = []
        updated_projects = []

        for project in projects:
            metadata = project.get('metadata', {})

            # Пропускаем уже завершенные проекты
            if metadata.get('progress', 0) >= 100:
                continue

            # Увеличиваем прогресс проекта
            duration = metadata.get('duration', 10)
            progress_increment = 100 / duration  # % за год

            new_progress = min(100, metadata.get('progress', 0) + progress_increment)
            new_remaining_years = max(0, metadata.get('remaining_years', 0) - 1)

            # Обновляем метаданные проекта
            metadata['progress'] = new_progress
            metadata['remaining_years'] = new_remaining_years

            # Если проект завершен
            if new_progress >= 100 or new_remaining_years <= 0:
                project_name = metadata.get('name', 'Неизвестный проект')
                project_category = metadata.get('category', 'Общий проект')

                completed_projects.append({
                    'name': project_name,
                    'category': project_category,
                    'metadata': metadata
                })
            else:
                updated_projects.append({
                    'name': metadata.get('name', 'Неизвестный проект'),
                    'progress': new_progress,
                    'remaining_years': new_remaining_years,
                    'metadata': metadata
                })

        return {
            "completed": completed_projects,
            "in_progress": updated_projects
        }

    @staticmethod
    @log_function_call
    def validate_era_compatibility(message: str) -> Tuple[bool, str]:
        """
        Проверяет, соответствует ли сообщение игрока эпохе древнего мира.

        Args:
            message: Сообщение игрока

        Returns:
            Tuple[bool, str]: (соответствует ли сообщение эпохе, комментарий)
        """
        return model.check_era_compatibility(message)


# Создаем экземпляр RAG-системы при импорте модуля
rag_system = RAGSystem()


def get_rag_system():
    """
    Функция для получения экземпляра RAG-системы.

    Returns:
        RAGSystem: Экземпляр RAG-системы
    """
    return rag_system
