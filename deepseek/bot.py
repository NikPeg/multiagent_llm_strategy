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
from utils import answer_html, send_html, keep_typing

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

model_handler = ModelHandler(MAX_NEW_TOKENS)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
executor = ThreadPoolExecutor(max_workers=1)

# Список аспектов страны: (кодовое_поле, человекочитаемое_название, вопрос)
ASPECTS = [
    ("экономика", "Экономика", "Опиши экономику своей страны:"),
    ("военное_дело", "Военное дело", "Расскажи о военном деле, армии, обороне и безопасности:"),
    ("внеш_политика", "Внешняя политика", "Как страна ведёт внешнюю политику (союзы, враги и т.д.):"),
    ("территория", "Территория", "Опиши территорию, размеры, климат, природные особенности:"),
    ("технологичность", "Технологичность", "Как развиты технологии в стране?"),
    ("религия_культура", "Религия и культура", "Культура, религия, искусство, традиции:"),
    ("управление", "Управление и право", "Какой строй, законы, судебная система, власть?"),
    ("стройка", "Строительство и инфраструктура", "Уровень инфраструктуры, дороги, города, постройки:"),
    ("общество", "Общественные отношения", "Структура общества, сословия, взаимодействие народов:"),
]
ASPECT_KEYS = [a[0] for a in ASPECTS]

@dp.message(Command("start"))
async def start(message: types.Message):
    user_id = message.from_user.id
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

@dp.message(Command("admin_status"))
async def admin_status(message: types.Message):
    if message.chat.id != ADMIN_CHAT_ID:
        await answer_html(message, "У вас нет прав на эту команду.")
        return

    countries = await get_all_active_countries()
    if not countries:
        await answer_html(message, "Активных стран не обнаружено.")
        return

    for country_tuple in countries:
        user_id, country_name, country_desc, *aspect_values = country_tuple
        # Если вдруг где-то не хватает полей — игнорируем
        if len(aspect_values) != len(ASPECTS):
            continue
        await send_html(
            bot,
            ADMIN_CHAT_ID,
            f"🗺 <b>Страна:</b> {country_name} (ID игрока: {user_id})\n"
            f"<b>Описание:</b>\n{country_desc or '(Нет)'}"
        )
        for (code, label, _), value in zip(ASPECTS, aspect_values):
            if value and value.strip():
                await send_html(
                    bot,
                    ADMIN_CHAT_ID,
                    f"<b>{label}:</b>\n{stars_to_bold(value)}"
                )

# Только для обычных сообщений с текстом, не команд
@dp.message(F.text & ~F.text.startswith('/'))
async def handle_message(message: types.Message):
    user_id = message.from_user.id
    user_text = message.text.strip()

    # Ловим этап игры: название страны, описание страны или опрос аспектов, иначе: игровой диалог
    country = await get_user_country(user_id)
    country_desc = await get_user_country_desc(user_id)
    aspect_index = await get_aspect_index(user_id)

    if not country:
        await handle_country_name(message, user_id, user_text)
    elif not country_desc:
        await handle_country_desc(message, user_id, user_text)
    elif aspect_index is not None:
        await handle_aspect_step(message, user_id, user_text, aspect_index)
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
    await set_user_country_desc(user_id, user_text)
    # Запустить опрос аспектов, начиная с первого (0)
    await set_aspect_index(user_id, 0)
    await answer_html(message, ASPECTS[0][2])

async def handle_aspect_step(message: types.Message, user_id: int, user_text: str, aspect_index: int):
    code, label, question = ASPECTS[aspect_index]
    await set_user_aspect(user_id, code, user_text)

    # Переходим к следующему аспекту, либо стартуем игру если все заполнено:
    if aspect_index + 1 < len(ASPECTS):
        await set_aspect_index(user_id, aspect_index + 1)
        next_question = ASPECTS[aspect_index + 1][2]
        await answer_html(message, next_question)
    else:
        await set_aspect_index(user_id, None)
        # Все аспекты сохранены — показываем итог и переходим к игре!
        summary_lines = []
        for code, label, _ in ASPECTS:
            value = await get_user_aspect(user_id, code)
            if value:
                summary_lines.append(f"<b>{label}:</b>\n{stars_to_bold(value)}")
        country = await get_user_country(user_id)
        await answer_html(
            message,
            f"✅ Все аспекты описаны! Начальное состояние страны <b>{country}</b>:\n\n" +
            "\n\n".join(summary_lines)
        )
        user_name = message.from_user.username
        await send_html(
            bot,
            ADMIN_CHAT_ID,
            f"📨 Новая страна от пользователя {user_id} {user_name}:\n\n"
            f"<b>Название:</b> {country}\n"
            f"<b>Описание:</b> {await get_user_country_desc(user_id)}\n\n"
            + "\n\n".join(summary_lines)
        )
        await answer_html(
            message,
            f"Игра начата! Действуй как правитель <b>{country}</b>.\n"
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
        # Можно собрать аспекты в один status для модельки при необходимости
        aspects = [await get_user_aspect(user_id, code) for code in ASPECT_KEYS]
        aspects_str = "\n".join(
            f"{label}: {value}" for (code, label, _), value in zip(ASPECTS, aspects) if value
        )
        prompt_context = (
                f"Название страны: '{country_name}'\n"
                f"Описание страны: {country_desc}\n"
                + aspects_str
        )

        assistant_reply, context = await asyncio.get_event_loop().run_in_executor(
            executor,
            model_handler.sync_generate_response,
            user_id, user_text, prompt_context, country_name, country_desc, HISTORY_LIMIT
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
