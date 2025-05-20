"""
prompt_templates.py - Шаблоны запросов к языковой модели.
Содержит стандартизированные промпты для различных сценариев взаимодействия с LLM.
"""

from typing import Dict, List, Any, Optional
from string import Template


# Системный промпт для задания общего контекста игры
SYSTEM_PROMPT = """Ты - игровой мастер исторической стратегии в жанре симуляции государства древнего мира.
Действие игры происходит в период примерно с 3000 г. до н.э. по 500 г. н.э.
Твоя задача - реалистично описывать события, консультировать правителя (игрока) и помогать ему принимать решения.

Вся информация должна быть исторически достоверной для данного периода. Не упоминай технологии, которых не существовало в древнем мире.
Используй соответствующий эпохе стиль речи - возвышенный, но понятный.

Опирайся на предоставленную информацию о текущем состоянии государства при формировании ответов.
"""


# Шаблон для анализа действия игрока
ANALYZE_ACTION_TEMPLATE = Template("""${system_prompt}

Вот текущая информация о стране ${country_name}:
${country_context}

Правитель страны ${country_name} отдал следующий приказ:
"${action}"

Проанализируй, как этот приказ повлияет на разные аспекты страны.

Ответь в следующем формате:
ВЫПОЛНЕНИЕ: [краткое описание того, как приказ был выполнен]
РЕЗУЛЬТАТ: [описание непосредственного результата]
ПОСЛЕДСТВИЯ: [описание долгосрочных последствий]
ИЗМЕНЕНИЯ:
- экономика: [краткое описание изменений в экономике]
- военное дело: [краткое описание изменений в военном деле]
- религия и культура: [краткое описание изменений в религии и культуре]
- управление и право: [краткое описание изменений в управлении и праве]
- строительство и инфраструктура: [краткое описание изменений в строительстве и инфраструктуре]
- внешняя политика: [краткое описание изменений во внешней политике]
- общественные отношения: [краткое описание изменений в общественных отношениях]
- территория: [краткое описание изменений в территории]
- технологичность: [краткое описание изменений в технологиях]""")


# Шаблон для обновления состояния аспекта
UPDATE_ASPECT_TEMPLATE = Template("""${system_prompt}

Ты - летописец древнего мира, записывающий историю страны ${country_name}.

Текущее состояние ${aspect} страны:
${current_state}

Недавно произошли следующие изменения:
${action_impact}

Напиши обновленное состояние ${aspect} страны, учитывая текущее состояние и произошедшие изменения.
Отвечай только обновленным состоянием без дополнительных комментариев и заголовков.""")


# Шаблон для оценки характеристик страны
EVALUATE_STATS_TEMPLATE = Template("""${system_prompt}

Ты - мудрый советник, оценивающий могущество страны ${country_name}.

На основе следующей информации о стране, оцени каждый аспект по шкале от 1 до 5, где 1 - очень слабо, 5 - очень сильно:

${state_text}

Дай свою оценку в следующем формате (только цифры от 1 до 5):

экономика: [оценка]
военное дело: [оценка]
религия и культура: [оценка]
управление и право: [оценка]
строительство и инфраструктура: [оценка]
внешняя политика: [оценка]
общественные отношения: [оценка]
территория: [оценка]
технологичность: [оценка]""")


# Шаблон для генерации случайного события
GENERATE_EVENT_TEMPLATE = Template("""${system_prompt}

Ты - оракул древнего мира, предсказывающий события для страны ${country_name}.

Вот текущая информация о стране:
${country_context}

Создай ${event_type} новость для страны. Это должно быть ${event_description}.
Убедись, что событие соответствует реалиям древнего мира и текущему состоянию страны.

Ответь в следующем формате:
ЗАГОЛОВОК: [краткий заголовок события]
СОБЫТИЕ: [подробное описание события]
ПОСЛЕДСТВИЯ: [как это событие повлияет на страну]
ЗАТРОНУТЫЕ АСПЕКТЫ:
- [название аспекта]: [как именно затронут аспект]""")


