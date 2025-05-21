import asyncio
import logging
from typing import Dict, List, Optional, Any
import random
from datetime import datetime, timedelta

from db import (
    get_active_projects,
    update_project_progress,
    complete_project,
    get_player_data,
    update_player_stats,
    add_notification,
    add_player_action,
    save_action_result
)

from ai import (
    generate_project_progress,
    analyze_project_impact,
    generate_innovation_breakthrough
)

from config.config import ADMIN_IDS
from config.game_constants import STATS
from utils.logger import get_logger

logger = get_logger(__name__)

async def update_projects_progress(bot):
    logger.info("Starting projects progress update")

    try:
        projects = await get_active_projects()

        if not projects:
            logger.info("No active projects found for update")
            return

        logger.info(f"Found {len(projects)} active projects for update")

        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(
                    admin_id,
                    f"🔄 Начинается процесс обновления проектов!\n\n"
                    f"Активных проектов: {len(projects)}\n\n"
                    f"Этот процесс может занять некоторое время."
                )
            except Exception as e:
                logger.error(f"Failed to notify admin {admin_id} about projects update: {str(e)}")

        for project in projects:
            try:
                project_id = project.get('id')
                project_name = project.get('name', 'Неизвестный проект')
                project_type = project.get('type', 'general')
                user_id = project.get('user_id')
                current_progress = project.get('progress', 0)
                goal_progress = project.get('goal_progress', 100)

                player = await get_player_data(user_id)

                if not player:
                    logger.warning(f"Project {project_id} ({project_name}) has no valid owner")
                    continue

                progress_data = await generate_project_progress(
                    project_name=project_name,
                    project_type=project_type,
                    current_progress=current_progress,
                    player_stats=player
                )

                progress_increment = progress_data.get('progress_increment', random.randint(5, 15))
                new_progress = min(current_progress + progress_increment, goal_progress)

                await update_project_progress(project_id, new_progress)

                message_text = (
                    f"📊 **Обновление проекта**\n\n"
                    f"*{project_name}*\n\n"
                    f"{progress_data.get('description', 'Проект продвигается.')}\n\n"
                    f"Прогресс: {current_progress}% → {new_progress}% (+{progress_increment}%)"
                )

                if new_progress >= goal_progress:
                    await complete_project(project_id)

                    impact_data = await analyze_project_impact(
                        project_name=project_name,
                        project_type=project_type,
                        player_stats=player
                    )

                    stats_changes = impact_data.get('stats_changes', {})
                    if stats_changes:
                        stats_updates = {}
                        for stat in STATS:
                            if stat in stats_changes:
                                stats_updates[stat] = stats_changes[stat]

                        await update_player_stats(user_id, **stats_updates)

                    message_text += (
                        f"\n\n✅ **Проект успешно завершен!**\n\n"
                        f"{impact_data.get('description', 'Проект успешно реализован.')}\n\n"
                    )

                    if stats_changes:
                        message_text += "**Влияние на характеристики:**\n"
                        for stat in STATS:
                            if stat in stats_changes and stats_changes[stat] != 0:
                                value = stats_changes[stat]
                                direction = "🔼" if value > 0 else "🔽"
                                message_text += f"{direction} {stat.capitalize()}: {value:+.1f}\n"

                    action_id = await add_player_action(
                        user_id=user_id,
                        action_text=f"Завершение проекта '{project_name}'",
                        action_type="project_completion"
                    )

                    await save_action_result(
                        action_id=action_id,
                        result_text=impact_data.get('description', 'Проект успешно реализован.'),
                        stats_impact=stats_changes
                    )

                    if project_type in ['technology', 'research', 'innovation'] and random.random() < 0.3:
                        breakthrough = await generate_innovation_breakthrough(
                            project_name=project_name,
                            player_stats=player
                        )

                        message_text += (
                            f"\n\n🔬 **Технологический прорыв!**\n\n"
                            f"{breakthrough.get('description', 'В ходе исследований произошло неожиданное открытие.')}"
                        )

                        extra_stats = breakthrough.get('stats_changes', {})
                        if extra_stats:
                            message_text += "\n\n**Дополнительное влияние:**\n"
                            for stat in STATS:
                                if stat in extra_stats and extra_stats[stat] != 0:
                                    value = extra_stats[stat]
                                    direction = "🔼" if value > 0 else "🔽"
                                    message_text += f"{direction} {stat.capitalize()}: {value:+.1f}\n"

                            await update_player_stats(user_id, **extra_stats)

                await bot.send_message(user_id, message_text)

                await add_notification(
                    user_id=user_id,
                    title=f"Прогресс проекта '{project_name}'",
                    content=message_text,
                    notification_type="project_update"
                )

                await asyncio.sleep(0.5)

            except Exception as e:
                logger.error(f"Error updating project {project.get('id', 'unknown')}: {str(e)}")

        for admin_id in ADMIN_IDS:
            try:
                completed_projects = sum(1 for p in projects if (p.get('progress', 0) + random.randint(5, 15)) >= p.get('goal_progress', 100))
                await bot.send_message(
                    admin_id,
                    f"✅ Обновление проектов успешно завершено!\n\n"
                    f"Обработано проектов: {len(projects)}\n"
                    f"Завершено проектов: примерно {completed_projects}"
                )
            except Exception as e:
                logger.error(f"Failed to notify admin {admin_id} about projects update completion: {str(e)}")

        logger.info(f"Projects update completed successfully. Processed {len(projects)} projects.")

    except Exception as e:
        logger.error(f"Error in projects update process: {str(e)}")

        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(
                    admin_id,
                    f"❌ Ошибка при выполнении обновления проектов!\n\n"
                    f"Ошибка: {str(e)}\n\n"
                    f"Проверьте логи для получения дополнительной информации."
                )
            except Exception as ex:
                logger.error(f"Failed to notify admin {admin_id} about error: {str(ex)}")

