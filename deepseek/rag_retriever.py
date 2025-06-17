from game import ASPECTS
from database import *
from typing import Tuple

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

async def detect_aspect_and_country(user_id: int, user_text: str) -> Tuple[str, str]:
    """
    Определяет аспект и страну из текста пользователя.
    По умолчанию: аспект = "описание", страна = собственная.
    """
    ut = user_text.lower()
    aspect = "описание"
    all_country_names = await get_all_country_names()
    country_name = await get_user_country(user_id)

    # Найти аспект по ключевым словам
    for asp, synonyms in ASPECT_SYNONYMS.items():
        for word in synonyms:
            if word in ut:
                aspect = asp
                break
        if aspect != "описание":
            break

    country_variants = await get_all_country_synonyms_and_names()
    # Проверить — есть ли в тексте имя или синоним другой страны
    for var, canonical in country_variants:
        if not var:
            continue
        # Пробуем: полное совпадение, совпадение без последней буквы, совпадение без двух последних букв
        lowers = [var, var[:-1], var[:-2]] if len(var) > 3 else [var]
        for form in lowers:
            if form and form in ut:
                country_name = canonical
                break
        if country_name == canonical:
            break

    return aspect, country_name

async def get_rag_context(user_id: int, user_text: str) -> str:
    """
    Возвращает текстовое описание аспекта для вставки в промпт.
    """
    aspect, country = await detect_aspect_and_country(user_id, user_text)

    if aspect == "описание":
        # Описание страны
        if not country:
            return ""
        desc = await get_user_country_desc(await get_user_id_by_country(country))
        if desc and desc.strip():
            return f"Описание страны {country}: {desc.strip()}"
        return f"Описание страны {country} отсутствует."

    # Если не "описание", то попробовать получить аспект из базы
    uid = await get_user_id_by_country(country)
    if not uid:
        return f"Страна {country} не найдена."
    value = await get_user_aspect(uid, aspect)
    aspect_label = next((label for code, label, _ in ASPECTS if code == aspect), aspect.capitalize())
    if value and value.strip():
        return f"{aspect_label} страны {country}: {value.strip()}"
    return ""
