from aiogram import types, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from utils import answer_html

router = Router()

@router.message(Command("cancel"))
async def admin_edit_cancel(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is not None:
        await state.clear()
        await answer_html(message, "Изменение отменено.")
    else:
        await answer_html(message, "Нет активных действий для отмены.")

def register(dp):
    dp.include_router(router)
