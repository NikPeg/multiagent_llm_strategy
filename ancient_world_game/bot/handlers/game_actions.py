from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import logging
from datetime import datetime

from storage import (
    get_player_data,
    update_player_stats,
    add_player_action,
    get_player_actions_history,
    get_action_results,
    save_action_result
)

from ai import (
    generate_action_result,
    generate_report,
    generate_minister_opinion,
    analyze_action_impact
)

from config.game_constants import STATS

# Состояния FSM для обработки игровых действий
class ActionStates(StatesGroup):
    waiting_for_action = State()  # Ожидание ввода приказа

# Клавиатура для подтверждения действия
def get_confirmation_keyboard():
    """Создает клавиатуру для подтверждения действия"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("✅ Подтвердить", callback_data="confirm_action"),
        InlineKeyboardButton("❌ Отменить", callback_data="cancel_action")
    )
    return keyboard

# Команда для инициирования нового действия
async def cmd_action(message: types.Message, state: FSMContext):
    """Начинает процесс создания нового действия (приказа)"""
    # Проверяем, является ли пользователь игроком
    player = get_player_data(message.from_user.id)
    if not player:
        await message.answer("Вы не являетесь игроком. Зарегистрируйтесь сначала.")
        return

    # Получаем действие непосредственно из сообщения пользователя
    action_text = message.text

    # Проверяем минимальную длину действия
    if len(action_text) < 3:  # Минимальная длина, чтобы отфильтровать команду /action
        await message.answer(
            "🎯 *Отдать приказ*\n\n"
            "Опишите свое действие. Вы можете делать всё что угодно:\n"
            "- Изменять внутреннюю политику\n"
            "- Взаимодействовать с другими странами\n"
            "- Проводить военные операции\n"
            "- Развивать экономику и технологии\n"
            "И многое другое.\n\n"
            "Просто напишите то, что хотите сделать в свободной форме."
        )
        return

    # Если сообщение начинается с команды /action, удаляем её из текста
    if action_text.startswith("/action"):
        action_text = action_text[7:].strip()

        # Если после команды нет текста, просим пользователя ввести действие
        if not action_text:
            await message.answer(
                "🎯 *Отдать приказ*\n\n"
                "Опишите свое действие в свободной форме. Что вы хотите сделать?"
            )
            await ActionStates.waiting_for_action.set()
            return

    # Получаем данные о стране игрока
    country_name = player.get('country_name', 'Неизвестная страна')

    # Просим подтверждение
    await message.answer(
        f"📜 *Подтверждение приказа*\n\n"
        f"Страна: {country_name}\n\n"
        f"Приказ: {action_text}\n\n"
        f"Подтвердите выполнение приказа:",
        reply_markup=get_confirmation_keyboard()
    )

    # Сохраняем введенное действие в состоянии
    await state.update_data(action_text=action_text)

# Обработчик ввода действия для случая, когда пользователь запустил команду без текста
async def process_action_input(message: types.Message, state: FSMContext):
    """Обрабатывает введенное игроком действие"""
    action_text = message.text

    # Получаем данные о стране игрока
    player = get_player_data(message.from_user.id)
    country_name = player.get('country_name', 'Неизвестная страна')

    # Просим подтверждение
    await message.answer(
        f"📜 *Подтверждение приказа*\n\n"
        f"Страна: {country_name}\n\n"
        f"Приказ: {action_text}\n\n"
        f"Подтвердите выполнение приказа:",
        reply_markup=get_confirmation_keyboard()
    )

    # Сохраняем введенное действие в состоянии
    await state.update_data(action_text=action_text)
    await state.reset_state(with_data=False)  # Сбрасываем состояние, но сохраняем данные

# Обработчик подтверждения действия
async def process_action_confirmation(callback_query: types.CallbackQuery, state: FSMContext):
    """Обрабатывает подтверждение или отмену действия"""
    action = callback_query.data

    if action == "cancel_action":
        await callback_query.message.edit_text("❌ Приказ отменен.")
        await state.finish()
        return

    # Получаем данные из состояния
    data = await state.get_data()
    action_text = data.get('action_text')

    # Получаем данные о стране игрока
    player = get_player_data(callback_query.from_user.id)
    country_name = player.get('country_name', 'Неизвестная страна')

    # Сначала сообщаем, что приказ обрабатывается
    await callback_query.message.edit_text(
        f"⏳ Идет обработка приказа для страны {country_name}...\n\n"
        f"Это может занять некоторое время."
    )

    # Сохраняем действие в базе данных
    action_id = add_player_action(
        callback_query.from_user.id,
        action_text,
        action_type="custom"
    )

    try:
        # Генерируем результат действия с помощью ИИ
        result = await generate_action_result(
            country_name=country_name,
            action=action_text,
            player_stats=player
        )

        # Анализируем влияние действия на характеристики страны
        stats_impact = await analyze_action_impact(
            country_name=country_name,
            action=action_text,
            action_result=result,
            current_stats=player
        )

        # Обновляем статистику игрока, используя STATS из констант
        stat_updates = {}
        for stat in STATS:
            if stat in stats_impact:
                stat_updates[stat] = stats_impact[stat]

        update_player_stats(
            callback_query.from_user.id,
            **stat_updates
        )

        # Сохраняем результат действия
        save_action_result(action_id, result, stats_impact)

        # Формируем сообщение с результатом
        result_message = (
            f"✅ *Результат приказа*\n\n"
            f"Страна: {country_name}\n\n"
            f"Приказ: {action_text}\n\n"
            f"Результат: {result}\n\n"
        )

        # Добавляем изменения характеристик, если они есть
        has_impact = any(stat in stats_impact and stats_impact[stat] != 0 for stat in STATS)
        if has_impact:
            result_message += "*Влияние на характеристики:*\n"

            for stat in STATS:
                if stat in stats_impact and stats_impact[stat] != 0:
                    value = stats_impact[stat]
                    emoji = "🔼" if value > 0 else "🔽"
                    # Получаем название статистики с заглавной буквы
                    stat_name = stat.capitalize()

                    result_message += f"{emoji} {stat_name}: {value:+.1f}\n"

        # Отправляем результат
        await callback_query.message.edit_text(result_message)

        # Генерируем и отправляем мнение министра (как дополнительное сообщение)
        minister_opinion = await generate_minister_opinion(
            country_name=country_name,
            action=action_text,
            action_result=result
        )

        await callback_query.message.answer(
            f"💼 *Мнение советника*\n\n{minister_opinion}"
        )

    except Exception as e:
        logging.error(f"Error processing action: {e}", exc_info=True)
        await callback_query.message.edit_text(
            f"❌ Произошла ошибка при обработке приказа: {str(e)}\n\n"
            f"Пожалуйста, попробуйте позже или обратитесь к администратору."
        )

    finally:
        # Завершаем состояние
        await state.finish()

# Прямое принятие текста сообщения как приказа
async def direct_action_processing(message: types.Message, state: FSMContext):
    """Обрабатывает обычное сообщение как приказ"""
    # Проверяем, является ли пользователь игроком
    player = get_player_data(message.from_user.id)
    if not player:
        return  # Если пользователь не игрок, просто игнорируем сообщение

    # Получаем текст действия
    action_text = message.text.strip()

    # Игнорируем очень короткие сообщения и сообщения, начинающиеся с '/'
    if len(action_text) < 5 or action_text.startswith('/'):
        return

    # Получаем данные о стране игрока
    country_name = player.get('country_name', 'Неизвестная страна')

    # Просим подтверждение
    await message.reply(
        f"📜 *Расценить как приказ?*\n\n"
        f"Страна: {country_name}\n\n"
        f"Приказ: {action_text}\n\n"
        f"Подтвердите выполнение приказа:",
        reply_markup=get_confirmation_keyboard()
    )

    # Сохраняем введенное действие в состоянии
    await state.update_data(action_text=action_text)

# Команда для просмотра истории действий
async def cmd_history(message: types.Message):
    """Показывает историю действий игрока"""
    # Проверяем, является ли пользователь игроком
    player = get_player_data(message.from_user.id)
    if not player:
        await message.answer("Вы не являетесь игроком. Зарегистрируйтесь сначала.")
        return

    # Получаем историю действий
    actions = get_player_actions_history(message.from_user.id, limit=5)

    if not actions:
        await message.answer("У вас пока нет выполненных действий.")
        return

    # Формируем сообщение с историей
    history_message = "📜 *История ваших последних действий*\n\n"

    for i, action in enumerate(actions, 1):
        action_text = action.get('action_text', 'Неизвестное действие')
        action_date = action.get('action_date', 'Неизвестная дата')
        action_id = action.get('id', 0)

        # Ограничиваем длину текста действия
        if len(action_text) > 50:
            action_text = action_text[:47] + "..."

        history_message += f"{i}. {action_date}\n   {action_text}\n   /result_{action_id} - подробнее\n\n"

    await message.answer(history_message)

# Обработчик команды для просмотра результата конкретного действия
async def cmd_action_result(message: types.Message):
    """Показывает результат конкретного действия"""
    # Извлекаем ID действия из команды
    command_parts = message.text.split('_')
    if len(command_parts) != 2:
        return

    try:
        action_id = int(command_parts[1])
    except ValueError:
        return

    # Получаем результат действия
    action_result = get_action_results(action_id)

    if not action_result:
        await message.answer("Действие не найдено или результаты недоступны.")
        return

    # Формируем сообщение с результатом
    action_text = action_result.get('action_text', 'Неизвестное действие')
    result_text = action_result.get('result_text', 'Результат неизвестен')
    action_date = action_result.get('action_date', 'Неизвестная дата')
    stats_impact = action_result.get('stats_impact', {})

    result_message = (
        f"📊 *Результат действия от {action_date}*\n\n"
        f"Действие: {action_text}\n\n"
        f"Результат: {result_text}\n\n"
    )

    # Добавляем изменения характеристик, если они есть
    has_impact = any(stat in stats_impact and stats_impact[stat] != 0 for stat in STATS)
    if has_impact:
        result_message += "*Влияние на характеристики:*\n"

        for stat in STATS:
            if stat in stats_impact and stats_impact[stat] != 0:
                value = stats_impact[stat]
                emoji = "🔼" if value > 0 else "🔽"
                # Получаем название статистики с заглавной буквы
                stat_name = stat.capitalize()

                result_message += f"{emoji} {stat_name}: {value:+.1f}\n"

    await message.answer(result_message)

# Команда для генерации отчета о текущем состоянии страны
async def cmd_report(message: types.Message):
    """Генерирует отчет о текущем состоянии страны"""
    # Проверяем, является ли пользователь игроком
    player = get_player_data(message.from_user.id)
    if not player:
        await message.answer("Вы не являетесь игроком. Зарегистрируйтесь сначала.")
        return

    # Отправляем сообщение о генерации отчета
    wait_message = await message.answer("⏳ Генерация отчета о состоянии страны...")

    try:
        # Получаем название страны и характеристики
        country_name = player.get('country_name', 'Неизвестная страна')

        # Генерируем отчет с помощью ИИ
        report = await generate_report(country_name=country_name, player_stats=player)

        # Отправляем отчет
        await wait_message.edit_text(
            f"📈 *Отчет о состоянии страны {country_name}*\n\n{report}"
        )

    except Exception as e:
        logging.error(f"Error generating report: {e}", exc_info=True)
        await wait_message.edit_text(
            "❌ Произошла ошибка при генерации отчета. Пожалуйста, попробуйте позже."
        )
