from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from database import (
    clear_history,
    clear_user_aspects,
    set_aspect_index,
    set_user_country,
    set_user_country_desc,
)
from utils import answer_html

from .fsm import RegisterCountry, ResetCountry

router = Router()


@router.message(Command("reset_country"))
async def reset_country(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    await state.set_state(ResetCountry.confirming)
    await answer_html(
        message,
        "⚠️ <b>Внимание!</b> После сброса вы потеряете ВСЮ информацию о вашей текущей стране, её аспектах и истории.\n\n"
        "Если вы уверены, напишите <b>ДА</b>.\n"
        "Для отмены введите /cancel.",
    )


@router.message(ResetCountry.confirming)
async def confirm_reset_country(message: types.Message, state: FSMContext):
    text = message.text.strip().lower()
    user_id = message.from_user.id
    if text in ("да", "yes", "подтвердить"):
        await clear_history(user_id)
        await clear_user_aspects(user_id)
        await set_user_country(user_id, None)
        await set_user_country_desc(user_id, None)
        await set_aspect_index(user_id, None)
        await state.set_state(RegisterCountry.waiting_for_name)
        await answer_html(
            message,
            "⏳ Регистрация страны сброшена!\n\n"
            "Введи <b>новое название твоей страны</b>, чтобы начать историю заново:",
        )
    else:
        await answer_html(message, "Введите <b>ДА</b>, чтобы подтвердить сброс, или /cancel для отмены.")


def register(dp):
    dp.include_router(router)
