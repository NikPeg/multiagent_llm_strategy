from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.callback_data import CallbackData

# CallbackData для действий
action_cb = CallbackData("action", "type", "target")

# CallbackData для управления приказами
order_cb = CallbackData("order", "action", "order_id")

def get_action_keyboard():
    """
    Создает инлайн-клавиатуру с основными действиями игрока

    Returns:
        InlineKeyboardMarkup: Клавиатура с действиями
    """
    markup = InlineKeyboardMarkup(row_width=1)

    markup.add(
        InlineKeyboardButton("🏹 Отдать приказ", callback_data=action_cb.new(type="new_order", target="none")),
        InlineKeyboardButton("📜 История приказов", callback_data=action_cb.new(type="history", target="none")),
        InlineKeyboardButton("📊 Отчет о стране", callback_data=action_cb.new(type="report", target="none")),
        InlineKeyboardButton("🔙 Назад", callback_data=action_cb.new(type="back", target="main_menu"))
    )

    return markup

def get_order_confirmation_keyboard():
    """
    Создает инлайн-клавиатуру для подтверждения отправки приказа

    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками подтверждения/отмены
    """
    markup = InlineKeyboardMarkup(row_width=2)

    markup.add(
        InlineKeyboardButton("✅ Подтвердить", callback_data="confirm_action"),
        InlineKeyboardButton("❌ Отменить", callback_data="cancel_action")
    )

    return markup

def get_action_suggestions_keyboard(suggestions):
    """
    Создает клавиатуру с предложениями действий

    Args:
        suggestions (list): Список предложений действий

    Returns:
        ReplyKeyboardMarkup: Клавиатура с предложениями
    """
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)

    # Добавляем каждое предложение как отдельную кнопку
    for suggestion in suggestions:
        markup.add(KeyboardButton(suggestion))

    # Добавляем кнопку отмены
    markup.add(KeyboardButton("❌ Отмена"))

    return markup

def get_action_categories_keyboard():
    """
    Создает инлайн-клавиатуру с категориями действий

    Returns:
        InlineKeyboardMarkup: Клавиатура с категориями
    """
    markup = InlineKeyboardMarkup(row_width=2)

    # Первый ряд кнопок
    markup.row(
        InlineKeyboardButton("💰 Экономика", callback_data=action_cb.new(type="category", target="economy")),
        InlineKeyboardButton("⚔️ Военное дело", callback_data=action_cb.new(type="category", target="military"))
    )

    # Второй ряд кнопок
    markup.row(
        InlineKeyboardButton("🏛 Религия и культура", callback_data=action_cb.new(type="category", target="religion")),
        InlineKeyboardButton("⚖️ Управление и право", callback_data=action_cb.new(type="category", target="governance"))
    )

    # Третий ряд кнопок
    markup.row(
        InlineKeyboardButton("🏗 Строительство", callback_data=action_cb.new(type="category", target="construction")),
        InlineKeyboardButton("🌐 Внешняя политика", callback_data=action_cb.new(type="category", target="diplomacy"))
    )

    # Четвертый ряд кнопок
    markup.row(
        InlineKeyboardButton("👥 Общество", callback_data=action_cb.new(type="category", target="society")),
        InlineKeyboardButton("🗺 Территория", callback_data=action_cb.new(type="category", target="territory"))
    )

    # Пятый ряд кнопок
    markup.row(
        InlineKeyboardButton("🔬 Технологии", callback_data=action_cb.new(type="category", target="technology")),
        InlineKeyboardButton("✨ Другое", callback_data=action_cb.new(type="category", target="other"))
    )

    # Кнопка для возврата
    markup.add(
        InlineKeyboardButton("🔙 Назад", callback_data=action_cb.new(type="back", target="main_menu"))
    )

    return markup

def get_order_history_keyboard(orders=None, page=0, page_size=5):
    """
    Создает инлайн-клавиатуру с историей приказов и пагинацией

    Args:
        orders (list): Список приказов для отображения
        page (int): Текущая страница
        page_size (int): Количество приказов на странице

    Returns:
        InlineKeyboardMarkup: Клавиатура с историей приказов
    """
    markup = InlineKeyboardMarkup(row_width=1)

    # Если приказы предоставлены
    if orders:
        # Рассчитываем общее количество страниц
        total_pages = (len(orders) + page_size - 1) // page_size

        # Получаем приказы для текущей страницы
        start_idx = page * page_size
        end_idx = min(start_idx + page_size, len(orders))
        current_page_orders = orders[start_idx:end_idx]

        # Добавляем кнопки для каждого приказа на текущей странице
        for order in current_page_orders:
            order_id = order.get('id', 0)
            order_text = order.get('action_text', 'Неизвестный приказ')

            # Ограничиваем длину текста приказа
            if len(order_text) > 35:
                order_text = order_text[:32] + "..."

            markup.add(
                InlineKeyboardButton(
                    f"{order_text}",
                    callback_data=order_cb.new(action="view", order_id=order_id)
                )
            )

        # Добавляем навигационные кнопки
        nav_buttons = []

        # Кнопка "Предыдущая страница"
        if page > 0:
            nav_buttons.append(
                InlineKeyboardButton(
                    "⬅️ Назад",
                    callback_data=action_cb.new(type="history_page", target=str(page-1))
                )
            )

        # Кнопка "Следующая страница"
        if page < total_pages - 1:
            nav_buttons.append(
                InlineKeyboardButton(
                    "➡️ Вперед",
                    callback_data=action_cb.new(type="history_page", target=str(page+1))
                )
            )

        # Добавляем навигационные кнопки, если они есть
        if nav_buttons:
            markup.row(*nav_buttons)

        # Добавляем номер текущей страницы
        markup.add(
            InlineKeyboardButton(
                f"📄 Стр. {page+1}/{total_pages}",
                callback_data=action_cb.new(type="page_info", target="none")
            )
        )

    # Кнопка возврата
    markup.add(
        InlineKeyboardButton("🔙 Назад", callback_data=action_cb.new(type="back", target="action_menu"))
    )

    return markup

