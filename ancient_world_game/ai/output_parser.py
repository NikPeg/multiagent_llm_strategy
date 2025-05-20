"""
output_parser.py - Модуль для парсинга и обработки ответов языковой модели.
Преобразует текстовые ответы модели в структурированные данные для использования в игровой логике.
"""

import re
from typing import Dict, List, Any, Tuple, Optional, Union
import json

from utils import logger, log_function_call


@log_function_call
def parse_action_analysis(response: str) -> Dict[str, Any]:
    """
    Парсит ответ модели с анализом действия игрока.

    Args:
        response: Текстовый ответ модели

    Returns:
        Dict[str, Any]: Структурированный анализ действия
    """
    result = {
        "execution": "",
        "result": "",
        "consequences": "",
        "changes": {}
    }

    # Шаблоны для извлечения секций
    execution_pattern = r"ВЫПОЛНЕНИЕ:\s*(.*?)(?=РЕЗУЛЬТАТ:|ПОСЛЕДСТВИЯ:|ИЗМЕНЕНИЯ:|$)"
    result_pattern = r"РЕЗУЛЬТАТ:\s*(.*?)(?=ВЫПОЛНЕНИЕ:|ПОСЛЕДСТВИЯ:|ИЗМЕНЕНИЯ:|$)"
    consequences_pattern = r"ПОСЛЕДСТВИЯ:\s*(.*?)(?=ВЫПОЛНЕНИЕ:|РЕЗУЛЬТАТ:|ИЗМЕНЕНИЯ:|$)"

    # Извлекаем основные секции
    execution_match = re.search(execution_pattern, response, re.DOTALL)
    if execution_match:
        result["execution"] = execution_match.group(1).strip()

    result_match = re.search(result_pattern, response, re.DOTALL)
    if result_match:
        result["result"] = result_match.group(1).strip()

    consequences_match = re.search(consequences_pattern, response, re.DOTALL)
    if consequences_match:
        result["consequences"] = consequences_match.group(1).strip()

    # Извлекаем изменения в аспектах
    changes_section = ""
    if "ИЗМЕНЕНИЯ:" in response:
        changes_section = response.split("ИЗМЕНЕНИЯ:", 1)[1].strip()

    if changes_section:
        # Ищем строки вида "- аспект: изменение"
        changes_pattern = r"-\s*([^:]+):\s*(.+?)(?=\n-|\n\n|$)"
        changes_matches = re.findall(changes_pattern, changes_section, re.DOTALL)

        for aspect, change in changes_matches:
            aspect = aspect.strip().lower()
            change = change.strip()
            result["changes"][aspect] = change

    return result


@log_function_call
def parse_event_generation(response: str) -> Dict[str, Any]:
    """
    Парсит ответ модели с генерацией события.

    Args:
        response: Текстовый ответ модели

    Returns:
        Dict[str, Any]: Структурированное описание события
    """
    event = {
        "title": "",
        "description": "",
        "consequences": "",
        "affected_aspects": {}
    }

    # Шаблоны для извлечения секций
    title_pattern = r"ЗАГОЛОВОК:\s*(.*?)(?=СОБЫТИЕ:|ПОСЛЕДСТВИЯ:|ЗАТРОНУТЫЕ АСПЕКТЫ:|$)"
    description_pattern = r"СОБЫТИЕ:\s*(.*?)(?=ЗАГОЛОВОК:|ПОСЛЕДСТВИЯ:|ЗАТРОНУТЫЕ АСПЕКТЫ:|$)"
    consequences_pattern = r"ПОСЛЕДСТВИЯ:\s*(.*?)(?=ЗАГОЛОВОК:|СОБЫТИЕ:|ЗАТРОНУТЫЕ АСПЕКТЫ:|$)"

    # Извлекаем основные секции
    title_match = re.search(title_pattern, response, re.DOTALL)
    if title_match:
        event["title"] = title_match.group(1).strip()

    description_match = re.search(description_pattern, response, re.DOTALL)
    if description_match:
        event["description"] = description_match.group(1).strip()

    consequences_match = re.search(consequences_pattern, response, re.DOTALL)
    if consequences_match:
        event["consequences"] = consequences_match.group(1).strip()

    # Извлекаем затронутые аспекты
    aspects_section = ""
    if "ЗАТРОНУТЫЕ АСПЕКТЫ:" in response:
        aspects_section = response.split("ЗАТРОНУТЫЕ АСПЕКТЫ:", 1)[1].strip()

    if aspects_section:
        # Ищем строки вида "- аспект: влияние"
        aspects_pattern = r"-\s*([^:]+):\s*(.+?)(?=\n-|\n\n|$)"
        aspects_matches = re.findall(aspects_pattern, aspects_section, re.DOTALL)

        for aspect, impact in aspects_matches:
            aspect = aspect.strip().lower()
            impact = impact.strip()
            event["affected_aspects"][aspect] = impact

    return event


