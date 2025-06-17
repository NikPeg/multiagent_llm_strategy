from database import get_user_id_by_country, get_user_country_desc, get_user_aspect
from game import ASPECTS
from config import GAME_PROMPT
from model_handler import model_handler, executor

import asyncio

async def generate_event_for_country(country_name: str) -> str:
    """
    Генерирует событие (ивент) для страны по её названию. Возвращает сгенерированный текст события.
    """
    user_id = await get_user_id_by_country(country_name)
    if not user_id:
        return f"Страна '{country_name}' не найдена!"

    desc = await get_user_country_desc(user_id)

    prompt = (
        f"{GAME_PROMPT}\n"
        f"Название страны: {country_name}\n"
        f"Описание страны: {desc or '(нет описания)'}\n"
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
