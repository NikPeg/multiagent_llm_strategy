import asyncio
from config import ADMIN_CHAT_ID, GAME_PROMPT, RPG_PROMPT, HISTORY_LIMIT
from database import (
    set_user_country, set_user_country_desc, set_user_aspect
)
from utils import answer_html, send_html, keep_typing, stars_to_bold
from game import ASPECTS
from model_handler import model_handler, executor
# Импорт функций получения страны/описания по user_id, если требуется
from database import get_user_country, get_user_country_desc

async def handle_country_name(message, user_id: int, user_text: str):
    await set_user_country(user_id, user_text)
    await answer_html(
        message,
        f"Название страны: <b>{user_text}</b>\n\n"
        f"Теперь опиши кратко свою страну (география, особенности, народ, культура, стартовые условия):"
    )

async def handle_country_desc(message, user_id: int, user_text: str):
    country = await get_user_country(user_id)
    chat_id = message.chat.id

    await answer_html(message, "Создаю подробное начальное описание всех аспектов вашей страны, пожалуйста, подождите...")
    typing_task = asyncio.create_task(keep_typing(message.bot, chat_id))

    loop = asyncio.get_event_loop()
    user_name = message.from_user.username
    await send_html(
        message.bot,
        ADMIN_CHAT_ID,
        f"📨 Регистрация новой страны от пользователя {user_id} {user_name}:\n\n"
        f"<b>Название страны:</b> {country}\n"
        f"<b>Описание страны:</b>\n{user_text.strip()}\n\n"
    )
    all_aspects = []

    for code, label, prompt in ASPECTS:
        aspect_prompt = (
            f"{GAME_PROMPT}"
            f"Название страны: {country}\n"
            f"Описание страны: {user_text.strip()}\n"
            f"{prompt}"
        )
        aspect_value = await loop.run_in_executor(
            executor,
            model_handler.generate_short_responce,
            aspect_prompt,
        )
        await answer_html(
            message,
            f"<b>{label}</b> страны {country}: {aspect_value}{'' if aspect_value.endswith('.') else '.'}"
        )
        await send_html(
            bot,
            ADMIN_CHAT_ID,
            f"<b>{label}</b> страны {country}: {aspect_value}{'' if aspect_value.endswith('.') else '.'}"
        )
        await set_user_aspect(user_id, code, aspect_value)
        all_aspects.append(aspect_value)

    desc_prompt = (
        f"{GAME_PROMPT}"
        f"Название страны: {country}\n"
        f"Описание страны: {user_text.strip()}\n"
        f"{chr(10).join(all_aspects)}"
        "Краткое описание страны: "
    )
    description = await loop.run_in_executor(
        executor,
        model_handler.generate_short_responce,
        desc_prompt,
    )
    await send_html(
        message.bot,
        ADMIN_CHAT_ID,
        f"<b>Описание</b> страны {country}: {description}{'' if description.endswith('.') else '.'}"
    )
    await set_user_country_desc(user_id, description)

    typing_task.cancel()

    await answer_html(
        message,
        f"Игра начата! Действуй как правитель страны <b>{country}</b>.\n"
        f"Ты можешь отдавать приказы, объявлять войны, строить города или устанавливать отношения с другими странами.\n"
        f"В любой момент используй /new чтобы сбросить контекст."
        "\n\nЧто будешь делать первым делом?"
    )

async def handle_game_dialog(message, user_id: int, user_text: str):
    chat_id = message.chat.id
    user_name = message.from_user.username

    try:
        await message.bot.send_chat_action(chat_id=chat_id, action="typing")
        typing_task = asyncio.create_task(keep_typing(message.bot, chat_id))

        country_name = await get_user_country(user_id)
        country_desc = await get_user_country_desc(user_id)

        assistant_reply, context = await asyncio.get_event_loop().run_in_executor(
            executor,
            model_handler.sync_generate_response,
            user_id, user_text, RPG_PROMPT, country_name, country_desc, HISTORY_LIMIT
        )
        typing_task.cancel()
        html_reply = stars_to_bold(assistant_reply)
        await answer_html(message, html_reply)

        await send_html(
            message.bot,
            ADMIN_CHAT_ID,
            f"📨 Новый запрос от пользователя {user_id} {user_name}:\n\n"
            f"<b>Промпт, переданный в модель:</b>\n"
            f"<code>{context}</code>\n\n"
            f"<b>Ответ модели:</b>\n"
            f"<code>{assistant_reply}</code>"
        )
    except Exception as e:
        await answer_html(message, f"Ошибка: {str(e)}")