@log_function_call
def parse_daily_update(response: str) -> Dict[str, Any]:
    """
    Парсит ответ модели с ежедневным обновлением страны.

    Args:
        response: Текстовый ответ модели

    Returns:
        Dict[str, Any]: Структурированное описание обновления
    """
    update = {
        "year": "",
        "general_changes": "",
        "aspect_changes": {}
    }

    # Извлекаем год
    year_match = re.search(r"ГОД:\s*(.+?)(?=\n|$)", response)
    if year_match:
        update["year"] = year_match.group(1).strip()

    # Извлекаем общие изменения
    general_changes_match = re.search(r"ОБЩИЕ ИЗМЕНЕНИЯ:\s*(.+?)(?=\nИЗМЕНЕНИЯ ПО АСПЕКТАМ:|\n\n|$)", response, re.DOTALL)
    if general_changes_match:
        update["general_changes"] = general_changes_match.group(1).strip()

    # Извлекаем изменения по аспектам
    aspects_section = ""
    if "ИЗМЕНЕНИЯ ПО АСПЕКТАМ:" in response:
        aspects_section = response.split("ИЗМЕНЕНИЯ ПО АСПЕКТАМ:", 1)[1].strip()

    if aspects_section:
        # Ищем строки вида "- аспект: изменение"
        aspects_pattern = r"-\s*([^:]+):\s*(.+?)(?=\n-|\n\n|$)"
        aspects_matches = re.findall(aspects_pattern, aspects_section, re.DOTALL)

        for aspect, change in aspects_matches:
            aspect = aspect.strip().lower()
            change = change.strip()
            update["aspect_changes"][aspect] = change

    return update


@log_function_call
def parse_era_check(response: str) -> Tuple[bool, str]:
    """
    Парсит ответ модели с проверкой соответствия эпохе.

    Args:
        response: Текстовый ответ модели

    Returns:
        Tuple[bool, str]: (соответствует ли сообщение эпохе, комментарий)
    """
    is_compatible = False
    comment = "Не удалось определить соответствие эпохе"

    # Ищем ответ о соответствии
    compatible_match = re.search(r"СООТВЕТСТВУЕТ:\s*(.+?)(?=\n|$)", response, re.IGNORECASE)
    if compatible_match:
        answer = compatible_match.group(1).strip().lower()
        is_compatible = answer in ["да", "yes", "true", "соответствует"]

    # Ищем комментарий
    comment_match = re.search(r"КОММЕНТАРИЙ:\s*(.+?)(?=\n\n|$)", response, re.DOTALL | re.IGNORECASE)
    if comment_match:
        comment = comment_match.group(1).strip()

    return is_compatible, comment


@log_function_call
def parse_initial_country_description(response: str) -> Dict[str, Any]:
    """
    Парсит ответ модели с начальным описанием страны.

    Args:
        response: Текстовый ответ модели

    Returns:
        Dict[str, Any]: Структурированное описание страны
    """
    result = {
        "description": "",
        "problems": []
    }

    # Извлекаем описание
    if "ОПИСАНИЕ:" in response:
        parts = response.split("ОПИСАНИЕ:", 1)
        if "ПРОБЛЕМЫ:" in parts[1]:
            result["description"] = parts[1].split("ПРОБЛЕМЫ:", 1)[0].strip()
        else:
            result["description"] = parts[1].strip()

    # Извлекаем проблемы
    problems_section = ""
    if "ПРОБЛЕМЫ:" in response:
        problems_section = response.split("ПРОБЛЕМЫ:", 1)[1].strip()

    if problems_section:
        # Ищем строки, начинающиеся с дефиса
        problems = re.findall(r"-\s*(.+?)(?=\n-|\n\n|$)", problems_section, re.DOTALL)
        result["problems"] = [problem.strip() for problem in problems if problem.strip()]

    return result


@log_function_call
def parse_project_completion(response: str) -> Dict[str, Any]:
    """
    Парсит ответ модели с завершением проекта.

    Args:
        response: Текстовый ответ модели

    Returns:
        Dict[str, Any]: Структурированное описание завершения проекта
    """
    result = {
        "event": "",
        "impact": "",
        "aspect_changes": {}
    }

    # Извлекаем описание события
    event_match = re.search(r"СОБЫТИЕ:\s*(.+?)(?=\nВЛИЯНИЕ:|\nИЗМЕНЕНИЯ В АСПЕКТАХ:|\n\n|$)", response, re.DOTALL)
    if event_match:
        result["event"] = event_match.group(1).strip()

    # Извлекаем влияние
    impact_match = re.search(r"ВЛИЯНИЕ:\s*(.+?)(?=\nСОБЫТИЕ:|\nИЗМЕНЕНИЯ В АСПЕКТАХ:|\n\n|$)", response, re.DOTALL)
    if impact_match:
        result["impact"] = impact_match.group(1).strip()

    # Извлекаем изменения в аспектах
    aspects_section = ""
    if "ИЗМЕНЕНИЯ В АСПЕКТАХ:" in response:
        aspects_section = response.split("ИЗМЕНЕНИЯ В АСПЕКТАХ:", 1)[1].strip()

    if aspects_section:
        # Ищем строки вида "- аспект: изменение"
        aspects_pattern = r"-\s*([^:]+):\s*(.+?)(?=\n-|\n\n|$)"
        aspects_matches = re.findall(aspects_pattern, aspects_section, re.DOTALL)

        for aspect, change in aspects_matches:
            aspect = aspect.strip().lower()
            change = change.strip()
            result["aspect_changes"][aspect] = change

    return result


