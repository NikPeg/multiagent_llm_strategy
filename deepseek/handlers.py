import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from concurrent.futures import ThreadPoolExecutor

from config import BOT_TOKEN, ADMIN_CHAT_ID, HISTORY_LIMIT, MAX_NEW_TOKENS, SHORT_NEW_TOKENS, GAME_PROMPT, RPG_PROMPT
from database import (
    init_db, user_exists, get_user_country_desc, clear_history, clear_user_aspects,
    set_user_country, set_user_country_desc, set_aspect_index, get_all_active_countries,
    get_user_country, get_user_id_by_country, get_user_aspect, set_user_aspect, set_aspect_index,
)
from model_handler import ModelHandler
from utils import answer_html, send_html, stars_to_bold, keep_typing
from game import ASPECTS, ASPECT_KEYS

import logging

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
executor = ThreadPoolExecutor(max_workers=1)
model_handler = ModelHandler(MAX_NEW_TOKENS, SHORT_NEW_TOKENS)
logger = logging.getLogger(__name__)


# --- USER COMMANDS ---

@dp.message(Command("start"))
async def start(message: types.Message):
    user_id = message.from_user.id

    if await user_exists(user_id):
        country_desc = await get_user_country_desc(user_id)
        help_text = (
            "👑 <b>Добро пожаловать снова!</b>\n\n"
            "Это ролевая игра в жанре геополитической стратегии древнего мира.\n"
            "Вы управляете собственной страной: развиваете экономику, армию, дипломатию.\n\n"
            f"<b>Описание вашей страны:</b>\n{country_desc or '(ещё не заполнено)'}\n\n"
            "📜 <b>Доступные команды:</b>\n"
            "/new — начать новый игровой диалог, сбросить текущий контекст\n"
            "/reset_country — сбросить страну и зарегистрировать новую\n"
            "\nДля игры просто отправляйте сообщения с приказами, вопросами или решениями, как правитель своей страны!\n"
        )
        await answer_html(message, help_text)
        return

    await clear_history(user_id)
    await clear_user_aspects(user_id)
    await set_user_country(user_id, None)
    await set_user_country_desc(user_id, None)
    await set_aspect_index(user_id, None)
    await answer_html(
        message,
        "Добро пожаловать в ролевую геополитическую игру эпохи древнего мира!\n\n"
        "Для начала укажи <b>название своей страны</b>:"
    )

@dp.message(Command("new"))
async def new_chat(message: types.Message):
    user_id = message.from_user.id
    await clear_history(user_id)
    await answer_html(message, "Контекст диалога сброшен!⚔️")

# --- FSM: СБРОС СТРАНЫ ---

class ResetCountry(StatesGroup):
    confirming = State()

