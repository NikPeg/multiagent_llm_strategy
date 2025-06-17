from aiogram import types, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from config import ADMIN_CHAT_ID
from database import (
    get_all_active_countries,
    get_user_id_by_country,
    get_user_aspect,
    set_user_aspect,
    get_user_country_desc,
    set_user_country_desc,
    clear_history,
    clear_user_aspects,
    set_user_country,
    set_user_country_desc,
    set_aspect_index,
    add_event_to_history,
    add_event_to_history_all,
)
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from utils import answer_html, send_html, stars_to_bold
from .fsm import EditAspect
from game import ASPECTS
from event_generator import generate_event_for_country
from .fsm import ConfirmEvent, AdminSendMessage

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
    # --- Добавляем "описание" как виртуальный аспект ---
    aspect_labels["описание"] = "Описание страны"
    aspect_codes.append("описание")

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

    # /info
    if not args:
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

    # /info <аспект>  или  /info <страна>
    if len(args) == 1:
        arg = args[0].lower()
        # Все описания стран
        if arg == "описание":
            for country_tuple in countries:
                country_name = country_tuple[1]
                user_id = country_tuple[0]
                desc = await get_user_country_desc(user_id)
                if desc and desc.strip():
                    await send_html(
                        message.bot, ADMIN_CHAT_ID,
                        f"<b>{country_name}</b> (ID: {user_id}):\n<b>Описание страны:</b>\n{desc}"
                    )
            return
        if arg in aspect_labels and arg != "описание":
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

    # /info <страна> <аспект>
    if len(args) == 2:
        country = args[0].lower()
        aspect = args[1].lower()
        if country not in countries_dict:
            await answer_html(message, "Страна не найдена.")
            return
        if aspect not in aspect_labels:
            await answer_html(message, "Аспект не найден.")
            return
        if aspect == "описание":
            desc = await get_user_country_desc(countries_dict[country]['user_id'])
            if desc and desc.strip():
                await send_html(
                    message.bot,
                    ADMIN_CHAT_ID,
                    f"<b>Описание страны</b> для <b>{countries_dict[country]['country_name']}</b>:\n{desc}"
                )
            else:
                await send_html(
                    message.bot,
                    ADMIN_CHAT_ID,
                    f"Описание страны для <b>{countries_dict[country]['country_name']}</b> не найдено."
                )
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

    # --- Изменение описания страны как "виртуального" аспекта ---
    if aspect_code == "описание":
        current_value = await get_user_country_desc(user_id)
        await answer_html(
            message,
            f"<b>Описание страны</b> для <b>{country_name}</b>:\n\n{current_value or '(нет данных)'}\n\n"
            "Введите новый текст для этого поля, или /cancel для отмены."
        )
        await state.set_state(EditAspect.waiting_new_value)
        await state.update_data(user_id=user_id, aspect_code=aspect_code, country_name=country_name)
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

    if aspect_code == "описание":
        await set_user_country_desc(user_id, new_value)
        await answer_html(
            message,
            f"<b>Описание страны</b> для <b>{country_name}</b> успешно обновлено!"
        )
        await state.clear()
        return

    await set_user_aspect(user_id, aspect_code, new_value)
    label = dict((a[0], a[1]) for a in ASPECTS).get(aspect_code, aspect_code)
    await answer_html(
        message,
        f"<b>{label}</b> для страны <b>{country_name}</b> успешно обновлён!"
    )
    await state.clear()

@router.message(Command("del_country"))
async def admin_delete_country(message: types.Message):
    if message.chat.id != ADMIN_CHAT_ID:
        await answer_html(message, "У вас нет прав на эту команду.")
        return

    args = message.text.split(maxsplit=1)[1:]
    if not args:
        await answer_html(message, "Формат: /del_country <название_страны>")
        return

    country_name = args[0].strip()
    user_id = await get_user_id_by_country(country_name)
    if not user_id:
        await answer_html(message, f'Страна "{country_name}" не найдена.')
        return

    await clear_history(user_id)
    await clear_user_aspects(user_id)
    await set_user_country(user_id, None)
    await set_user_country_desc(user_id, None)
    await set_aspect_index(user_id, None)

    await answer_html(message, f'Страна "{country_name}" и все связанные данные удалены.')

