"""
__init__.py для модуля ai.

Экспортирует основные компоненты искусственного интеллекта и обработки естественного языка
для использования в других модулях приложения.
"""

from .model_interface import model, get_model
from .rag_system import rag_system, get_rag_system
from .prompt_templates import (
    get_analyze_action_prompt,
    get_update_aspect_prompt,
    get_evaluate_stats_prompt,
    get_generate_event_prompt,
    get_predict_future_prompt,
    get_generate_problems_prompt,
    get_daily_update_prompt,
    get_check_era_prompt,
    get_initial_country_description_prompt,
    get_command_response_prompt,
    get_aspect_details_prompt,
    get_divine_message_prompt,
    get_project_completion_prompt,
    get_clarification_prompt,
    get_interact_with_country_prompt
)
from .output_parser import (
    ModelResponseParser,
    parse_action_analysis,
    parse_event_generation,
    parse_daily_update,
    parse_era_check,
    parse_initial_country_description,
    parse_project_completion,
    parse_interact_with_country,
    extract_stats_from_text,
    extract_projects_from_text,
    extract_problems_from_text,
    extract_resources_from_text
)
from .validators import is_era_compatible, suggest_alternative

# Создаем парсер ответов для удобного доступа
response_parser = ModelResponseParser()

__all__ = [
    # Интерфейс языковой модели
    'model',
    'get_model',

    # RAG-система
    'rag_system',
    'get_rag_system',

    # Шаблоны запросов
    'get_analyze_action_prompt',
    'get_update_aspect_prompt',
    'get_evaluate_stats_prompt',
    'get_generate_event_prompt',
    'get_predict_future_prompt',
    'get_generate_problems_prompt',
    'get_daily_update_prompt',
    'get_check_era_prompt',
    'get_initial_country_description_prompt',
    'get_command_response_prompt',
    'get_aspect_details_prompt',
    'get_divine_message_prompt',
    'get_project_completion_prompt',
    'get_clarification_prompt',
    'get_interact_with_country_prompt',

    # Парсеры ответов
    'response_parser',
    'parse_action_analysis',
    'parse_event_generation',
    'parse_daily_update',
    'parse_era_check',
    'parse_initial_country_description',
    'parse_project_completion',
    'parse_interact_with_country',
    'extract_stats_from_text',
    'extract_projects_from_text',
    'extract_problems_from_text',
    'extract_resources_from_text',

    # Валидаторы
    'is_era_compatible',
    'suggest_alternative'
]

# Убедимся, что модель готова к использованию при импорте модуля
# Это может занять некоторое время при первом импорте
try:
    # Простой запрос для инициализации модели
    model.generate_response("Инициализация модели DeepSeek", max_tokens=10)
except Exception as e:
    # В случае ошибки инициализации модели логируем её, но не прерываем импорт
    # Это позволит приложению загрузиться, даже если модель временно недоступна
    import logging
    logging.error(f"Ошибка инициализации модели: {e}")
    logging.warning("Модуль AI загружен с ошибками. Функциональность может быть ограничена.")
