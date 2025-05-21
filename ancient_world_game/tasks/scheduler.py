import asyncio
import logging
import aioschedule as schedule
from datetime import datetime, time, timedelta
import random
from typing import Dict, List, Callable, Coroutine, Any

from config.config import ADMIN_IDS
from .daily_update import process_daily_update
from .projects_progress import update_projects_progress
from utils.logger import get_logger
from db import get_active_players

# Инициализация логгера
logger = get_logger(__name__)

# Словарь для хранения запланированных задач
scheduled_tasks: Dict[str, schedule.Job] = {}

# Словарь для хранения случайных задач и их интервалов
random_tasks: Dict[str, Dict] = {}

async def setup_scheduler(bot):
    """
    Настраивает планировщик задач

    Args:
        bot: Экземпляр бота для отправки уведомлений
    """
    logger.info("Setting up scheduler...")

    # Очищаем все задачи при перезапуске
    schedule.clear()

    # Устанавливаем ежедневные задачи
    # Обновление игрового мира (смена года) в 00:00
    scheduled_tasks['daily_update'] = schedule.every().day.at("00:00").do(
        lambda: asyncio.create_task(process_daily_update(bot))
    )
    logger.info("Scheduled daily update at 00:00")

    # Обновление прогресса проектов каждые 4 часа
    for hour in [0, 4, 8, 12, 16, 20]:
        task_name = f'projects_update_{hour}'
        scheduled_tasks[task_name] = schedule.every().day.at(f"{hour:02d}:00").do(
            lambda: asyncio.create_task(update_projects_progress(bot))
        )
    logger.info("Scheduled projects updates every 4 hours")

    # Рассылка случайных событий несколько раз в день
    setup_random_events(bot)
    logger.info("Scheduled random events")

    # Запуск бесконечного цикла для выполнения запланированных задач
    asyncio.create_task(scheduler_loop())

    # Уведомляем администраторов о настройке планировщика
    for admin_id in ADMIN_IDS:
        try:
            daily_next_run = scheduled_tasks['daily_update'].next_run
            next_run_str = daily_next_run.strftime("%Y-%m-%d %H:%M:%S") if daily_next_run else "Not scheduled"
            await bot.send_message(
                admin_id,
                f"⏰ Планировщик задач настроен!\n\n"
                f"Следующее обновление мира: {next_run_str}\n"
                f"Обновление проектов: каждые 4 часа\n"
                f"Случайные события: {len(random_tasks)} в день"
            )
        except Exception as e:
            logger.error(f"Failed to notify admin {admin_id} about scheduler setup: {str(e)}")

async def scheduler_loop():
    """
    Бесконечный цикл для выполнения запланированных задач
    """
    logger.info("Starting scheduler loop")
    while True:
        await schedule.run_pending()
        await asyncio.sleep(1)  # Проверка каждую секунду

def setup_random_events(bot):
    """
    Настраивает случайные события в течение дня

    Args:
        bot: Экземпляр бота для отправки уведомлений
    """
    # Получаем текущий день
    current_day = datetime.now().date()

    # Генерируем от 3 до 7 случайных событий в день
    num_events = random.randint(3, 7)

    # Очищаем предыдущие случайные задачи
    random_tasks.clear()

    # Создаем случайные события
    for i in range(num_events):
        # Генерируем случайное время между 9:00 и 21:00
        hour = random.randint(9, 21)
        minute = random.randint(0, 59)
        event_time = time(hour, minute)

        # Создаем имя события
        event_name = f"random_event_{i}"

        # Запланируем событие
        scheduled_tasks[event_name] = schedule.every().day.at(f"{hour:02d}:{minute:02d}").do(
            lambda: asyncio.create_task(trigger_random_event(bot))
        )

        # Сохраняем информацию о событии
        random_tasks[event_name] = {
            "time": event_time,
            "type": random.choice(["natural_disaster", "diplomatic_incident", "economic_change", "cultural_event"]),
            "scheduled_for": datetime.combine(current_day, event_time)
        }

    logger.info(f"Set up {num_events} random events for today")