@router.message(Command("help"))
async def admin_help(message: types.Message):
    if message.chat.id != ADMIN_CHAT_ID:
        await answer_html(message, "У вас нет прав на эту команду.")
        return
    await answer_html(
        message,
        "<b>Админ-команды:</b>\n\n"
        "<b>/info</b> — информация по странам/аспектам\n"
        "  /info — список всех стран и аспектов\n"
        "  /info &lt;страна&gt; — все аспекты и описание страны\n"
        "  /info &lt;аспект&gt; — один аспект для всех стран\n"
        "  /info &lt;страна&gt; &lt;аспект&gt; — аспект определённой страны\n"
        "  /info (описание работает как отдельный \"аспект\")\n\n"
        "<b>/edit &lt;страна&gt; &lt;аспект/описание&gt;</b> — изменить значение любого аспекта или описание страны (через диалог)\n\n"
        "<b>/del_country &lt;страна&gt;</b> — полностью удалить страну (история, описание и аспекты)\n\n"
        "<b>/event &lt;страна&gt;</b> — сгенерировать ивент для страны\n\n"
        "<b>/event &lt;все&gt;</b> — сгенерировать ивент для всех стран\n\n"
        "<b>/help</b> — эта справка\n"
        "\n<b>Доступные аспекты:</b>\n"
        + "\n".join(f"<b>{a[0]}</b>: {a[1]}" for a in ASPECTS) +
        "\n<b>описание</b>: Описание страны"
    )

@router.message(Command("event"))
async def admin_generate_event(message: types.Message, state: FSMContext):
    if message.chat.id != ADMIN_CHAT_ID:
        await answer_html(message, "У вас нет прав на эту команду.")
        return

    args = message.text.split(maxsplit=1)[1:]
    if not args:
        await answer_html(message, "Формат: /event <название_страны> или /event все")
        return

    country_name = args[0].strip()
    await answer_html(message, f"⏳ Генерация ивента для {country_name}...")

    # Сгенерировать для одной страны или для всех
    if country_name.lower() == "все":
        event_text = await generate_event_for_country("все")
    else:
        event_text = await generate_event_for_country(country_name)

    # Сохраняем ивент и страну в FSM для подтверждения
    await state.set_state(ConfirmEvent.waiting_approve)
    await state.update_data(event_text=event_text, country_name=country_name)

    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Да")], [KeyboardButton(text="Нет")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await answer_html(
        message,
        f"<b>Событие для страны {country_name}:</b>\n\n{event_text}\n\nПодходит ли это событие? (Да/Нет)",
        reply_markup=kb
    )

@router.message(ConfirmEvent.waiting_approve)
async def confirm_event_send(message: types.Message, state: FSMContext):
    text = message.text.strip().lower()
    data = await state.get_data()
    event_text = data.get("event_text")
    country_name = data.get("country_name")
    await state.clear()

    if text not in ("да", "yes"):
        await answer_html(message, "Событие не отправлено.", reply_markup=None)
        return

    # Если "все" — отправить всем странам
    if country_name.lower() == "все":
        countries = await get_all_active_countries()
        for row in countries:
            user_id = row[0]
            try:
                await message.bot.send_message(user_id, f"⚡️ <b>В вашей стране случилось новое событие:</b>\n\n{event_text}", parse_mode="HTML")
                await add_event_to_history_all(event_text)
            except Exception as e:
                continue
        await answer_html(message, "Событие отправлено всем странам!", reply_markup=None)
        return

    # Для одной страны
    user_id = await get_user_id_by_country(country_name)
    if not user_id:
        await answer_html(message, f'Страна "{country_name}" не найдена.', reply_markup=None)
        return
    try:
        await message.bot.send_message(user_id, f"⚡️ <b>В вашей стране случилось новое событие:</b>\n\n{event_text}", parse_mode="HTML")
        await add_event_to_history(user_id, event_text)
        await answer_html(message, "Событие отправлено игроку.", reply_markup=None)
    except Exception as e:
        await answer_html(message, "Ошибка при отправке события игроку.", reply_markup=None)

@router.message(Command("send"))
async def admin_prepare_send_message(message: types.Message, state: FSMContext):
    if message.chat.id != ADMIN_CHAT_ID:
        await answer_html(message, "У вас нет прав на эту команду.")
        return

    args = message.text.split(maxsplit=1)[1:]
    if not args:
        await answer_html(message, "Формат: /send <название_страны> или /send все")
        return

    target = args[0].strip()
    await state.set_state(AdminSendMessage.waiting_message)
    await state.update_data(target=target)

    await answer_html(message, f"Введите текст сообщения, которое нужно отправить {'всем странам' if target.lower() == 'все' else f'стране {target}'}:")

@router.message(AdminSendMessage.waiting_message)
async def admin_do_send_message(message: types.Message, state: FSMContext):
    data = await state.get_data()
    target = data.get("target")
    text = message.text.strip()
    await state.clear()

    if target.lower() == "все":
        countries = await get_all_active_countries()
        success = 0
        for row in countries:
            user_id = row[0]
            try:
                await message.bot.send_message(user_id, text, parse_mode="HTML")
                success += 1
            except Exception:
                continue
        await answer_html(message, f"Сообщение отправлено всем {success} странам!")
        return

    user_id = await get_user_id_by_country(target)
    if not user_id:
        await answer_html(message, f'Страна "{target}" не найдена.')
        return
    try:
        await message.bot.send_message(user_id, text, parse_mode="HTML")
        await answer_html(message, "Сообщение отправлено стране.")
    except Exception:
        await answer_html(message, "Ошибка при отправке сообщения игроку.")

def register(dp):
    dp.include_router(router)
