import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from dotenv import load_dotenv
from random import sample, shuffle, randint
from concurrent.futures import ThreadPoolExecutor
from model_handler import ModelHandler
from utils import try_send_html

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID"))

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
executor = ThreadPoolExecutor(max_workers=1)
model_handler = ModelHandler(max_new_tokens=128)

NAMES = [
    "Иван", "Петр", "Алексей", "Дмитрий", "Сергей", "Михаил",
    "Андрей", "Владимир", "Артем", "Николай", "Егор", "Игорь",
    "Федор", "Глеб", "Максим", "Роман", "Григорий", "Лев"
]

PLAYER_PROMPTS = [
    "Ты обычный житель деревни, веди себя искренне и постарайся убедить других, что ты не мафия. Выскажи свою речь на голосовании.",
    "Ты мафия, старайся убедить всех, что ты обычный житель. Выскажи свою речь на голосовании, не выдавая себя."
]

def get_next_button():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Далее")]], resize_keyboard=True)

def get_vote_button():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Голосование")]], resize_keyboard=True)

def remove_keyboard():
    return ReplyKeyboardRemove()

game = {}

async def send_typing(chat_id):
    try:
        while True:
            await bot.send_chat_action(chat_id, "typing")
            await asyncio.sleep(2)
    except asyncio.CancelledError:
        pass

@dp.message(Command("start"))
async def start(message: types.Message):
    game.clear()
    await try_send_html(
        message,
        "Добро пожаловать в игру 'Мафия'. Введите количество игроков (от 4 до 12):",
        reply_markup=remove_keyboard()
    )
    game['state'] = 'wait_players'

@dp.message()
async def handler(message: types.Message):
    user_text = message.text.strip()
    if game.get('state') == 'wait_players':
        try:
            n_players = int(user_text)
            if 4 <= n_players <= 12:
                game['n_players'] = n_players
                await try_send_html(message, "Сколько должно быть мафий (1 или 2)?")
                game['state'] = 'wait_mafia'
            else:
                await try_send_html(message, "Введите число от 4 до 12")
        except:
            await try_send_html(message, "Пожалуйста, введите целое число.")
        return

    if game.get('state') == 'wait_mafia':
        try:
            n_mafia = int(user_text)
            if n_mafia not in (1, 2) or n_mafia >= game['n_players']:
                await try_send_html(message, "Мафий должно быть 1 или 2, и меньше чем всех игроков.")
                return
            await setup_game(message, game['n_players'], n_mafia)
        except:
            await try_send_html(message, "Пожалуйста, напишите 1 или 2.")
        return

    if user_text.lower() == "далее" and game.get('state') == 'game':
        await next_player_phase(message)
        return

    if user_text.lower() == "голосование" and game.get('state') == 'game':
        await voting_phase(message)
        return

async def setup_game(message, n_players, n_mafia):
    names = sample(NAMES, n_players)
    mafia_indices = sample(range(n_players), n_mafia)
    roles = ["мафия" if i in mafia_indices else "мирный" for i in range(n_players)]
    prompts = []
    for i in range(n_players):
        if i in mafia_indices:
            mafia_names = [names[j] for j in mafia_indices if j != i]
            if mafia_names:
                info = f"Ты мафия. Другие мафии: {', '.join(mafia_names)}."
            else:
                info = "Ты мафия. Ты один в команде мафии."
            prompts.append(info + " " + PLAYER_PROMPTS[1])
        else:
            prompts.append("Ты мирный житель. " + PLAYER_PROMPTS[0])

    game.update({
        'names': names,
        'roles': roles,
        'prompts': prompts,
        'step': 0,
        'state': 'game',
        'alive': [True] * n_players
    })

    awaiting = []
    for i, (name, role, prompt) in enumerate(zip(names, roles, prompts)):
        txt = f"Игрок {name}: {prompt}"
        awaiting.append(txt)
    await try_send_html(
        message,
        "Роли розданы. Нажмите 'Далее', чтобы начать игру. Далее каждый игрок будет произносить свою речь.",
        reply_markup=get_next_button()
    )
    await try_send_html(
        types.SimpleNamespace(answer=lambda text, **kwargs: bot.send_message(ADMIN_CHAT_ID, text, **kwargs)),
        "Запущена игра в мафию.\n" + "\n\n".join(awaiting)
    )

