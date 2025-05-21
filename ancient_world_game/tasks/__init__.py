from aiogram import Bot
import asyncio
import logging

from .scheduler import setup_scheduler, force_run_task, schedule_task
from .daily_update import process_daily_update, generate_random_event
from .projects_progress import update_projects_progress, create_new_project

from utils.logger import get_logger

# Инициализация логгера
logger = get_logger(__name__)

async def initialize_tasks(bot: Bot):
    """
    Инициализирует все задачи и планировщик

    Args:
        bot: Экземпляр бота для отправки уведомлений
    """
    logger.info("Initializing tasks module")

    try:
        # Настраиваем планировщик задач
        await setup_scheduler(bot)
        logger.info("Scheduler has been initialized")

        return True
    except Exception as e:
        logger.error(f"Error initializing tasks module: {str(e)}")
        return False

async def run_immediate_task(task_name: str, bot: Bot):
    """
    Запускает указанную задачу немедленно

    Args:
        task_name: Имя задачи для запуска
        bot: Экземпляр бота для отправки уведомлений

    Returns:
        bool: True если задача запущена успешно, False в противном случае
    """
    logger.info(f"Requesting immediate execution of task: {task_name}")

    try:
        result = await force_run_task(task_name, bot)
        return result
    except Exception as e:
        logger.error(f"Error running immediate task {task_name}: {str(e)}")
        return False

async def schedule_delayed_task(task_name: str, delay_seconds: int, bot: Bot):
    """
    Планирует выполнение задачи через указанное время

    Args:
        task_name: Имя задачи для запуска
        delay_seconds: Задержка в секундах
        bot: Экземпляр бота для отправки уведомлений

    Returns:
        bool: True если задача запланирована успешно, False в противном случае
    """
    logger.info(f"Scheduling delayed task {task_name} in {delay_seconds} seconds")

    try:
        # Определяем функцию для выполнения в зависимости от имени задачи
        task_function = None

        if task_name == "daily_update":
            task_function = process_daily_update
        elif task_name == "projects_progress":
            task_function = update_projects_progress
        elif task_name == "random_event":
            task_function = lambda bot: generate_random_event()
        else:
            logger.warning(f"Unknown task name for delayed execution: {task_name}")
            return False

        # Планируем задачу
        task = await schedule_task(task_name, task_function, delay_seconds, bot)
        return True
    except Exception as e:
        logger.error(f"Error scheduling delayed task {task_name}: {str(e)}")
        return False

# Экспортируем функции
__all__ = [
    'initialize_tasks',
    'run_immediate_task',
    'schedule_delayed_task',
    'process_daily_update',
    'update_projects_progress',
    'create_new_project',
    'generate_random_event'
]
