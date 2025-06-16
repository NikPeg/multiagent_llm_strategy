from aiogram.fsm.state import StatesGroup, State

class ResetCountry(StatesGroup):
    confirming = State()

class EditAspect(StatesGroup):
    waiting_new_value = State()
