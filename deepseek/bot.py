import asyncio
from typing import Dict
from dotenv import load_dotenv
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from transformers import AutoModelForCausalLM, AutoTokenizer

# Загрузка токена из .env
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("Токен бота не найден в .env!")

# Инициализация модели и токенизатора
model_name = "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    device_map="auto",
    torch_dtype="auto"
)

# Хранилище диалогов (user_id: history)
user_chats: Dict[int, list] = {}

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

async def generate_response(user_id: int, text: str) -> str:
    """Генерирует ответ модели с учётом истории диалога."""
    if user_id not in user_chats:
        user_chats[user_id] = []
    
    history = user_chats[user_id]
    history.append(f"User: {text}")
    context = '\n'.join(history) + "\nAssistant:"
    
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
    
    history.append(f"Assistant: {assistant_reply}")
    return assistant_reply

# Команда /start
@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "Привет! Я бот с локальной моделью DeepSeek-R1-Distill-Qwen-32B.\n"
        "Просто напиши сообщение, и я отвечу.\n"
        "Чтобы сбросить диалог, используй /new."
    )

# Команда /new (сброс истории)
@dp.message(Command("new"))
async def new_chat(message: types.Message):
    user_id = message.from_user.id
    if user_id in user_chats:
        del user_chats[user_id]
    await message.answer("История диалога очищена. Начнём заново!")

# Обработка обычных сообщений
@dp.message(F.text)
async def handle_message(message: types.Message):
    user_id = message.from_user.id
    try:
        response = await generate_response(user_id, message.text)
        await message.answer(response)
    except Exception as e:
        await message.answer(f"Ошибка: {str(e)}")

# Запуск бота
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

