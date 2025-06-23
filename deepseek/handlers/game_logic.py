import asyncio
from config import ADMIN_CHAT_ID, GAME_PROMPT, RPG_PROMPT, HISTORY_LIMIT
from database import (
    set_user_country, set_user_country_desc, set_user_aspect
)
from aiogram import Router, types
from utils import answer_html, send_html, keep_typing, stars_to_bold
from game import ASPECTS
from model_handler import model_handler, executor
# Импорт функций получения страны/описания по user_id, если требуется
from database import *
from keyboard import ASPECTS_KEYBOARD
from rag_retriever import get_rag_context
from style_checker import contains_modern_words
from .fsm import *

router = Router()

@router.message(RegisterCountry.waiting_for_name)
async def handle_country_name(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_text = message.text.strip()
    await set_user_country(user_id, user_text)
    await answer_html(
        message,
        f"🏺 Ты даровал своей державе имя: <b>{user_text}</b>.\n\n"
        f"Опиши землю и народ своего царства: его географию, древние обычаи, таланты и традиции. "
        f"Поведай о начальных условиях и уникальных чертах своего государства.\n\n"
        f"✋ Если захочешь изменить имя, просто напиши <b>/cancel</b>.",
    )
    await state.set_state(RegisterCountry.waiting_for_desc)

@router.message(RegisterCountry.waiting_for_desc)
async def handle_country_desc(message, user_id: int, user_text: str):
    if user_text.strip().lower() == "/cancel":
        await answer_html(
            message,
            "Регистрация отменена. Введите новое название своей страны:",
        )
        await handle_country_name(message, user_id, "")
        return
    country = await get_user_country(user_id)
    chat_id = message.chat.id

    # Проверка на современные слова
    bad_word = contains_modern_words(user_text)
    if bad_word:
        await answer_html(
            message,
            f"❗️Описание содержит слова, не подходящие для эпохи древнего мира — например, <b>{bad_word}</b>. "
            "Пожалуйста, перепиши описание, избегая современных понятий (автомобили, интернет, доллары и т.п.)"
        )
        return

    await answer_html(
        message,
        "Создаю подробное начальное описание всех аспектов вашей страны, пожалуйста, подождите...",
    )
    typing_task = asyncio.create_task(keep_typing(message.bot, chat_id))

    loop = asyncio.get_event_loop()
    user_name = message.from_user.username
    await send_html(
        message.bot,
        ADMIN_CHAT_ID,
        f"📨 Регистрация новой страны от пользователя {user_id} {user_name}:\n\n"
        f"<b>Название страны:</b> {country}\n"
        f"<b>Описание страны:</b>\n{user_text.strip()}\n\n",
    )
    all_aspects = []

    for code, label, prompt in ASPECTS:
        aspect_prompt = (
            f"{GAME_PROMPT}"
            f"Название страны: {country}\n"
            f"Описание страны: {user_text.strip()}\n"
        )

        # --- Особый контекст для ВНЕШНЕЙ ПОЛИТИКИ ---
        if code == "внеш_политика":
            # Получаем описания всех остальных стран
            other_descs = await get_other_countries_descs(country)
            if other_descs:
                aspect_prompt += (
                        "Краткие описания других стран в мире:\n" +
                        "".join([f"- {c_name}: {desc.strip() if desc else '(нет описания)'}\n" for c_name, desc in other_descs])
                )
        # --- Особый контекст для ТЕРРИТОРИИ ---
        if code == "территория":
            # Получаем аспект территория остальных стран
            other_territories = await get_other_countries_aspect(country, "территория")
            if other_territories:
                aspect_prompt += (
                        "Краткое описание границ и земель других стран:\n" +
                        "".join([f"- {c_name}: {territory.strip() if territory else '(нет описания)'}\n" for c_name, territory in other_territories])
                )

        # Основной промпт аспекта
        aspect_prompt += prompt

        # --- Отправить промпт в чат админов (для контроля) ---
        await send_html(
            message.bot,
            ADMIN_CHAT_ID,
            f"<b>Промпт для генерации аспекта <u>{label}</u> страны {country}:</b>\n"
            f"<pre>{aspect_prompt}</pre>"
        )

        # Генерация аспекта
        aspect_value = await loop.run_in_executor(
            executor,
            model_handler.generate_short_responce,
            aspect_prompt,
        )
        await answer_html(
            message,
            f"<b>{label}</b> страны {country}: {aspect_value.strip()}{'' if aspect_value.strip().endswith('.') else '.'}",
        )
        await send_html(
            message.bot,
            ADMIN_CHAT_ID,
            f"<b>{label}</b> страны {country}: {aspect_value.strip()}{'' if aspect_value.strip().endswith('.') else '.'}",
        )
        await set_user_aspect(user_id, code, aspect_value.strip())
        all_aspects.append(aspect_value.strip())

    # Генерируем итоговое краткое описание страны
    desc_prompt = (
        f"{GAME_PROMPT}"
        f"Название страны: {country}\n"
        f"Описание страны: {user_text.strip()}\n"
        f"{chr(10).join(all_aspects)}"
        "Краткое описание страны: "
    )

    # Так же логируем итоговый промпт для описания!
    await send_html(
        message.bot,
        ADMIN_CHAT_ID,
        f"<b>Промпт для генерации общего описания страны {country}:</b>\n"
        f"<pre>{desc_prompt}</pre>"
    )

    description = await loop.run_in_executor(
        executor,
        model_handler.generate_short_responce,
        desc_prompt,
    )
    await send_html(
        message.bot,
        ADMIN_CHAT_ID,
        f"<b>Описание</b> страны {country}: {description.strip()}{'' if description.strip().endswith('.') else '.'}",
    )
    await set_user_country_desc(user_id, description.strip())

    typing_task.cancel()

    await answer_html(
        message,
        f"⚖️ Да будет воля богов благосклонна к тебе, правитель страны <b>{country}</b>!\n\n"
        f"Отныне твое слово — закон для народа и воинов древнего мира. Ты можешь объявить себя императором и устремиться к завоеванию всех земель, "
        f"развивать тайны науки и искусство магии, чтобы превзойти других в могуществе, либо заботиться о счастье и благополучии своих подданных. "
        f"Какую судьбу изберешь для своей державы — решать лишь тебе!\n\n"
        f"<b>Твоё государство сейчас:</b>\n{description or '(ещё не заполнено)'}\n\n"
        "📜 <b>Полезные свитки:</b>\n"
        "/new — начать новую главу своей истории\n"
        "/send — отправить послание иному государству\n"
        "/reset_country — забыть прежнее и создать новое царство\n",
        reply_markup=ASPECTS_KEYBOARD,
    )

@router.message(F.text & ~F.text.startswith('/'))
async def handle_game_dialog(message, user_id: int, user_text: str):
    chat_id = message.chat.id
    user_name = message.from_user.username

    # Проверка на запрещённые современные слова
    bad_word = contains_modern_words(user_text)
    if bad_word:
        await answer_html(
            message,
            f"❗️Описание содержит слова, не подходящие для эпохи древнего мира — например, <b>{bad_word}</b>. "
            "Пожалуйста, перепиши описание, избегая современных понятий (автомобили, интернет, доллары и т.п.)",
            reply_markup=ASPECTS_KEYBOARD,
        )
        return

    try:
        await message.bot.send_chat_action(chat_id=chat_id, action="typing")
        typing_task = asyncio.create_task(keep_typing(message.bot, chat_id))

        await send_html(
            message.bot,
            ADMIN_CHAT_ID,
            f"📨 Новый запрос от пользователя {user_id} {user_name}:\n\n"
            f"<code>{user_text}</code>"
        )

        country_name = await get_user_country(user_id)
        country_desc = await get_user_country_desc(user_id)

        # Получить RAG-контекст (расширенную справку) для вставки в промпт к модели
        rag_context = await get_rag_context(user_id, user_text)

        # RPG_PROMPT + rag_context + история + пользовательский запрос
        # Модифицируем RPG_PROMPT если rag_context есть
        if rag_context:
            prompt_with_rag = f"{RPG_PROMPT}\n\n{rag_context}\n"
        else:
            prompt_with_rag = RPG_PROMPT + "\n\n"

        await send_html(
            message.bot,
            ADMIN_CHAT_ID,
            f"<b>Промпт:</b>\n"
            f"{prompt_with_rag}"
        )

        # Передадим rag-расширенный prompt в LLM
        assistant_reply, context = await asyncio.get_event_loop().run_in_executor(
            executor,
            model_handler.sync_generate_response,
            user_id, user_text, prompt_with_rag, country_name, country_desc, HISTORY_LIMIT
        )
        typing_task.cancel()
        html_reply = stars_to_bold(assistant_reply)
        await answer_html(message, html_reply, reply_markup=ASPECTS_KEYBOARD)

        await send_html(
            message.bot,
            ADMIN_CHAT_ID,
            f"<b>Полный ответ модели:</b>\n"
            f"{context[len(prompt_with_rag):]}"
        )
        await send_html(
            message.bot,
            ADMIN_CHAT_ID,
            f"<b>Ответ игроку:</b>\n"
            f"<code>{assistant_reply}</code>",
        )
    except Exception as e:
        await send_html(
            message.bot,
            ADMIN_CHAT_ID,
            f"Ошибка: {str(e)}"
        )

def register(dp):
    dp.include_router(router)