@log_function_call
def parse_interact_with_country(response: str) -> Dict[str, Any]:
    """
    Парсит ответ модели с взаимодействием с другой страной.

    Args:
        response: Текстовый ответ модели

    Returns:
        Dict[str, Any]: Структурированное описание взаимодействия
    """
    result = {
        "meeting": "",
        "result": "",
        "relations": "",
        "influence": ""
    }

    # Извлекаем описание встречи
    meeting_match = re.search(r"ВСТРЕЧА:\s*(.+?)(?=\nРЕЗУЛЬТАТ:|\nОТНОШЕНИЯ:|\nВЛИЯНИЕ:|\n\n|$)", response, re.DOTALL)
    if meeting_match:
        result["meeting"] = meeting_match.group(1).strip()

    # Извлекаем результат
    result_match = re.search(r"РЕЗУЛЬТАТ:\s*(.+?)(?=\nВСТРЕЧА:|\nОТНОШЕНИЯ:|\nВЛИЯНИЕ:|\n\n|$)", response, re.DOTALL)
    if result_match:
        result["result"] = result_match.group(1).strip()

    # Извлекаем отношения
    relations_match = re.search(r"ОТНОШЕНИЯ:\s*(.+?)(?=\nВСТРЕЧА:|\nРЕЗУЛЬТАТ:|\nВЛИЯНИЕ:|\n\n|$)", response, re.DOTALL)
    if relations_match:
        result["relations"] = relations_match.group(1).strip()

    # Извлекаем влияние
    influence_match = re.search(r"ВЛИЯНИЕ:\s*(.+?)(?=\nВСТРЕЧА:|\nРЕЗУЛЬТАТ:|\nОТНОШЕНИЯ:|\n\n|$)", response, re.DOTALL)
    if influence_match:
        result["influence"] = influence_match.group(1).strip()

    return result


@log_function_call
def extract_stats_from_text(response: str) -> Dict[str, int]:
    """
    Извлекает числовые оценки характеристик из текста модели.

    Args:
        response: Текстовый ответ модели

    Returns:
        Dict[str, int]: Словарь с оценками характеристик
    """
    stats = {}

    # Список всех возможных характеристик
    stat_names = [
        "экономика", "военное дело", "религия и культура",
        "управление и право", "строительство и инфраструктура",
        "внешняя политика", "общественные отношения",
        "территория", "технологичность"
    ]

    # Ищем строки вида "характеристика: число"
    for stat in stat_names:
        # Пробуем несколько вариантов регулярных выражений для повышения надежности
        patterns = [
            fr"{stat}:\s*(\d)",
            fr"{stat}\s*[-—:]\s*(\d)",
            fr"{stat}\s*[-—:]\s*(\d)/5",
            fr"{stat}\s*[-—:]\s*(\d) из 5"
        ]

        for pattern in patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                try:
                    value = int(match.group(1))
                    # Проверяем, что значение в допустимом диапазоне
                    if 1 <= value <= 5:
                        stats[stat] = value
                        break
                except ValueError:
                    # Если не удалось преобразовать в число, продолжаем поиск
                    continue

    # Заполняем отсутствующие характеристики значением по умолчанию (3)
    for stat in stat_names:
        if stat not in stats:
            stats[stat] = 3

    return stats


@log_function_call
def extract_projects_from_text(response: str) -> List[Dict[str, Any]]:
    """
    Извлекает информацию о проектах из текста модели.

    Args:
        response: Текстовый ответ модели

    Returns:
        List[Dict[str, Any]]: Список с информацией о проектах
    """
    projects = []

    # Ищем упоминания строительства или проектов
    project_mentions = [
        r"(строит(?:ь|ельство)|построить|возвести|создать|соорудить)\s+([^\.,:;]+)",
        r"(начать|инициировать|запустить)\s+(?:строительство|проект|создание)\s+([^\.,:;]+)",
        r"(проект|строительство)\s+([^\.,:;]+)",
    ]

    for pattern in project_mentions:
        matches = re.findall(pattern, response, re.IGNORECASE)
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

                projects.append({
                    "name": project_name.strip(),
                    "category": category,
                    "scale": scale
                })

    return projects


