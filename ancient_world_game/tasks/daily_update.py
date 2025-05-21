import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import random

from storage import (
    get_all_players,
    update_player_stats,
    increment_game_year,
    get_game_year,
    save_yearly_history,
    update_player_resources,
    get_player_data,
    add_notification
)

from ai import (
    generate_yearly_summary,
    generate_country_development,
    analyze_world_situation,
    generate_random_event_description
)

from config.config import ADMIN_IDS
from config.game_constants import STATS
from utils.logger import get_logger

# Инициализация логгера
logger = get_logger(__name__)

async def process_daily_update(bot):
    """
    Обрабатывает ежедневное обновление игрового мира (смена года)

    Args:
        bot: Экземпляр бота для отправки уведомлений
    """
    logger.info("Starting daily update process (year change)")

    try:
        # Получаем текущий игровой год и увеличиваем его
        current_year = await get_game_year()
        new_year = current_year + 1
        await increment_game_year()

        logger.info(f"Game year changed from {current_year} to {new_year}")

        # Получаем список всех активных игроков
        players = await get_all_players(active_only=True)

        if not players:
            logger.warning("No active players found for daily update")
            return

        # Уведомляем администраторов о начале процесса обновления
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(
                    admin_id,
                    f"🔄 Начинается процесс ежедневного обновления!\n\n"
                    f"Игровой год: {current_year} → {new_year}\n"
                    f"Активных игроков: {len(players)}\n\n"
                    f"Этот процесс может занять некоторое время."
                )
            except Exception as e:
                logger.error(f"Failed to notify admin {admin_id} about daily update: {str(e)}")

        # Генерируем общий обзор мировой ситуации с помощью LLM
        world_situation = await analyze_world_situation(players, new_year)

        # Сохраняем исторические данные о мировой ситуации
        await save_yearly_history(new_year, world_situation)

        # Обновляем каждую страну и отправляем уведомления игрокам
        for player in players:
            try:
                # Получаем ID игрока и название страны
                user_id = player.get('user_id')
                country_name = player.get('country_name', 'Неизвестная страна')

                # Генерируем развитие страны за год с помощью LLM
                country_development = await generate_country_development(player, new_year)

                # Обновляем характеристики страны
                stats_changes = country_development.get('stats_changes', {})
                if stats_changes:
                    # Преобразуем изменения в формат для функции update_player_stats
                    stats_updates = {}
                    for stat in STATS:
                        if stat in stats_changes:
                            stats_updates[stat] = stats_changes[stat]

                    # Обновляем статистику игрока
                    await update_player_stats(user_id, **stats_updates)

                # Обновляем ресурсы страны
                resources_changes = country_development.get('resources_changes', {})
                if resources_changes:
                    await update_player_resources(user_id, resources_changes)

                # Генерируем годовой отчет для страны
                yearly_summary = await generate_yearly_summary(
                    country_name=country_name,
                    year=new_year,
                    player_stats=player,
                    world_situation=world_situation,
                    country_development=country_development
                )

                # Отправляем годовой отчет игроку
                message_text = (
                    f"📅 **Наступил новый год: {new_year}!**\n\n"
                    f"*Годовой отчет для {country_name}*\n\n"
                    f"{yearly_summary['summary']}\n\n"
                )

                # Если есть изменения в характеристиках, добавляем их
                if stats_changes:
                    message_text += "**Изменения характеристик:**\n"
                    for stat in STATS:
                        if stat in stats_changes and stats_changes[stat] != 0:
                            value = stats_changes[stat]
                            direction = "🔼" if value > 0 else "🔽"
                            message_text += f"{direction} {stat.capitalize()}: {value:+.1f}\n"
                    message_text += "\n"

                # Если есть изменения в ресурсах, добавляем их
                if resources_changes:
                    message_text += "**Изменения ресурсов:**\n"
                    for resource, value in resources_changes.items():
                        direction = "🔼" if value > 0 else "🔽"
                        message_text += f"{direction} {resource.capitalize()}: {value:+}\n"
                    message_text += "\n"

                # Добавляем информацию о мировой ситуации
                message_text += (
                    f"**Мировая ситуация:**\n"
                    f"{world_situation['summary'][:300]}...\n\n"
                    f"Используйте команду /world для получения полного обзора мировой ситуации."
                )

                # Отправляем сообщение
                await bot.send_message(user_id, message_text)

                # Добавляем запись в уведомления
                await add_notification(
                    user_id=user_id,
                    title=f"Годовой отчет {new_year}",
                    content=message_text,
                    notification_type="yearly_report"
                )

                # Делаем небольшую паузу между отправками
                await asyncio.sleep(0.5)

            except Exception as e:
                logger.error(f"Error processing daily update for player {player.get('user_id')}: {str(e)}")

        # Уведомляем администраторов о завершении процесса
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(
                    admin_id,
                    f"✅ Ежедневное обновление успешно завершено!\n\n"
                    f"Новый игровой год: {new_year}\n"
                    f"Обработано игроков: {len(players)}\n\n"
                    f"Мировая ситуация:\n{world_situation['summary'][:200]}..."
                )
            except Exception as e:
                logger.error(f"Failed to notify admin {admin_id} about daily update completion: {str(e)}")

        logger.info(f"Daily update completed successfully. New game year: {new_year}")

    except Exception as e:
        logger.error(f"Error in daily update process: {str(e)}")

        # Уведомляем администраторов об ошибке
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(
                    admin_id,
                    f"❌ Ошибка при выполнении ежедневного обновления!\n\n"
                    f"Ошибка: {str(e)}\n\n"
                    f"Проверьте логи для получения дополнительной информации."
                )
            except Exception as ex:
                logger.error(f"Failed to notify admin {admin_id} about error: {str(ex)}")

async def generate_random_event(event_type: Optional[str] = None) -> Dict[str, Any]:
    """
    Генерирует случайное событие определенного типа с помощью LLM

    Args:
        event_type (str, optional): Тип события. Если не указан, выбирается случайно.

    Returns:
        Dict[str, Any]: Данные о случайном событии
    """
    # Если тип события не указан, выбираем случайно
    if not event_type:
        event_type = random.choice([
            "natural_disaster",  # Природное бедствие
            "diplomatic_incident",  # Дипломатический инцидент
            "economic_change",  # Экономическое изменение
            "cultural_event",  # Культурное событие
            "technological_breakthrough"  # Технологический прорыв
        ])

    try:
        # Получаем текущий игровой год
        game_year = await get_game_year()

        # Генерируем описание события с помощью LLM
        event_description = await generate_random_event_description(event_type, game_year)

        # Формируем и возвращаем данные о событии
        return {
            "type": event_type,
            "title": event_description.get("title", "Случайное событие"),
            "description": event_description.get("description", "Произошло неожиданное событие."),
            "year": game_year
        }

    except Exception as e:
        logger.error(f"Error generating random event: {str(e)}")
        return {
            "type": event_type,
            "title": "Неизвестное событие",
            "description": "Произошло событие, но детали недоступны из-за технических проблем.",
            "year": await get_game_year()
        }

# Экспортируем функции
__all__ = [
    'process_daily_update',
    'generate_random_event'
]
