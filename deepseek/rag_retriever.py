from game import ASPECTS
from database import *
from typing import Tuple
import logging

logger = logging.getLogger("detect_aspect_and_country")

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
    logger.info(f"detect_aspect_and_country: user_id={user_id}, user_text='{user_text}' (ut='{ut}')")
    aspect = "описание"
    all_country_names = await get_all_country_names()
    logger.info(f"Все названия стран (основные): {all_country_names}")
    country_name = await get_user_country(user_id)
    logger.info(f"Страна пользователя по умолчанию: {country_name}")

    # Найти аспект по ключевым словам
    aspect_found = False
    for asp, synonyms in ASPECT_SYNONYMS.items():
        for word in synonyms:
            if word in ut:
                aspect = asp
                aspect_found = True
                logger.info(f"Найден аспект '{aspect}' по синониму '{word}' в тексте '{user_text}'")
                break
        if aspect_found:
            break
    if not aspect_found:
        logger.info("Аспект не найден, используется 'описание'")

    country_variants = await get_all_country_synonyms_and_names()
    logger.info(f"country_variants (все варианты поиска): {country_variants}")

    country_found = None
    for var, canonical in country_variants:
        if not var:
            continue
        # Пробуем: полное совпадение, совпадение без последней буквы, без двух последних букв
        lowers = [var, var[:-1], var[:-2]] if len(var) > 3 else [var]
        for form in lowers:
            if form and form in ut:
                logger.info(
                    f"В тексте '{ut}' найдено упоминание страны/синонима '{form}' "
                    f"(оригинал: '{var}', каноническое: '{canonical}')"
                )
                country_found = canonical
                break
        if country_found:
            break

    if country_found:
        logger.debug(f"Итоговая страна (поиск по тексту): {country_found}")
        country_name = country_found
    else:
        all_marker_found = False
        for marker in ALL_MARKERS:
            if marker in ut:
                logger.debug(f"В тексте найден маркер '{marker}' из ALL_MARKERS, возвращаем 'все' страны")
                country_name = "все"
                all_marker_found = True
                break
        if not all_marker_found:
            logger.debug("Страна не найдена в тексте и не найден маркер, используется страна пользователя")

    logger.debug(f"Результат: aspect={aspect}, country_name={country_name}")
    return aspect, country_name

async def get_rag_context(user_id: int, user_text: str) -> str:
    logger.info(f"get_rag_context: user_id={user_id}, user_text='{user_text}'")
    aspect, country = await detect_aspect_and_country(user_id, user_text)
    logger.info(f"get_rag_context: detect_aspect_and_country вернул aspect={aspect}, country={country}")

    if country == "все":
        if aspect == "описание":
            # Получить описания всех стран
            descs = await get_all_user_country_descs()
            logger.info(f"Все описания стран: {descs}")
            lines = []
            for cname, desc in descs.items():
                if desc and desc.strip():
                    lines.append(f"{cname}: {desc.strip()}")
                else:
                    lines.append(f"{cname}: (нет описания)")
            return "Описание всех стран:\n" + "\n".join(lines)

        # Получить значения выбранного аспекта для всех стран
        values = await get_all_user_aspect_values(aspect)
        aspect_label = next((label for code, label, _ in ASPECTS if code == aspect), aspect.capitalize())
        logger.info(f"Аспект '{aspect}' ('{aspect_label}') всех стран: {values}")
        lines = []
        for cname, val in values.items():
            if val and val.strip():
                lines.append(f"{aspect_label} {cname}: {val.strip()}")
            else:
                lines.append(f"{aspect_label} {cname}: (нет данных)")
        return f"{aspect_label} всех стран:\n" + "\n".join(lines)

    # --- если country != "все"
    if aspect == "описание":
        if not country:
            logger.info("Страна не определена, возвращаем пустую строку")
            return ""
        desc = await get_user_country_desc(await get_user_id_by_country(country))
        logger.info(f"Описание страны '{country}': {desc}")
        if desc and desc.strip():
            return f"Описание страны {country}: {desc.strip()}"
        return f"Описание страны {country} отсутствует."

    uid = await get_user_id_by_country(country)
    if not uid:
        logger.info(f"Страна '{country}' не найдена в базе!")
        return ""
    value = await get_user_aspect(uid, aspect)
    aspect_label = next((label for code, label, _ in ASPECTS if code == aspect), aspect.capitalize())
    logger.info(f"Аспект '{aspect}' ('{aspect_label}') страны '{country}': {value}")
    if value and value.strip():
        return f"{aspect_label} страны {country}: {value.strip()}"
    return ""

