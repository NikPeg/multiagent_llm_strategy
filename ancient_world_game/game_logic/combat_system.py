"""
combat_system.py - Система боевых действий для игры.
Отвечает за обработку военных конфликтов между странами.
"""

from typing import Dict, List, Any, Optional, Tuple, Union
import random
import json
import re
from datetime import datetime
import uuid

from config import config
from utils import logger, log_function_call, get_current_game_year
from storage import db, chroma
from ai import model, rag_system, response_parser


class CombatSystem:
    """
    Класс для обработки военных конфликтов между странами.
    Предоставляет методы для расчета исходов сражений и войн.
    """

    @staticmethod
    @log_function_call
    def initiate_conflict(attacker_id: int, defender_id: int,
                          attack_type: str, description: str) -> Dict[str, Any]:
        """
        Инициирует военный конфликт между двумя странами.

        Args:
            attacker_id: ID атакующего пользователя
            defender_id: ID обороняющегося пользователя
            attack_type: Тип атаки (полное нападение, рейд, осада и т.д.)
            description: Описание атаки от игрока

        Returns:
            Dict[str, Any]: Результаты конфликта
        """
        # Получаем информацию о странах
        attacker_info = db.get_player_info(attacker_id)
        defender_info = db.get_player_info(defender_id)

        if not attacker_info or not defender_info:
            return {"error": "Не удалось получить информацию о странах"}

        attacker_name = attacker_info.get('country_name', 'Атакующая страна')
        defender_name = defender_info.get('country_name', 'Обороняющаяся страна')

        # Получаем дополнительный контекст о странах
        attacker_context = rag_system.get_country_context(attacker_id, "военное дело армия")
        defender_context = rag_system.get_country_context(defender_id, "военное дело оборона")

        # Рассчитываем военную мощь сторон
        attacker_power = CombatSystem._calculate_military_power(attacker_id)
        defender_power = CombatSystem._calculate_military_power(defender_id)

        # Генерируем результат конфликта
        conflict_result = CombatSystem._generate_conflict_result(
            attacker_name, defender_name,
            attack_type, description,
            attacker_context, defender_context,
            attacker_power, defender_power
        )

        # Применяем результаты к странам
        attacker_changes = CombatSystem._apply_conflict_results(
            attacker_id, attacker_name, conflict_result, "attacker")
        defender_changes = CombatSystem._apply_conflict_results(
            defender_id, defender_name, conflict_result, "defender")

        # Сохраняем информацию о конфликте
        conflict_id = CombatSystem._save_conflict(
            attacker_id, defender_id, conflict_result)

        # Форматируем итоговый результат
        result = {
            "conflict_id": conflict_id,
            "attacker": {
                "id": attacker_id,
                "name": attacker_name,
                "power": attacker_power,
                "changes": attacker_changes
            },
            "defender": {
                "id": defender_id,
                "name": defender_name,
                "power": defender_power,
                "changes": defender_changes
            },
            "type": attack_type,
            "description": description,
            "result": conflict_result.get("result", ""),
            "battle_description": conflict_result.get("battle_description", ""),
            "casualties": conflict_result.get("casualties", {}),
            "aftermath": conflict_result.get("aftermath", ""),
            "timestamp": datetime.now().isoformat(),
            "game_year": get_current_game_year()
        }

        return result

    @staticmethod
    @log_function_call
    def _calculate_military_power(user_id: int) -> Dict[str, Any]:
        """
        Рассчитывает военную мощь страны.

        Args:
            user_id: ID пользователя

        Returns:
            Dict[str, Any]: Информация о военной мощи
        """
        # Получаем характеристики страны
        stats = db.get_player_stats(user_id)

        # Базовая военная мощь на основе характеристики "военное дело"
        base_power = stats.get("военное дело", 1)

        # Получаем контекст о военном деле страны
        military_context = rag_system.get_country_context(user_id, "военное дело армия оружие")

        # Находим упоминания о численности войск
        troop_count = CombatSystem._extract_troop_count(military_context)

        # Определяем типы войск и их количество
        troop_types = CombatSystem._extract_troop_types(military_context)

        # Определяем наличие укреплений для защиты
        fortifications = CombatSystem._extract_fortifications(military_context)

        # Рассчитываем итоговую мощь
        total_power = base_power

        # Модификатор от численности войск (больше войск - больше мощь)
        if troop_count > 0:
            troop_modifier = min(3, max(0.5, troop_count / 10000))
            total_power *= troop_modifier

        # Модификатор от разнообразия войск (более разнообразные войска дают преимущество)
        unit_diversity_modifier = min(1.5, max(0.8, len(troop_types) / 3))
        total_power *= unit_diversity_modifier

        # Модификатор от укреплений (только для обороны, учитывается позже)

        return {
            "base_power": base_power,
            "troop_count": troop_count,
            "troop_types": troop_types,
            "fortifications": fortifications,
            "total_power": total_power
        }

    @staticmethod
    @log_function_call
    def _extract_troop_count(military_context: str) -> int:
        """
        Извлекает информацию о численности войск из текста.

        Args:
            military_context: Текст с информацией о военном деле

        Returns:
            int: Оценка численности войск
        """
        # Ищем упоминания чисел рядом с ключевыми словами
        troop_patterns = [
            r'(\d+[\.,]?\d*) (?:тысяч|тысячи) (?:воин|солдат|человек)',
            r'армия (?:численностью|размером) (?:в )?(\d+[\.,]?\d*) (?:тысяч|тысячи)',
            r'(\d+[\.,]?\d*) (?:воин|солдат|человек)',
            r'войско (?:численностью|размером) (?:в )?(\d+[\.,]?\d*)'
        ]

        for pattern in troop_patterns:
            matches = re.findall(pattern, military_context, re.IGNORECASE)
            if matches:
                for match in matches:
                    try:
                        # Преобразуем в число
                        count = float(match.replace(',', '.'))

                        # Если число с "тысяч", умножаем на 1000
                        if "тысяч" in pattern:
                            count *= 1000

                        return int(count)
                    except ValueError:
                        continue

        # Если не удалось найти конкретное число, оцениваем на основе ключевых слов
        small_army_keywords = ["небольшое войско", "малочисленная армия", "горстка воинов"]
        medium_army_keywords = ["значительные силы", "существенное войско", "армия"]
        large_army_keywords = ["огромное войско", "многочисленная армия", "великая армия"]

        if any(keyword in military_context.lower() for keyword in large_army_keywords):
            return 30000
        elif any(keyword in military_context.lower() for keyword in medium_army_keywords):
            return 10000
        elif any(keyword in military_context.lower() for keyword in small_army_keywords):
            return 3000

        # По умолчанию - небольшое войско
        return 5000

    @staticmethod
    @log_function_call
    def _extract_troop_types(military_context: str) -> Dict[str, int]:
        """
        Извлекает информацию о типах войск из текста.

        Args:
            military_context: Текст с информацией о военном деле

        Returns:
            Dict[str, int]: Словарь {тип войск: относительное количество}
        """
        # Типы войск и соответствующие ключевые слова
        troop_types = {
            "пехота": ["пехот", "пеш", "гоплит", "легионер", "копейщик"],
            "лучники": ["лучник", "стрел", "стрельц"],
            "кавалерия": ["кавалер", "конниц", "всадник", "конный"],
            "колесницы": ["колесниц"],
            "осадные орудия": ["осадн", "катапульт", "баллист", "таран"],
            "флот": ["флот", "корабл", "судн", "лодк", "галер", "триер"]
        }

        # Результаты
        found_types = {}

        # Ищем упоминания типов войск
        for troop_type, keywords in troop_types.items():
            for keyword in keywords:
                if keyword in military_context.lower():
                    # Пытаемся найти число рядом с ключевым словом
                    number_pattern = r'(\d+)[\s\-]*' + keyword
                    matches = re.findall(number_pattern, military_context.lower())

                    if matches:
                        # Если найдено число, используем его
                        try:
                            found_types[troop_type] = int(matches[0])
                        except ValueError:
                            found_types[troop_type] = 1
                    else:
                        # Если число не найдено, просто отмечаем наличие
                        found_types[troop_type] = 1

                    break

        return found_types

    @staticmethod
    @log_function_call
    def _extract_fortifications(military_context: str) -> Dict[str, int]:
        """
        Извлекает информацию об укреплениях из текста.

        Args:
            military_context: Текст с информацией о военном деле и инфраструктуре

        Returns:
            Dict[str, int]: Словарь {тип укрепления: уровень (1-5)}
        """
        # Типы укреплений и соответствующие ключевые слова
        fortification_types = {
            "стены": ["стен", "городск стен", "оборонительн стен"],
            "башни": ["башн", "сторожев башн", "оборонительн башн"],
            "ров": ["ров", "оборонительный ров", "водный ров"],
            "крепость": ["крепост", "цитадел", "форт", "замок"],
            "валы": ["вал", "земляной вал", "оборонительный вал"]
        }

        # Модификаторы для оценки уровня укреплений
        strength_modifiers = {
            "мощн": 1.5,
            "крепк": 1.3,
            "сильн": 1.2,
            "высок": 1.2,
            "неприступн": 2.0,
            "слаб": 0.7,
            "низк": 0.8,
            "ветх": 0.5,
            "разрушающ": 0.3
        }

        # Результаты
        found_fortifications = {}

        # Ищем упоминания укреплений
        for fort_type, keywords in fortification_types.items():
            base_level = 0

            for keyword in keywords:
                if keyword in military_context.lower():
                    # Находим уровень укрепления (базовый уровень + модификаторы)
                    base_level = 3  # Базовый уровень по умолчанию

                    # Определяем контекст вокруг упоминания укрепления
                    context_pattern = r'.{0,50}' + keyword + r'.{0,50}'
                    contexts = re.findall(context_pattern, military_context.lower())

                    for context in contexts:
                        # Применяем модификаторы на основе качественных характеристик
                        for modifier_word, modifier_value in strength_modifiers.items():
                            if modifier_word in context:
                                base_level *= modifier_value

                    break

            # Если найдено укрепление, добавляем его в результаты
            if base_level > 0:
                # Ограничиваем уровень диапазоном от 1 до 5
                found_fortifications[fort_type] = max(1, min(5, round(base_level)))

        return found_fortifications

    @staticmethod
    @log_function_call
    def _generate_conflict_result(attacker_name: str, defender_name: str,
                                  attack_type: str, description: str,
                                  attacker_context: str, defender_context: str,
                                  attacker_power: Dict[str, Any],
                                  defender_power: Dict[str, Any]) -> Dict[str, Any]:
        """
        Генерирует результат военного конфликта с помощью LLM.

        Args:
            attacker_name: Название атакующей страны
            defender_name: Название обороняющейся страны
            attack_type: Тип атаки
            description: Описание атаки от игрока
            attacker_context: Контекст об атакующей стране
            defender_context: Контекст о обороняющейся стране
            attacker_power: Информация о военной мощи атакующей страны
            defender_power: Информация о военной мощи обороняющейся страны

        Returns:
            Dict[str, Any]: Результаты конфликта
        """
        # Формируем промпт для LLM
        prompt = f"""Ты - летописец древнего мира, описывающий военный конфликт между двумя государствами.

АТАКУЮЩЕЕ ГОСУДАРСТВО: {attacker_name}
Военная мощь: {attacker_power['total_power']:.2f} из 10
Численность войск: примерно {attacker_power['troop_count']}
Типы войск: {', '.join(attacker_power['troop_types'].keys())}

ОБОРОНЯЮЩЕЕСЯ ГОСУДАРСТВО: {defender_name}
Военная мощь: {defender_power['total_power']:.2f} из 10
Численность войск: примерно {defender_power['troop_count']}
Типы войск: {', '.join(defender_power['troop_types'].keys())}
Укрепления: {', '.join(defender_power['fortifications'].keys()) if defender_power['fortifications'] else 'отсутствуют'}

ТИП АТАКИ: {attack_type}
ОПИСАНИЕ: {description}

Дополнительная информация об атакующем государстве:
{attacker_context}

Дополнительная информация о обороняющемся государстве:
{defender_context}

Опиши исход этого военного конфликта, учитывая соотношение сил, тип атаки и особенности обеих сторон.
Исход должен быть реалистичным и соответствовать данным о военной мощи.

Ответь в следующем формате:
РЕЗУЛЬТАТ: [краткий результат конфликта - победа атакующего/обороняющегося или ничья]
ОПИСАНИЕ БИТВЫ: [подробное описание хода сражения]
ПОТЕРИ: [описание потерь с обеих сторон]
ПОСЛЕДСТВИЯ: [политические и экономические последствия конфликта]
ВЛИЯНИЕ НА АТАКУЮЩЕГО:
- военное дело: [изменения]
- экономика: [изменения]
- [другие затронутые аспекты]
ВЛИЯНИЕ НА ОБОРОНЯЮЩЕГОСЯ:
- военное дело: [изменения]
- экономика: [изменения]
- [другие затронутые аспекты]
"""

        # Получаем ответ LLM
        response = model.generate_response(prompt, max_tokens=1200, temperature=0.7)

        # Парсим результат
        result = {}

        # Извлекаем основной результат
        result_match = re.search(r"РЕЗУЛЬТАТ:\s*(.+?)(?=\n|$)", response, re.DOTALL)
        if result_match:
            result["result"] = result_match.group(1).strip()

        # Извлекаем описание битвы
        battle_match = re.search(r"ОПИСАНИЕ БИТВЫ:\s*(.+?)(?=\nПОТЕРИ:|$)", response, re.DOTALL)
        if battle_match:
            result["battle_description"] = battle_match.group(1).strip()

        # Извлекаем потери
        losses_match = re.search(r"ПОТЕРИ:\s*(.+?)(?=\nПОСЛЕДСТВИЯ:|$)", response, re.DOTALL)
        if losses_match:
            result["casualties"] = losses_match.group(1).strip()

        # Извлекаем последствия
        aftermath_match = re.search(r"ПОСЛЕДСТВИЯ:\s*(.+?)(?=\nВЛИЯНИЕ НА АТАКУЮЩЕГО:|$)", response, re.DOTALL)
        if aftermath_match:
            result["aftermath"] = aftermath_match.group(1).strip()

        # Извлекаем влияние на атакующего
        attacker_effects = {}
        attacker_section_match = re.search(r"ВЛИЯНИЕ НА АТАКУЮЩЕГО:(.*?)(?=ВЛИЯНИЕ НА ОБОРОНЯЮЩЕГОСЯ:|$)",
                                           response, re.DOTALL)
        if attacker_section_match:
            attacker_section = attacker_section_match.group(1).strip()
            effect_pattern = r"-\s*([^:]+):\s*(.+?)(?=\n-|\n\n|$)"
            effects = re.findall(effect_pattern, attacker_section, re.DOTALL)

            for aspect, effect in effects:
                attacker_effects[aspect.strip().lower()] = effect.strip()

        result["attacker_effects"] = attacker_effects

        # Извлекаем влияние на обороняющегося
        defender_effects = {}
        defender_section_match = re.search(r"ВЛИЯНИЕ НА ОБОРОНЯЮЩЕГОСЯ:(.*?)(?=$)",
                                           response, re.DOTALL)
        if defender_section_match:
            defender_section = defender_section_match.group(1).strip()
            effect_pattern = r"-\s*([^:]+):\s*(.+?)(?=\n-|\n\n|$)"
            effects = re.findall(effect_pattern, defender_section, re.DOTALL)

            for aspect, effect in effects:
                defender_effects[aspect.strip().lower()] = effect.strip()

        result["defender_effects"] = defender_effects

        return result

    @staticmethod
    @log_function_call
    def _apply_conflict_results(user_id: int, country_name: str,
                                conflict_result: Dict[str, Any], role: str) -> Dict[str, str]:
        """
        Применяет результаты конфликта к стране.

        Args:
            user_id: ID пользователя
            country_name: Название страны
            conflict_result: Результаты конфликта
            role: Роль страны ("attacker" или "defender")

        Returns:
            Dict[str, str]: Внесенные изменения
        """
        # Определяем, какие эффекты применять
        effects = conflict_result.get(f"{role}_effects", {})

        # Отслеживаем внесенные изменения
        changes = {}

        # Применяем изменения к каждому затронутому аспекту
        for aspect, effect in effects.items():
            # Нормализуем название аспекта
            aspect = aspect.lower().strip()

            # Получаем текущее описание аспекта
            current_description = db.get_country_state(user_id, aspect).get(aspect, "")

            # Генерируем обновленное описание
            updated_description = rag_system.update_aspect_state(
                user_id, country_name, aspect, current_description, effect)

            # Сохраняем обновленное описание
            db.save_country_state(user_id, aspect, updated_description)

            # Отмечаем изменение
            changes[aspect] = effect

        return changes

    @staticmethod
    @log_function_call
    def _save_conflict(attacker_id: int, defender_id: int,
                       conflict_result: Dict[str, Any]) -> str:
        """
        Сохраняет информацию о конфликте.

        Args:
            attacker_id: ID атакующего пользователя
            defender_id: ID обороняющегося пользователя
            conflict_result: Результаты конфликта

        Returns:
            str: ID конфликта
        """
        # Генерируем уникальный ID конфликта
        conflict_id = str(uuid.uuid4())

        # Создаем запись о конфликте
        conflict_data = {
            "id": conflict_id,
            "attacker_id": attacker_id,
            "defender_id": defender_id,
            "result": conflict_result.get("result", ""),
            "battle_description": conflict_result.get("battle_description", ""),
            "casualties": conflict_result.get("casualties", ""),
            "aftermath": conflict_result.get("aftermath", ""),
            "timestamp": datetime.now().isoformat(),
            "game_year": get_current_game_year()
        }

        # TODO: Сохранение конфликта в базу данных
        # В текущей версии мы не имеем отдельной таблицы для конфликтов,
        # поэтому просто возвращаем ID. В полной реализации здесь будет
        # сохранение в соответствующую таблицу.

        return conflict_id

    @staticmethod
    @log_function_call
    def get_conflict_details(conflict_id: str) -> Optional[Dict[str, Any]]:
        """
        Получает детальную информацию о конфликте.

        Args:
            conflict_id: ID конфликта

        Returns:
            Optional[Dict[str, Any]]: Информация о конфликте или None, если не найден
        """
        # TODO: Загрузка информации о конфликте из базы данных
        # В текущей версии мы не имеем отдельной таблицы для конфликтов,
        # поэтому возвращаем None. В полной реализации здесь будет
        # загрузка из соответствующей таблицы.

        return None

    @staticmethod
    @log_function_call
    def get_country_conflicts(user_id: int, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Получает список конфликтов страны.

        Args:
            user_id: ID пользователя
            limit: Максимальное количество конфликтов для возврата

        Returns:
            List[Dict[str, Any]]: Список конфликтов
        """
        # TODO: Загрузка списка конфликтов из базы данных
        # В текущей версии мы не имеем отдельной таблицы для конфликтов,
        # поэтому возвращаем пустой список. В полной реализации здесь будет
        # загрузка из соответствующей таблицы.

        return []


# Экспортируем функции для удобного доступа
initiate_conflict = CombatSystem.initiate_conflict
get_conflict_details = CombatSystem.get_conflict_details
get_country_conflicts = CombatSystem.get_country_conflicts
