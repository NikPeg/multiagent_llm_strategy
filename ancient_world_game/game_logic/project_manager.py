"""
project_manager.py - Модуль для управления долгосрочными проектами.
Отвечает за создание, мониторинг и завершение проектов стран.
"""

from typing import Dict, List, Any, Optional, Tuple, Union
import json
import re
from datetime import datetime
import uuid

from config import config
from utils import logger, log_function_call, format_game_year, get_current_game_year
from utils import calculate_project_duration, calculate_project_progress
from storage import db, chroma, Project
from ai import model, rag_system, response_parser
from ai import get_project_completion_prompt


class ProjectManager:
    """
    Класс для управления долгосрочными проектами стран.
    Предоставляет методы для создания, отслеживания и завершения проектов.
    """

    @staticmethod
    @log_function_call
    def create_project(user_id: int, country_name: str, project_name: str,
                       project_category: str, description: str = "",
                       scale: int = 3, technology_level: int = 1) -> Dict[str, Any]:
        """
        Создает новый проект для страны.

        Args:
            user_id: ID пользователя
            country_name: Название страны
            project_name: Название проекта
            project_category: Категория проекта (строительство, исследование и т.д.)
            description: Описание проекта
            scale: Масштаб проекта (1-5)
            technology_level: Уровень технологий страны (1-5)

        Returns:
            Dict[str, Any]: Информация о созданном проекте
        """
        # Рассчитываем продолжительность проекта
        duration = calculate_project_duration(project_category, scale, technology_level)

        # Получаем текущий игровой год
        current_game_year = get_current_game_year()

        # Генерируем уникальный ID проекта
        project_id = str(uuid.uuid4())

        # Если описание не предоставлено, генерируем его с помощью LLM
        if not description:
            description = ProjectManager._generate_project_description(
                country_name, project_name, project_category, scale)

        # Создаем объект проекта
        project = Project(
            id=project_id,
            user_id=user_id,
            name=project_name,
            description=description,
            start_year=current_game_year,
            duration=duration,
            progress=0,
            category=project_category
        )

        # Сохраняем проект в Chroma
        project_data = {
            "id": project_id,
            "name": project_name,
            "category": project_category,
            "description": description,
            "start_year": current_game_year,
            "duration": duration,
            "progress": 0,
            "remaining_years": duration
        }
        chroma.save_project(user_id, project_data)

        # Обновляем соответствующий аспект страны
        ProjectManager._update_aspect_with_project(
            user_id, country_name, project_name, project_category, "start")

        return project_data

    @staticmethod
    @log_function_call
    def _generate_project_description(country_name: str, project_name: str,
                                      project_category: str, scale: int) -> str:
        """
        Генерирует описание проекта с помощью LLM.

        Args:
            country_name: Название страны
            project_name: Название проекта
            project_category: Категория проекта
            scale: Масштаб проекта (1-5)

        Returns:
            str: Сгенерированное описание проекта
        """
        # Формируем промпт для LLM
        prompt = f"""Ты - летописец древнего мира, описывающий масштабные проекты страны {country_name}.

Страна {country_name} начинает новый проект:
Название: {project_name}
Категория: {project_category}
Масштаб: {scale}/5

Напиши подробное описание этого проекта. Включи информацию о:
- Цели проекта
- Используемых ресурсах и технологиях
- Вовлеченных людях
- Ожидаемых результатах

Убедись, что описание соответствует реалиям древнего мира и учитывает масштаб проекта.
Ответ дай в форме связного текста без заголовков и разделов."""

        # Получаем ответ LLM
        response = model.generate_response(prompt, max_tokens=500, temperature=0.7)

        return response.strip()

    @staticmethod
    @log_function_call
    def _update_aspect_with_project(user_id: int, country_name: str, project_name: str,
                                    project_category: str, phase: str) -> None:
        """
        Обновляет соответствующий аспект страны при создании или завершении проекта.

        Args:
            user_id: ID пользователя
            country_name: Название страны
            project_name: Название проекта
            project_category: Категория проекта
            phase: Фаза проекта ("start" или "complete")
        """
        # Определяем, какой аспект соответствует категории проекта
        aspect_mapping = {
            "строительство": "строительство и инфраструктура",
            "исследование": "технологичность",
            "военная подготовка": "военное дело",
            "религиозный проект": "религия и культура",
            "инфраструктура": "строительство и инфраструктура",
            "экономический проект": "экономика"
        }

        aspect = aspect_mapping.get(project_category, "строительство и инфраструктура")

        # Получаем текущее описание аспекта
        current_description = db.get_country_state(user_id, aspect).get(aspect, "")

        # Формируем текст для добавления в описание
        if phase == "start":
            addition = f"Начато строительство/реализация проекта '{project_name}'."
        else:  # complete
            addition = f"Завершено строительство/реализация проекта '{project_name}'."

        # Добавляем информацию о проекте к описанию аспекта
        new_description = current_description
        if not new_description:
            new_description = addition
        else:
            new_description += f"\n\n{addition}"

        # Сохраняем обновленное описание
        db.save_country_state(user_id, aspect, new_description)

    @staticmethod
    @log_function_call
    def get_projects(user_id: int) -> List[Dict[str, Any]]:
        """
        Получает список всех проектов страны.

        Args:
            user_id: ID пользователя

        Returns:
            List[Dict[str, Any]]: Список проектов
        """
        # Получаем данные о стране из Chroma
        country_data = chroma.get_all_country_data(user_id)

        # Извлекаем проекты
        projects = []
        if 'projects' in country_data:
            for project in country_data['projects']:
                # Обновляем прогресс проекта
                metadata = project.get('metadata', {})

                # Рассчитываем текущий прогресс и оставшиеся годы
                start_year = metadata.get('start_year', 0)
                duration = metadata.get('duration', 10)

                progress, remaining_years = calculate_project_progress(start_year, duration)

                # Обновляем метаданные
                metadata['progress'] = progress
                metadata['remaining_years'] = remaining_years

                # Добавляем проект в список
                projects.append({
                    'text': project.get('text', ''),
                    'metadata': metadata
                })

        return projects

    @staticmethod
    @log_function_call
    def update_projects_progress(user_id: int) -> Dict[str, Any]:
        """
        Обновляет прогресс всех проектов страны.

        Args:
            user_id: ID пользователя

        Returns:
            Dict[str, Any]: Результаты обновления
        """
        # Получаем данные о стране из Chroma
        country_data = chroma.get_all_country_data(user_id)

        # Извлекаем проекты
        projects = country_data.get('projects', [])

        # Списки для результатов
        completed = []
        updated = []

        for project in projects:
            metadata = project.get('metadata', {})

            # Пропускаем уже завершенные проекты
            current_progress = metadata.get('progress', 0)
            if current_progress >= 100:
                continue

            # Рассчитываем текущий прогресс и оставшиеся годы
            start_year = metadata.get('start_year', 0)
            duration = metadata.get('duration', 10)

            progress, remaining_years = calculate_project_progress(start_year, duration)

            # Обновляем метаданные
            metadata['progress'] = progress
            metadata['remaining_years'] = remaining_years

            # Если проект завершен
            if progress >= 100:
                completed.append({
                    'name': metadata.get('name', 'Неизвестный проект'),
                    'category': metadata.get('category', 'Общий проект'),
                    'metadata': metadata
                })
            else:
                updated.append({
                    'name': metadata.get('name', 'Неизвестный проект'),
                    'progress': progress,
                    'remaining_years': remaining_years,
                    'metadata': metadata
                })

            # Сохраняем обновленные метаданные
            project_id = metadata.get('id', '')
            if project_id:
                chroma.save_project(user_id, metadata)

        return {
            "completed": completed,
            "in_progress": updated
        }

    @staticmethod
    @log_function_call
    def handle_project_completion(user_id: int, country_name: str, project_name: str,
                                  project_category: str) -> Dict[str, Any]:
        """
        Обрабатывает завершение проекта и его влияние на страну.

        Args:
            user_id: ID пользователя
            country_name: Название страны
            project_name: Название проекта
            project_category: Категория проекта

        Returns:
            Dict[str, Any]: Результаты завершения проекта
        """
        # Получаем контекст о стране
        country_context = rag_system.get_country_context(user_id, project_name)

        # Формируем промпт для описания завершения проекта
        prompt = get_project_completion_prompt(country_name, project_name, project_category, country_context)

        # Получаем ответ LLM
        response = model.generate_response(prompt, max_tokens=800, temperature=0.7)

        # Парсим результат
        result = response_parser.parse(response, "project_completion")

        # Обновляем соответствующий аспект страны
        ProjectManager._update_aspect_with_project(
            user_id, country_name, project_name, project_category, "complete")

        # Обновляем аспекты, затронутые завершением проекта
        aspect_changes = result.get("aspect_changes", {})

        for aspect, change in aspect_changes.items():
            # Нормализуем название аспекта
            aspect = aspect.lower().strip()

            # Получаем текущее описание аспекта
            current_description = db.get_country_state(user_id, aspect).get(aspect, "")

            # Генерируем обновленное описание
            updated_description = rag_system.update_aspect_state(
                user_id, country_name, aspect, current_description, change)

            # Сохраняем обновленное описание
            db.save_country_state(user_id, aspect, updated_description)

        return result

    @staticmethod
    @log_function_call
    def extract_potential_projects(text: str) -> List[Dict[str, Any]]:
        """
        Извлекает информацию о потенциальных проектах из текста.

        Args:
            text: Текст для анализа

        Returns:
            List[Dict[str, Any]]: Список потенциальных проектов
        """
        # Ищем упоминания строительства или проектов
        project_patterns = [
            r"(строит(?:ь|ельство)|построить|возвести|создать|соорудить)\s+([^\.,:;]+)",
            r"(начать|инициировать|запустить)\s+(?:строительство|проект|создание)\s+([^\.,:;]+)",
            r"(проект|строительство)\s+([^\.,:;]+)"
        ]

        potential_projects = []

        for pattern in project_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple) and len(match) >= 2:
                    action, project_name = match

                    # Определяем категорию проекта
                    category = "строительство"  # по умолчанию
                    if "храм" in project_name.lower() or "святилище" in project_name.lower():
                        category = "религиозный проект"
                    elif "дорог" in project_name.lower() or "канал" in project_name.lower() or "акведук" in project_name.lower():
                        category = "инфраструктура"
                    elif "крепост" in project_name.lower() or "стен" in project_name.lower() or "башн" in project_name.lower():
                        category = "военная подготовка"
                    elif "исследовани" in project_name.lower() or "изучени" in project_name.lower() or "изучить" in project_name.lower():
                        category = "исследование"
                    elif "рынок" in project_name.lower() or "торгов" in project_name.lower() or "экономич" in project_name.lower():
                        category = "экономический проект"

                    # Оцениваем масштаб проекта от 1 до 5
                    scale = 3  # средний масштаб по умолчанию
                    if any(word in project_name.lower() for word in ["грандиозн", "велик", "огромн", "масштабн"]):
                        scale = 5
                    elif any(word in project_name.lower() for word in ["крупн", "больш"]):
                        scale = 4
                    elif any(word in project_name.lower() for word in ["небольш", "маленьк", "скромн"]):
                        scale = 2
                    elif any(word in project_name.lower() for word in ["минимальн", "крошечн", "простейш"]):
                        scale = 1

                    # Создаем потенциальный проект
                    potential_project = {
                        "name": project_name.strip(),
                        "category": category,
                        "scale": scale,
                        "action": action.strip()
                    }

                    # Проверяем, нет ли дубликатов
                    duplicate = False
                    for existing_project in potential_projects:
                        if existing_project["name"].lower() == potential_project["name"].lower():
                            duplicate = True
                            break

                    if not duplicate:
                        potential_projects.append(potential_project)

        return potential_projects

    @staticmethod
    @log_function_call
    def confirm_project_creation(user_id: int, country_name: str,
                                 potential_project: Dict[str, Any]) -> Dict[str, Any]:
        """
        Подтверждает создание проекта на основе потенциального проекта.

        Args:
            user_id: ID пользователя
            country_name: Название страны
            potential_project: Информация о потенциальном проекте

        Returns:
            Dict[str, Any]: Информация о созданном проекте
        """
        # Извлекаем данные о проекте
        project_name = potential_project.get("name", "")
        project_category = potential_project.get("category", "строительство")
        scale = potential_project.get("scale", 3)

        # Оцениваем технологический уровень страны
        stats = db.get_player_stats(user_id)
        technology_level = stats.get("технологичность", 1)

        # Создаем проект
        return ProjectManager.create_project(
            user_id, country_name, project_name, project_category, "", scale, technology_level)

    @staticmethod
    @log_function_call
    def get_project_details(user_id: int, project_id: str) -> Optional[Dict[str, Any]]:
        """
        Получает детальную информацию о проекте.

        Args:
            user_id: ID пользователя
            project_id: ID проекта

        Returns:
            Optional[Dict[str, Any]]: Информация о проекте или None, если проект не найден
        """
        # Получаем данные о стране из Chroma
        country_data = chroma.get_all_country_data(user_id)

        # Извлекаем проекты
        projects = country_data.get('projects', [])

        # Ищем проект с указанным ID
        for project in projects:
            metadata = project.get('metadata', {})
            if metadata.get('id') == project_id:
                # Обновляем прогресс проекта
                start_year = metadata.get('start_year', 0)
                duration = metadata.get('duration', 10)

                progress, remaining_years = calculate_project_progress(start_year, duration)

                # Обновляем метаданные
                metadata['progress'] = progress
                metadata['remaining_years'] = remaining_years

                return {
                    'text': project.get('text', ''),
                    'metadata': metadata
                }

        return None


# Экспортируем функции для удобного доступа
create_project = ProjectManager.create_project
get_projects = ProjectManager.get_projects
update_projects_progress = ProjectManager.update_projects_progress
handle_project_completion = ProjectManager.handle_project_completion
extract_potential_projects = ProjectManager.extract_potential_projects
confirm_project_creation = ProjectManager.confirm_project_creation
get_project_details = ProjectManager.get_project_details
