from aiogram import Router, types, F
from database import get_user_aspect, get_user_country_desc, get_user_country
from game import ASPECTS
from utils import answer_html, stars_to_bold

router = Router()

# Множество всех названий аспектов (лейблы)
ASPECT_LABELS = {label for _, label, _ in ASPECTS}
ASPECT_LABEL_TO_CODE = {label: code for code, label, _ in ASPECTS}

@router.message(F.text.in_(ASPECT_LABELS | {"Описание страны"}))
async def handle_aspect_button(message: types.Message):
    user_id = message.from_user.id
    user_text = message.text.strip()
    if user_text == "Описание страны":
        desc = await get_user_country_desc(user_id)
        if desc and desc.strip():
            await answer_html(message, f"<b>Описание вашей страны:</b>\n{desc}")
        else:
            await answer_html(message, "Описание вашей страны не найдено.")
        return

    # Для аспектов
    aspect_code = ASPECT_LABEL_TO_CODE.get(user_text)
    if not aspect_code:
        await answer_html(message, "Неизвестный аспект.")
        return

    value = await get_user_aspect(user_id, aspect_code)
    if value and value.strip():
        await answer_html(message, f"<b>{user_text}:</b>\n{stars_to_bold(value)}")
    else:
        await answer_html(message, f"Аспект <b>{user_text}</b> ещё не заполнен для вашей страны.")

def register(dp):
    dp.include_router(router)
