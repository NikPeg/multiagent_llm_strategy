from aiogram import types, Router
from aiogram.filters import Command

from utils import answer_html
from database import (
    user_exists,
    get_user_country_desc,
    clear_history,
    clear_user_aspects,
    set_user_country,
    set_user_country_desc,
    set_aspect_index,
)

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


def register(dp):
    dp.include_router(router)
