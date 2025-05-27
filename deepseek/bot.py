import asyncio
import logging
from dotenv import load_dotenv
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from concurrent.futures import ThreadPoolExecutor
from model_handler import ModelHandler
from database import *
from parsing import stars_to_bold
from utils import *

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID"))
HISTORY_LIMIT = int(os.getenv("HISTORY_LIMIT", 4))
MAX_NEW_TOKENS = int(os.getenv("MAX_NEW_TOKENS", 512))

if not BOT_TOKEN:
    raise ValueError("Токен бота не найден в .env!")

# Initialize model handler
model_handler = ModelHandler(MAX_NEW_TOKENS)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

executor = ThreadPoolExecutor(max_workers=1)

# Промпт для ролевого режима
RPG_PROMPT = (
    "Ты — ведущий ролевой текстовой игры в стиле геополитики древнего мира. "
    "Каждый игрок управляет страной, развивает её экономику, дипломатию "
    "и армию, строит отношения с соседями и принимает решения. "
    "Цель — сделать свою страну процветающей и могущественной, "
    "любое решение должно иметь последствия! Ты рассказываешь, что происходит, "
    "отвечаешь только от лица мастера игры, четко следуя выбранному игроком сеттингу, "
    "никогда не отступаешь от выбранной роли."
)

@dp.message(Command("start"))
async def start(message: types.Message):
    user_id = message.from_user.id
    await clear_history(user_id)
    await set_user_state(user_id, 'waiting_for_country_name')
    await set_user_country(user_id, None)
    await set_user_country_desc(user_id, None)
    await answer_html(
        message,
        "Добро пожаловать в ролевую геополитическую игру эпохи древнего мира!\n\n"
        "Для начала игры укажи название своей страны:"
    )

@dp.message(Command("new"))
async def new_chat(message: types.Message):
    user_id = message.from_user.id
    await clear_history(user_id)
    await clear_user_state(user_id)
    await set_user_country(user_id, None)
    await set_user_country_desc(user_id, None)
    await answer_html(message, "⚔️Контекст диалога сброшен!⚔️")

@dp.message(Command("admin_status"))
async def admin_status(message: types.Message):
    # Проверка, что запрос от администратора
    if message.chat.id != ADMIN_CHAT_ID:
        await answer_html(message, "У вас нет прав на эту команду.")
        return

    # Получаем информацию о всех странах через специальную функцию
    countries = await get_all_active_countries()

    if not countries:
        await answer_html(message, "Активных стран не обнаружено.")
        return

    # Отправляем статус каждой страны
    for user_id, country_name, status in countries:
        await answer_html(
            message,
            f"<b>Страна:</b> {country_name}\n"
            f"<b>ID игрока:</b> {user_id}\n\n"
            f"<b>Текущее состояние:</b>\n{stars_to_bold(status)}"
        )

# Основной обработчик обычных текстовых сообщений пользователя (НЕ команд)
@dp.message(F.text & ~F.text.startswith('/'))
async def handle_message(message: types.Message):
    user_id = message.from_user.id
    user_text = message.text
    state = await get_user_state(user_id)

    if state == 'waiting_for_country_name':
        await handle_country_name(message, user_id, user_text)
    elif state == 'waiting_for_country_desc':
        await handle_country_desc(message, user_id, user_text)
    else:
        await handle_game_dialog(message, user_id, user_text)

async def handle_country_name(message: types.Message, user_id: int, user_text: str):
    await set_user_country(user_id, user_text.strip())
    await set_user_state(user_id, 'waiting_for_country_desc')
    await answer_html(
        message,
        f"Название страны: <b>{user_text.strip()}</b>\n\n"
        f"Теперь опиши кратко свою страну (география, особенности, народ, культура, стартовые условия):"
    )

async def handle_country_desc(message: types.Message, user_id: int, user_text: str):
    await set_user_country_desc(user_id, user_text.strip())
    country = await get_user_country(user_id)

    # Генерируем начальное состояние страны после получения описания
    await answer_html(message, "Создаю детальное описание состояния вашей страны...")
    chat_id = message.chat.id
    typing_task = asyncio.create_task(keep_typing(bot, chat_id))

    initial_status_prompt = (
        f"Название страны: '{country}'\n"
        f"Описание страны: {user_text.strip()}\n"
        f"Подробное состояние страны в игре (экономика, культура, армия, территории):"
    )

    loop = asyncio.get_event_loop()
    country_status = await loop.run_in_executor(
        executor,
        model_handler.generate_short_responce,
        initial_status_prompt,
    )
    logger.info(f"Состояние страны {country}: {country_status}")

    # Сохраняем сгенерированное состояние страны
    await set_country_status(user_id, country_status)

    # Показываем пользователю начальное состояние страны
    await answer_html(
        message,
        f"<b>Начальное состояние вашей страны:</b>\n\n{stars_to_bold(country_status)}"
    )
    user_name = message.from_user.username
    await send_html(
        ADMIN_CHAT_ID,
        f"📨 Регистрация новой страны от пользователя {user_id} {user_name}:\n\n"
        f"Название страны: <b>{country}</b>\n"
        f"Описание страны:\n{user_text}\n\n"
        f"<b>Состояние страны:</b>\n"
        f"{country_status}"
    )

    # Завершаем установку и переходим к игре
    await set_user_state(user_id, None)  # Сбросить состояние
    await answer_html(
        message,
        f"Игра начата! Действуй как правитель страны <b>{country}</b>.\n"
        f"Ты можешь отдавать приказы, объявлять войны, строить города или устанавливать отношения с другими странами.\n"
        f"В любой момент используй /new чтобы сбросить контекст."
        "\n\nЧто будешь делать первым делом?"
    )
    typing_task.cancel()

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
        logger.info(f"Ответ отправлен пользователю {user_id}")

        await send_html(
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

async def update_country_status(user_id, country_name, country_desc, action):
    """Обновляет состояние страны после действия игрока"""
    current_status = await get_country_status(user_id)

    status_update_prompt = (
        f"Страна: {country_name}\n"
        f"Текущее состояние страны:\n{current_status}\n\n"
        f"Игрок выполнил действие: {action}\n\n"
        f"Обнови параметры страны с учетом выполненного действия. "
        f"Сохрани структуру, но измени соответствующие показатели."
    )

    loop = asyncio.get_event_loop()
    new_status, _ = await loop.run_in_executor(
        executor,
        model_handler.sync_generate_response,
        user_id, status_update_prompt, RPG_PROMPT, country_name, country_desc, HISTORY_LIMIT
    )

    await set_country_status(user_id, new_status)
    return new_status

async def main():
    logger.info("Инициализация базы данных...")
    await init_db()
    logger.info("Запуск бота...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        logger.info("Запуск приложения...")
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Приложение завершено")
    except Exception as e:
        logger.critical(f"Критическая ошибка: {str(e)}", exc_info=True)
