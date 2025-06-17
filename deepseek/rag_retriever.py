from game import ASPECTS
from database import (
    get_user_aspect,
    get_all_active_countries,
    get_all_country_names,
    get_user_id_by_country
)

# Карта синонимов для аспектов
ASPECT_SYNONYMS = {
    "экономика": [
        "экономик", "торгов", "богатств", "финанс", "ресурс", "бюджет", "деньги", "доход", "налог"
    ],
    "военное_дело": [
        "армия", "войско", "воен", "солдат", "боеспособн", "сражен", "защит", "оборона", "война", "войн"
    ],
    "внеш_политика": [
        "внешн", "политик", "сосед", "другие страны", "альянс", "враг", "мир", "дипломат", "международ", "отношен", "союз"
    ],
    "территория": [
        "территор", "земл", "границ", "географ", "пространств", "природ", "рельеф", "климат", "карта", "ландшафт"
    ],
    "технологичность": [
        "технол", "развитие", "изобретен", "уровень развития", "техника", "инноваци", "открыти", "прогресс"
    ],
    "религия_культура": [
        "религ", "культур", "искусств", "традиц", "обряды", "праздник", "верован", "обычаи", "храм", "наследие"
    ],
    "управление": [
        "управлен", "власть", "закон", "право", "госуда", "правител", "строй", "монарх", "совет", "администра", "структур"
    ],
    "стройка": [
        "строит", "инфраструктур", "дорог", "здания", "дворец", "город", "построй", "объект", "ремонт"
    ],
    "общество": [
        "обществ", "класс", "слой", "населен", "социальн", "отнoшени", "народ", "сослов", "житель", "структур"
    ],
}

ALL_MARKERS = ["все", "другие", "сосед", "проч", "остальны", "других"]

def detect_aspect_and_scope(user_text: str, all_countries: list[str]) -> tuple[str|None, str, str|None]:
    """
    Возвращает (aspect_code, scope, country_name)
        scope: "self", "all", "other", "none"
    country_name заполняется только при "other"
    """
    ut = user_text.lower()
    aspect_detected = None

    # Найти аспект по ключевым словам
    for aspect, synonyms in ASPECT_SYNONYMS.items():
        for word in synonyms:
            if word in ut:
                aspect_detected = aspect
                break
        if aspect_detected:
            break

    if not aspect_detected:
        return None, "none", None

    # Проверить если запрос ко всем странам
    if any(marker in ut for marker in ALL_MARKERS):
        return aspect_detected, "all", None

    # Проверить — есть ли в тексте имя другой страны
    for c in all_countries:
        if c is not None and c.strip():  # страховка от None
            # Проверяем по вхождению фрагмента (можно доработать морфологически)
            name_fragment = c.lower()[:-1]
            # Чтобы не ловить на своё
            if name_fragment in ut and ut.find(name_fragment) > 0:
                return aspect_detected, "other", c

    return aspect_detected, "self", None

async def get_rag_context(user_id: int, user_text: str) -> str:
    """
    Возвращает строку со справкой по аспекту для вставки в промпт LLM.
    """
    all_country_names = await get_all_country_names()
    aspect, scope, country_name = detect_aspect_and_scope(user_text, all_country_names)
    if not aspect:
        return ""

    aspect_label = next((label for code, label, _ in ASPECTS if code == aspect), aspect.capitalize())

    if scope == "self":
        value = await get_user_aspect(user_id, aspect)
        if value and value.strip():
            return f"Справка: {aspect_label} вашей страны — {value.strip()}"
    elif scope == "all":
        countries = await get_all_active_countries()
        lines = []
        idx = [c for c, _, _ in ASPECTS].index(aspect)
        for ct in countries:
            uid, country, *_aspects = ct
            val = _aspects[idx]
            if val and val.strip():
                lines.append(f"{country}: {val.strip()}")
        if lines:
            return f"Справка по аспекту '{aspect_label}' для всех стран:\n" + "\n".join(lines)
    elif scope == "other" and country_name:
        # Получить user_id страны и аспект
        other_user_id = await get_user_id_by_country(country_name)
        if not other_user_id:
            return f"Данных о стране {country_name} не найдено."
        value = await get_user_aspect(other_user_id, aspect)
        if value and value.strip():
            return f"Справка: {aspect_label} страны {country_name} — {value.strip()}"
        return ""

    return ""
