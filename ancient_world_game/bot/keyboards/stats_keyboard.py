from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.callback_data import CallbackData
from config.game_constants import STATS

# CallbackData для взаимодействия с характеристиками
stats_cb = CallbackData("stats", "action", "stat_name")

# CallbackData для действий с характеристиками
stat_action_cb = CallbackData("stat_action", "action", "stat_name", "value")

def get_stats_keyboard(player_stats=None, selected_stat=None):
    """
    Создает инлайн-клавиатуру с характеристиками страны

    Args:
        player_stats (dict): Словарь с текущими значениями характеристик игрока
        selected_stat (str): Имя выбранной характеристики (для подсветки)

    Returns:
        InlineKeyboardMarkup: Клавиатура с характеристиками
    """
    markup = InlineKeyboardMarkup(row_width=1)

    # Если статистика не предоставлена, создаем клавиатуру без значений
    if player_stats is None:
        for stat in STATS:
            button_text = f"{stat_emoji(stat)} {stat.capitalize()}"
            markup.add(InlineKeyboardButton(
                button_text,
                callback_data=stats_cb.new(action="view", stat_name=stat)
            ))
    else:
        # Создаем клавиатуру с текущими значениями
        for stat in STATS:
            stat_value = player_stats.get(stat, 0)
            # Если это выбранная характеристика, добавляем маркер
            if selected_stat and stat == selected_stat:
                button_text = f"➡️ {stat_emoji(stat)} {stat.capitalize()}: {stat_value}"
            else:
                button_text = f"{stat_emoji(stat)} {stat.capitalize()}: {stat_value}"

            markup.add(InlineKeyboardButton(
                button_text,
                callback_data=stats_cb.new(action="view", stat_name=stat)
            ))

    # Добавляем кнопки навигации
    markup.row(
        InlineKeyboardButton("🔄 Обновить", callback_data=stats_cb.new(action="refresh", stat_name="all")),
        InlineKeyboardButton("🔙 Назад", callback_data=stats_cb.new(action="back", stat_name="none"))
    )

    return markup

def get_stat_detail_keyboard(stat_name, stat_value=0):
    """
    Создает клавиатуру для детального просмотра характеристики

    Args:
        stat_name (str): Название характеристики
        stat_value (int): Текущее значение характеристики

    Returns:
        InlineKeyboardMarkup: Клавиатура для детального просмотра
    """
    markup = InlineKeyboardMarkup(row_width=3)

    # Кнопки для управления характеристикой (для администраторов)
    markup.row(
        InlineKeyboardButton("-10", callback_data=stat_action_cb.new(
            action="change", stat_name=stat_name, value=-10)),
        InlineKeyboardButton("-5", callback_data=stat_action_cb.new(
            action="change", stat_name=stat_name, value=-5)),
        InlineKeyboardButton("-1", callback_data=stat_action_cb.new(
            action="change", stat_name=stat_name, value=-1))
    )

    # Кнопка с текущим значением
    markup.add(InlineKeyboardButton(
        f"{stat_value}",
        callback_data=stat_action_cb.new(action="none", stat_name=stat_name, value=0)
    ))

    # Кнопки для увеличения характеристики
    markup.row(
        InlineKeyboardButton("+1", callback_data=stat_action_cb.new(
            action="change", stat_name=stat_name, value=1)),
        InlineKeyboardButton("+5", callback_data=stat_action_cb.new(
            action="change", stat_name=stat_name, value=5)),
        InlineKeyboardButton("+10", callback_data=stat_action_cb.new(
            action="change", stat_name=stat_name, value=10))
    )

    # Кнопка сброса и возврата
    markup.row(
        InlineKeyboardButton("🔄 Сбросить", callback_data=stat_action_cb.new(
            action="reset", stat_name=stat_name, value=0)),
        InlineKeyboardButton("🔙 Назад", callback_data=stats_cb.new(
            action="back_to_list", stat_name="none"))
    )

    return markup

