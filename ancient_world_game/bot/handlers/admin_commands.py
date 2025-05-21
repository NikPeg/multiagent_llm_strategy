from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.callback_data import CallbackData
import logging

from storage import (
    get_user_by_telegram_id,
    update_user_role,
    create_user_if_not_exists,
    db_stats
)

# Callback для административных действий
admin_cb = CallbackData("admin", "action", "user_id")
stats_cb = CallbackData("stats", "type")

# Состояния для административных FSM
class AddAdminStates(StatesGroup):
    waiting_for_user_id = State()

class RemoveAdminStates(StatesGroup):
    waiting_for_user_id = State()

class UserInfoStates(StatesGroup):
    waiting_for_user_id = State()

# Получение административной клавиатуры
def get_admin_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("Статистика", callback_data=stats_cb.new(type="general")),
        InlineKeyboardButton("Список пользователей", callback_data=admin_cb.new(action="list_users", user_id="0")),
        InlineKeyboardButton("Список подписчиков", callback_data=admin_cb.new(action="list_subscribers", user_id="0")),
        InlineKeyboardButton("Активные пользователи", callback_data=admin_cb.new(action="list_active", user_id="0")),
        InlineKeyboardButton("Добавить админа", callback_data=admin_cb.new(action="add_admin", user_id="0")),
        InlineKeyboardButton("Удалить админа", callback_data=admin_cb.new(action="remove_admin", user_id="0")),
        InlineKeyboardButton("Информация о пользователе", callback_data=admin_cb.new(action="user_info", user_id="0"))
    )
    return keyboard

# Команда admin
async def cmd_admin(message: types.Message, admin_ids: list):
    """Обработка команды /admin - показывает административную панель"""
    user_id = message.from_user.id

    # Проверяем, является ли пользователь администратором
    if user_id not in admin_ids:
        await message.answer("У вас нет прав доступа к административной панели.")
        return

    await message.answer(
        "Административная панель управления ботом\n\n"
        "Выберите действие из меню ниже:",
        reply_markup=get_admin_keyboard()
    )

# Обработчик административных callback-запросов
async def process_admin_callback(callback_query: types.CallbackQuery, callback_data: dict, state: FSMContext, admin_ids: list):
    """Обработка нажатий на кнопки административной панели"""
    user_id = callback_query.from_user.id

    # Проверка прав администратора
    if user_id not in admin_ids:
        await callback_query.answer("У вас нет прав администратора")
        return

    action = callback_data["action"]

    # Обработка разных действий
    if action == "add_admin":
        await callback_query.message.answer("Введите Telegram ID пользователя, которого хотите назначить администратором:")
        await AddAdminStates.waiting_for_user_id.set()

    elif action == "remove_admin":
        await callback_query.message.answer("Введите Telegram ID пользователя, у которого хотите убрать права администратора:")
        await RemoveAdminStates.waiting_for_user_id.set()

    elif action == "user_info":
        await callback_query.message.answer("Введите Telegram ID пользователя, информацию о котором хотите получить:")
        await UserInfoStates.waiting_for_user_id.set()

    # Подтверждаем обработку callback
    await callback_query.answer()

# Вывод статистики
async def show_stats(callback_query: types.CallbackQuery, callback_data: dict):
    """Вывод статистики использования бота"""
    stats_type = callback_data["type"]

    if stats_type == "general":
        stats = db_stats()

        await callback_query.message.answer(
            "📊 **Статистика бота**\n\n"
            f"👥 Всего пользователей: {stats['total_users']}\n"
            f"🔔 Активных подписчиков: {stats['subscribers']}\n"
            f"📅 Пользователей за последние 24 часа: {stats['active_today']}\n"
            f"📆 Пользователей за последние 7 дней: {stats['active_week']}\n"
            f"👑 Администраторов: {stats['admins']}\n\n"
            f"🚀 Бот работает с: {stats['bot_started']}"
        )

    await callback_query.answer()

# Вывод списка всех пользователей
async def list_all_users(callback_query: types.CallbackQuery):
    """Вывод списка всех пользователей"""
    users = get_all_users()

    if not users:
        await callback_query.message.answer("В базе данных нет пользователей.")
        return

    # Формируем сообщение со списком пользователей
    message_text = "📋 Список всех пользователей бота:\n\n"

    for i, user in enumerate(users[:20], 1):  # Ограничиваем список первыми 20 записями
        message_text += (f"{i}. ID: {user['telegram_id']}, "
                         f"Имя: {user['first_name']} {user['last_name'] or ''}\n"
                         f"   Username: @{user['username'] or 'нет'}, "
                         f"Подписан: {'✅' if user['is_subscribed'] else '❌'}\n")

    if len(users) > 20:
        message_text += f"\n... и еще {len(users) - 20} пользователей"

    message_text += f"\n\nВсего пользователей: {len(users)}"

    await callback_query.message.answer(message_text)

