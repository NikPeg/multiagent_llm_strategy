"""
stats_manager.py - Модуль для управления характеристиками стран.
Отвечает за распределение, изменение и анализ числовых характеристик стран.
"""

from typing import Dict, List, Any, Optional, Tuple, Union
import json
import re
from datetime import datetime

from config import config, STATS, MAX_STAT_VALUE, INITIAL_STAT_VALUE, INITIAL_STAT_POINTS
from utils import logger, log_function_call
from storage import db, chroma
from ai import model, rag_system


class StatsManager:
    """
    Класс для управления характеристиками стран.
    Предоставляет методы для инициализации, изменения и анализа статов.
    """

    @staticmethod
    @log_function_call
    def init_stats(points: int = INITIAL_STAT_POINTS) -> Dict[str, int]:
        """
        Инициализирует базовые характеристики страны с минимальными значениями.

        Args:
            points: Количество очков для распределения

        Returns:
            Dict[str, int]: Словарь с начальными характеристиками
        """
        # Создаем словарь с минимальными значениями для всех характеристик
        stats = {stat.lower(): INITIAL_STAT_VALUE for stat in STATS}

        # Добавляем информацию о доступных очках
        stats['available_points'] = points

        return stats

    @staticmethod
    @log_function_call
    def distribute_points(stats: Dict[str, int], stat_name: str,
                          points_to_add: int = 1) -> Dict[str, int]:
        """
        Распределяет очки в указанную характеристику.

        Args:
            stats: Текущие характеристики
            stat_name: Название характеристики
            points_to_add: Количество очков для добавления

        Returns:
            Dict[str, int]: Обновленные характеристики
        """
        # Нормализуем название характеристики
        stat_name = stat_name.lower()

        # Проверяем, существует ли характеристика
        if stat_name not in stats:
            logger.warning(f"Попытка добавить очки в несуществующую характеристику: {stat_name}")
            return stats

        # Проверяем доступные очки
        available_points = stats.get('available_points', 0)
        if available_points < points_to_add:
            logger.warning(f"Недостаточно очков для распределения: {available_points} < {points_to_add}")
            return stats

        # Проверяем, не превышает ли новое значение максимум
        current_value = stats[stat_name]
        if current_value + points_to_add > MAX_STAT_VALUE:
            logger.warning(f"Попытка превысить максимальное значение характеристики {stat_name}: "
                           f"{current_value} + {points_to_add} > {MAX_STAT_VALUE}")
            points_to_add = MAX_STAT_VALUE - current_value

        # Обновляем значение характеристики и количество доступных очков
        stats[stat_name] += points_to_add
        stats['available_points'] -= points_to_add

        return stats

    @staticmethod
    @log_function_call
    def reset_stats(stats: Dict[str, int]) -> Dict[str, int]:
        """
        Сбрасывает характеристики к начальным значениям.

        Args:
            stats: Текущие характеристики

        Returns:
            Dict[str, int]: Сброшенные характеристики
        """
        # Подсчитываем, сколько очков было распределено
        total_distributed = 0
        for stat in STATS:
            stat_lower = stat.lower()
            if stat_lower in stats:
                total_distributed += stats[stat_lower] - INITIAL_STAT_VALUE

        # Возвращаем начальные значения
        reset_stats = {stat.lower(): INITIAL_STAT_VALUE for stat in STATS}

        # Восстанавливаем доступные очки
        initial_points = stats.get('available_points', 0) + total_distributed
        reset_stats['available_points'] = initial_points

        return reset_stats

    @staticmethod
    @log_function_call
    def validate_stats(stats: Dict[str, int]) -> bool:
        """
        Проверяет корректность характеристик.

        Args:
            stats: Характеристики для проверки

        Returns:
            bool: True, если характеристики корректны, иначе False
        """
        # Проверяем, что все необходимые характеристики присутствуют
        for stat in STATS:
            stat_lower = stat.lower()
            if stat_lower not in stats:
                logger.warning(f"Отсутствует характеристика: {stat_lower}")
                return False

        # Проверяем, что значения в допустимом диапазоне
        for stat, value in stats.items():
            if stat == 'available_points':
                continue

            if not isinstance(value, int):
                logger.warning(f"Значение характеристики {stat} не является целым числом: {value}")
                return False

            if value < INITIAL_STAT_VALUE or value > MAX_STAT_VALUE:
                logger.warning(f"Значение характеристики {stat} вне допустимого диапазона: "
                               f"{value} (должно быть от {INITIAL_STAT_VALUE} до {MAX_STAT_VALUE})")
                return False

        # Проверяем, что сумма очков не превышает допустимую
        total_points = sum(stats[stat.lower()] - INITIAL_STAT_VALUE for stat in STATS)
        available_points = stats.get('available_points', 0)
        expected_total = INITIAL_STAT_POINTS

        if total_points + available_points != expected_total:
            logger.warning(f"Неверная сумма очков: {total_points} + {available_points} != {expected_total}")
            return False

        return True

    @staticmethod
    @log_function_call
    def analyze_stats(user_id: int, stats: Dict[str, int]) -> Dict[str, Any]:
        """
        Анализирует характеристики страны с помощью LLM.

        Args:
            user_id: ID пользователя
            stats: Характеристики страны

        Returns:
            Dict[str, Any]: Результаты анализа
        """
        # Формируем текст характеристик для анализа
        stats_text = "\n".join([f"{stat.capitalize()}: {value}" for stat, value in stats.items()
                                if stat != 'available_points'])

        # Формируем промпт для LLM
        prompt = f"""Ты - мудрый советник в древнем мире, анализирующий сильные и слабые стороны государства.

Вот текущие характеристики государства (по шкале от 1 до 5):
{stats_text}

Проанализируй эти характеристики и определи:
1. Сильные стороны государства (характеристики с высокими значениями)
2. Слабые стороны государства (характеристики с низкими значениями)
3. Общий баланс развития
4. Возможные пути развития

Ответь в следующем формате:
СИЛЬНЫЕ СТОРОНЫ: [перечень сильных сторон]
СЛАБЫЕ СТОРОНЫ: [перечень слабых сторон]
ОБЩИЙ БАЛАНС: [оценка сбалансированности развития]
РЕКОМЕНДАЦИИ: [рекомендации по развитию]
"""

        # Получаем ответ LLM
        response = model.generate_response(prompt, max_tokens=800, temperature=0.7)

        # Парсим результат
        result = {
            "strengths": [],
            "weaknesses": [],
            "balance": "",
            "recommendations": []
        }

        # Ищем секции в ответе
        strengths_match = re.search(r"СИЛЬНЫЕ СТОРОНЫ:\s*(.*?)(?=СЛАБЫЕ СТОРОНЫ:|ОБЩИЙ БАЛАНС:|РЕКОМЕНДАЦИИ:|$)",
                                    response, re.DOTALL)
        if strengths_match:
            strengths_text = strengths_match.group(1).strip()
            result["strengths"] = [strength.strip() for strength in re.split(r'[\n•-]+', strengths_text)
                                   if strength.strip()]

        weaknesses_match = re.search(r"СЛАБЫЕ СТОРОНЫ:\s*(.*?)(?=СИЛЬНЫЕ СТОРОНЫ:|ОБЩИЙ БАЛАНС:|РЕКОМЕНДАЦИИ:|$)",
                                     response, re.DOTALL)
        if weaknesses_match:
            weaknesses_text = weaknesses_match.group(1).strip()
            result["weaknesses"] = [weakness.strip() for weakness in re.split(r'[\n•-]+', weaknesses_text)
                                    if weakness.strip()]

        balance_match = re.search(r"ОБЩИЙ БАЛАНС:\s*(.*?)(?=СИЛЬНЫЕ СТОРОНЫ:|СЛАБЫЕ СТОРОНЫ:|РЕКОМЕНДАЦИИ:|$)",
                                  response, re.DOTALL)
        if balance_match:
            result["balance"] = balance_match.group(1).strip()

        recommendations_match = re.search(r"РЕКОМЕНДАЦИИ:\s*(.*?)(?=СИЛЬНЫЕ СТОРОНЫ:|СЛАБЫЕ СТОРОНЫ:|ОБЩИЙ БАЛАНС:|$)",
                                          response, re.DOTALL)
        if recommendations_match:
            recommendations_text = recommendations_match.group(1).strip()
            result["recommendations"] = [rec.strip() for rec in re.split(r'[\n•-]+', recommendations_text)
                                         if rec.strip()]

        return result

    @staticmethod
    @log_function_call
    def evaluate_stat_changes(old_stats: Dict[str, int], new_stats: Dict[str, int]) -> Dict[str, Dict[str, Any]]:
        """
        Анализирует изменения в характеристиках.

        Args:
            old_stats: Предыдущие характеристики
            new_stats: Новые характеристики

        Returns:
            Dict[str, Dict[str, Any]]: Анализ изменений по каждой характеристике
        """
        changes = {}

        for stat in STATS:
            stat_lower = stat.lower()

            # Пропускаем, если характеристика отсутствует в одном из словарей
            if stat_lower not in old_stats or stat_lower not in new_stats:
                continue

            old_value = old_stats[stat_lower]
            new_value = new_stats[stat_lower]

            # Вычисляем разницу
            diff = new_value - old_value

            # Определяем тип изменения
            change_type = "unchanged"
            if diff > 0:
                change_type = "increased"
            elif diff < 0:
                change_type = "decreased"

            # Добавляем информацию о изменении
            changes[stat_lower] = {
                "old_value": old_value,
                "new_value": new_value,
                "difference": diff,
                "change_type": change_type
            }

        return changes

    @staticmethod
    @log_function_call
    def format_stats_for_display(stats: Dict[str, int]) -> str:
        """
        Форматирует характеристики для отображения игроку.

        Args:
            stats: Характеристики страны

        Returns:
            str: Отформатированная строка с характеристиками
        """
        result = "📊 <b>Характеристики государства:</b>\n\n"

        # Эмодзи для характеристик
        stat_emojis = {
            "экономика": "💰",
            "военное дело": "⚔️",
            "религия и культура": "🏛️",
            "управление и право": "👑",
            "строительство и инфраструктура": "🏗️",
            "внешняя политика": "🌐",
            "общественные отношения": "👥",
            "территория": "🗺️",
            "технологичность": "⚙️"
        }

        # Форматируем каждую характеристику
        for stat in STATS:
            stat_lower = stat.lower()
            if stat_lower in stats:
                value = stats[stat_lower]
                emoji = stat_emojis.get(stat_lower, "📋")
                stars = "★" * value + "☆" * (MAX_STAT_VALUE - value)
                result += f"{emoji} <b>{stat}:</b> {stars} ({value}/{MAX_STAT_VALUE})\n"

        # Добавляем доступные очки, если есть
        if 'available_points' in stats and stats['available_points'] > 0:
            result += f"\n🔄 <b>Доступные очки:</b> {stats['available_points']}"

        return result

    @staticmethod
    @log_function_call
    def calculate_average_stats(stats: Dict[str, int]) -> float:
        """
        Вычисляет среднее значение всех характеристик.

        Args:
            stats: Характеристики страны

        Returns:
            float: Среднее значение характеристик
        """
        values = [stats[stat.lower()] for stat in STATS if stat.lower() in stats]

        if not values:
            return 0.0

        return sum(values) / len(values)

    @staticmethod
    @log_function_call
    def get_effective_stats(user_id: int) -> Dict[str, int]:
        """
        Получает актуальные характеристики страны, рассчитанные на основе
        текстовых описаний аспектов.

        Args:
            user_id: ID пользователя

        Returns:
            Dict[str, int]: Актуальные характеристики
        """
        # Получаем базовые характеристики из БД
        base_stats = db.get_player_stats(user_id)

        # Если есть, используем их
        if base_stats:
            return base_stats

        # Иначе рассчитываем на основе текстовых описаний
        return rag_system.update_country_stats(user_id, "")

    @staticmethod
    @log_function_call
    def save_stats(user_id: int, stats: Dict[str, int]) -> bool:
        """
        Сохраняет характеристики страны.

        Args:
            user_id: ID пользователя
            stats: Характеристики для сохранения

        Returns:
            bool: True, если сохранение успешно, иначе False
        """
        # Создаем копию словаря, исключая служебные ключи
        save_stats = {k: v for k, v in stats.items() if k != 'available_points'}

        # Сохраняем в БД
        return db.save_player_stats(user_id, save_stats)

    @staticmethod
    @log_function_call
    def modify_stat(user_id: int, stat_name: str, change: int) -> Dict[str, int]:
        """
        Изменяет значение указанной характеристики.

        Args:
            user_id: ID пользователя
            stat_name: Название характеристики
            change: Величина изменения (положительная или отрицательная)

        Returns:
            Dict[str, int]: Обновленные характеристики
        """
        # Нормализуем название характеристики
        stat_name = stat_name.lower()

        # Получаем текущие характеристики
        stats = StatsManager.get_effective_stats(user_id)

        # Проверяем, существует ли характеристика
        if stat_name not in stats:
            logger.warning(f"Попытка изменить несуществующую характеристику: {stat_name}")
            return stats

        # Вычисляем новое значение
        current_value = stats[stat_name]
        new_value = current_value + change

        # Ограничиваем диапазоном
        new_value = max(INITIAL_STAT_VALUE, min(new_value, MAX_STAT_VALUE))

        # Обновляем значение
        stats[stat_name] = new_value

        # Сохраняем в БД
        StatsManager.save_stats(user_id, stats)

        return stats


# Экспортируем функции для удобного доступа
init_stats = StatsManager.init_stats
distribute_points = StatsManager.distribute_points
reset_stats = StatsManager.reset_stats
validate_stats = StatsManager.validate_stats
analyze_stats = StatsManager.analyze_stats
format_stats_for_display = StatsManager.format_stats_for_display
get_effective_stats = StatsManager.get_effective_stats
modify_stat = StatsManager.modify_stat
