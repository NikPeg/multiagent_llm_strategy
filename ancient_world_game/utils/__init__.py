"""
__init__.py для модуля utils.

Экспортирует основные утилиты для использования в других модулях.
Позволяет импортировать функции напрямую из пакета utils.
"""

# Импорт из text_formatter.py
from .text_formatter import (
    format_country_stats,
    format_country_description,
    format_project_status,
    format_event_message,
    format_divine_message,
    format_aspect_details,
    format_war_report,
    format_help_message,
    clean_text_for_storage,
    truncate_text
)

# Импорт из diagram_generator.py
from .diagram_generator import (
    generate_radar_chart,
    generate_comparative_chart,
    generate_timeline_chart,
    generate_resources_chart
)

# Импорт из time_utils.py
from .time_utils import (
    get_current_game_year,
    format_game_year,
    calculate_project_duration,
    calculate_project_progress,
    estimate_project_completion_year,
    GameScheduler,
    format_time_period,
    days_since_real_start,
    is_new_game_day,
    reset_game_time,
    measure_execution_time
)

# Импорт из logger.py
from .logger import (
    setup_logging,
    log_function_call,
    log_bot_message,
    log_admin_action,
    log_game_event,
    log_error,
    log_model_interaction,
    get_logger,
    enable_debug_logging,
    disable_debug_logging
)

# Создаем экземпляр планировщика для доступа из других модулей
game_scheduler = GameScheduler()

# Получаем настроенный логгер
logger = get_logger()

__all__ = [
    # Из text_formatter.py
    'format_country_stats', 'format_country_description', 'format_project_status',
    'format_event_message', 'format_divine_message', 'format_aspect_details',
    'format_war_report', 'format_help_message', 'clean_text_for_storage',
    'truncate_text',

    # Из diagram_generator.py
    'generate_radar_chart', 'generate_comparative_chart', 'generate_timeline_chart',
    'generate_resources_chart',

    # Из time_utils.py
    'get_current_game_year', 'format_game_year', 'calculate_project_duration',
    'calculate_project_progress', 'estimate_project_completion_year', 'GameScheduler',
    'format_time_period', 'days_since_real_start', 'is_new_game_day',
    'reset_game_time', 'measure_execution_time', 'game_scheduler',

    # Из logger.py
    'setup_logging', 'log_function_call', 'log_bot_message', 'log_admin_action',
    'log_game_event', 'log_error', 'log_model_interaction', 'get_logger',
    'enable_debug_logging', 'disable_debug_logging', 'logger'
]
