from aiogram import types, Router
from aiogram.filters import Command

from utils import answer_html
from database import *
from aiogram.fsm.context import FSMContext
from .fsm import SendMessageFSM

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
            "/send <страна> — отправить послание иному государству\n"
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

def format_ancient_letter(sender_country: str, text: str) -> str:
    return (
        f"📜 К воротам вашего дворца явился глашатай из державы {sender_country}!\n\n"
        f"Передает вам свиток с посланием:\n\n"
        f"{text}"
    )

@router.message(Command("send"))
async def cmd_send(message: types.Message, state: FSMContext):
    args = message.text.split(maxsplit=1)[1:]
    if args:
        country = args[0].strip()
        recipient_user_id = await get_user_id_by_country(country)
        if not recipient_user_id:
            await message.answer(f"Страна '{country}' не найдена. Введите корректное название страны.")
            await state.set_state(SendMessageFSM.waiting_for_country)
            return
        # Сохраняем страну и ждем текст
        await state.update_data(country=country)
        await state.set_state(SendMessageFSM.waiting_for_text)
        await message.answer(f"Введите текст послания для державы '{country}':")
    else:
        example_country = await get_random_country_name()
        if example_country:
            await message.answer(f"Укажите название страны, например: /send {example_country}")
        else:
            await message.answer("Укажите название страны. В системе пока нет зарегистрированных стран.")
        await state.set_state(SendMessageFSM.waiting_for_country)

@router.message(SendMessageFSM.waiting_for_country)
async def ask_country(message: types.Message, state: FSMContext):
    country = message.text.strip()
    recipient_user_id = await get_user_id_by_country(country)
    if not recipient_user_id:
        await message.answer(f"Страна '{country}' не найдена! Попробуйте ещё раз.")
        return
    await state.update_data(country=country)
    await state.set_state(SendMessageFSM.waiting_for_text)
    await message.answer(f"Введите текст послания для державы '{country}':")

@router.message(SendMessageFSM.waiting_for_text)
async def send_letter(message: types.Message, state: FSMContext):
    data = await state.get_data()
    country = data.get("country")
    recipient_user_id = await get_user_id_by_country(country)
    if not recipient_user_id:
        await message.answer(f"Страна '{country}' не найдена, отмена отправки.")
        await state.clear()
        return
    # Получаем страну отправителя
    sender_country = await get_country_name_by_user_id(message.from_user.id)
    if recipient_user_id == message.from_user.id:
        await message.answer("Нельзя отправить послание самому себе.")
        await state.clear()
        return

    text = message.text.strip()
    send_text = format_ancient_letter(sender_country, text)
    try:
        await message.bot.send_message(recipient_user_id, send_text)
        await message.answer("Послание отправлено!")
    except Exception:
        await message.answer("Ошибка: не удалось отправить сообщение получателю (он мог заблокировать бота).")
    await state.clear()

def register(dp):
    dp.include_router(router)