def get_order_detail_keyboard(order_id):
    """
    Создает инлайн-клавиатуру для детального просмотра приказа

    Args:
        order_id (int): ID приказа

    Returns:
        InlineKeyboardMarkup: Клавиатура для детального просмотра
    """
    markup = InlineKeyboardMarkup(row_width=2)

    markup.row(
        InlineKeyboardButton(
            "📊 Влияние на характеристики",
            callback_data=order_cb.new(action="impact", order_id=order_id)
        ),
        InlineKeyboardButton(
            "📝 Мнение советника",
            callback_data=order_cb.new(action="opinion", order_id=order_id)
        )
    )

    markup.add(
        InlineKeyboardButton(
            "🏹 Повторить приказ",
            callback_data=order_cb.new(action="repeat", order_id=order_id)
        )
    )

    markup.add(
        InlineKeyboardButton("🔙 Назад", callback_data=action_cb.new(type="history", target="none"))
    )

    return markup

def get_quick_action_buttons():
    """
    Создает клавиатуру с быстрыми действиями для ReplyKeyboardMarkup

    Returns:
        ReplyKeyboardMarkup: Клавиатура с быстрыми действиями
    """
    markup = ReplyKeyboardMarkup(resize_keyboard=True)

    markup.row(
        KeyboardButton("🏹 Новый приказ"),
        KeyboardButton("📜 История приказов")
    )

    markup.row(
        KeyboardButton("📊 Отчет о стране"),
        KeyboardButton("👑 Профиль")
    )

    markup.row(
        KeyboardButton("⚙️ Настройки"),
        KeyboardButton("❓ Помощь")
    )

    return markup

def get_suggestion_examples_keyboard(category=None):
    """
    Создает инлайн-клавиатуру с примерами приказов в зависимости от категории

    Args:
        category (str): Категория приказов

    Returns:
        InlineKeyboardMarkup: Клавиатура с примерами
    """
    markup = InlineKeyboardMarkup(row_width=1)

    # Примеры для разных категорий
    examples = {
        "economy": [
            "Построить новую фабрику в столице",
            "Снизить налоги для малого бизнеса",
            "Увеличить торговлю с соседними странами"
        ],
        "military": [
            "Увеличить финансирование армии",
            "Модернизировать вооружение",
            "Построить новую военную базу"
        ],
        "religion": [
            "Объявить новый религиозный праздник",
            "Построить величественный храм",
            "Поддержать культурный обмен с другими странами"
        ],
        "governance": [
            "Провести судебную реформу",
            "Усилить борьбу с коррупцией",
            "Создать новое министерство"
        ],
        "construction": [
            "Построить новый мост через реку",
            "Модернизировать дорожную сеть",
            "Начать строительство нового города"
        ],
        "diplomacy": [
            "Заключить торговый союз с соседями",
            "Объявить войну враждебному государству",
            "Отправить дипломатическую миссию"
        ],
        "society": [
            "Улучшить систему образования",
            "Провести социальную реформу",
            "Ввести новую программу здравоохранения"
        ],
        "territory": [
            "Основать новую колонию",
            "Аннексировать соседнюю территорию",
            "Провести административную реформу регионов"
        ],
        "technology": [
            "Инвестировать в научные исследования",
            "Создать новый технологический центр",
            "Разработать инновационное вооружение"
        ],
        "other": [
            "Организовать национальный праздник",
            "Провести амнистию для заключенных",
            "Начать тайную операцию в другой стране"
        ]
    }

    # Если категория указана и существует в словаре
    if category and category in examples:
        # Добавляем примеры как кнопки
        for example in examples[category]:
            markup.add(
                InlineKeyboardButton(
                    example,
                    callback_data=action_cb.new(type="use_example", target=example[:50])  # Ограничиваем длину
                )
            )
    else:
        # Добавляем общие примеры
        general_examples = [
            "Построить новый город",
            "Модернизировать армию",
            "Провести экономическую реформу",
            "Заключить союз с соседней страной"
        ]

        for example in general_examples:
            markup.add(
                InlineKeyboardButton(
                    example,
                    callback_data=action_cb.new(type="use_example", target=example[:50])
                )
            )

    # Кнопка возврата
    markup.add(
        InlineKeyboardButton("🔙 Назад", callback_data=action_cb.new(type="back", target="categories"))
    )

    return markup

# Экспортируем все наши клавиатуры
__all__ = [
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