async def trigger_random_event(bot):
    """
    Создает и отправляет случайное событие активным игрокам

    Args:
        bot: Экземпляр бота для отправки уведомлений
    """
    try:
        # Получаем список активных игроков
        players = await get_active_players()

        if not players:
            logger.warning("No active players found for random event")
            return

        # Выбираем случайный тип события, если не передан
        event_type = random.choice(["natural_disaster", "diplomatic_incident", "economic_change", "cultural_event"])

        # Получаем случайное событие от LLM (реализовано в daily_update.py)
        from .daily_update import generate_random_event
        event_data = await generate_random_event(event_type)

        if not event_data:
            logger.error("Failed to generate random event")
            return

        # Отправляем событие всем активным игрокам
        for player in players:
            try:
                user_id = player.get('user_id')
                country_name = player.get('country_name', 'Неизвестная страна')

                # Персонализируем событие для каждой страны
                event_impact = await personalize_event_impact(event_data, player)

                # Формируем сообщение
                message_text = (
                    f"🌍 **Случайное событие!**\n\n"
                    f"*{event_data['title']}*\n\n"
                    f"{event_data['description']}\n\n"
                    f"**Влияние на {country_name}:**\n{event_impact['description']}"
                )

                # Если есть изменения в характеристиках, добавляем их
                if event_impact.get('stats_changes'):
                    message_text += "\n\n**Изменения характеристик:**\n"
                    for stat, value in event_impact['stats_changes'].items():
                        direction = "🔼" if value > 0 else "🔽"
                        message_text += f"{direction} {stat.capitalize()}: {value:+.1f}\n"

                # Отправляем сообщение
                await bot.send_message(user_id, message_text)

                # Применяем изменения к характеристикам страны
                if event_impact.get('stats_changes'):
                    from db import update_player_stats
                    await update_player_stats(user_id, **event_impact['stats_changes'])

            except Exception as e:
                logger.error(f"Failed to send random event to player {player.get('user_id')}: {str(e)}")

        # Логируем информацию о событии
        logger.info(f"Triggered random event '{event_data['title']}' for {len(players)} players")

    except Exception as e:
        logger.error(f"Error in trigger_random_event: {str(e)}")

async def personalize_event_impact(event_data, player):
    """
    Персонализирует влияние события на конкретную страну

    Args:
        event_data (dict): Данные о событии
        player (dict): Информация об игроке и его стране

    Returns:
        dict: Персонализированное влияние события
    """
    try:
        # Импортируем функцию для работы с локальной LLM из модуля ai
        from ai import generate_event_impact

        # Получаем информацию о стране
        country_name = player.get('country_name', 'Неизвестная страна')

        # Генерируем персонализированное влияние с помощью LLM
        impact = await generate_event_impact(
            event_type=event_data['type'],
            event_title=event_data['title'],
            event_description=event_data['description'],
            country_name=country_name,
            player_stats=player
        )

        return impact

    except Exception as e:
        logger.error(f"Error personalizing event impact: {str(e)}")
        # Возвращаем шаблонное влияние в случае ошибки
        return {
            "description": "Влияние события неизвестно из-за технических проблем.",
            "stats_changes": {}
        }

async def schedule_task(task_name: str, coroutine_func: Callable[..., Coroutine], delay_seconds: int, *args, **kwargs):
    """
    Планирует выполнение задачи через указанное время

    Args:
        task_name (str): Уникальное имя задачи
        coroutine_func (Callable): Корутина для выполнения
        delay_seconds (int): Задержка в секундах
        *args, **kwargs: Аргументы для передачи в корутину
    """
    logger.info(f"Scheduling task '{task_name}' to run in {delay_seconds} seconds")

    async def delayed_task():
        await asyncio.sleep(delay_seconds)
        try:
            await coroutine_func(*args, **kwargs)
            logger.info(f"Task '{task_name}' completed successfully")
        except Exception as e:
            logger.error(f"Error executing task '{task_name}': {str(e)}")

    # Создаем и запускаем задачу
    task = asyncio.create_task(delayed_task())

    # Сохраняем задачу (при необходимости)
    return task

async def force_run_task(task_name: str, bot):
    """
    Принудительно запускает задачу по имени

    Args:
        task_name (str): Имя задачи для запуска
        bot: Экземпляр бота для отправки уведомлений

    Returns:
        bool: True если задача была запущена, False в противном случае
    """
    logger.info(f"Force running task: {task_name}")

    if task_name == "daily_update":
        asyncio.create_task(process_daily_update(bot))
        return True

    elif task_name == "projects_progress":
        asyncio.create_task(update_projects_progress(bot))
        return True

    elif task_name == "random_event":
        asyncio.create_task(trigger_random_event(bot))
        return True

    else:
        logger.warning(f"Unknown task name: {task_name}")
        return False

# Экспортируем функции
__all__ = [
    'setup_scheduler',
    'scheduler_loop',
    'schedule_task',
    'force_run_task'
]
