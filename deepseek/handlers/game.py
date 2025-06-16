from aiogram import types, Router, F
from database import get_user_country, get_user_country_desc
from .game_logic import handle_country_name, handle_country_desc, handle_game_dialog

router = Router()

@router.message(F.text & ~F.text.startswith('/'))
async def handle_message(message: types.Message):
    user_id = message.from_user.id
    user_text = message.text.strip()

    country = await get_user_country(user_id)
    country_desc = await get_user_country_desc(user_id)

    if not country:
        await handle_country_name(message, user_id, user_text)
    elif not country_desc:
        await handle_country_desc(message, user_id, user_text)
    else:
        await handle_game_dialog(message, user_id, user_text)

def register(dp):
    dp.include_router(router)
