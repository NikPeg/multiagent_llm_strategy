from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from game import ASPECTS

def aspects_keyboard():
    # Кнопки с названиями аспектов (плюс описание страны)
    buttons = [KeyboardButton(text=label) for _, label, _ in ASPECTS]
    buttons.append(KeyboardButton(text="Описание страны"))
    # Можно разбивать кнопки по рядам, если хотите несколько в строке:
    keyboard = [buttons]  # всё в одну строку
    # Или так для вертикального расположения:
    # keyboard = [[b] for b in buttons]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        is_persistent=True,  # клавиатура постоянная
        input_field_placeholder="Выбери аспект или напиши свой ход"
    )

ASPECTS_KEYBOARD = aspects_keyboard()
