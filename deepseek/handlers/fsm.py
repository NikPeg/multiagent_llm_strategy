from aiogram.fsm.state import StatesGroup, State

class ResetCountry(StatesGroup):
    confirming = State()

class EditAspect(StatesGroup):
    waiting_new_value = State()

class ConfirmEvent(StatesGroup):
    waiting_approve = State()

class AdminSendMessage(StatesGroup):
    waiting_message = State()