@log_function_call
def extract_problems_from_text(response: str) -> List[str]:
    """
    Извлекает проблемы из текста модели.

    Args:
        response: Текстовый ответ модели

    Returns:
        List[str]: Список проблем
    """
    problems = []

    # Сначала пробуем найти списки проблем
    if "ПРОБЛЕМЫ:" in response:
        problems_section = response.split("ПРОБЛЕМЫ:", 1)[1].strip()
        problem_items = re.findall(r"-\s*(.+?)(?=\n-|\n\n|$)", problems_section, re.DOTALL)
        if problem_items:
            return [problem.strip() for problem in problem_items if problem.strip()]

    # Если не нашли списки, ищем предложения, содержащие ключевые слова
    problem_keywords = [
        "проблем", "кризис", "угроз", "опасност", "недостат",
        "нехватк", "голод", "эпидеми", "восстани", "бунт",
        "недовольств", "разлад", "конфликт"
    ]

    sentences = re.split(r'[.!?]+', response)
    for sentence in sentences:
        sentence = sentence.strip()
        if any(keyword in sentence.lower() for keyword in problem_keywords):
            if len(sentence) > 15 and sentence not in problems:  # Минимальная длина проблемы
                problems.append(sentence)

    return problems[:5]  # Ограничиваем 5 проблемами


@log_function_call
def extract_resources_from_text(response: str) -> Dict[str, int]:
    """
    Извлекает информацию о ресурсах из текста модели.

    Args:
        response: Текстовый ответ модели

    Returns:
        Dict[str, int]: Словарь с ресурсами и их количеством
    """
    resources = {}

    # Список основных ресурсов древнего мира
    resource_types = [
        "золото", "дерево", "камень", "еда", "зерно", "рабы", "рабочая сила",
        "железо", "медь", "ткани", "специи", "лошади", "скот", "серебро"
    ]

    # Ищем упоминания ресурсов с числами
    for resource in resource_types:
        # Несколько шаблонов для поиска
        patterns = [
            fr"{resource}[а-я]*\s*[-:]?\s*(\d+)",
            fr"(\d+)\s*{resource}[а-я]*",
            fr"{resource}[а-я]*\s*в\s*количестве\s*(\d+)",
            fr"запас[а-я]*\s*{resource}[а-я]*\s*[-:]?\s*(\d+)"
        ]

        for pattern in patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            for match in matches:
                try:
                    amount = int(match)
                    # Если ресурс уже есть, берем максимальное значение
                    resources[resource] = max(resources.get(resource, 0), amount)
                except ValueError:
                    continue

    return resources


@log_function_call
def clean_and_normalize_text(text: str) -> str:
    """
    Очищает и нормализует текст для более надежного парсинга.

    Args:
        text: Исходный текст

    Returns:
        str: Очищенный и нормализованный текст
    """
    # Заменяем несколько переносов строк на один
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Заменяем множественные пробелы на один
    text = re.sub(r'\s{2,}', ' ', text)

    # Заменяем различные типы тире на стандартное
    text = text.replace('–', '-').replace('—', '-')

    # Нормализуем заголовки (убираем лишние символы)
    text = re.sub(r'([А-ЯA-Z][А-ЯA-Z\s]+):', r'\1:', text)

    return text.strip()


class ModelResponseParser:
    """
    Класс для обработки ответов модели с выбором подходящего парсера.
    """

    @staticmethod
    def parse(response: str, response_type: str) -> Any:
        """
        Парсит ответ модели в зависимости от типа ответа.

        Args:
            response: Текстовый ответ модели
            response_type: Тип ответа (action_analysis, event, era_check и т.д.)

        Returns:
            Any: Распарсенный ответ соответствующего типа
        """
        # Предварительная очистка и нормализация ответа
        normalized_response = clean_and_normalize_text(response)

        # Выбор подходящего парсера в зависимости от типа ответа
        parsers = {
            "action_analysis": parse_action_analysis,
            "event": parse_event_generation,
            "daily_update": parse_daily_update,
            "era_check": parse_era_check,
            "initial_description": parse_initial_country_description,
            "project_completion": parse_project_completion,
            "interaction": parse_interact_with_country,
            "stats": extract_stats_from_text,
            "projects": extract_projects_from_text,
            "problems": extract_problems_from_text,
            "resources": extract_resources_from_text
        }

        parser = parsers.get(response_type)
        if not parser:
            logger.warning(f"Неизвестный тип ответа: {response_type}")
            return normalized_response

        try:
            return parser(normalized_response)
        except Exception as e:
            logger.error(f"Ошибка при парсинге ответа типа {response_type}: {e}")
            return normalized_response
