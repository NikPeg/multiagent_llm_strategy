import asyncio
import logging
from dotenv import load_dotenv
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from transformers import AutoModelForCausalLM, AutoTokenizer
from database import (
    init_db, get_history, update_history, clear_history,
    get_user_state, set_user_state, clear_user_state,
    get_user_country, set_user_country,
    get_user_country_desc, set_user_country_desc
)
import torch
from concurrent.futures import ThreadPoolExecutor
import re
from parsing import *

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID"))
HISTORY_LIMIT = int(os.getenv("HISTORY_LIMIT", 4))

if not BOT_TOKEN:
    raise ValueError("Токен бота не найден в .env!")

model_name = "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    device_map="auto",
    torch_dtype=torch.float16,
    use_flash_attention_2=False
)

device_info = f"Модель использует устройство: {model.device}"
logger.info(device_info)
cuda_available = torch.cuda.is_available()
logger.info(f"CUDA доступен: {cuda_available}")

if cuda_available:
    cuda_device_count = torch.cuda.device_count()
    cuda_device_name = torch.cuda.get_device_name(0) if cuda_device_count > 0 else "Нет"
    logger.info(f"Количество GPU: {cuda_device_count}")
    logger.info(f"Название GPU: {cuda_device_name}")
    logger.info(f"Текущее использование GPU памяти: {torch.cuda.memory_allocated() / 1024**2:.2f} МБ")
    logger.info(f"Максимальная доступная GPU память: {torch.cuda.get_device_properties(0).total_memory / 1024**2:.2f} МБ")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

executor = ThreadPoolExecutor(max_workers=1)

# Промпт для ролевого режима (передадим в модель первым контекстом!)
RPG_PROMPT = (
    "Ты — ведущий ролевой текстовой игры в стиле геополитики древнего мира. "
    "Каждый игрок управляет страной, развивает её экономику, дипломатию "
    "и армию, строит отношения с соседями и принимает решения. "
    "Цель — сделать свою страну процветающей и могущественной, "
    "любое решение должно иметь последствия! Ты рассказываешь, что происходит, "
    "отвечаешь только от лица мастера игры, четко следуя выбранному игроком сеттингу, "
    "никогда не отступаешь от выбранной роли. Всегда заканчивай свои ответы вопросами о дальнейших действиях игрока."
)

@dp.message(Command("start"))
async def start(message: types.Message):
    user_id = message.from_user.id
    await clear_history(user_id)
    await set_user_state(user_id, 'waiting_for_country_name')
    await set_user_country(user_id, None)
    await set_user_country_desc(user_id, None)
    await message.answer(
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
    await message.answer("⚔️Контекст диалога сброшен!⚔️")

@dp.message(F.text)
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
    await message.answer(
        f"Название страны: <b>{user_text.strip()}</b>\n\n"
        f"Теперь опиши кратко свою страну (география, особенности, народ, культура, стартовые условия):",
        parse_mode="HTML"
    )

async def handle_country_desc(message: types.Message, user_id: int, user_text: str):
    await set_user_country_desc(user_id, user_text.strip())
    await set_user_state(user_id, None)  # Сбросить состояние
    country = await get_user_country(user_id)
    await message.answer(
        f"Описание страны сохранено. Игра начата!\n"
        f"Действуй как правитель страны <b>{country}</b>.\n"
        f"Ты можешь отдавать приказы, объявлять войны, строить города или устанавливать отношения с другими странами.\n"
        f"В любой момент используй /new чтобы сбросить контекст."
        "\n\nЧто будешь делать первым делом?",
        parse_mode="HTML"
    )

async def handle_game_dialog(message: types.Message, user_id: int, user_text: str):
    chat_id = message.chat.id
    user_name = message.from_user.username
    logger.info(f"Получено сообщение от пользователя {user_id} {user_name}: {user_text[:50]}...")
    try:
        await bot.send_chat_action(chat_id=chat_id, action="typing")
        loop = asyncio.get_event_loop()
        typing_task = asyncio.create_task(keep_typing(chat_id))
        logger.info(f"Ожидание генерации ответа для пользователя {user_id}...")
        country_name = await get_user_country(user_id)
        country_desc = await get_user_country_desc(user_id)
        assistant_reply, context = await loop.run_in_executor(
            executor, sync_generate_response, user_id, user_text, country_name, country_desc
        )
        logger.info(f"Ответ сгенерирован для пользователя {user_id}")
        typing_task.cancel()
        html_reply = stars_to_bold(assistant_reply)
        try:
            await message.answer(html_reply, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения с HTML: {str(e)}", exc_info=True)
            await message.answer(assistant_reply)
        logger.info(f"Ответ отправлен пользователю {user_id}")
        await bot.send_message(
            ADMIN_CHAT_ID,
            f"📨 Новый запрос от пользователя {user_id} {user_name}:\n\n"
            f"<b>Промпт, переданный в модель:</b>\n"
            f"<code>{context}</code>\n\n"
            f"<b>Ответ модели:</b>\n"
            f"<code>{assistant_reply}</code>",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Ошибка при обработке сообщения: {str(e)}", exc_info=True)
        await message.answer(f"Ошибка: {str(e)}")

async def keep_typing(chat_id):
    try:
        typing_count = 0
        while True:
            await bot.send_chat_action(chat_id=chat_id, action="typing")
            typing_count += 1
            await asyncio.sleep(3)
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"Ошибка в keep_typing: {str(e)}", exc_info=True)

def sync_generate_response(user_id, message_text, country_name=None, country_desc=None):
    import asyncio
    from database import get_history, update_history  # Импортируем здесь для процесса
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        history = loop.run_until_complete(get_history(user_id))

        context_prompts = [RPG_PROMPT]
        if country_name and country_desc:
            context_prompts.append(
                f'Игрок управляет страной "{country_name}". Описание страны: {country_desc}'
            )
        context = '\n'.join(context_prompts + history + [f"User: {message_text}"]) + "\nAssistant:"

        inputs = tokenizer(context, return_tensors="pt").to(model.device)
        outputs = model.generate(
            **inputs,
            max_new_tokens=250,
            do_sample=True,
            temperature=0.7,
            top_p=0.95,
            eos_token_id=tokenizer.eos_token_id,
            pad_token_id=tokenizer.eos_token_id
        )
        response = tokenizer.decode(outputs[0], skip_special_tokens=True)

        # Чистим ответ ассистента
        ai_response = clean_ai_response(response[len(context):].strip())

        loop.run_until_complete(update_history(user_id, message_text, ai_response, HISTORY_LIMIT))
        loop.close()
        return ai_response, context
    except Exception as e:
        logger.error(f"Ошибка в generate_response: {str(e)}", exc_info=True)
        raise

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
