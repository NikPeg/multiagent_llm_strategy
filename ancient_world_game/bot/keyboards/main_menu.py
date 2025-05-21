from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.callback_data import CallbackData

# CallbackData для кнопок основного меню
main_menu_cb = CallbackData("menu", "action")

# CallbackData для игровых действий
game_cb = CallbackData("game", "action")

# CallbackData для настроек
settings_cb = CallbackData("settings", "section")

# CallbackData для профиля
profile_cb = CallbackData("profile", "action")

def get_main_menu(is_player=False, is_admin=False):
    """
    Создает инлайн-клавиатуру с основным меню

    Args:
        is_player (bool): Является ли пользователь игроком
        is_admin (bool): Является ли пользователь администратором

    Returns:
        InlineKeyboardMarkup: Клавиатура с основным меню
    """
    markup = InlineKeyboardMarkup(row_width=2)

    # Базовые кнопки для всех пользователей
    markup.add(
        InlineKeyboardButton("🏛 Профиль", callback_data=profile_cb.new(action="view")),
        InlineKeyboardButton("⚙️ Настройки", callback_data=settings_cb.new(section="main"))
    )

    # Добавление кнопок для игроков
    if is_player:
        markup.add(
            InlineKeyboardButton("📜 Мои приказы", callback_data=game_cb.new(action="history")),
            InlineKeyboardButton("🔍 Отчет о стране", callback_data=game_cb.new(action="report"))
        )
        markup.add(
            InlineKeyboardButton("🎖 Отдать приказ", callback_data=game_cb.new(action="new_action"))
        )
    else:
        # Кнопка для регистрации в игре
        markup.add(
            InlineKeyboardButton("🎮 Стать игроком", callback_data=game_cb.new(action="register"))
        )

    # Добавление кнопок для администраторов
    if is_admin:
        markup.add(
            InlineKeyboardButton("👑 Панель администратора", callback_data=main_menu_cb.new(action="admin"))
        )

    # Кнопка справки
    markup.add(
        InlineKeyboardButton("❓ Помощь", callback_data=main_menu_cb.new(action="help"))
    )

    return markup

def get_player_action_menu():
    """
    Создает инлайн-клавиатуру с действиями игрока

    Returns:
        InlineKeyboardMarkup: Клавиатура с действиями игрока
    """
    markup = InlineKeyboardMarkup(row_width=2)

    markup.add(
        InlineKeyboardButton("📢 Отдать приказ", callback_data=game_cb.new(action="new_action")),
        InlineKeyboardButton("📋 История приказов", callback_data=game_cb.new(action="history"))
    )

    markup.add(
        InlineKeyboardButton("📊 Статистика страны", callback_data=game_cb.new(action="stats")),
        InlineKeyboardButton("📜 Отчет о стране", callback_data=game_cb.new(action="report"))
    )

    markup.add(
        InlineKeyboardButton("🔄 Вернуться в меню", callback_data=main_menu_cb.new(action="main"))
    )

    return markup

def get_settings_menu(is_subscribed=False):
    """
    Создает инлайн-клавиатуру с настройками

    Args:
        is_subscribed (bool): Подписан ли пользователь на уведомления

    Returns:
        InlineKeyboardMarkup: Клавиатура с настройками
    """
    markup = InlineKeyboardMarkup(row_width=1)

    # Кнопка подписки/отписки
    sub_text = "❌ Отписаться от уведомлений" if is_subscribed else "✅ Подписаться на уведомления"
    sub_action = "unsubscribe" if is_subscribed else "subscribe"

    markup.add(
        InlineKeyboardButton(sub_text, callback_data=settings_cb.new(section=sub_action))
    )

    # Настройки уведомлений
    markup.add(
        InlineKeyboardButton("🔔 Настройки уведомлений", callback_data=settings_cb.new(section="notifications"))
    )

    # Настройки игры
    markup.add(
        InlineKeyboardButton("🎮 Настройки игры", callback_data=settings_cb.new(section="game"))
    )

    # Кнопка возврата в главное меню
    markup.add(
        InlineKeyboardButton("🔄 Вернуться в меню", callback_data=main_menu_cb.new(action="main"))
    )

    return markup

