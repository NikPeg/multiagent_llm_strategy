import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from dotenv import load_dotenv
from random import sample, shuffle, randint

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID"))

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

NAMES = [
    "Иван", "Петр", "Алексей", "Дмитрий", "Сергей", "Михаил",
    "Андрей", "Владимир", "Артем", "Николай", "Егор", "Игорь",
    "Федор", "Глеб", "Максим", "Роман", "Григорий", "Лев"
]

PLAYER_PROMPTS = [
    "Ты обычный житель деревни, веди себя искренне и постарайся убедить других, что ты не мафия.",
    "Ты мафия, старайся убедить всех, что ты обычный житель, не выдавая себя.",
]

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
    await message.answer("Добро пожаловать в игру 'Мафия'. Введите количество игроков (от 4 до 12):")
    game['state'] = 'wait_players'

@dp.message()
async def handler(message: types.Message):
    user_text = message.text.strip()
    if game.get('state') == 'wait_players':
        try:
            n_players = int(user_text)
            if 4 <= n_players <= 12:
                game['n_players'] = n_players
                await message.answer("Сколько должно быть мафий (1 или 2)?")
                game['state'] = 'wait_mafia'
            else:
                await message.answer("Введите число от 4 до 12")
        except:
            await message.answer("Пожалуйста, введите целое число.")
        return

    if game.get('state') == 'wait_mafia':
        try:
            n_mafia = int(user_text)
            if n_mafia not in (1, 2) or n_mafia >= game['n_players']:
                await message.answer("Мафий должно быть 1 или 2, и меньше чем всех игроков.")
                return
            await setup_game(message, game['n_players'], n_mafia)
        except:
            await message.answer("Пожалуйста, напишите 1 или 2.")
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
                info = "Ты мафия. Другие мафии: " + ", ".join(mafia_names) + "."
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
    await message.answer("Роли розданы. Нажмите 'далее', чтобы начать игру. Далее каждый игрок будет произносить свою речь.")
    await bot.send_message(ADMIN_CHAT_ID, "Запущена игра в мафию.\n" + "\n\n".join(awaiting))

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
        await message.answer("Все игроки выступили, напишите 'голосование' чтобы перейти к голосованию.")
        return

    name = names[step]
    speech = await generate_fake_speech(name, prompts[step], roles[step])
    await send_to_admin_and_user(message, f"🗣 <b>{name}:</b>\n{speech}")
    game['step'] += 1

async def generate_fake_speech(name, prompt, role):
    dummy = [
        f"Меня зовут {name}. Я считаю, что город должен сплотиться и разобраться, кто мафия.",
        f"{name}: Я невиновен, но кто-то из нас играет не очень честно.",
        f"{name}: Мирные должны держаться вместе, у меня подозрения на тех, кто слишком молчит.",
        f"{name}: Я уверен, что мафия скрывается среди нас и будет пытаться запутать разговор.",
        f"{name}: В первую очередь надо слушать поведение других в этой дискуссии.",
    ]
    if role == "мафия":
        idx = randint(0, len(dummy) - 1)
        return dummy[idx] + " " + "Я бы предложил присмотреться к самому активному голосующему."
    else:
        idx = randint(0, len(dummy) - 1)
        return dummy[idx]

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
    await send_to_admin_and_user(message, "<b>Голоса:</b>\n" + "\n".join(results))
    await send_to_admin_and_user(message, f"<b>{names[most_voted]} выбыл из игры!</b>")
    survivors = [names[i] for i, a in enumerate(game['alive']) if a]
    if sum([game['roles'][i] == 'мафия' and game['alive'][i] for i in range(len(names))]) == 0:
        await send_to_admin_and_user(message, "Мирные победили! Игра окончена.")
        game['state'] = 'over'
        return
    elif sum([game['roles'][i] == 'мирный' and game['alive'][i] for i in range(len(names))]) <= sum([game['roles'][i] == 'мафия' and game['alive'][i] for i in range(len(names))]):
        await send_to_admin_and_user(message, "Мафия победила! Игра окончена.")
        game['state'] = 'over'
        return
    else:
        await send_to_admin_and_user(message, "Продолжается следующий круг. Введите 'далее'.")

async def send_to_admin_and_user(message, text):
    await message.answer(text, parse_mode="HTML")
    await bot.send_message(ADMIN_CHAT_ID, text, parse_mode="HTML")

if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot))
