import asyncio
import logging
from dotenv import load_dotenv
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from transformers import AutoModelForCausalLM, AutoTokenizer
from database import init_db, get_history, update_history, clear_history
import torch
from concurrent.futures import ThreadPoolExecutor

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
HISTORY_LIMIT = int(os.getenv("HISTORY_LIMIT", 10))

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

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
            "Я виртуальный помощник на основе DeepSeek-R1. "
        "Чтобы сбросить контекст диалога - /new")

@dp.message(Command("new"))
async def new_chat(message: types.Message):
    await clear_history(message.from_user.id)
    await message.answer("⚔️ Контекст диалога сброшен!⚔️")

@dp.message(F.text)
async def handle_message(message: types.Message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    user_text = message.text
    
    logger.info(f"Получено сообщение от пользователя {user_id}: {user_text[:50]}...")
    try:
        await bot.send_chat_action(chat_id=chat_id, action="typing")
        loop = asyncio.get_event_loop()
        typing_task = asyncio.create_task(keep_typing(chat_id))
        logger.info(f"Ожидание генерации ответа для пользователя {user_id}...")
        assistant_reply = await loop.run_in_executor(executor, sync_generate_response, user_id, user_text)
        logger.info(f"Ответ сгенерирован для пользователя {user_id}")
        typing_task.cancel()
        await message.answer(assistant_reply)
        logger.info(f"Ответ отправлен пользователю {user_id}")
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

def sync_generate_response(user_id, message_text):
    import asyncio
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        history = loop.run_until_complete(get_history(user_id))
        context = '\n'.join(history + [f"User: {message_text}"]) + "\nAssistant:"
        inputs = tokenizer(context, return_tensors="pt").to(model.device)
        outputs = model.generate(
            **inputs,
            max_new_tokens=512,
            do_sample=True,
            temperature=0.7,
            top_p=0.95,
            eos_token_id=tokenizer.eos_token_id,
            pad_token_id=tokenizer.eos_token_id
        )
        response = tokenizer.decode(outputs[0], skip_special_tokens=True)
        assistant_reply = response[len(context):].strip().split('\n')[0]
        loop.run_until_complete(update_history(user_id, message_text, assistant_reply, HISTORY_LIMIT))
        loop.close()
        return assistant_reply
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

