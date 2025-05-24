import asyncio
import logging
from dotenv import load_dotenv
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from transformers import AutoModelForCausalLM, AutoTokenizer
from database import init_db, get_history, update_history, clear_history
import torch

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
HISTORY_LIMIT = int(os.getenv("HISTORY_LIMIT", 10))

if not BOT_TOKEN:
    raise ValueError("Токен бота не найден в .env!")

logger.info("Загрузка модели и токенизатора...")
model_name = "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    device_map="auto",
    torch_dtype=torch.float16,
    use_flash_attention_2=False
)

# Логирование информации об устройстве
device_info = f"Модель использует устройство: {model.device}"
logger.info(device_info)

# Проверка доступности CUDA
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
        # Начинаем показывать "печатает..."
        await bot.send_chat_action(chat_id=chat_id, action="typing")
        
        # Запускаем генерацию ответа в отдельном таске
        generation_task = asyncio.create_task(generate_response(user_id, user_text))
        
        # Запускаем задачу периодической отправки статуса "печатает..."
        typing_task = asyncio.create_task(keep_typing(chat_id))
        
        # Ждем завершения генерации ответа
        logger.info(f"Ожидание генерации ответа для пользователя {user_id}...")
        assistant_reply = await generation_task
        logger.info(f"Ответ сгенерирован для пользователя {user_id}")
        
        # Останавливаем отправку статуса "печатает..."
        typing_task.cancel()
        
        # Отправляем ответ
        await message.answer(assistant_reply)
        logger.info(f"Ответ отправлен пользователю {user_id}")
        
    except Exception as e:
        logger.error(f"Ошибка при обработке сообщения: {str(e)}", exc_info=True)
        await message.answer(f"Ошибка: {str(e)}")

async def keep_typing(chat_id):
    """Периодически отправляет статус 'печатает...' в чат"""
    try:
        typing_count = 0
        while True:
            await bot.send_chat_action(chat_id=chat_id, action="typing")
            typing_count += 1
            logger.debug(f"Отправлен статус typing... для chat_id {chat_id} (#{typing_count})")
            # Отправляем статус чаще - каждые 3 секунды
            await asyncio.sleep(3)
    except asyncio.CancelledError:
        logger.debug(f"Задача keep_typing для chat_id {chat_id} отменена после {typing_count} отправок")
        pass
    except Exception as e:
        logger.error(f"Ошибка в keep_typing: {str(e)}", exc_info=True)

async def generate_response(user_id, message_text):
    """Генерирует ответ модели"""
    try:
        if torch.cuda.is_available():
            logger.info(f"Перед генерацией: {torch.cuda.memory_allocated() / 1024**2:.2f} МБ GPU используется")
            logger.info(f"Перед генерацией: {torch.cuda.memory_reserved() / 1024**2:.2f} МБ GPU зарезервировано")
        
        start_time = asyncio.get_event_loop().time()
        logger.info(f"Получение истории для пользователя {user_id}")
        history = await get_history(user_id)
        
        logger.info(f"Подготовка контекста для пользователя {user_id}")
        context = '\n'.join(history + [f"User: {message_text}"]) + "\nAssistant:"
        
        logger.info(f"Токенизация ввода для пользователя {user_id}")
        inputs = tokenizer(context, return_tensors="pt").to(model.device)
        
        logger.info(f"Начало генерации ответа для пользователя {user_id}")
        outputs = model.generate(
            **inputs,
            max_new_tokens=512,
            do_sample=True,
            temperature=0.7,
            top_p=0.95,
            eos_token_id=tokenizer.eos_token_id,
            pad_token_id=tokenizer.eos_token_id
        )
        
        logger.info(f"Декодирование ответа для пользователя {user_id}")
        response = tokenizer.decode(outputs[0], skip_special_tokens=True)
        assistant_reply = response[len(context):].strip().split('\n')[0]
        
        end_time = asyncio.get_event_loop().time()
        generation_time = end_time - start_time
        logger.info(f"Генерация заняла {generation_time:.2f} секунд для пользователя {user_id}")
        
        if torch.cuda.is_available():
            logger.info(f"После генерации: {torch.cuda.memory_allocated() / 1024**2:.2f} МБ GPU используется")
            logger.info(f"После генерации: {torch.cuda.memory_reserved() / 1024**2:.2f} МБ GPU зарезервировано")
        
        # Обновляем историю
        logger.info(f"Обновление истории для пользователя {user_id}")
        await update_history(user_id, message_text, assistant_reply, HISTORY_LIMIT)
        
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

