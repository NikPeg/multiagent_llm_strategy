"""
registration.py - Обработчики для регистрации новой страны в игре.
Отвечает за создание профиля, выбор имени страны и настройку характеристик.
"""

from aiogram import Router, F, types
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import config, STATS, STAT_EMOJIS, MAX_STAT_VALUE, INITIAL_STAT_VALUE, INITIAL_STAT_POINTS
from utils import logger, log_function_call
from game_logic import (
    get_player,
    init_stats,
    distribute_points,
    reset_stats,
    validate_stats,
    format_stats_for_display
)
from ..keyboards import (
    create_stats_keyboard,
    create_confirmation_keyboard,
    create_main_menu_keyboard
)
from ..bot_instance import bot


# Определяем состояния для регистрации
class RegistrationStates(StatesGroup):
    waiting_for_country_name = State()
    distributing_stats = State()
    entering_description = State()
    confirming_registration = State()


# Создаем роутер для обработчиков регистрации
registration_router = Router()


@registration_router.message(Command("start"))
@log_function_call
async def cmd_start(message: Message, state: FSMContext):
    """
    Обработчик команды /start.
    Начинает процесс регистрации или показывает основное меню.

    Args:
        message: Сообщение пользователя
        state: Состояние FSM
    """
    user_id = message.from_user.id
    username = message.from_user.username

    # Получаем объект игрока
    player = get_player(user_id, username)

    # Если игрок уже зарегистрирован
    if player.is_registered():
        await message.answer(
            f"Добро пожаловать обратно, правитель {player.country_name}! "
            f"Выберите действие из меню.",
            reply_markup=create_main_menu_keyboard()
        )
        return

    # Если игрок не зарегистрирован, начинаем процесс регистрации
    await message.answer(
        f"Приветствую, {message.from_user.first_name}! "
        f"Добро пожаловать в игру \"Древний Мир\".\n\n"
        f"Для начала игры необходимо создать свою страну. "
        f"Как будет называться ваше государство?"
    )

    # Переходим к состоянию ожидания имени страны
    await state.set_state(RegistrationStates.waiting_for_country_name)


@registration_router.message(RegistrationStates.waiting_for_country_name)
@log_function_call
async def process_country_name(message: Message, state: FSMContext):
    """
    Обработчик ввода названия страны.

    Args:
        message: Сообщение пользователя
        state: Состояние FSM
    """
    country_name = message.text.strip()

    # Проверяем длину названия
    if len(country_name) < 3 or len(country_name) > 30:
        await message.answer(
            "Название страны должно содержать от 3 до 30 символов. "
            "Пожалуйста, выберите другое название."
        )
        return

    # Сохраняем название страны в состоянии
    await state.update_data(country_name=country_name)

    # Инициализируем начальные статы
    stats = init_stats(INITIAL_STAT_POINTS)
    await state.update_data(stats=stats)

    # Показываем интерфейс распределения характеристик
    stats_text = format_stats_for_display(stats)

    await message.answer(
        f"Отлично! Ваша страна будет называться *{country_name}*.\n\n"
        f"Теперь распределите очки между характеристиками вашего государства. "
        f"У вас есть {INITIAL_STAT_POINTS} очков.\n\n"
        f"{stats_text}",
        reply_markup=create_stats_keyboard(stats),
        parse_mode="HTML"
    )

    # Переходим к состоянию распределения характеристик
    await state.set_state(RegistrationStates.distributing_stats)