# Вывод списка подписчиков
async def list_subscribers(callback_query: types.CallbackQuery):
    """Вывод списка подписчиков"""
    subscribers = get_subscribers()

    if not subscribers:
        await callback_query.message.answer("В базе данных нет подписчиков.")
        return

    # Формируем сообщение со списком подписчиков
    message_text = "📋 Список подписчиков бота:\n\n"

    for i, user in enumerate(subscribers[:20], 1):  # Ограничиваем список первыми 20 записями
        message_text += (f"{i}. ID: {user['telegram_id']}, "
                         f"Имя: {user['first_name']} {user['last_name'] or ''}\n"
                         f"   Username: @{user['username'] or 'нет'}\n")

    if len(subscribers) > 20:
        message_text += f"\n... и еще {len(subscribers) - 20} подписчиков"

    message_text += f"\n\nВсего подписчиков: {len(subscribers)}"

    await callback_query.message.answer(message_text)

# Вывод списка активных пользователей
async def list_active_users(callback_query: types.CallbackQuery):
    """Вывод списка активных пользователей за последние 7 дней"""
    active_users = get_active_users(days=7)

    if not active_users:
        await callback_query.message.answer("В базе данных нет активных пользователей за последние 7 дней.")
        return

    # Формируем сообщение со списком активных пользователей
    message_text = "📋 Список активных пользователей бота за последние 7 дней:\n\n"

    for i, user in enumerate(active_users[:20], 1):  # Ограничиваем список первыми 20 записями
        message_text += (f"{i}. ID: {user['telegram_id']}, "
                         f"Имя: {user['first_name']} {user['last_name'] or ''}\n"
                         f"   Username: @{user['username'] or 'нет'}, "
                         f"Последняя активность: {user['last_activity']}\n")

    if len(active_users) > 20:
        message_text += f"\n... и еще {len(active_users) - 20} пользователей"

    message_text += f"\n\nВсего активных пользователей: {len(active_users)}"

    await callback_query.message.answer(message_text)

# Добавление администратора
async def add_admin(message: types.Message, state: FSMContext, admin_ids: list):
    """Добавление нового администратора"""
    try:
        user_id = int(message.text.strip())

        # Проверяем существование пользователя в базе
        user = get_user_by_telegram_id(user_id)

        if not user:
            await message.answer("Пользователь с таким ID не найден в базе данных.")
            await state.finish()
            return

        # Обновляем роль пользователя
        update_user_role(user_id, is_admin=True)
        admin_ids.append(user_id)  # Добавляем в список администраторов

        await message.answer(f"Пользователь с ID {user_id} успешно назначен администратором.")
    except ValueError:
        await message.answer("Некорректный формат ID. Пожалуйста, введите числовой ID.")
    finally:
        await state.finish()

# Удаление администратора
async def remove_admin(message: types.Message, state: FSMContext, admin_ids: list):
    """Удаление администратора"""
    try:
        user_id = int(message.text.strip())

        # Проверяем, является ли пользователь администратором
        if user_id not in admin_ids:
            await message.answer("Этот пользователь не является администратором.")
            await state.finish()
            return

        # Проверяем, не удаляет ли администратор сам себя
        if user_id == message.from_user.id:
            await message.answer("Вы не можете удалить права администратора у самого себя.")
            await state.finish()
            return

        # Обновляем роль пользователя
        update_user_role(user_id, is_admin=False)
        admin_ids.remove(user_id)  # Удаляем из списка администраторов

        await message.answer(f"Пользователь с ID {user_id} больше не является администратором.")
    except ValueError:
        await message.answer("Некорректный формат ID. Пожалуйста, введите числовой ID.")
    finally:
        await state.finish()

# Информация о пользователе
async def get_user_info(message: types.Message, state: FSMContext):
    """Получение подробной информации о пользователе"""
    try:
        user_id = int(message.text.strip())

        # Получаем информацию о пользователе
        user = get_user_by_telegram_id(user_id)

        if not user:
            await message.answer("Пользователь с таким ID не найден в базе данных.")
            await state.finish()
            return

        # Формируем сообщение с информацией о пользователе
        user_info = (
            f"📌 Информация о пользователе:\n\n"
            f"ID: {user['telegram_id']}\n"
            f"Имя: {user['first_name']} {user['last_name'] or ''}\n"
            f"Username: @{user['username'] or 'нет'}\n"
            f"Подписан на уведомления: {'✅' if user['is_subscribed'] else '❌'}\n"
            f"Администратор: {'✅' if user['is_admin'] else '❌'}\n"
            f"Дата регистрации: {user['registration_date']}\n"
            f"Последняя активность: {user['last_activity']}\n"
        )

        await message.answer(user_info)
    except ValueError:
        await message.answer("Некорректный формат ID. Пожалуйста, введите числовой ID.")
    finally:
        await state.finish()

# Обновление last_activity для пользователя
async def update_user_activity(message: types.Message):
    """Обновление времени последней активности пользователя"""
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    username = message.from_user.username

    try:
        # Создаем пользователя, если его нет, или обновляем активность
        create_user_if_not_exists(user_id, first_name, last_name, username, update_activity=True)
    except Exception as e:
        logging.error(f"Error updating user activity: {e}")
