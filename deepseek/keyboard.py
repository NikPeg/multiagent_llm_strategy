from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from game import ASPECTS

# Список кнопок: для каждого аспекта своя кнопка
def aspects_keyboard():
    keyboard = []
    for code, label, _ in ASPECTS:
        keyboard.append([InlineKeyboardButton(text=label, callback_data=f"aspect:{code}")])
    keyboard.append([InlineKeyboardButton(text="Описание страны", callback_data="aspect:описание")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# Можно сделать просто переменную, тогда не нужно вызывать функцию:
ASPECTS_KEYBOARD = aspects_keyboard()