@dp.message(Command("reset_country"))
async def reset_country(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    await state.set_state(ResetCountry.confirming)
    await answer_html(
        message,
        "⚠️ <b>Внимание!</b> После сброса вы потеряете ВСЮ информацию о вашей текущей стране, её аспектах и истории.\n\n"
        "Если вы уверены, напишите <b>ДА</b>.\n"
        "Для отмены введите /cancel."
    )

@dp.message(ResetCountry.confirming)
async def confirm_reset_country(message: types.Message, state: FSMContext):
    text = message.text.strip().lower()
    user_id = message.from_user.id
    if text in ("да", "yes", "подтвердить"):
        await clear_history(user_id)
        await clear_user_aspects(user_id)
        await set_user_country(user_id, None)
        await set_user_country_desc(user_id, None)
        await set_aspect_index(user_id, None)
        await state.clear()
        await answer_html(
            message,
            "⏳ Регистрация страны сброшена!\n\n"
            "Введите <b>новое название вашей страны</b> для повторной регистрации:"
        )
    else:
        await answer_html(
            message,
            "Введите <b>ДА</b>, чтобы подтвердить сброс, или /cancel для отмены."
        )

@dp.message(Command("cancel"))
async def admin_edit_cancel(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is not None:
        await state.clear()
        await answer_html(message, "Изменение отменено.")
    else:
        await answer_html(message, "Нет активных действий для отмены.")

# --- ADMIN BLOCK ---

class EditAspect(StatesGroup):
    waiting_new_value = State()

@dp.message(Command("info"))
async def info(message: types.Message):
    if message.chat.id != ADMIN_CHAT_ID:
        await answer_html(message, "У вас нет прав на эту команду.")
        return

    params = message.text.split(maxsplit=1)[1:]  # всё, что после команды
    args = params[0].split() if params else []

    countries = await get_all_active_countries()
    if not countries:
        await answer_html(message, "Активных стран не обнаружено.")
        return

    countries_dict = {}
    for country_tuple in countries:
        user_id, country_name, country_desc, *aspect_values = country_tuple
        countries_dict[country_name.strip().lower()] = {
            "user_id": user_id,
            "country_name": country_name,
            "country_desc": country_desc,
            "aspects": aspect_values
        }

    aspect_labels = {a[0]: a[1] for a in ASPECTS}
    aspect_codes = list(aspect_labels.keys())

    # HELP
    if args and args[0].lower() in ("help", "справка", "?"):
        help_text = (
                "<b>/info</b> — просмотр стран и аспектов\n"
                "<b>Использование:</b>\n"
                "/info — все страны и все аспекты\n"
                "/info <i>страна</i> — все аспекты по стране\n"
                "/info <i>аспект</i> — этот аспект по всем странам\n"
                "/info <i>страна</i> <i>аспект</i> — выбранный аспект страны\n\n"
                "<b>Доступные коды аспектов:</b>\n" +
                "\n".join(f"<b>{code}</b>: {aspect_labels[code]}" for code in aspect_codes)
        )
        await send_html(bot, ADMIN_CHAT_ID, help_text)
        return

    if not args:
        for country_tuple in countries:
            user_id, country_name, country_desc, *aspect_values = country_tuple
            await send_html(
                bot,
                ADMIN_CHAT_ID,
                f"🗺 <b>Страна:</b> {country_name} (ID: {user_id})"
            )
            await send_html(
                bot,
                ADMIN_CHAT_ID,
                f"<b>Описание:</b>\n{country_desc or '(Нет)'}"
            )
            for (code, label, _), value in zip(ASPECTS, aspect_values):
                if value and value.strip():
                    await send_html(
                        bot,
                        ADMIN_CHAT_ID,
                        f"<b>{label}</b>:\n{stars_to_bold(value)}"
                    )
        return

    if len(args) == 1:
        arg = args[0].lower()
        if arg in aspect_labels:
            idx = aspect_codes.index(arg)
            for country_tuple in countries:
                country_name = country_tuple[1]
                user_id = country_tuple[0]
                aspect_value = country_tuple[3 + idx]
                if aspect_value and aspect_value.strip():
                    await send_html(
                        bot, ADMIN_CHAT_ID,
                        f"<b>{country_name}</b> (ID: {user_id}):\n<b>{aspect_labels[arg]}</b>:\n{stars_to_bold(aspect_value)}"
                    )
            return
        if arg in countries_dict:
            c = countries_dict[arg]
            await send_html(
                bot,
                ADMIN_CHAT_ID,
                f"🗺 <b>Страна:</b> {c['country_name']} (ID: {c['user_id']})"
            )
            await send_html(
                bot,
                ADMIN_CHAT_ID,
                f"<b>Описание:</b>\n{c['country_desc'] or '(Нет)'}"
            )
            for (code, label, _), value in zip(ASPECTS, c["aspects"]):
                if value and value.strip():
                    await send_html(
                        bot, ADMIN_CHAT_ID, f"<b>{label}:</b>\n{stars_to_bold(value)}"
                    )
            return
        await answer_html(message, "Не найдено ни страны, ни аспекта с таким названием.")
        return

    if len(args) == 2:
        country = args[0].lower()
        aspect = args[1].lower()
        if country not in countries_dict:
            await answer_html(message, "Страна не найдена.")
            return
        if aspect not in aspect_labels:
            await answer_html(message, "Аспект не найден.")
            return
        idx = aspect_codes.index(aspect)
        value = countries_dict[country]["aspects"][idx]
        label = aspect_labels[aspect]
        if value and value.strip():
            await send_html(
                bot,
                ADMIN_CHAT_ID,
                f"<b>{label}</b> для страны <b>{countries_dict[country]['country_name']}</b>:\n{stars_to_bold(value)}"
            )
        else:
            await send_html(
                bot,
                ADMIN_CHAT_ID,
                f"Аспект <b>{label}</b> для страны <b>{countries_dict[country]['country_name']}</b> не найден."
            )
        return

    await answer_html(
        message,
        "Некорректные параметры. Форматы:\n/info [страна]\n/info [аспект]\n/info [страна] [аспект]\n\n"
        "Для помощи введите /info help"
    )

@dp.message(Command("edit"))
async def admin_edit(message: types.Message, state: FSMContext):
    if message.chat.id != ADMIN_CHAT_ID:
        await answer_html(message, "У вас нет прав на эту команду.")
        return

    args = message.text.split(maxsplit=1)[1:]
    if not args:
        await answer_html(message, "Формат: /edit <страна> <аспект>")
        return
    parts = args[0].split()
    if len(parts) != 2:
        await answer_html(message, "Формат: /edit <страна> <аспект>")
        return

    country_name = parts[0].strip()
    aspect_code = parts[1].strip()
    user_id = await get_user_id_by_country(country_name)
    if not user_id:
        await answer_html(message, f'Страна "{country_name}" не найдена.')
        return

    if aspect_code not in [a[0] for a in ASPECTS]:
        await answer_html(message, f'Аспект "{aspect_code}" не найден.')
        return

    current_value = await get_user_aspect(user_id, aspect_code)
    label = dict((a[0], a[1]) for a in ASPECTS)[aspect_code]
    await answer_html(
        message,
        f"<b>{label}</b> для страны <b>{country_name}</b>:\n\n{stars_to_bold(current_value or '(нет данных)')}\n\n"
        "Введите новый текст для этого поля, или /cancel для отмены."
    )
    await state.set_state(EditAspect.waiting_new_value)
    await state.update_data(user_id=user_id, aspect_code=aspect_code, country_name=country_name)

@dp.message(EditAspect.waiting_new_value)
async def process_new_value(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if not data:
        await answer_html(message, "Внутренняя ошибка: не указаны страна и аспект.")
        await state.clear()
        return

    user_id = data["user_id"]
    aspect_code = data["aspect_code"]
    country_name = data["country_name"]
    new_value = message.text.strip()

    await set_user_aspect(user_id, aspect_code, new_value)
    label = dict((a[0], a[1]) for a in ASPECTS)[aspect_code]

    await answer_html(
        message,
        f"<b>{label}</b> для страны <b>{country_name}</b> успешно обновлён!"
    )
    await state.clear()


# --- GAME/REGISTRATION: ОБЫЧНЫЕ СООБЩЕНИЯ ---

@dp.message(F.text & ~F.text.startswith('/'))
async def handle_message(message: types.Message):
    user_id = message.from_user.id
    user_text = message.text.strip()

    country = await get_user_country(user_id)
    country_desc = await get_user_country_desc(user_id)

    if not country:
        await handle_country_name(message, user_id, user_text)
    elif not country_desc:
        await handle_country_desc(message, user_id, user_text)
    else:
        await handle_game_dialog(message, user_id, user_text)


async def handle_country_name(message: types.Message, user_id: int, user_text: str):
    await set_user_country(user_id, user_text)
    await answer_html(
        message,
        f"Название страны: <b>{user_text}</b>\n\n"
        f"Теперь опиши кратко свою страну (география, особенности, народ, культура, стартовые условия):"
    )

async def handle_country_desc(message: types.Message, user_id: int, user_text: str):
    country = await get_user_country(user_id)
    chat_id = message.chat.id

    await answer_html(message, "Создаю подробное начальное описание всех аспектов вашей страны, пожалуйста, подождите...")
    typing_task = asyncio.create_task(keep_typing(bot, chat_id))

    loop = asyncio.get_event_loop()
    user_name = message.from_user.username
    await send_html(
        bot,
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
        bot,
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


async def handle_game_dialog(message: types.Message, user_id: int, user_text: str):
    chat_id = message.chat.id
    user_name = message.from_user.username

    logger.info(f"Получено сообщение от пользователя {user_id} {user_name}: {user_text[:50]}...")
    try:
        await bot.send_chat_action(chat_id=chat_id, action="typing")
        typing_task = asyncio.create_task(keep_typing(bot, chat_id))
        logger.info(f"Ожидание генерации ответа для пользователя {user_id}...")
        country_name = await get_user_country(user_id)
        country_desc = await get_user_country_desc(user_id)

        assistant_reply, context = await asyncio.get_event_loop().run_in_executor(
            executor,
            model_handler.sync_generate_response,
            user_id, user_text, RPG_PROMPT, country_name, country_desc, HISTORY_LIMIT
        )
        logger.info(f"Ответ сгенерирован для пользователя {user_id}")
        typing_task.cancel()
        html_reply = stars_to_bold(assistant_reply)
        await answer_html(message, html_reply)

        await send_html(
            bot,
            ADMIN_CHAT_ID,
            f"📨 Новый запрос от пользователя {user_id} {user_name}:\n\n"
            f"<b>Промпт, переданный в модель:</b>\n"
            f"<code>{context}</code>\n\n"
            f"<b>Ответ модели:</b>\n"
            f"<code>{assistant_reply}</code>"
        )
    except Exception as e:
        logger.error(f"Ошибка при обработке сообщения: {str(e)}", exc_info=True)
        await answer_html(message, f"Ошибка: {str(e)}")