# Шаблон для предсказания будущего страны
PREDICT_FUTURE_TEMPLATE = Template("""${system_prompt}

Ты - провидец древнего мира, способный заглянуть в будущее страны ${country_name}.

Вот информация о текущем состоянии страны:
${country_context}

Составь краткое поэтическое предсказание о том, что ждет страну в ближайшее время.
Предсказание должно быть туманным и загадочным, как и положено настоящему оракулу,
но содержать намеки на возможные события, основанные на текущем положении дел.

Ответ дай от первого лица, как будто ты вещаешь правителю этой страны.""")


# Шаблон для генерации проблем страны
GENERATE_PROBLEMS_TEMPLATE = Template("""${system_prompt}

Ты - советник правителя страны ${country_name} в древнем мире.

Вот информация о состоянии страны:
${country_context}

Определи 3-5 наиболее острых проблем, с которыми сталкивается страна в данный момент.
Перечисли их в виде списка, каждая проблема должна быть на отдельной строке и начинаться с тире (-).""")


# Шаблон для ежедневного обновления страны
DAILY_UPDATE_TEMPLATE = Template("""${system_prompt}

Ты - историк-летописец, документирующий развитие страны ${country_name} в древнем мире.
        
Вот текущее состояние страны:
${country_context}

Опиши изменения, которые произошли за прошедший год:
1. Как изменились различные аспекты страны?
2. Какие текущие процессы продолжаются?
3. Какие естественные изменения произошли?

Ответь в следующем формате:
ГОД: [текущий год]
ОБЩИЕ ИЗМЕНЕНИЯ:ений за год]
ИЗМЕНЕНИЯ ПО АСПЕКТАМ:
- экономика: [изменения]
- военное дело: [изменения]
- религия и культура: [изменения]
- управление и право: [изменения]
- строительство и инфраструктура: [изменения]
- внешняя политика: [изменения]
- общественные отношения: [изменения]
- территория: [изменения]
- технологичность: [изменения]""")


# Шаблон для проверки соответствия эпохе
CHECK_ERA_TEMPLATE = Template("""${system_prompt}

Ты - исторический консультант игры, действие которой происходит в древнем мире (примерно 3000 г. до н.э. - 500 г. н.э.).
        
Проверь, соответствует ли следующее сообщение игрока эпохе древнего мира:

"${message}"

Ответь в формате:
СООТВЕТСТВУЕТ: да/нет
КОММЕНТАРИЙ: [объяснение, почему сообщение соответствует или не соответствует эпохе]""")


# Шаблон для создания начального описания страны
INITIAL_COUNTRY_DESCRIPTION_TEMPLATE = Template("""${system_prompt}

Создай описание для новой страны древнего мира под названием "${country_name}" со следующими характеристиками:

Экономика: ${economy}/5
Военное дело: ${military}/5
Религия и культура: ${religion}/5
Управление и право: ${governance}/5
Строительство и инфраструктура: ${construction}/5
Внешняя политика: ${diplomacy}/5
Общественные отношения: ${society}/5
Территория: ${territory}/5
Технологичность: ${technology}/5

Дополнительная информация от игрока:
${player_description}

Составь детальное описание страны, учитывая эти характеристики и дополнительную информацию.
Включи географические особенности, форму правления, основные занятия населения, религиозные верования и культурные традиции.
Описание должно быть реалистичным для эпохи древнего мира (примерно 3000 г. до н.э. - 500 г. н.э.).

Затем перечисли 3-5 основных проблем, с которыми сталкивается страна в начале игры.

Ответь в следующем формате:
ОПИСАНИЕ:
[детальное описание страны в нескольких абзацах]

ПРОБЛЕМЫ:
- [проблема 1]
- [проблема 2]
- [проблема 3]
- [и т.д. если нужно]""")


# Шаблон для составления ответа на приказ игрока
COMMAND_RESPONSE_TEMPLATE = Template("""${system_prompt}

Ты - верховный советник правителя страны ${country_name}.

Правитель отдал следующий приказ:
"${command}"

Анализ выполнения приказа:
${execution}

Результат:
${result}

Последствия:
${consequences}

Составь ответ от имени советника, подробно объясняющий результаты выполнения приказа правителя.
Используй соответствующий древнему миру стиль речи - почтительный к правителю, но информативный.
Включи в ответ детали о том, как был выполнен приказ, каковы его непосредственные результаты и возможные долгосрочные последствия.""")


