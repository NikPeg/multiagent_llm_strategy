from aiogram import types, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from config import ADMIN_CHAT_ID
from database import (
    get_all_active_countries,
    get_user_id_by_country,
    get_user_aspect,
    set_user_aspect,
)
from utils import answer_html, send_html, stars_to_bold
from .fsm import EditAspect
from game import ASPECTS

router = Router()

@router.message(Command("info"))
async def info(message: types.Message):
    if message.chat.id != ADMIN_CHAT_ID:
        await answer_html(message, "У вас нет прав на эту команду.")
        return

    params = message.text.split(maxsplit=1)[1:]
    args = params[0].split() if params else []

    countries = await get_all_active_countries()
    if not countries:
        await answer_html(message, "Активных стран не обнаружено.")
        return

    countries_dict = {}
    for country_tuple in countries:
        user_id, country_name, country_desc, *aspect_values = country_tuple
        countries_dict[country_name.strip().lower()] = {
            "user_id": user_id,
            "country_name": country_name,
            "country_desc": country_desc,
            "aspects": aspect_values
        }

    aspect_labels = {a[0]: a[1] for a in ASPECTS}
    aspect_codes = list(aspect_labels.keys())

    # HELP
    if args and args[0].lower() in ("help", "справка", "?"):
        help_text = (
                "<b>/info</b> — просмотр стран и аспектов\n"
                "<b>Использование:</b>\n"
                "/info — все страны и все аспекты\n"
                "/info <i>страна</i> — все аспекты по стране\n"
                "/info <i>аспект</i> — этот аспект по всем странам\n"
                "/info <i>страна</i> <i>аспект</i> — выбранный аспект страны\n\n"
                "<b>Доступные коды аспектов:</b>\n" +
                "\n".join(f"<b>{code}</b>: {aspect_labels[code]}" for code in aspect_codes)
        )
        await send_html(message.bot, ADMIN_CHAT_ID, help_text)
        return

    if not args:
        # Все страны и их аспекты
        for country_tuple in countries:
            user_id, country_name, country_desc, *aspect_values = country_tuple
            await send_html(
                message.bot,
                ADMIN_CHAT_ID,
                f"🗺 <b>Страна:</b> {country_name} (ID: {user_id})"
            )
            await send_html(
                message.bot,
                ADMIN_CHAT_ID,
                f"<b>Описание:</b>\n{country_desc or '(Нет)'}"
            )
            for (code, label, _), value in zip(ASPECTS, aspect_values):
                if value and value.strip():
                    await send_html(
                        message.bot,
                        ADMIN_CHAT_ID,
                        f"<b>{label}</b>:\n{stars_to_bold(value)}"
                    )
        return

    if len(args) == 1:
        arg = args[0].lower()
        if arg in aspect_labels:
            idx = aspect_codes.index(arg)
            for country_tuple in countries:
                country_name = country_tuple[1]
                user_id = country_tuple[0]
                aspect_value = country_tuple[3 + idx]
                if aspect_value and aspect_value.strip():
                    await send_html(
                        message.bot, ADMIN_CHAT_ID,
                        f"<b>{country_name}</b> (ID: {user_id}):\n<b>{aspect_labels[arg]}</b>:\n{stars_to_bold(aspect_value)}"
                    )
            return
        if arg in countries_dict:
            c = countries_dict[arg]
            await send_html(
                message.bot,
                ADMIN_CHAT_ID,
                f"🗺 <b>Страна:</b> {c['country_name']} (ID: {c['user_id']})"
            )
            await send_html(
                message.bot,
                ADMIN_CHAT_ID,
                f"<b>Описание:</b>\n{c['country_desc'] or '(Нет)'}"
            )
            for (code, label, _), value in zip(ASPECTS, c["aspects"]):
                if value and value.strip():
                    await send_html(
                        message.bot, ADMIN_CHAT_ID, f"<b>{label}:</b>\n{stars_to_bold(value)}"
                    )
            return
        await answer_html(message, "Не найдено ни страны, ни аспекта с таким названием.")
        return

    if len(args) == 2:
        country = args[0].lower()
        aspect = args[1].lower()
        if country not in countries_dict:
            await answer_html(message, "Страна не найдена.")
            return
        if aspect not in aspect_labels:
            await answer_html(message, "Аспект не найден.")
            return
        idx = aspect_codes.index(aspect)
        value = countries_dict[country]["aspects"][idx]
        label = aspect_labels[aspect]
        if value and value.strip():
            await send_html(
                message.bot,
                ADMIN_CHAT_ID,
                f"<b>{label}</b> для страны <b>{countries_dict[country]['country_name']}</b>:\n{stars_to_bold(value)}"
            )
        else:
            await send_html(
                message.bot,
                ADMIN_CHAT_ID,
                f"Аспект <b>{label}</b> для страны <b>{countries_dict[country]['country_name']}</b> не найден."
            )
        return

    await answer_html(
        message,
        "Некорректные параметры. Форматы:\n/info [страна]\n/info [аспект]\n/info [страна] [аспект]\n\n"
        "Для помощи введите /info help"
    )

@router.message(Command("edit"))
async def admin_edit(message: types.Message, state: FSMContext):
    if message.chat.id != ADMIN_CHAT_ID:
        await answer_html(message, "У вас нет прав на эту команду.")
        return

    args = message.text.split(maxsplit=1)[1:]
    if not args:
        await answer_html(message, "Формат: /edit <страна> <аспект>")
        return
    parts = args[0].split()
    if len(parts) != 2:
        await answer_html(message, "Формат: /edit <страна> <аспект>")
        return

    country_name = parts[0].strip()
    aspect_code = parts[1].strip()
    user_id = await get_user_id_by_country(country_name)
    if not user_id:
        await answer_html(message, f'Страна "{country_name}" не найдена.')
        return

    if aspect_code not in [a[0] for a in ASPECTS]:
        await answer_html(message, f'Аспект "{aspect_code}" не найден.')
        return

    current_value = await get_user_aspect(user_id, aspect_code)
    label = dict((a[0], a[1]) for a in ASPECTS)[aspect_code]
    await answer_html(
        message,
        f"<b>{label}</b> для страны <b>{country_name}</b>:\n\n{stars_to_bold(current_value or '(нет данных)')}\n\n"
        "Введите новый текст для этого поля, или /cancel для отмены."
    )
    await state.set_state(EditAspect.waiting_new_value)
    await state.update_data(user_id=user_id, aspect_code=aspect_code, country_name=country_name)

@router.message(EditAspect.waiting_new_value)
async def process_new_value(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if not data:
        await answer_html(message, "Внутренняя ошибка: не указаны страна и аспект.")
        await state.clear()
        return

    user_id = data["user_id"]
    aspect_code = data["aspect_code"]
    country_name = data["country_name"]
    new_value = message.text.strip()

    await set_user_aspect(user_id, aspect_code, new_value)
    label = dict((a[0], a[1]) for a in ASPECTS)[aspect_code]

    await answer_html(
        message,
        f"<b>{label}</b> для страны <b>{country_name}</b> успешно обновлён!"
    )
    await state.clear()

def register(dp):
    dp.include_router(router)
