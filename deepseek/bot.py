import asyncio
from typing import Dict
from dotenv import load_dotenv
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from transformers import AutoModelForCausalLM, AutoTokenizer
import aiosqlite

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
HISTORY_LIMIT = int(os.getenv("HISTORY_LIMIT", 10))
DB_PATH = "chats.db"

if not BOT_TOKEN:
    raise ValueError("Токен бота не найден в .env!")

model_name = "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    device_map="auto",
    torch_dtype="auto"
)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """CREATE TABLE IF NOT EXISTS chats (
                user_id INTEGER PRIMARY KEY,
                history TEXT
            )"""
        )
        await db.commit()

async def get_history(user_id: int) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT history FROM chats WHERE user_id = ?", 
            (user_id,)
        ) as cursor:
            result = await cursor.fetchone()
            return eval(result[0]) if result else []

async def update_history(user_id: int, message: str, response: str):
    history = await get_history(user_id)
    history.extend([f"User: {message}", f"Assistant: {response}"])
    history = history[-HISTORY_LIMIT:]
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO chats (user_id, history) VALUES (?, ?)",
            (user_id, str(history))
        )
        await db.commit()

async def clear_history(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM chats WHERE user_id = ?", (user_id,))
        await db.commit()

async def generate_response(user_id: int, text: str) -> str:
    history = await get_history(user_id)
    context = '\n'.join(history + [f"User: {text}"]) + "\nAssistant:"
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
    await update_history(user_id, text, assistant_reply)
    return assistant_reply

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "Привет! Я бот с локальной моделью DeepSeek-R1-Distill-Qwen-32B.\n"
        f"Храню последние {HISTORY_LIMIT} сообщений. Чтобы сбросить диалог - /new.")

@dp.message(Command("new"))
async def new_chat(message: types.Message):
    await clear_history(message.from_user.id)
    await message.answer("История диалога очищена!")

@dp.message(F.text)
async def handle_message(message: types.Message):
    user_id = message.from_user.id
    try:
        response = await generate_response(user_id, message.text)
        await message.answer(response)
    except Exception as e:
        await message.answer(f"Ошибка: {str(e)}")

async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

