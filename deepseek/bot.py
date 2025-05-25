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
import datetime

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
HISTORY_LIMIT = int(os.getenv("HISTORY_LIMIT", 10))
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")  # Получаем ID чата администраторов из .env

if not BOT_TOKEN:
    raise ValueError("Токен бота не найден в .env!")

if not ADMIN_CHAT_ID:
    logger.warning("ID чата администраторов не найден в .env! Пересылка сообщений будет отключена.")

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

# Определение состояний для FSM (упрощенная версия)
class CountryRegistration(StatesGroup):
    waiting_for_name = State()
    waiting_for_description = State()

# Системный промпт для модели
SYSTEM_PROMPT = """
Ты - нейтральный и мудрый судья в геополитической РПГ-игре, где пользователи играют за разные страны.
Твоя задача - создавать интересные и реалистичные сценарии, отвечать на действия игроков и определять их последствия.
Учитывай экономику, дипломатию, военную мощь, ресурсы и другие факторы в своих ответах.
Будь справедливым и объективным, не отдавай предпочтение ни одной из стран.
Описывай мир в деталях, помогай игрокам развивать их истории.
Не используй шаблонные ответы - каждая ситуация должна быть уникальной.
"""

# Функция для пересылки сообщений администраторам
async def forward_to_admins(user_message, bot_reply, user_info):
    if not ADMIN_CHAT_ID:
        return

    try:
        admin_notification = (
            f"📨 Новое сообщение в боте\n\n"
            f"👤 От пользователя: {user_info}\n\n"
            f"💬 Сообщение пользователя:\n{user_message}\n\n"
            f"🤖 Ответ бота:\n{bot_reply}"
        )

        # Если сообщение слишком длинное, разбиваем его
        if len(admin_notification) > 4000:
            # Отправляем информацию о пользователе
            await bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=f"📨 Новое сообщение в боте\n\n👤 От пользователя: {user_info}"
            )

            # Отправляем сообщение пользователя
            await bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=f"💬 Сообщение пользователя:\n{user_message}"
            )

            # Отправляем ответ бота
            await bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=f"🤖 Ответ бота:\n{bot_reply}"
            )
        else:
            await bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_notification)

        logger.info(f"Сообщение пользователя {user_info} переслано администраторам")
    except Exception as e:
        logger.error(f"Ошибка при пересылке сообщения администраторам: {str(e)}", exc_info=True)

@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    user_info = f"{message.from_user.full_name} (@{message.from_user.username}, ID: {message.from_user.id})"
    logger.info(f"Пользователь {user_info} запустил бота")

    await clear_history(message.from_user.id)

    reply_text = (
        "🌍 Добро пожаловать в геополитическую РПГ! 🌍\n\n"
        "Здесь вы можете создать и управлять своей страной, взаимодействовать с миром и другими игроками.\n\n"
        "Для начала, как называется ваша страна?"
    )

    await message.answer(reply_text)

    # Пересылаем администраторам
    if ADMIN_CHAT_ID:
        await forward_to_admins(
            "Пользователь запустил бота",
            reply_text,
            user_info
        )

    await state.set_state(CountryRegistration.waiting_for_name)

@dp.message(CountryRegistration.waiting_for_name)
async def process_country_name(message: types.Message, state: FSMContext):
    user_info = f"{message.from_user.full_name} (@{message.from_user.username}, ID: {message.from_user.id})"

    await state.update_data(country_name=message.text)

    reply_text = (
        f"Отлично! Ваша страна называется {message.text}.\n\n"
        "Теперь, пожалуйста, опишите свою страну: форма правления, ресурсы, экономика, культура, "
        "геополитические цели, отношения с соседями и любые другие важные детали."
    )

    await message.answer(reply_text)

    # Пересылаем администраторам
    if ADMIN_CHAT_ID:
        await forward_to_admins(
            f"Название страны: {message.text}",
            reply_text,
            user_info
        )

    await state.set_state(CountryRegistration.waiting_for_description)

@dp.message(CountryRegistration.waiting_for_description)
async def process_country_description(message: types.Message, state: FSMContext):
    user_info = f"{message.from_user.full_name} (@{message.from_user.username}, ID: {message.from_user.id})"

    await state.update_data(description=message.text)

    # Получаем все данные
    data = await state.get_data()
    country_name = data.get("country_name")
    description = data.get("description")

    # Формируем описание страны
    country_description = (
        f"Страна игрока: {country_name}\n"
        f"Описание страны: {description}"
    )

    # Добавляем начальную информацию в историю диалога
    initial_message = (
        "Игрок зарегистрировал свою страну в геополитической РПГ.\n"
        f"{country_description}"
    )

    await update_history(message.from_user.id, "Регистрация страны", initial_message, HISTORY_LIMIT)

    reply_text = (
        f"🎉 Поздравляем! Ваша страна {country_name} успешно создана! 🎉\n\n"
        "Теперь вы можете взаимодействовать с миром. Просто опишите свои действия, "
        "планы или задайте вопросы о текущей ситуации.\n\n"
        "Чтобы начать новую игру с другой страной, используйте команду /new."
    )

    await message.answer(reply_text)

    # Пересылаем администраторам полную информацию о стране
    if ADMIN_CHAT_ID:
        await forward_to_admins(
            f"Описание страны: {message.text}\n\n"
            f"СТРАНА ПОЛНОСТЬЮ ЗАРЕГИСТРИРОВАНА:\n{country_description}",
            reply_text,
            user_info
        )

    await state.clear()

