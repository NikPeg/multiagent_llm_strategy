import re
from database import get_country_by_user, get_country_by_name, get_all_countries

# Вынеси свой RPG_PROMPT сюда или импортируй его, если он общий
RPG_PROMPT = (
    "Ты — ведущий ролевой текстовой игры в стиле геополитики древнего мира. "
    "Каждый игрок управляет страной, развивает её экономику, дипломатию "
    "и армию, строит отношения с соседями и принимает решения. "
    "Цель — сделать свою страну процветающей и могущественной, "
    "любое решение должно иметь последствия! Ты рассказываешь, что происходит, "
    "отвечаешь только от лица мастера игры, четко следуя выбранному игроком сеттингу, "
    "никогда не отступаешь от выбранной роли. Всегда заканчивай свои ответы вопросами о дальнейших действиях игрока."
)

async def get_rag_context(user_id: int, user_text: str) -> dict:
    """
    Собирает релевантные данные для текущего запроса игрока
    (RAG — retrieval-augmented generation)
    Возвращает словарь-структуру.
    """
    facts = {}

    # 1. Сначала ищем информацию о стране самого пользователя
    user_country_row = await get_country_by_user(user_id)
    if user_country_row:
        facts['my_country'] = row_to_dict(user_country_row)

    # 2. Ищем другие страны, упомянутые игроком
    mentioned = await extract_mentioned_countries(user_text)
    mentioned_countries = []

    # Исключаем собственную страну из поиска, если она упомянута
    my_name = facts['my_country']['name'] if 'my_country' in facts else None
    for name in set(mentioned):
        if name == my_name:
            continue
        row = await get_country_by_name(name)
        if row:
            mentioned_countries.append(row_to_dict(row))
    if mentioned_countries:
        facts['mentioned_countries'] = mentioned_countries

    # 3. Проверяем, требуется ли агрегированная информация по всем странам
    if needs_all_countries(user_text):
        all_rows = await get_all_countries()
        all_dicts = []
        for row in all_rows:
            # Пропусти страну пользователя, если не хочешь дублировать
            # if row[2] != my_name:
            all_dicts.append(row_to_dict(row))
        facts['all_countries'] = all_dicts

    # 4. Определяем, какие именно параметры нужны
    facts['wanted_params'] = extract_wanted_params(user_text)
    return facts

def row_to_dict(row):
    """
    Преобразует строку из SQLite в словарь.
    Измени индексы полей если твоя структура другая!
    """
    return {
        "id": row[0],
        "user_id": row[1],
        "name": row[2],
        "gold": row[3],
        "population": row[4],
        "army": row[5],
        "food": row[6],
        "territory": row[7],
        "religion": row[8],
        "economy": row[9],
        "diplomacy": row[10],
        "resources": row[11],
        "summary": row[12],
    }

async def extract_mentioned_countries(user_text: str):
    """
    Очень простой вариант:
    По всем странам из БД смотрим, входит ли их имя в текст запроса.
    Можно сделать кэш имен или более умный разбор.
    """
    all_rows = await get_all_countries()
    all_names = [row[2] for row in all_rows]  # Индекс 2 — name
    mentioned = set()
    words = set(re.findall(r'\w+', user_text.lower()))
    for name in all_names:
        # Приводим к lower для поиска
        if name and name.lower() in user_text.lower():
            mentioned.add(name)
        # Можно искать по частичному совпадению:
        # if any(name.lower() in word for word in words):
        #     mentioned.add(name)
    return list(mentioned)

def extract_wanted_params(user_text: str):
    """
    Определяет, какие параметры нужны на основе ключевых слов в запросе.
    Расширяй как нужно!
    """
    text = user_text.lower()
    params = set()
    key_map = {
        "золото": "gold",
        "золота": "gold",
        "армия": "army",
        "армии": "army",
        "население": "population",
        "людей": "population",
        "еда": "food",
        "территор": "territory",
        "религ": "religion",
        "экономик": "economy",
        "дипломат": "diplomacy",
        "ресурс": "resources",
    }
    for word, key in key_map.items():
        if word in text:
            params.add(key)
    # Если ничего не найдено – значит нужен summary/state в целом
    if not params:
        params = {"gold", "army", "population"}
    return params

def needs_all_countries(user_text: str) -> bool:
    """
    Проверяет по ключевым словам необходимость агрегированной выборки по всем странам.
    """
    text = user_text.lower()
    triggers = [
        "все страны", "сравни", "топ", "самый богат", "самая сильная",
        "государства", "кто", "самая могущественная"
    ]
    if any(trigger in text for trigger in triggers):
        return True
    # Ищем сравнения/суперлативы
    if re.search(r"сам\w+", text):
        return True
    return False

def build_prompt(user_id: int, user_text: str, rag_info: dict) -> str:
    """
    Формирует промпт для LLM из RAG-контекста и текущего запроса пользователя
    """
    lines = []
    lines.append(RPG_PROMPT)
    params = rag_info.get('wanted_params', {"gold", "army", "population"})

    # --- Моя страна
    if 'my_country' in rag_info:
        c = rag_info['my_country']
        param_str = ', '.join(f'{p}: {c.get(p, "")}' for p in params if p in c)
        lines.append(f"Государство {c.get('name')}: {param_str}.")

    # --- Упомянутые страны
    if 'mentioned_countries' in rag_info:
        for c in rag_info['mentioned_countries']:
            param_str = ', '.join(f'{p}: {c.get(p, "")}' for p in params if p in c)
            lines.append(f"Государство {c.get('name')}: {param_str}.")

    # --- Все страны (если требуется)
    if 'all_countries' in rag_info:
        for c in rag_info['all_countries']:
            param_str = ', '.join(f'{p}: {c.get(p, "")}' for p in params if p in c)
            lines.append(f"{c.get('name')}: {param_str}")

    # --- Вопрос игрока
    lines.append(f"Вопрос игрока: {user_text}")
    lines.append("Assistant:")
    return "\n".join(lines)