# Шаблон для описания аспекта страны по запросу игрока
ASPECT_DETAILS_TEMPLATE = Template("""${system_prompt}

Ты - мудрый советник правителя страны ${country_name}, отвечающий за ${aspect}.

Вот текущая информация об этом аспекте:
${aspect_description}

Составь подробный доклад для правителя о текущем состоянии ${aspect} в государстве.
Упомяни текущую ситуацию, проблемы, успехи и перспективы развития.
Используй соответствующий древнему миру стиль речи - почтительный, но информативный.

Не давай конкретных советов, если правитель их не просил.""")


# Шаблон для божественного послания (от администратора)
DIVINE_MESSAGE_TEMPLATE = Template("""${system_prompt}

Ты - верховное божество, решившее напрямую обратиться к правителю страны ${country_name}.

Вот послание, которое ты хочешь передать:
"${message}"

Переформулируй это послание в стиле божественного откровения, соответствующего эпохе древнего мира.
Текст должен быть величественным, внушительным и таинственным, но при этом передавать суть оригинального послания.
Используй архаичные обороты речи, метафоры и аллегории, характерные для священных текстов.""")


# Шаблон для завершения проекта
PROJECT_COMPLETION_TEMPLATE = Template("""${system_prompt}

Ты - летописец древнего мира, записывающий историю страны ${country_name}.

Проект "${project_name}" категории "${project_category}" был завершен!

Вот текущая информация о стране:
${country_context}

Опиши, как завершение этого проекта повлияло на страну. Включи информацию о:
1. Церемонии открытия/завершения проекта
2. Реакции населения
3. Конкретных выгодах для государства
4. Влиянии на различные аспекты жизни страны

Ответь в следующем формате:
СОБЫТИЕ: [описание завершения проекта]
ВЛИЯНИЕ: [описание влияния на страну]
ИЗМЕНЕНИЯ В АСПЕКТАХ:
- [аспект]: [изменения]""")


# Шаблон для уточнения ответа (если игрок запросил пояснение)
CLARIFICATION_TEMPLATE = Template("""${system_prompt}

Ты - верховный советник правителя страны ${country_name}.

Правитель запрашивает пояснение по следующему вопросу:
"${question}"

Контекст предыдущего ответа:
${previous_response}

Информация о текущем состоянии страны:
${country_context}

Дай подробное и понятное объяснение, оставаясь в рамках реалий древнего мира.
Используй примеры и аналогии, если это поможет правителю лучше понять ситуацию.""")


# Шаблон для взаимодействия с другой страной
INTERACT_WITH_COUNTRY_TEMPLATE = Template("""${system_prompt}

Ты - дипломат/посланник страны ${country_name}.

Ты отправлен к правителю страны ${target_country} с целью:
"${interaction_purpose}"

Вот информация о твоей стране:
${country_context}

Вот информация о стране ${target_country}:
${target_country_context}

Опиши, как прошли переговоры или взаимодействие между странами.
Учитывай текущие отношения, силу сторон и реалии древнего мира.

Ответь в следующем формате:
ВСТРЕЧА: [описание встречи/переговоров]
РЕЗУЛЬТАТ: [достигнутые договоренности или последствия]
ОТНОШЕНИЯ: [как изменились отношения между странами]
ВЛИЯНИЕ: [влияние на различные аспекты твоей страны]""")


# Функции для получения готовых промптов с подставленными значениями

def get_analyze_action_prompt(country_name: str, action: str, country_context: str) -> str:
    """
    Создает промпт для анализа действия игрока.

    Args:
        country_name: Название страны
        action: Действие игрока
        country_context: Контекст о стране

    Returns:
        str: Готовый промпт
    """
    return ANALYZE_ACTION_TEMPLATE.substitute(
        system_prompt=SYSTEM_PROMPT,
        country_name=country_name,
        action=action,
        country_context=country_context
    )


def get_update_aspect_prompt(country_name: str, aspect: str, current_state: str, action_impact: str) -> str:
    """
    Создает промпт для обновления состояния аспекта.

    Args:
        country_name: Название страны
        aspect: Название аспекта
        current_state: Текущее состояние аспекта
        action_impact: Описание воздействия действия

    Returns:
        str: Готовый промпт
    """
    return UPDATE_ASPECT_TEMPLATE.substitute(
        system_prompt=SYSTEM_PROMPT,
        country_name=country_name,
        aspect=aspect,
        current_state=current_state or "Информация отсутствует",
        action_impact=action_impact
    )


