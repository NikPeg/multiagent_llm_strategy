from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.callback_data import CallbackData

from db import update_user_subscription_status, get_user_by_telegram_id
from subscription import check_subscription_status
from broadcast import broadcast_to_subscribers

# Определение состояний для FSM
class BroadcastStates(StatesGroup):
    waiting_for_message = State()

# Callback для кнопок
subscription_cb = CallbackData("subscription", "action")

# Клавиатура с кнопками подписки
def get_subscription_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("Подписаться", callback_data=subscription_cb.new(action="subscribe")),
        InlineKeyboardButton("Отписаться", callback_data=subscription_cb.new(action="unsubscribe")),
        InlineKeyboardButton("Проверить статус подписки", callback_data=subscription_cb.new(action="check"))
    )
    return keyboard

# Команда старт
async def cmd_start(message: types.Message):
    """Обработка команды /start"""
    user_name = message.from_user.first_name
    await message.answer(
        f"Привет, {user_name}! 👋\n\n"
        f"Я бот для управления подписками на уведомления.\n"
        f"Вы можете подписаться на уведомления, чтобы получать важные сообщения.\n\n"
        f"Используйте /help для получения списка команд.",
        reply_markup=get_subscription_keyboard()
    )

# Команда помощи
async def cmd_help(message: types.Message):
    """Обработка команды /help"""
    await message.answer(
        "Доступные команды:\n\n"
        "/start - Начать работу с ботом\n"
        "/help - Показать список команд\n"
        "/subscribe - Подписаться на уведомления\n"
        "/unsubscribe - Отписаться от уведомлений\n"
        "/status - Проверить статус подписки\n"
        "/broadcast - Отправить сообщение всем подписчикам (только для администраторов)"
    )

# Команда подписки
async def cmd_subscribe(message: types.Message):
    """Обработка команды /subscribe"""
    user_id = message.from_user.id
    update_user_subscription_status(user_id, True)
    await message.answer("Вы успешно подписались на уведомления! ✅")

# Команда отписки
async def cmd_unsubscribe(message: types.Message):
    """Обработка команды /unsubscribe"""
    user_id = message.from_user.id
    update_user_subscription_status(user_id, False)
    await message.answer("Вы отписались от уведомлений. ❌")

# Проверка статуса подписки
async def cmd_status(message: types.Message):
    """Обработка команды /status"""
    user_id = message.from_user.id
    is_subscribed = check_subscription_status(user_id)

    if is_subscribed:
        await message.answer("Вы подписаны на уведомления! ✅")
    else:
        await message.answer("Вы не подписаны на уведомления. ❌\nИспользуйте /subscribe чтобы подписаться.")

# Обработка callback запросов для подписки/отписки
async def process_subscription_callback(callback_query: types.CallbackQuery, callback_data: dict):
    """Обработка нажатий на кнопки подписки"""
    user_id = callback_query.from_user.id
    action = callback_data["action"]

    if action == "subscribe":
        update_user_subscription_status(user_id, True)
        await callback_query.answer("Вы подписались на уведомления!")
        await callback_query.message.answer("Вы успешно подписались на уведомления! ✅")

    elif action == "unsubscribe":
        update_user_subscription_status(user_id, False)
        await callback_query.answer("Вы отписались от уведомлений")
        await callback_query.message.answer("Вы отписались от уведомлений. ❌")

    elif action == "check":
        is_subscribed = check_subscription_status(user_id)
        if is_subscribed:
            await callback_query.answer("Вы подписаны на уведомления!")
            await callback_query.message.answer("Вы подписаны на уведомления! ✅")
        else:
            await callback_query.answer("Вы не подписаны на уведомления")
            await callback_query.message.answer("Вы не подписаны на уведомления. ❌")

# Инициирование рассылки (только для администраторов)
async def cmd_broadcast(message: types.Message, state: FSMContext, admin_ids: list):
    """Начало процесса рассылки"""
    user_id = message.from_user.id

    # Проверяем, является ли пользователь администратором
    if user_id not in admin_ids:
        await message.answer("Эта команда доступна только администраторам.")
        return

    await message.answer("Введите сообщение для рассылки всем подписчикам:")
    await BroadcastStates.waiting_for_message.set()

# Получение текста для рассылки
async def process_broadcast_message(message: types.Message, state: FSMContext, admin_ids: list):
    """Обработка сообщения для рассылки"""
    if message.from_user.id not in admin_ids:
        await state.finish()
        return

    broadcast_text = message.text

    # Подтверждение перед отправкой
    await message.answer(
        f"Вы собираетесь отправить следующее сообщение всем подписчикам:\n\n"
        f"{broadcast_text}\n\n"
        f"Подтвердите отправку /confirm или отмените /cancel"
    )

    # Сохраняем текст в состоянии
    await state.update_data(broadcast_text=broadcast_text)

# Подтверждение рассылки
async def confirm_broadcast(message: types.Message, state: FSMContext):
    """Подтверждение и выполнение рассылки"""
    data = await state.get_data()
    broadcast_text = data.get("broadcast_text")

    # Делаем рассылку
    sent_count = await broadcast_to_subscribers(broadcast_text)

    await message.answer(f"Сообщение успешно отправлено {sent_count} подписчикам.")
    await state.finish()

# Отмена рассылки
async def cancel_broadcast(message: types.Message, state: FSMContext):
    """Отмена рассылки"""
    await message.answer("Рассылка отменена.")
    await state.finish()

# Обработка всех остальных сообщений в состоянии ожидания текста для рассылки
async def process_other_message(message: types.Message, state: FSMContext):
    """Обработка других сообщений во время ожидания текста рассылки"""
    await message.answer(
        "Введите текст сообщения для рассылки или воспользуйтесь командами:\n"
        "/confirm - подтвердить отправку\n"
        "/cancel - отменить рассылку"
    )
