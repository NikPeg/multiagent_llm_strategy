import asyncio
import logging
from dotenv import load_dotenv
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from transformers import AutoModelForCausalLM, AutoTokenizer
from database import init_db, get_history, update_history, clear_history
import torch
from concurrent.futures import ThreadPoolExecutor

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
HISTORY_LIMIT = int(os.getenv("HISTORY_LIMIT", 10))

if not BOT_TOKEN:
    raise ValueError("Токен бота не найден в .env!")

# Инициализация модели
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
cuda_available = torch.cuda.is_available()
logger.info(f"CUDA доступен: {cuda_available}")

if cuda_available:
    cuda_device_count = torch.cuda.device_count()
    cuda_device_name = torch.cuda.get_device_name(0) if cuda_device_count > 0 else "Нет"
    logger.info(f"Количество GPU: {cuda_device_count}")
    logger.info(f"Название GPU: {cuda_device_name}")
    logger.info(f"Текущее использование GPU памяти: {torch.cuda.memory_allocated() / 1024**2:.2f} МБ")
    logger.info(f"Максимальная доступная GPU память: {torch.cuda.get_device_properties(0).total_memory / 1024**2:.2f} МБ")

# Инициализация бота
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

executor = ThreadPoolExecutor(max_workers=1)

# Определение состояний для FSM
class CountryRegistration(StatesGroup):
    waiting_for_name = State()
    waiting_for_government = State()
    waiting_for_resources = State()
    waiting_for_goals = State()

# Системный промпт для модели
SYSTEM_PROMPT = """
Ты - нейтральный и мудрый судья в геополитической РПГ-игре, где пользователи играют за разные страны.
Твоя задача - создавать интересные и реалистичные сценарии, отвечать на действия игроков и определять их последствия.
Учитывай экономику, дипломатию, военную мощь, ресурсы и другие факторы в своих ответах.
Будь справедливым и объективным, не отдавай предпочтение ни одной из стран.
Описывай мир в деталях, помогай игрокам развивать их истории.
Не используй шаблонные ответы - каждая ситуация должна быть уникальной.
"""

@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    await clear_history(message.from_user.id)
    await message.answer(
        "🌍 Добро пожаловать в геополитическую РПГ! 🌍\n\n"
        "Здесь вы можете создать и управлять своей страной, взаимодействовать с миром и другими игроками.\n\n"
        "Давайте начнем с создания вашей страны. Как называется ваша страна?"
    )
    await state.set_state(CountryRegistration.waiting_for_name)

@dp.message(CountryRegistration.waiting_for_name)
async def process_country_name(message: types.Message, state: FSMContext):
    await state.update_data(country_name=message.text)
    await message.answer(
        f"Отлично! Ваша страна называется {message.text}.\n\n"
        "Какая форма правления в вашей стране? (например: демократия, монархия, диктатура и т.д.)"
    )
    await state.set_state(CountryRegistration.waiting_for_government)

@dp.message(CountryRegistration.waiting_for_government)
async def process_government(message: types.Message, state: FSMContext):
    await state.update_data(government=message.text)
    await message.answer(
        f"Ваша страна - {message.text}.\n\n"
        "Какими основными ресурсами и индустриями обладает ваша страна?"
    )
    await state.set_state(CountryRegistration.waiting_for_resources)

@dp.message(CountryRegistration.waiting_for_resources)
async def process_resources(message: types.Message, state: FSMContext):
    await state.update_data(resources=message.text)
    await message.answer(
        "Какие главные геополитические цели преследует ваша страна? Какие отношения с соседями?"
    )
    await state.set_state(CountryRegistration.waiting_for_goals)

@dp.message(CountryRegistration.waiting_for_goals)
async def process_goals(message: types.Message, state: FSMContext):
    await state.update_data(goals=message.text)

    # Получаем все данные
    data = await state.get_data()
    country_name = data.get("country_name")
    government = data.get("government")
    resources = data.get("resources")
    goals = data.get("goals")

    # Формируем описание страны
    country_description = (
        f"Страна игрока: {country_name}\n"
        f"Форма правления: {government}\n"
        f"Ресурсы и индустрии: {resources}\n"
        f"Геополитические цели: {goals}"
    )

    # Добавляем начальную информацию в историю диалога
    initial_message = (
        "Игрок зарегистрировал свою страну в геополитической РПГ.\n"
        f"{country_description}"
    )

    await update_history(message.from_user.id, "Регистрация страны", initial_message, HISTORY_LIMIT)

    await message.answer(
        f"🎉 Поздравляем! Ваша страна {country_name} успешно создана! 🎉\n\n"
        "Теперь вы можете взаимодействовать с миром. Просто опишите свои действия, "
        "планы или задайте вопросы о текущей ситуации.\n\n"
        "Чтобы начать новую игру с другой страной, используйте команду /new."
    )

    await state.clear()

@dp.message(Command("new"))
async def new_chat(message: types.Message, state: FSMContext):
    await clear_history(message.from_user.id)
    await message.answer("⚔️ Новая игра начата! Предыдущая история сброшена. ⚔️")
    await message.answer("Чтобы зарегистрировать новую страну, используйте команду /start")

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

        # Добавляем системный промпт к контексту
        context = SYSTEM_PROMPT + "\n\n" + '\n'.join(history + [f"Игрок: {message_text}"]) + "\nСудья игры:"

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
        assistant_reply = response[len(context):].strip()

        # Обрабатываем многострочный ответ
        if '\n' in assistant_reply:
            assistant_reply = '\n'.join([line for line in assistant_reply.split('\n')
                                         if not line.strip().startswith('Игрок:') and not line.strip().startswith('User:')])

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