async def create_new_project(user_id: int, project_name: str, project_type: str, project_description: str, duration_days: int = 5) -> Dict[str, Any]:
    from db import create_project

    try:
        player = await get_player_data(user_id)

        if not player:
            logger.warning(f"Cannot create project for non-existent player {user_id}")
            return {"success": False, "error": "Player not found"}

        goal_progress = 100

        goal_progress = goal_progress * duration_days / 5

        relevant_stat = 0
        if project_type in ['technology', 'research', 'innovation']:
            relevant_stat = player.get('технологичность', 50)
        elif project_type in ['economy', 'trade', 'industry']:
            relevant_stat = player.get('экономика', 50)
        elif project_type in ['military', 'defense', 'warfare']:
            relevant_stat = player.get('военное дело', 50)
        elif project_type in ['culture', 'religion', 'arts']:
            relevant_stat = player.get('религия и культура', 50)
        elif project_type in ['infrastructure', 'construction', 'development']:
            relevant_stat = player.get('строительство и инфраструктура', 50)
        else:
            relevant_stat = sum(player.get(stat, 50) for stat in STATS) / len(STATS)

        stat_factor = 1.5 - (relevant_stat / 100)
        goal_progress = max(50, min(250, goal_progress * stat_factor))

        goal_progress = round(goal_progress)

        project_id = await create_project(
            user_id=user_id,
            name=project_name,
            description=project_description,
            type=project_type,
            goal_progress=goal_progress
        )

        return {
            "success": True,
            "project_id": project_id,
            "name": project_name,
            "type": project_type,
            "description": project_description,
            "goal_progress": goal_progress,
            "estimated_days": duration_days,
            "progress": 0
        }

    except Exception as e:
        logger.error(f"Error creating new project: {str(e)}")
        return {"success": False, "error": str(e)}

__all__ = [
    'update_projects_progress',
    'create_new_project'
]
