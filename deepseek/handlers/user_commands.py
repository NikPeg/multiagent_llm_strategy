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
            "👑 <b>Добро пожаловать снова!</b>\n\n"
            "Это ролевая игра в жанре геополитической стратегии древнего мира.\n"
            "Вы управляете собственной страной: развиваете экономику, армию, дипломатию.\n\n"
            f"<b>Описание вашей страны:</b>\n{country_desc or '(ещё не заполнено)'}\n\n"
            "📜 <b>Доступные команды:</b>\n"
            "/new — начать новый игровой диалог, сбросить текущий контекст\n"
            "/reset_country — сбросить страну и зарегистрировать новую\n"
            "\nДля игры просто отправляйте сообщения с приказами, вопросами или решениями, как правитель своей страны!\n"
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
