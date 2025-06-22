from aiogram import types, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from utils import answer_html

from .fsm import (
    EditAspect, ConfirmEvent, AdminSendMessage, AddCountrySynonym,
    SendMessageFSM, RegisterCountry, ResetCountry
)
from aiogram import types

router = Router()

@router.message(Command("cancel"))
async def global_cancel(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        await answer_html(message, "Нет активных действий для отмены.")
        return

    # Реакция на разные FSM-состояния:
    if current_state.startswith(SendMessageFSM.__name__):
        await state.clear()
        await answer_html(message, "Отправка сообщения отменена.")
        return

    if current_state.startswith(RegisterCountry.__name__):
        await state.clear()
        await answer_html(
            message,
            "Регистрация страны отменена. Введите новое название своей страны:"
        )
        await state.set_state(RegisterCountry.waiting_for_name)
        return

    if current_state.startswith(EditAspect.__name__):
        await state.clear()
        await answer_html(message, "Изменение аспекта отменено.")
        return

    if current_state.startswith(ConfirmEvent.__name__):
        await state.clear()
        await answer_html(message, "Отправка события отменена.")
        return

    if current_state.startswith(AdminSendMessage.__name__):
        await state.clear()
        await answer_html(message, "Отправка административного сообщения отменена.")
        return

    if current_state.startswith(AddCountrySynonym.__name__):
        await state.clear()
        await answer_html(message, "Добавление синонима отменено.")
        return

    if current_state.startswith(ResetCountry.__name__):
        await state.clear()
        await answer_html(message, "Сброс страны отменён.")
        return

    # Если вдруг неизвестное состояние
    await state.clear()
    await answer_html(message, "Действие отменено.")

def register(dp):
    dp.include_router(router)