@registration_router.callback_query(
    RegistrationStates.distributing_stats,
    F.data.startswith("stat_")
)
@log_function_call
async def process_stat_selection(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик выбора характеристики для увеличения.

    Args:
        callback: Данные коллбэка
        state: Состояние FSM
    """
    # Извлекаем имя характеристики из данных коллбэка
    stat_name = callback.data.split("_")[1]

    # Получаем текущие статы
    data = await state.get_data()
    stats = data.get("stats", {})

    # Пытаемся увеличить выбранную характеристику
    stats = distribute_points(stats, stat_name)

    # Обновляем статы в состоянии
    await state.update_data(stats=stats)

    # Обновляем сообщение с клавиатурой
    stats_text = format_stats_for_display(stats)

    await callback.message.edit_text(
        f"Распределите очки между характеристиками вашего государства. "
        f"У вас осталось {stats.get('available_points', 0)} очков.\n\n"
        f"{stats_text}",
        reply_markup=create_stats_keyboard(stats),
        parse_mode="HTML"
    )


@registration_router.callback_query(
    RegistrationStates.distributing_stats,
    F.data == "reset_stats"
)
@log_function_call
async def process_reset_stats(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик сброса характеристик.

    Args:
        callback: Данные коллбэка
        state: Состояние FSM
    """
    # Получаем текущие статы
    data = await state.get_data()
    stats = data.get("stats", {})

    # Сбрасываем статы
    stats = reset_stats(stats)

    # Обновляем статы в состоянии
    await state.update_data(stats=stats)

    # Обновляем сообщение с клавиатурой
    stats_text = format_stats_for_display(stats)

    await callback.message.edit_text(
        f"Характеристики сброшены. Распределите очки заново. "
        f"У вас есть {stats.get('available_points', 0)} очков.\n\n"
        f"{stats_text}",
        reply_markup=create_stats_keyboard(stats),
        parse_mode="HTML"
    )


@registration_router.callback_query(
    RegistrationStates.distributing_stats,
    F.data == "confirm_stats"
)
@log_function_call
async def process_confirm_stats(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик подтверждения выбранных характеристик.

    Args:
        callback: Данные коллбэка
        state: Состояние FSM
    """
    # Получаем текущие статы
    data = await state.get_data()
    stats = data.get("stats", {})

    # Проверяем, что все очки распределены
    if stats.get('available_points', 0) > 0:
        await callback.answer(
            f"У вас остались нераспределенные очки: {stats.get('available_points', 0)}. "
            f"Распределите все очки или продолжите с текущими характеристиками.",
            show_alert=True
        )
        return

    # Подтверждаем выбор и переходим к следующему шагу
    await callback.answer("Характеристики подтверждены!")

    await callback.message.answer(
        "Теперь напишите краткое описание вашей страны. "
        "Включите географические особенности, форму правления, основные занятия населения, "
        "религиозные верования и культурные традиции.\n\n"
        "Это поможет сформировать уникальную историю вашего государства."
    )

    # Переходим к состоянию ввода описания
    await state.set_state(RegistrationStates.entering_description)


@registration_router.message(RegistrationStates.entering_description)
@log_function_call
async def process_country_description(message: Message, state: FSMContext):
    """
    Обработчик ввода описания страны.

    Args:
        message: Сообщение пользователя
        state: Состояние FSM
    """
    description = message.text.strip()

    # Проверяем длину описания
    if len(description) < 10:
        await message.answer(
            "Пожалуйста, введите более подробное описание вашей страны "
            "(минимум 10 символов)."
        )
        return

    # Сохраняем описание в состоянии
    await state.update_data(description=description)

    # Получаем все данные для подтверждения
    data = await state.get_data()
    country_name = data.get("country_name", "")
    stats = data.get("stats", {})

    # Формируем сообщение для подтверждения
    stats_text = format_stats_for_display(stats)

    await message.answer(
        f"Пожалуйста, проверьте информацию о вашей стране:\n\n"
        f"Название: *{country_name}*\n\n"
        f"Характеристики:\n{stats_text}\n\n"
        f"Описание:\n{description}\n\n"
        f"Всё верно?",
        reply_markup=create_confirmation_keyboard(),
        parse_mode="HTML"
    )

    # Переходим к состоянию подтверждения регистрации
    await state.set_state(RegistrationStates.confirming_registration)


@registration_router.callback_query(
    RegistrationStates.confirming_registration,
    F.data == "confirm_registration"
)
@log_function_call
async def process_final_confirmation(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик окончательного подтверждения регистрации.

    Args:
        callback: Данные коллбэка
        state: Состояние FSM
    """
    # Получаем данные регистрации
    data = await state.get_data()
    country_name = data.get("country_name", "")
    stats = data.get("stats", {})
    description = data.get("description", "")

    # Убираем служебное поле из статов
    if 'available_points' in stats:
        del stats['available_points']

    # Получаем объект игрока
    user_id = callback.from_user.id
    username = callback.from_user.username
    player = get_player(user_id, username)

    # Регистрируем страну
    success = player.register_country(country_name, stats, description)

    if success:
        # Отправляем приветственное сообщение
        await callback.message.answer(
            f"Поздравляем! Ваша страна *{country_name}* успешно создана и "
            f"готова к покорению древнего мира!\n\n"
            f"Используйте кнопки меню для управления своим государством.",
            reply_markup=create_main_menu_keyboard(),
            parse_mode="Markdown"
        )

        # Опционально: отправляем уведомление администраторам
        for admin_id in config.ADMIN_IDS:
            try:
                await bot.send_message(
                    admin_id,
                    f"Новая страна зарегистрирована!\n"
                    f"Игрок: {username} (ID: {user_id})\n"
                    f"Страна: {country_name}"
                )
            except Exception as e:
                logger.error(f"Не удалось отправить уведомление администратору {admin_id}: {e}")
    else:
        # В случае ошибки
        await callback.message.answer(
            "К сожалению, произошла ошибка при регистрации страны. "
            "Пожалуйста, попробуйте еще раз или обратитесь к администратору."
        )

    # Сбрасываем состояние
    await state.clear()


@registration_router.callback_query(
    RegistrationStates.confirming_registration,
    F.data == "edit_registration"
)
@log_function_call
async def process_edit_registration(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик редактирования регистрации.

    Args:
        callback: Данные коллбэка
        state: Состояние FSM
    """
    # Возвращаемся к распределению характеристик
    data = await state.get_data()
    stats = data.get("stats", {})

    # Обновляем сообщение с клавиатурой
    stats_text = format_stats_for_display(stats)

    await callback.message.edit_text(
        f"Вернемся к настройке характеристик. "
        f"У вас осталось {stats.get('available_points', 0)} нераспределенных очков.\n\n"
        f"{stats_text}",
        reply_markup=create_stats_keyboard(stats),
        parse_mode="HTML"
    )

    # Переходим к состоянию распределения характеристик
    await state.set_state(RegistrationStates.distributing_stats)


# Обработчик отмены регистрации на любом этапе
@registration_router.message(Command("cancel"))
@log_function_call
async def cmd_cancel(message: Message, state: FSMContext):
    """
    Обработчик команды /cancel.
    Отменяет процесс регистрации.

    Args:
        message: Сообщение пользователя
        state: Состояние FSM
    """
    current_state = await state.get_state()

    if current_state is not None:
        # Если процесс регистрации был начат, отменяем его
        await state.clear()
        await message.answer(
            "Процесс регистрации отменен. Вы можете начать заново с помощью команды /start."
        )
    else:
        # Если регистрация не была начата
        await message.answer(
            "Нет активного процесса регистрации для отмены."
        )
