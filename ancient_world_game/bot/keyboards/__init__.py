from .main_menu import (
    get_main_menu,
    get_player_action_menu,
    get_settings_menu,
    get_profile_menu,
    get_admin_menu,
    get_help_menu,
    get_confirmation_keyboard,
    get_game_registration_keyboard,
    main_menu_cb,
    game_cb,
    settings_cb,
    profile_cb
)

from .stats_keyboard import (
    get_stats_keyboard,
    get_stat_detail_keyboard,
    get_country_stats_keyboard,
    get_stats_comparison_keyboard,
    get_radar_chart_settings_keyboard,
    stats_cb,
    stat_action_cb
)

from .action_buttons import (
    get_action_keyboard,
    get_order_confirmation_keyboard,
    get_action_suggestions_keyboard,
    get_action_categories_keyboard,
    get_order_history_keyboard,
    get_order_detail_keyboard,
    get_quick_action_buttons,
    get_suggestion_examples_keyboard,
    action_cb,
    order_cb
)

# Экспортируем все клавиатуры для удобного импорта
__all__ = [
    # Из main_menu.py
    'get_main_menu',
    'get_player_action_menu',
    'get_settings_menu',
    'get_profile_menu',
    'get_admin_menu',
    'get_help_menu',
    'get_confirmation_keyboard',
    'get_game_registration_keyboard',
    'main_menu_cb',
    'game_cb',
    'settings_cb',
    'profile_cb',

    # Из stats_keyboard.py
    'get_stats_keyboard',
    'get_stat_detail_keyboard',
    'get_country_stats_keyboard',
    'get_stats_comparison_keyboard',
    'get_radar_chart_settings_keyboard',
    'stats_cb',
    'stat_action_cb',

    # Из action_buttons.py
    'get_action_keyboard',
    'get_order_confirmation_keyboard',
    'get_action_suggestions_keyboard',
    'get_action_categories_keyboard',
    'get_order_history_keyboard',
    'get_order_detail_keyboard',
    'get_quick_action_buttons',
    'get_suggestion_examples_keyboard',
    'action_cb',
    'order_cb'
]

# Словарь для маппинга callback_data к обработчикам
callback_map = {
    main_menu_cb.prefix: 'process_main_menu_callback',
    game_cb.prefix: 'process_game_callback',
    settings_cb.prefix: 'process_settings_callback',
    profile_cb.prefix: 'process_profile_callback',
    stats_cb.prefix: 'process_stats_callback',
    stat_action_cb.prefix: 'process_stat_action_callback',
    action_cb.prefix: 'process_action_callback',
    order_cb.prefix: 'process_order_callback'
}

def get_callback_handler(callback_data):
    """
    Возвращает имя функции обработчика для данного callback_data

    Args:
        callback_data (str): Полученный callback_data

    Returns:
        str: Имя функции обработчика или None, если обработчик не найден
    """
    if not callback_data:
        return None

    # Извлекаем префикс (часть до первого ':')
    parts = callback_data.split(':')
    if not parts:
        return None

    prefix = parts[0]

    # Возвращаем имя обработчика или None
    return callback_map.get(prefix)
