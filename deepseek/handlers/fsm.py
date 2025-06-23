from aiogram.fsm.state import State, StatesGroup


class ResetCountry(StatesGroup):
    confirming = State()


class EditAspect(StatesGroup):
    waiting_new_value = State()


class ConfirmEvent(StatesGroup):
    waiting_approve = State()


class AdminSendMessage(StatesGroup):
    waiting_message = State()


class AddCountrySynonym(StatesGroup):
    waiting_for_synonym = State()


class SendMessageFSM(StatesGroup):
    waiting_for_country = State()
    waiting_for_text = State()


class RegisterCountry(StatesGroup):
    waiting_for_name = State()
    waiting_for_desc = State()
