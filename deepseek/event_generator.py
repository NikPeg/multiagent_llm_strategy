from database import get_user_id_by_country, get_user_country_desc, get_user_aspect
from game import ASPECTS
from config import GAME_PROMPT
from model_handler import model_handler, executor

import asyncio

async def generate_event_for_country(country):
    """
    Генерирует событие (ивент) для страны (str) или для списка стран.
    Если country == 'все' — ивент общий, на основе инфо о всех странах.
    Если передан список названий — индивидуальный ивент для каждой страны (требует цикла).
    """
    if isinstance(country, list):
        # Массив стран: единый ивент на основе всех, промпт с инфой по каждой из стран
        descs = []
        aspects_data = []
        for c in country:
            user_id = await get_user_id_by_country(c)
            desc = await get_user_country_desc(user_id)
            descs.append(f"{c}: {desc or '(нет описания)'}")
        prompt = (
                f"{GAME_PROMPT}\n"
                "Владыки следующих стран и их государства:\n"
                + "\n".join(descs) + "\n"
                "Во времена те необычайное и судьбоносное событие обрушилось на все эти державы, смутив умы владык и народов. "
                "Случившееся изменило течение древней истории, оставив глубокий след в летописях. "
                "Краткое описание сего события:"
        )
    elif isinstance(country, str) and country.lower() == "все":
        # Получить имена всех стран и применить логику для всех
        from database import get_all_country_names
        all_names = await get_all_country_names()
        return await generate_event_for_country(all_names)
    else:
        # Как раньше — для одной страны по названию
        user_id = await get_user_id_by_country(country)
        if not user_id:
            return f"Страна '{country}' не найдена!"

        desc = await get_user_country_desc(user_id)
        aspect_texts = []
        for code, label, _ in ASPECTS:
            asp = await get_user_aspect(user_id, code)
            if asp:
                aspect_texts.append(f"{label}: {asp}")

        prompt = (
            f"{GAME_PROMPT}\n"
            f"Название страны: {country}\n"
            f"Описание страны: {desc or '(нет описания)'}\n"
            f"{chr(10).join(aspect_texts)}\n"
            "В летописях страны свершилось необычайное, важное событие — то, что потрясло народ и властителя. "
            "Это происшествие требует мудрых решений и может изменить течение истории. "
            "Краткое описание сего события:"
        )

    loop = asyncio.get_event_loop()
    event_text = await loop.run_in_executor(
        executor,
        model_handler.generate_short_responce,
        prompt,
    )
    return event_text.strip()