def get_evaluate_stats_prompt(country_name: str, state_text: str) -> str:
    """
    Создает промпт для оценки характеристик страны.

    Args:
        country_name: Название страны
        state_text: Текст с описанием состояния страны

    Returns:
        str: Готовый промпт
    """
    return EVALUATE_STATS_TEMPLATE.substitute(
        system_prompt=SYSTEM_PROMPT,
        country_name=country_name,
        state_text=state_text
    )


def get_generate_event_prompt(country_name: str, event_type: str, country_context: str) -> str:
    """
    Создает промпт для генерации события.

    Args:
        country_name: Название страны
        event_type: Тип события (очень плохое, плохое, нейтральное, хорошее, очень хорошее)
        country_context: Контекст о стране

    Returns:
        str: Готовый промпт
    """
    event_descriptions = {
        "очень плохую": "катастрофическое событие, которое серьезно негативно повлияет на страну",
        "плохую": "негативное событие, которое создаст проблемы для страны",
        "нейтральную": "событие, которое имеет как положительные, так и отрицательные аспекты",
        "хорошую": "позитивное событие, которое принесет пользу стране",
        "очень хорошую": "чрезвычайно благоприятное событие, которое значительно улучшит положение страны"
    }

    event_description = event_descriptions.get(event_type, "нейтральное событие")

    return GENERATE_EVENT_TEMPLATE.substitute(
        system_prompt=SYSTEM_PROMPT,
        country_name=country_name,
        event_type=event_type,
        event_description=event_description,
        country_context=country_context
    )


def get_predict_future_prompt(country_name: str, country_context: str) -> str:
    """
    Создает промпт для предсказания будущего страны.

    Args:
        country_name: Название страны
        country_context: Контекст о стране

    Returns:
        str: Готовый промпт
    """
    return PREDICT_FUTURE_TEMPLATE.substitute(
        system_prompt=SYSTEM_PROMPT,
        country_name=country_name,
        country_context=country_context
    )


def get_generate_problems_prompt(country_name: str, country_context: str) -> str:
    """
    Создает промпт для генерации проблем страны.

    Args:
        country_name: Название страны
        country_context: Контекст о стране

    Returns:
        str: Готовый промпт
    """
    return GENERATE_PROBLEMS_TEMPLATE.substitute(
        system_prompt=SYSTEM_PROMPT,
        country_name=country_name,
        country_context=country_context
    )


def get_daily_update_prompt(country_name: str, country_context: str) -> str:
    """
    Создает промпт для ежедневного обновления страны.

    Args:
        country_name: Название страны
        country_context: Контекст о стране

    Returns:
        str: Готовый промпт
    """
    return DAILY_UPDATE_TEMPLATE.substitute(
        system_prompt=SYSTEM_PROMPT,
        country_name=country_name,
        country_context=country_context
    )


def get_check_era_prompt(message: str) -> str:
    """
    Создает промпт для проверки соответствия сообщения эпохе.

    Args:
        message: Сообщение игрока

    Returns:
        str: Готовый промпт
    """
    return CHECK_ERA_TEMPLATE.substitute(
        system_prompt=SYSTEM_PROMPT,
        message=message
    )


def get_initial_country_description_prompt(
        country_name: str,
        stats: Dict[str, int],
        player_description: str
) -> str:
    """
    Создает промпт для создания начального описания страны.

    Args:
        country_name: Название страны
        stats: Словарь с характеристиками страны
        player_description: Дополнительное описание от игрока

    Returns:
        str: Готовый промпт
    """
    # Преобразуем названия характеристик в английские для соответствия шаблону
    stats_mapping = {
        "экономика": "economy",
        "военное дело": "military",
        "религия и культура": "religion",
        "управление и право": "governance",
        "строительство и инфраструктура": "construction",
        "внешняя политика": "diplomacy",
        "общественные отношения": "society",
        "территория": "territory",
        "технологичность": "technology"
    }

    # Создаем словарь с характеристиками
    template_stats = {}
    for rus_name, eng_name in stats_mapping.items():
        template_stats[eng_name] = stats.get(rus_name, 1)

    return INITIAL_COUNTRY_DESCRIPTION_TEMPLATE.substitute(
        system_prompt=SYSTEM_PROMPT,
        country_name=country_name,
        economy=template_stats.get("economy", 1),
        military=template_stats.get("military", 1),
        religion=template_stats.get("religion", 1),
        governance=template_stats.get("governance", 1),
        construction=template_stats.get("construction", 1),
        diplomacy=template_stats.get("diplomacy", 1),
        society=template_stats.get("society", 1),
        territory=template_stats.get("territory", 1),
        technology=template_stats.get("technology", 1),
        player_description=player_description
    )