async def next_player_phase(message):
    names = game['names']
    prompts = game['prompts']
    roles = game['roles']
    step = game['step']
    alive = game['alive']
    total = len(names)

    while step < total and not alive[step]:
        game['step'] += 1
        step = game['step']

    if step >= total:
        await try_send_html(
            message,
            "Все игроки выступили, напишите 'Голосование' чтобы перейти к голосованию.",
            reply_markup=get_vote_button()
        )
        return

    name = names[step]
    prompt = prompts[step]
    role = roles[step]
    aspect_prompt = f"Ты игрок {name}, твоя роль: {role}. Вот твоя информация: {prompt}\nСкажи свою речь на голосовании."
    typing_task = asyncio.create_task(send_typing(message.chat.id))
    loop = asyncio.get_event_loop()
    speech = await loop.run_in_executor(
        executor,
        model_handler.generate_short_responce,
        aspect_prompt
    )
    typing_task.cancel()

    await try_send_html(
        message,
        f"🗣 <b>{name}:</b>\n{speech}",
        reply_markup=get_next_button()
    )
    admin_report = (
        f"Промпт, переданный в модель:\n"
        f"{aspect_prompt}\n\n"
        f"🗣 <b>{name}:</b>\n"
        f"{speech}"
    )
    await try_send_html(
        types.SimpleNamespace(answer=lambda text, **kwargs: bot.send_message(ADMIN_CHAT_ID, text, **kwargs)),
        admin_report
    )
    game['step'] += 1

async def voting_phase(message):
    names = game['names']
    alive = game['alive']
    surviving_indices = [i for i, a in enumerate(alive) if a]
    shuffle(surviving_indices)
    votes = {}
    n_alive = len(surviving_indices)
    for i in surviving_indices:
        candidates = [j for j in surviving_indices if j != i]
        target = candidates[randint(0, len(candidates) - 1)]
        votes.setdefault(target, []).append(i)
    results = []
    for voted, voters in votes.items():
        voter_names = ", ".join([names[i] for i in voters])
        results.append(f"За {names[voted]} проголосовали: {voter_names}")
    most_voted = max(votes.items(), key=lambda x: len(x[1]))[0]
    game['alive'][most_voted] = False
    game['step'] = 0
    await try_send_html(
        message,
        "<b>Голоса:</b>\n" + "\n".join(results),
        reply_markup=get_next_button()
    )
    await try_send_html(
        message,
        f"<b>{names[most_voted]} выбыл из игры!</b>",
        reply_markup=get_next_button()
    )
    await try_send_html(
        types.SimpleNamespace(answer=lambda text, **kwargs: bot.send_message(ADMIN_CHAT_ID, text, **kwargs)),
        "<b>Голоса:</b>\n" + "\n".join(results) + f"\n\n<b>{names[most_voted]} выбыл из игры!</b>"
    )
    mafia_alive = sum([game['roles'][i] == 'мафия' and game['alive'][i] for i in range(len(names))])
    city_alive = sum([game['roles'][i] == 'мирный' and game['alive'][i] for i in range(len(names))])
    if mafia_alive == 0:
        await try_send_html(
            message,
            "Мирные победили! Игра окончена.",
            reply_markup=remove_keyboard()
        )
        await try_send_html(
            types.SimpleNamespace(answer=lambda text, **kwargs: bot.send_message(ADMIN_CHAT_ID, text, **kwargs)),
            "Мирные победили! Игра окончена."
        )
        game['state'] = 'over'
        return
    elif city_alive <= mafia_alive:
        await try_send_html(
            message,
            "Мафия победила! Игра окончена.",
            reply_markup=remove_keyboard()
        )
        await try_send_html(
            types.SimpleNamespace(answer=lambda text, **kwargs: bot.send_message(ADMIN_CHAT_ID, text, **kwargs)),
            "Мафия победила! Игра окончена."
        )
        game['state'] = 'over'
        return
    else:
        await try_send_html(
            message,
            "Продолжается следующий круг. Введите 'Далее'.",
            reply_markup=get_next_button()
        )
        await try_send_html(
            types.SimpleNamespace(answer=lambda text, **kwargs: bot.send_message(ADMIN_CHAT_ID, text, **kwargs)),
            "Продолжается следующий круг. Введите 'Далее'."
        )

if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot))