def get_profile_menu(is_player=False):
    """
    Создает инлайн-клавиатуру с действиями для профиля

    Args:
        is_player (bool): Является ли пользователь игроком

    Returns:
        InlineKeyboardMarkup: Клавиатура с опциями профиля
    """
    markup = InlineKeyboardMarkup(row_width=2)

    if is_player:
        markup.add(
            InlineKeyboardButton("🏷 Изменить название страны", callback_data=profile_cb.new(action="change_name")),
            InlineKeyboardButton("✏️ Изменить описание", callback_data=profile_cb.new(action="change_description"))
        )
        markup.add(
            InlineKeyboardButton("🖼 Изменить флаг", callback_data=profile_cb.new(action="change_flag")),
            InlineKeyboardButton("👑 Изменить форму правления", callback_data=profile_cb.new(action="change_government"))
        )
    else:
        markup.add(
            InlineKeyboardButton("🎮 Стать игроком", callback_data=game_cb.new(action="register"))
        )

    # Кнопка возврата в главное меню
    markup.add(
        InlineKeyboardButton("🔄 Вернуться в меню", callback_data=main_menu_cb.new(action="main"))
    )

    return markup

def get_admin_menu():
    """
    Создает инлайн-клавиатуру для администраторов

    Returns:
        InlineKeyboardMarkup: Клавиатура с административными функциями
    """
    markup = InlineKeyboardMarkup(row_width=2)

    markup.add(
        InlineKeyboardButton("📊 Статистика", callback_data=main_menu_cb.new(action="admin_stats")),
        InlineKeyboardButton("👥 Пользователи", callback_data=main_menu_cb.new(action="admin_users"))
    )

    markup.add(
        InlineKeyboardButton("🎮 Управление игрой", callback_data=main_menu_cb.new(action="admin_game")),
        InlineKeyboardButton("📢 Рассылка", callback_data=main_menu_cb.new(action="admin_broadcast"))
    )

    markup.add(
        InlineKeyboardButton("👑 Управление администраторами", callback_data=main_menu_cb.new(action="admin_admins"))
    )

    # Кнопка возврата в главное меню
    markup.add(
        InlineKeyboardButton("🔄 Вернуться в меню", callback_data=main_menu_cb.new(action="main"))
    )

    return markup

def get_help_menu():
    """
    Создает инлайн-клавиатуру со справочными разделами

    Returns:
        InlineKeyboardMarkup: Клавиатура со справкой
    """
    markup = InlineKeyboardMarkup(row_width=2)

    markup.add(
        InlineKeyboardButton("🎮 Об игре", callback_data=main_menu_cb.new(action="help_game")),
        InlineKeyboardButton("📜 Команды", callback_data=main_menu_cb.new(action="help_commands"))
    )

    markup.add(
        InlineKeyboardButton("❓ FAQ", callback_data=main_menu_cb.new(action="help_faq")),
        InlineKeyboardButton("📞 Поддержка", callback_data=main_menu_cb.new(action="help_support"))
    )

    # Кнопка возврата в главное меню
    markup.add(
        InlineKeyboardButton("🔄 Вернуться в меню", callback_data=main_menu_cb.new(action="main"))
    )

    return markup

def get_confirmation_keyboard(action_type="action", custom_text=None):
    """
    Создает инлайн-клавиатуру для подтверждения действия

    Args:
        action_type (str): Тип действия (для формирования callback data)
        custom_text (tuple): Кастомные тексты для кнопок (подтвердить, отменить)

    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками подтверждения/отмены
    """
    markup = InlineKeyboardMarkup(row_width=2)

    confirm_text = "✅ Подтвердить" if custom_text is None else custom_text[0]
    cancel_text = "❌ Отменить" if custom_text is None else custom_text[1]

    markup.add(
        InlineKeyboardButton(confirm_text, callback_data=f"confirm_{action_type}"),
        InlineKeyboardButton(cancel_text, callback_data=f"cancel_{action_type}")
    )

    return markup

def get_game_registration_keyboard():
    """
    Создает клавиатуру с типами правления для регистрации в игре

    Returns:
        InlineKeyboardMarkup: Клавиатура с типами правления
    """
    markup = InlineKeyboardMarkup(row_width=2)

    markup.add(
        InlineKeyboardButton("🏛 Демократия", callback_data=game_cb.new(action="register_democracy")),
        InlineKeyboardButton("👑 Монархия", callback_data=game_cb.new(action="register_monarchy"))
    )

    markup.add(
        InlineKeyboardButton("🦅 Республика", callback_data=game_cb.new(action="register_republic")),
        InlineKeyboardButton("⚔️ Военная диктатура", callback_data=game_cb.new(action="register_military"))
    )

    markup.add(
        InlineKeyboardButton("☭ Социализм", callback_data=game_cb.new(action="register_socialism")),
        InlineKeyboardButton("🏴 Анархия", callback_data=game_cb.new(action="register_anarchy"))
    )

    markup.add(
        InlineKeyboardButton("🔄 Вернуться в меню", callback_data=main_menu_cb.new(action="main"))
    )

    return markup

# Экспортируем все наши клавиатуры
__all__ = [
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
    'profile_cb'
]
