from aiogram import types, Router
from aiogram.filters import Command

from utils import answer_html
from database import *
from aiogram.fsm.context import FSMContext

router = Router()

@router.message(Command("start"))
async def start(message: types.Message):
    user_id = message.from_user.id

    if await user_exists(user_id):
        country_desc = await get_user_country_desc(user_id)
        help_text = (
            "👑 <b>Снова приветствуем тебя, властитель!</b>\n\n"
            "Ты продолжаешь летопись своей державы в мире, где переплетаются войны, наука, магия и судьбы народов.\n"
            "Власть твоя — закон для страны, армии, ремёсел и духовных традиций.\n"
            "Ты волен возвысить свой народ, подчинить соперников или принести счастье своим подданным.\n\n"
            f"<b>Твоё государство сейчас:</b>\n{country_desc or '(ещё не заполнено)'}\n\n"
            "📜 <b>Полезные свитки:</b>\n"
            "/new — начать новую главу своей истории\n"
            "/reset_country — забыть прежнее и создать новое царство\n"
            "\nОбъявляй приказы, вопрошай о судьбе или соверши деяние — ты сам творишь свою легенду!"
        )
        await answer_html(message, help_text)
        return

    await clear_history(user_id)
    await clear_user_aspects(user_id)
    await set_user_country(user_id, None)
    await set_user_country_desc(user_id, None)
    await set_aspect_index(user_id, None)
    await answer_html(
        message,
        "Добро пожаловать в ролевую геополитическую игру эпохи древнего мира!\n\n"
        "Для начала укажи <b>название своей страны</b>:"
    )


@router.message(Command("new"))
async def new_chat(message: types.Message):
    user_id = message.from_user.id
    await clear_history(user_id)
    await answer_html(message, "Контекст диалога сброшен!⚔️")

@router.message(Command("send"))
async def player_send_message(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    # Получаем название страны игрока-отправителя
    sender_country = await get_country_name_by_user_id(user_id)

    args = message.text.split(maxsplit=1)[1:]
    if not args or len(args[0].strip().split()) == 0:
        await message.reply("Формат: /send <название_страны> <текст послания>")
        return

    # Получаем предполагаемое название страны и текст послания
    remaining = args[0].strip()
    if ' ' in remaining:
        country_name, msg = remaining.split(' ', 1)
    else:
        await message.reply("Введите название страны и текст послания, например: /send Германия Привет!")
        return

    country_name = country_name.strip()
    msg = msg.strip()
    if not country_name or not msg:
        await message.reply("Введите название страны и текст послания, например: /send Германия Привет!")
        return

    # Получаем user_id получателя
    recipient_user_id = await get_user_id_by_country(country_name)
    if not recipient_user_id:
        await message.reply(f"Страна '{country_name}' не найдена.")
        return

    if recipient_user_id == user_id:
        await message.reply("Нельзя отправлять послание самому себе.")
        return

    # Формируем и отправляем сообщение получателю
    text = f"Вам послание из страны {sender_country}: {msg}"
    try:
        await message.bot.send_message(recipient_user_id, text)
        await message.reply("Послание отправлено!")
    except Exception as e:
        await message.reply("Ошибка при отправке послания. Возможно, пользователь заблокировал бота или никогда ему не писал.")


def register(dp):
    dp.include_router(router)