def get_country_stats_keyboard(player_stats=None):
    """
    Создает клавиатуру с общим обзором характеристик страны

    Args:
        player_stats (dict): Словарь с текущими значениями характеристик игрока

    Returns:
        InlineKeyboardMarkup: Клавиатура с общим обзором характеристик
    """
    markup = InlineKeyboardMarkup(row_width=2)

    if player_stats:
        # Группируем характеристики парами для компактности
        stats_pairs = [STATS[i:i+2] for i in range(0, len(STATS), 2)]

        for pair in stats_pairs:
            row_buttons = []
            for stat in pair:
                stat_value = player_stats.get(stat, 0)
                button_text = f"{stat_emoji(stat)} {stat.capitalize()}: {stat_value}"
                row_buttons.append(InlineKeyboardButton(
                    button_text,
                    callback_data=stats_cb.new(action="view", stat_name=stat)
                ))
            markup.row(*row_buttons)

    # Добавляем кнопки действий
    markup.row(
        InlineKeyboardButton("📊 Подробнее", callback_data=stats_cb.new(action="details", stat_name="all")),
        InlineKeyboardButton("📈 График", callback_data=stats_cb.new(action="chart", stat_name="all"))
    )

    # Кнопка возврата
    markup.add(
        InlineKeyboardButton("🔙 Назад", callback_data=stats_cb.new(action="back", stat_name="none"))
    )

    return markup

def get_stats_comparison_keyboard(available_players):
    """
    Создает клавиатуру для сравнения характеристик с другими игроками

    Args:
        available_players (list): Список доступных для сравнения игроков

    Returns:
        InlineKeyboardMarkup: Клавиатура со списком игроков для сравнения
    """
    markup = InlineKeyboardMarkup(row_width=1)

    # Добавляем кнопки для каждого игрока
    for player in available_players:
        player_id = player.get('user_id')
        country_name = player.get('country_name', 'Неизвестная страна')

        markup.add(InlineKeyboardButton(
            f"🌍 {country_name}",
            callback_data=stats_cb.new(action="compare", stat_name=player_id)
        ))

    # Кнопка возврата
    markup.add(
        InlineKeyboardButton("🔙 Назад", callback_data=stats_cb.new(action="back", stat_name="none"))
    )

    return markup

def stat_emoji(stat_name):
    """
    Возвращает эмодзи для соответствующей характеристики

    Args:
        stat_name (str): Название характеристики

    Returns:
        str: Эмодзи
    """
    # Словарь с эмодзи для каждой характеристики
    emoji_map = {
        "экономика": "💰",
        "военное дело": "⚔️",
        "религия и культура": "🏛",
        "управление и право": "⚖️",
        "строительство и инфраструктура": "🏗",
        "внешняя политика": "🌐",
        "общественные отношения": "👥",
        "территория": "🗺",
        "технологичность": "🔬"
    }

    # Возвращаем соответствующий эмодзи или вопросительный знак, если не найден
    return emoji_map.get(stat_name, "❓")

def get_radar_chart_settings_keyboard():
    """
    Создает клавиатуру с настройками для радарной диаграммы

    Returns:
        InlineKeyboardMarkup: Клавиатура с настройками диаграммы
    """
    markup = InlineKeyboardMarkup(row_width=2)

    # Добавляем кнопки для настройки отображения
    markup.row(
        InlineKeyboardButton("🔄 Обновить", callback_data=stats_cb.new(action="refresh_chart", stat_name="all")),
        InlineKeyboardButton("📊 Линейный график", callback_data=stats_cb.new(action="line_chart", stat_name="all"))
    )

    # Кнопки для выбора периода
    markup.row(
        InlineKeyboardButton("📅 За неделю", callback_data=stats_cb.new(action="chart_week", stat_name="all")),
        InlineKeyboardButton("📅 За месяц", callback_data=stats_cb.new(action="chart_month", stat_name="all"))
    )

    # Кнопка для сравнения с другими игроками
    markup.add(
        InlineKeyboardButton("🔄 Сравнить с другими", callback_data=stats_cb.new(action="compare_menu", stat_name="all"))
    )

    # Кнопка возврата
    markup.add(
        InlineKeyboardButton("🔙 Назад", callback_data=stats_cb.new(action="back", stat_name="none"))
    )

    return markup

# Экспортируем все наши клавиатуры
__all__ = [
    'get_stats_keyboard',
    'get_stat_detail_keyboard',
    'get_country_stats_keyboard',
    'get_stats_comparison_keyboard',
    'get_radar_chart_settings_keyboard',
    'stats_cb',
    'stat_action_cb'
]
