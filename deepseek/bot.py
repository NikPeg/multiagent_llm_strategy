import asyncio
from dotenv import load_dotenv
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from transformers import AutoModelForCausalLM, AutoTokenizer
from database import init_db, get_history, update_history, clear_history
import torch

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

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

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
        history = await get_history(user_id)
        context = '\n'.join(history + [f"User: {message.text}"]) + "\nAssistant:"
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
        await update_history(user_id, message.text, assistant_reply, HISTORY_LIMIT)
        await message.answer(assistant_reply)
    except Exception as e:
        await message.answer(f"Ошибка: {str(e)}")

async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

