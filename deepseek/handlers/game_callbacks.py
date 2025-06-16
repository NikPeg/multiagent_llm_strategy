from aiogram import Router, types
from config import ADMIN_CHAT_ID
from database import (
    get_user_country,
    get_user_aspect,
    get_user_country_desc,
)
from utils import answer_html, stars_to_bold
from game import ASPECTS

router = Router()

@router.callback_query(lambda c: c.data.startswith("aspect:"))
async def aspect_callback(call: types.CallbackQuery):
    if call.from_user.id == ADMIN_CHAT_ID:
        await call.answer("Для админа эта функция недоступна.", show_alert=True)
        return

    user_id = call.from_user.id
    aspect_code = call.data.split(":")[1]

    if aspect_code == "описание":
        desc = await get_user_country_desc(user_id)
        if desc and desc.strip():
            await call.message.answer(
                f"<b>Описание вашей страны:</b>\n{desc}",
                parse_mode="HTML"
            )
        else:
            await call.message.answer(
                "Описание вашей страны не найдено.",
                parse_mode="HTML"
            )
        await call.answer()
        return

    # Для аспектов
    country = await get_user_country(user_id)
    label = None
    for code, asp_label, _ in ASPECTS:
        if code == aspect_code:
            label = asp_label
            break

    if label is None:
        await call.answer("Неизвестный аспект.", show_alert=True)
        return

    value = await get_user_aspect(user_id, aspect_code)
    if value and value.strip():
        await call.message.answer(
            f"<b>{label}:</b>\n{stars_to_bold(value)}",
            parse_mode="HTML"
        )
    else:
        await call.message.answer(
            f"Аспект <b>{label}</b> ещё не заполнен для вашей страны.",
            parse_mode="HTML"
        )
    await call.answer()


def register(dp):
    dp.include_router(router)