@dp.message(Command("new"))
async def new_chat(message: types.Message, state: FSMContext):
    user_info = f"{message.from_user.full_name} (@{message.from_user.username}, ID: {message.from_user.id})"
    logger.info(f"Пользователь {user_info} начал новую игру")

    await clear_history(message.from_user.id)
    reply_text = "⚔️ Новая игра начата! Предыдущая история сброшена. ⚔️\nЧтобы зарегистрировать новую страну, используйте команду /start"

    await message.answer(reply_text)

    # Пересылаем администраторам
    if ADMIN_CHAT_ID:
        await forward_to_admins(
            "Пользователь сбросил историю и начал новую игру",
            reply_text,
            user_info
        )

@dp.message(F.text)
async def handle_message(message: types.Message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    user_text = message.text
    user_info = f"{message.from_user.full_name} (@{message.from_user.username}, ID: {user_id})"

    logger.info(f"Получено сообщение от пользователя {user_info}: {user_text[:50]}...")
    try:
        await bot.send_chat_action(chat_id=chat_id, action="typing")
        loop = asyncio.get_event_loop()
        typing_task = asyncio.create_task(keep_typing(chat_id))
        logger.info(f"Ожидание генерации ответа для пользователя {user_id}...")
        assistant_reply = await loop.run_in_executor(executor, sync_generate_response, user_id, user_text)
        logger.info(f"Ответ сгенерирован для пользователя {user_id}")
        typing_task.cancel()

        # Проверяем, что ответ не пустой
        if not assistant_reply or assistant_reply.strip() == "":
            logger.warning(f"Получен пустой ответ от модели для пользователя {user_id}")
            assistant_reply = "К сожалению, произошла ошибка при генерации ответа. Пожалуйста, попробуйте переформулировать ваш запрос или продолжить взаимодействие."

        await message.answer(assistant_reply)
        logger.info(f"Ответ отправлен пользователю {user_id}")

        # Пересылаем сообщение и ответ администраторам
        if ADMIN_CHAT_ID:
            await forward_to_admins(user_text, assistant_reply, user_info)

    except Exception as e:
        error_message = f"Ошибка: {str(e)}"
        logger.error(f"Ошибка при обработке сообщения: {str(e)}", exc_info=True)

        # Отправляем пользователю информацию об ошибке
        try:
            await message.answer("Произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте еще раз позже.")
        except Exception as reply_error:
            logger.error(f"Не удалось отправить сообщение об ошибке пользователю: {str(reply_error)}")

        # Уведомляем администраторов об ошибке
        if ADMIN_CHAT_ID:
            try:
                await bot.send_message(
                    chat_id=ADMIN_CHAT_ID,
                    text=f"❌ ОШИБКА при обработке сообщения от {user_info}:\n{str(e)}\n\nСообщение пользователя: {user_text}"
                )
            except Exception as admin_error:
                logger.error(f"Не удалось отправить уведомление об ошибке администраторам: {str(admin_error)}")

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

        try:
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

            # Проверяем, что ответ не пустой
            if not assistant_reply or assistant_reply.strip() == "":
                assistant_reply = "Как судья игры, я должен ответить на ваш запрос. Пожалуйста, опишите ваши следующие действия или задайте более конкретный вопрос о текущей ситуации в мире."

            # Обрабатываем многострочный ответ
            if '\n' in assistant_reply:
                clean_lines = []
                for line in assistant_reply.split('\n'):
                    if not line.strip().startswith('Игрок:') and not line.strip().startswith('User:'):
                        clean_lines.append(line)
                assistant_reply = '\n'.join(clean_lines)

            # Последняя проверка на пустой ответ
            if not assistant_reply or assistant_reply.strip() == "":
                assistant_reply = "Извините, произошла техническая ошибка. Продолжайте вашу игру, опишите следующие действия вашей страны."

        except Exception as gen_error:
            logger.error(f"Ошибка при генерации ответа: {str(gen_error)}", exc_info=True)
            assistant_reply = "Произошла техническая ошибка в работе модели. Пожалуйста, попробуйте еще раз."

        loop.run_until_complete(update_history(user_id, message_text, assistant_reply, HISTORY_LIMIT))
        loop.close()
        return assistant_reply
    except Exception as e:
        logger.error(f"Ошибка в generate_response: {str(e)}", exc_info=True)
        return "Извините, произошла внутренняя ошибка. Пожалуйста, попробуйте позже."

async def main():
    logger.info("Инициализация базы данных...")
    await init_db()

    # Отправляем уведомление о запуске бота
    if ADMIN_CHAT_ID:
        try:
            await bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=f"🤖 Бот запущен и готов к работе!\n\nВерсия: Геополитическая РПГ\nВремя запуска: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
        except Exception as e:
            logger.error(f"Не удалось отправить уведомление о запуске: {str(e)}")

    logger.info("Запуск бота...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        logger.info("Запуск приложения...")
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Приложение завершено")

        # Отправляем уведомление о завершении работы бота
        if ADMIN_CHAT_ID:
            try:
                asyncio.run(bot.send_message(
                    chat_id=ADMIN_CHAT_ID,
                    text=f"🔴 Бот остановлен!\nВремя остановки: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                ))
            except:
                pass
    except Exception as e:
        logger.critical(f"Критическая ошибка: {str(e)}", exc_info=True)

        # Отправляем уведомление о критической ошибке
        if ADMIN_CHAT_ID:
            try:
                asyncio.run(bot.send_message(
                    chat_id=ADMIN_CHAT_ID,
                    text=f"⛔ КРИТИЧЕСКАЯ ОШИБКА! Бот аварийно остановлен:\n{str(e)}\nВремя: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                ))
            except:
                pass
