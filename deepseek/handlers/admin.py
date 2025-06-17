from aiogram import types, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from config import ADMIN_CHAT_ID
from database import *
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from utils import answer_html, send_html, stars_to_bold
from .fsm import EditAspect
from game import ASPECTS
from event_generator import generate_event_for_country
from .fsm import ConfirmEvent, AdminSendMessage

router = Router()

from database import get_country_by_synonym_or_name  # Не забудьте импортировать!

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
                "/info <аспект> — этот аспект/описание по всем странам\n"
                "/info <аспект> <название страны> — выбранный аспект данной страны\n\n"
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

    # /info <аспект>
    if len(args) == 1:
        aspect = args[0].lower()
        if aspect not in aspect_labels:
            await answer_html(message, "Аспект не найден.")
            return
        if aspect == "описание":
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
        idx = aspect_codes.index(aspect)
        for country_tuple in countries:
            country_name = country_tuple[1]
            user_id = country_tuple[0]
            aspect_value = country_tuple[3 + idx]
            if aspect_value and aspect_value.strip():
                await send_html(
                    message.bot, ADMIN_CHAT_ID,
                    f"<b>{country_name}</b> (ID: {user_id}):\n<b>{aspect_labels[aspect]}</b>:\n{stars_to_bold(aspect_value)}"
                )
        return

    # /info <аспект> <название_страны>
    if len(args) >= 2:
        aspect = args[0].lower()
        country_input = " ".join(args[1:]).strip()
        main_country_name = await get_country_by_synonym_or_name(country_input)

        if not main_country_name or main_country_name.strip().lower() not in countries_dict:
            await answer_html(message, "Страна не найдена.")
            return
        country_info = countries_dict[main_country_name.strip().lower()]

        if aspect not in aspect_labels:
            await answer_html(message, "Аспект не найден.")
            return
        if aspect == "описание":
            desc = await get_user_country_desc(country_info['user_id'])
            if desc and desc.strip():
                await send_html(
                    message.bot,
                    ADMIN_CHAT_ID,
                    f"<b>Описание страны</b> для <b>{country_info['country_name']}</b>:\n{desc}"
                )
            else:
                await send_html(
                    message.bot,
                    ADMIN_CHAT_ID,
                    f"Описание страны для <b>{country_info['country_name']}</b> не найдено."
                )
            return
        idx = aspect_codes.index(aspect)
        value = country_info["aspects"][idx]
        label = aspect_labels[aspect]
        if value and value.strip():
            await send_html(
                message.bot,
                ADMIN_CHAT_ID,
                f"<b>{label}</b> для страны <b>{country_info['country_name']}</b>:\n{stars_to_bold(value)}"
            )
        else:
            await send_html(
                message.bot,
                ADMIN_CHAT_ID,
                f"Аспект <b>{label}</b> для страны <b>{country_info['country_name']}</b> не найден."
            )
        return

    await answer_html(
        message,
        "Некорректные параметры. Форматы:\n"
        "/info [аспект]\n"
        "/info [аспект] [название страны]\n"
        "/info\n\n"
        "Для помощи введите /info help"
    )

@router.message(Command("edit"))
async def admin_edit(message: types.Message, state: FSMContext):
    if message.chat.id != ADMIN_CHAT_ID:
        await answer_html(message, "У вас нет прав на эту команду.")
        return

    args = message.text.split(maxsplit=1)[1:]
    if not args:
        await answer_html(message, "Формат: /edit <аспект> <название страны>")
        return
    parts = args[0].split()
    if len(parts) < 2:
        await answer_html(message, "Формат: /edit <аспект> <название страны>")
        return

    aspect_code = parts[0].strip()
    country_name = " ".join(parts[1:]).strip()
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
    # Если страна состоит из нескольких слов — ждём их слитно:
    if len(args) > 1:
        country_name = " ".join(args).strip()

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
        "<b>/info [аспект] [страна]</b> — посмотреть аспекты (или описание) стран\n"
        "<b>/edit [аспект] [страна]</b> — изменить аспект или описание страны\n"
        "<b>/del_country [страна]</b> — удалить страну\n"
        "<b>/event [страна|все]</b> — сгенерировать ивент для страны или всех\n"
        "<b>/send [страна|все]</b> — отправить сообщение в страну или всем\n"
        "<b>/help</b> — показать эту справку\n\n"
        "<b>Доступные аспекты:</b>\n"
        + ", ".join(f"<b>{a[0]}</b>" for a in ASPECTS) +
        ", <b>описание</b>"
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
    # Если страна состоит из нескольких слов — ждём их слитно:
    if len(args) > 1:
        country_name = " ".join(args).strip()

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
    # Если страна состоит из нескольких слов — ждём их слитно:
    if len(args) > 1:
        target = " ".join(args).strip()
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

@router.message(Command("countries"))
async def admin_list_country_synonyms(message: types.Message):
    if message.chat.id != ADMIN_CHAT_ID:
        await answer_html(message, "У вас нет прав на эту команду.")
        return

    country_synonyms = await get_all_countries_and_synonyms()
    if not country_synonyms:
        await answer_html(message, "Страны не обнаружены.")
        return

    lines = []
    for country, synonyms in country_synonyms.items():
        if synonyms:
            lines.append(f"<b>{country}</b>: {', '.join(synonyms)}")
        else:
            lines.append(f"<b>{country}</b>: -")

    text = "<b>Страны и их синонимы:</b>\n" + "\n".join(lines)
    await answer_html(message, text)

def register(dp):
    dp.include_router(router)
