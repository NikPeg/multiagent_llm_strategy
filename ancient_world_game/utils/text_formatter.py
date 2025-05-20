"""
text_formatter.py - Утилиты для форматирования текстовых сообщений в боте.
"""

from typing import Dict, List, Any, Optional
import textwrap
import html
import re


def format_country_stats(stats: Dict[str, int]) -> str:
    """
    Форматирует характеристики страны для отображения.

    Args:
        stats: Словарь характеристик вида {"экономика": 3, "военное дело": 4, ...}

    Returns:
        Отформатированная строка с характеристиками
    """
    result = "📊 <b>Характеристики государства:</b>\n\n"

    stat_emojis = {
        "экономика": "💰",
        "военное дело": "⚔️",
        "религия и культура": "🏛️",
        "управление и право": "👑",
        "строительство и инфраструктура": "🏗️",
        "внешняя политика": "🌐",
        "общественные отношения": "👥",
        "территория": "🗺️",
        "технологичность": "⚙️"
    }

    for stat, value in stats.items():
        emoji = stat_emojis.get(stat.lower(), "📋")
        stars = "★" * value + "☆" * (5 - value)
        result += f"{emoji} <b>{stat.capitalize()}:</b> {stars} ({value}/5)\n"

    return result


def format_country_description(name: str, description: str, problems: Optional[List[str]] = None) -> str:
    """
    Форматирует описание страны.

    Args:
        name: Название страны
        description: Основное описание страны
        problems: Список текущих проблем (опционально)

    Returns:
        Отформатированная строка с описанием
    """
    result = f"🏛️ <b>{html.escape(name)}</b>\n\n"
    result += f"{html.escape(description)}\n"

    if problems and len(problems) > 0:
        result += "\n<b>Текущие проблемы:</b>\n"
        for i, problem in enumerate(problems, 1):
            result += f"  {i}. {html.escape(problem)}\n"

    return result


def format_project_status(project_name: str, progress: int, years_left: int) -> str:
    """
    Форматирует статус проекта.

    Args:
        project_name: Название проекта
        progress: Процент завершения (0-100)
        years_left: Оставшееся количество лет

    Returns:
        Отформатированная строка со статусом проекта
    """
    progress_bar = generate_progress_bar(progress)
    return f"🏗️ <b>{html.escape(project_name)}</b>: {progress}% завершено, осталось {years_left} лет\n{progress_bar}"


def format_event_message(event_text: str, severity: str) -> str:
    """
    Форматирует сообщение о событии.

    Args:
        event_text: Текст события
        severity: Тип события ("good", "neutral", "bad", "very_good", "very_bad")

    Returns:
        Отформатированное сообщение о событии
    """
    emojis = {
        "very_good": "🎉",
        "good": "✨",
        "neutral": "📢",
        "bad": "⚠️",
        "very_bad": "🔥"
    }

    emoji = emojis.get(severity, "📢")

    return f"{emoji} <b>СОБЫТИЕ</b> {emoji}\n\n{html.escape(event_text)}"


def format_divine_message(message: str) -> str:
    """
    Форматирует божественное послание (от админа).

    Args:
        message: Текст послания

    Returns:
        Отформатированное божественное послание
    """
    return f"☀️ <b>БОЖЕСТВЕННОЕ ЗНАМЕНИЕ</b> ☀️\n\n<i>{html.escape(message)}</i>"


def format_aspect_details(aspect: str, details: str) -> str:
    """
    Форматирует детальную информацию об аспекте государства.

    Args:
        aspect: Название аспекта
        details: Детальное описание

    Returns:
        Отформатированная информация об аспекте
    """
    aspect_emojis = {
        "экономика": "💰",
        "военное дело": "⚔️",
        "религия и культура": "🏛️",
        "управление и право": "👑",
        "строительство и инфраструктура": "🏗️",
        "внешняя политика": "🌐",
        "общественные отношения": "👥",
        "территория": "🗺️",
        "технологичность": "⚙️"
    }

    emoji = aspect_emojis.get(aspect.lower(), "📋")
    return f"{emoji} <b>{aspect.upper()}</b> {emoji}\n\n{html.escape(details)}"


def generate_progress_bar(percentage: int, length: int = 10) -> str:
    """
    Генерирует текстовый прогресс-бар.

    Args:
        percentage: Процент прогресса (0-100)
        length: Длина прогресс-бара

    Returns:
        Строка с прогресс-баром
    """
    filled = int(percentage / 100 * length)
    return "▓" * filled + "░" * (length - filled)


def truncate_text(text: str, max_length: int = 4000) -> str:
    """
    Обрезает текст до указанной длины если необходимо.

    Args:
        text: Исходный текст
        max_length: Максимальная длина

    Returns:
        Обрезанный текст
    """
    if len(text) <= max_length:
        return text

    return text[:max_length-3] + "..."


def format_war_report(attacker: str, defender: str, result: str, details: str) -> str:
    """
    Форматирует отчет о военных действиях.

    Args:
        attacker: Название атакующей страны
        defender: Название обороняющейся страны
        result: Результат конфликта
        details: Детали сражения

    Returns:
        Отформатированный отчет о войне
    """
    return (
        f"⚔️ <b>ВОЕННЫЙ КОНФЛИКТ</b> ⚔️\n\n"
        f"<b>{html.escape(attacker)}</b> ⚔️ <b>{html.escape(defender)}</b>\n\n"
        f"<b>Исход:</b> {html.escape(result)}\n\n"
        f"<b>Детали:</b>\n{html.escape(details)}"
    )


def format_help_message() -> str:
    """
    Форматирует сообщение помощи для пользователей.

    Returns:
        Отформатированная справка
    """
    return (
        "<b>📜 Справка по игре 'Древний Мир'</b>\n\n"
        "<b>Основные команды:</b>\n"
        "/start - Начать игру или вернуться в главное меню\n"
        "/who - Информация о вашей стране\n"
        "/who @username - Информация о чужой стране\n"
        "/future - Предсказание о будущем вашей страны\n"
        "/goal - Забить гол (игровая механика)\n"
        "/stat - Статистика забитых голов\n\n"
        "<b>Как играть:</b>\n"
        "• Управляйте своей страной через отправку приказов\n"
        "• Развивайте различные аспекты государства\n"
        "• Взаимодействуйте с другими игроками\n"
        "• Реагируйте на случайные события\n\n"
        "<b>Подсказка:</b> Используйте кнопки внизу экрана для быстрого доступа к информации"
    )


def clean_text_for_storage(text: str) -> str:
    """
    Очищает текст от лишних пробелов и форматирования для хранения в базе.

    Args:
        text: Исходный текст

    Returns:
        Очищенный текст
    """
    # Удаление лишних пробелов и переносов строк
    text = re.sub(r'\s+', ' ', text.strip())
    # Удаление специальных символов HTML
    text = html.unescape(text)
    return text