def get_command_response_prompt(
        country_name: str,
        command: str,
        execution: str,
        result: str,
        consequences: str
) -> str:
    """
    Создает промпт для составления ответа на приказ игрока.

    Args:
        country_name: Название страны
        command: Приказ игрока
        execution: Описание выполнения приказа
        result: Результат выполнения
        consequences: Последствия выполнения

    Returns:
        str: Готовый промпт
    """
    return COMMAND_RESPONSE_TEMPLATE.substitute(
        system_prompt=SYSTEM_PROMPT,
        country_name=country_name,
        command=command,
        execution=execution,
        result=result,
        consequences=consequences
    )


def get_aspect_details_prompt(country_name: str, aspect: str, aspect_description: str) -> str:
    """
    Создает промпт для описания аспекта страны по запросу игрока.

    Args:
        country_name: Название страны
        aspect: Название аспекта
        aspect_description: Текущее описание аспекта

    Returns:
        str: Готовый промпт
    """
    return ASPECT_DETAILS_TEMPLATE.substitute(
        system_prompt=SYSTEM_PROMPT,
        country_name=country_name,
        aspect=aspect,
        aspect_description=aspect_description or "Информация отсутствует"
    )


def get_divine_message_prompt(country_name: str, message: str) -> str:
    """
    Создает промпт для божественного послания (от администратора).

    Args:
        country_name: Название страны
        message: Исходное сообщение

    Returns:
        str: Готовый промпт
    """
    return DIVINE_MESSAGE_TEMPLATE.substitute(
        system_prompt=SYSTEM_PROMPT,
        country_name=country_name,
        message=message
    )


def get_project_completion_prompt(
        country_name: str,
        project_name: str,
        project_category: str,
        country_context: str
) -> str:
    """
    Создает промпт для описания завершения проекта.

    Args:
        country_name: Название страны
        project_name: Название проекта
        project_category: Категория проекта
        country_context: Контекст о стране

    Returns:
        str: Готовый промпт
    """
    return PROJECT_COMPLETION_TEMPLATE.substitute(
        system_prompt=SYSTEM_PROMPT,
        country_name=country_name,
        project_name=project_name,
        project_category=project_category,
        country_context=country_context
    )


def get_clarification_prompt(
        country_name: str,
        question: str,
        previous_response: str,
        country_context: str
) -> str:
    """
    Создает промпт для уточнения ответа.

    Args:
        country_name: Название страны
        question: Вопрос игрока
        previous_response: Предыдущий ответ
        country_context: Контекст о стране

    Returns:
        str: Готовый промпт
    """
    return CLARIFICATION_TEMPLATE.substitute(
        system_prompt=SYSTEM_PROMPT,
        country_name=country_name,
        question=question,
        previous_response=previous_response,
        country_context=country_context
    )


def get_interact_with_country_prompt(
        country_name: str,
        target_country: str,
        interaction_purpose: str,
        country_context: str,
        target_country_context: str
) -> str:
    """
    Создает промпт для взаимодействия с другой страной.

    Args:
        country_name: Название страны игрока
        target_country: Название целевой страны
        interaction_purpose: Цель взаимодействия
        country_context: Контекст о стране игрока
        target_country_context: Контекст о целевой стране

    Returns:
        str: Готовый промпт
    """
    return INTERACT_WITH_COUNTRY_TEMPLATE.substitute(
        system_prompt=SYSTEM_PROMPT,
        country_name=country_name,
        target_country=target_country,
        interaction_purpose=interaction_purpose,
        country_context=country_context,
        target_country_context=target_country_context
    )
