from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.callback_data import CallbackData
import logging

from commands import subscription_cb, process_subscription_callback
from admin_commands import admin_cb, process_admin_callback, stats_cb, show_stats
from db import update_user_subscription_status, get_user_by_telegram_id, toggle_feature

# Callback для настроек уведомлений
notification_cb = CallbackData("notification", "feature", "status")

# Callback для дополнительных настроек
settings_cb = CallbackData("settings", "action")

# Клавиатура настроек
def get_settings_keyboard(user_id):
    """Возвращает клавиатуру с настройками уведомлений"""
    user = get_user_by_telegram_id(user_id)

    # Создаем клавиатуру для настроек
    keyboard = InlineKeyboardMarkup(row_width=2)

    # Если пользователь найден, добавляем кнопки с текущими настройками
    if user:
        # Статусы различных типов уведомлений
        news_status = "✅ ВКЛ" if user.get('notify_news', True) else "❌ ВЫКЛ"
        updates_status = "✅ ВКЛ" if user.get('notify_updates', True) else "❌ ВЫКЛ"
        events_status = "✅ ВКЛ" if user.get('notify_events', True) else "❌ ВЫКЛ"

        # Добавляем кнопки переключения типов уведомлений
        keyboard.add(
            InlineKeyboardButton(
                f"Новости: {news_status}",
                callback_data=notification_cb.new(feature="notify_news", status="toggle")
            ),
            InlineKeyboardButton(
                f"Обновления: {updates_status}",
                callback_data=notification_cb.new(feature="notify_updates", status="toggle")
            ),
            InlineKeyboardButton(
                f"События: {events_status}",
                callback_data=notification_cb.new(feature="notify_events", status="toggle")
            )
        )

    # Общие кнопки для всех пользователей
    keyboard.add(
        InlineKeyboardButton("Назад", callback_data=settings_cb.new(action="back")),
        InlineKeyboardButton("Закрыть", callback_data=settings_cb.new(action="close"))
    )

    return keyboard

# Команда /settings
async def cmd_settings(message: types.Message):
    """Обработка команды /settings - настройки уведомлений"""
    user_id = message.from_user.id

    await message.answer(
        "⚙️ *Настройки уведомлений*\n\n"
        "Здесь вы можете настроить типы уведомлений, которые хотите получать.\n"
        "Нажмите на кнопку, чтобы включить или выключить соответствующий тип уведомлений.",
        reply_markup=get_settings_keyboard(user_id)
    )

# Обработчик всех callback-запросов
async def process_callback(callback_query: types.CallbackQuery, callback_data: dict, state: FSMContext, admin_ids: list):
    """Маршрутизация callback-запросов к соответствующим обработчикам"""
    try:
        # Получаем название callback
        callback_name = callback_query.data.split(":")[0]

        # Перенаправляем к соответствующему обработчику
        if callback_name == subscription_cb.prefix:
            await process_subscription_callback(callback_query, callback_data)

        elif callback_name == admin_cb.prefix:
            await process_admin_callback(callback_query, callback_data, state, admin_ids)

        elif callback_name == stats_cb.prefix:
            await show_stats(callback_query, callback_data)

        elif callback_name == notification_cb.prefix:
            await process_notification_callback(callback_query, callback_data)

        elif callback_name == settings_cb.prefix:
            await process_settings_callback(callback_query, callback_data)

        else:
            logging.warning(f"Unknown callback: {callback_query.data}")
            await callback_query.answer("Неизвестная команда")

    except Exception as e:
        logging.error(f"Error processing callback: {e}", exc_info=True)
        await callback_query.answer("Произошла ошибка, попробуйте позже")

# Обработчик настроек уведомлений
async def process_notification_callback(callback_query: types.CallbackQuery, callback_data: dict):
    """Обработка нажатий на кнопки настроек уведомлений"""
    user_id = callback_query.from_user.id
    feature = callback_data["feature"]
    status = callback_data["status"]

    if status == "toggle":
        # Переключаем статус функции
        new_status = toggle_feature(user_id, feature)

        feature_names = {
            "notify_news": "новостей",
            "notify_updates": "обновлений",
            "notify_events": "событий"
        }

        feature_name = feature_names.get(feature, feature)
        status_text = "включены" if new_status else "выключены"

        await callback_query.answer(f"Уведомления {feature_name} {status_text}")

        # Обновляем клавиатуру с новыми настройками
        await callback_query.message.edit_reply_markup(
            reply_markup=get_settings_keyboard(user_id)
        )
    else:
        await callback_query.answer("Неизвестное действие")

# Обработчик дополнительных настроек
async def process_settings_callback(callback_query: types.CallbackQuery, callback_data: dict):
    """Обработка нажатий на кнопки дополнительных настроек"""
    action = callback_data["action"]

    if action == "back":
        # Возвращаемся к основному меню
        await callback_query.message.edit_text(
            "Основное меню",
            reply_markup=get_main_keyboard(callback_query.from_user.id)
        )

    elif action == "close":
        # Закрываем меню настроек
        await callback_query.message.edit_text("Настройки сохранены.")

    else:
        await callback_query.answer("Неизвестное действие")

# Основная клавиатура бота
def get_main_keyboard(user_id):
    """Возвращает основную клавиатуру бота"""
    keyboard = InlineKeyboardMarkup(row_width=2)

    # Получаем информацию о пользователе
    user = get_user_by_telegram_id(user_id)
    is_subscribed = user.get('is_subscribed', False) if user else False

    # Кнопки подписки/отписки
    if is_subscribed:
        sub_button = InlineKeyboardButton("Отписаться", callback_data=subscription_cb.new(action="unsubscribe"))
    else:
        sub_button = InlineKeyboardButton("Подписаться", callback_data=subscription_cb.new(action="subscribe"))

    # Добавляем основные кнопки
    keyboard.add(
        sub_button,
        InlineKeyboardButton("Настройки", callback_data=settings_cb.new(action="settings")),
        InlineKeyboardButton("Помощь", callback_data=settings_cb.new(action="help"))
    )

    return keyboard

# Команда main_menu
async def cmd_menu(message: types.Message):
    """Обработка команды /menu - показывает основное меню бота"""
    user_id = message.from_user.id

    await message.answer(
        "🔍 *Главное меню*\n\n"
        "Выберите действие из меню ниже:",
        reply_markup=get_main_keyboard(user_id)
    )

# Обработчик нажатия кнопки "Помощь"
async def process_help_button(callback_query: types.CallbackQuery):
    """Показывает справку по использованию бота"""
    await callback_query.message.edit_text(
        "📚 *Справка по использованию бота*\n\n"
        "*/start* - начать работу с ботом\n"
        "*/menu* - открыть главное меню\n"
        "*/help* - показать эту справку\n"
        "*/settings* - настроить уведомления\n"
        "*/subscribe* - подписаться на уведомления\n"
        "*/unsubscribe* - отписаться от уведомлений\n"
        "*/status* - проверить статус подписки\n\n"
        "Для возврата в главное меню используйте /menu",
        parse_mode="Markdown"
    )
    await callback_query.answer()
