"""
economy.py - Модуль для экономических расчетов в игре.
Отвечает за управление ресурсами, торговлей и экономическим развитием стран.
"""

from typing import Dict, List, Any, Optional, Tuple, Union
import re
import json
import random
from datetime import datetime

from config import config
from utils import logger, log_function_call, get_current_game_year
from storage import db, chroma
from ai import model, rag_system, response_parser


class Economy:
    """
    Класс для управления экономическими аспектами стран.
    Предоставляет методы для расчета ресурсов, управления торговлей и экономическим развитием.
    """

    @staticmethod
    @log_function_call
    def extract_resources(user_id: int) -> Dict[str, int]:
        """
        Извлекает информацию о ресурсах страны из описания экономики.

        Args:
            user_id: ID пользователя

        Returns:
            Dict[str, int]: Словарь {ресурс: количество}
        """
        # Получаем описание экономики
        economy_state = db.get_country_state(user_id, "экономика").get("экономика", "")

        # Основные ресурсы древнего мира
        resource_types = [
            "золото", "дерево", "камень", "еда", "зерно", "рабы", "рабочая сила",
            "железо", "медь", "ткани", "специи", "лошади", "скот", "серебро"
        ]

        # Извлекаем ресурсы с помощью регулярных выражений
        resources = {}

        for resource in resource_types:
            # Ищем упоминания ресурсов с числами
            patterns = [
                fr'{resource}[а-я]*\s*[-:]?\s*(\d+)',
                fr'(\d+)\s*{resource}[а-я]*',
                fr'{resource}[а-я]*\s*в\s*количестве\s*(\d+)',
                fr'запас[а-я]*\s*{resource}[а-я]*\s*[-:]?\s*(\d+)'
            ]

            for pattern in patterns:
                matches = re.findall(pattern, economy_state, re.IGNORECASE)
                if matches:
                    for match in matches:
                        try:
                            # Преобразуем в число
                            resources[resource] = max(resources.get(resource, 0), int(match))
                        except ValueError:
                            continue

        # Если не удалось извлечь ресурсы, используем LLM для оценки
        if not resources:
            resources = Economy._estimate_resources_with_llm(user_id, economy_state)

        return resources

    @staticmethod
    @log_function_call
    def _estimate_resources_with_llm(user_id: int, economy_description: str) -> Dict[str, int]:
        """
        Оценивает ресурсы страны с помощью LLM.

        Args:
            user_id: ID пользователя
            economy_description: Описание экономики

        Returns:
            Dict[str, int]: Словарь {ресурс: количество}
        """
        # Получаем информацию о стране
        player_info = db.get_player_info(user_id)
        if not player_info:
            return {}

        country_name = player_info.get('country_name', 'Неизвестная страна')

        # Формируем промпт для LLM
        prompt = f"""Ты - опытный экономист древнего мира, оценивающий ресурсы государства {country_name}.

Вот описание экономики этого государства:
{economy_description}

На основе этого описания оцени доступные ресурсы государства.
Учитывай уровень развития, географическое положение, основные занятия населения и торговые связи.

Ответь в следующем формате:
РЕСУРСЫ:
- золото: [количество]
- дерево: [количество]
- камень: [количество]
- еда: [количество]
- железо: [количество]
- медь: [количество]
- серебро: [количество]
- ткани: [количество]
- специи: [количество]
- рабочая сила: [количество]

Указывай только те ресурсы, которые можно оценить из текста. Количество должно быть реалистичным для древнего мира."""

        # Получаем ответ LLM
        response = model.generate_response(prompt, max_tokens=500, temperature=0.7)

        # Парсим ответ
        resources = {}

        # Ищем секцию с ресурсами
        resources_section = ""
        if "РЕСУРСЫ:" in response:
            resources_section = response.split("РЕСУРСЫ:", 1)[1].strip()

        if resources_section:
            # Ищем строки вида "- ресурс: количество"
            resource_pattern = r"-\s*([^:]+):\s*(\d+)"
            resource_matches = re.findall(resource_pattern, resources_section)

            for resource, amount in resource_matches:
                resource = resource.strip().lower()
                try:
                    resources[resource] = int(amount)
                except ValueError:
                    continue

        return resources

    @staticmethod
    @log_function_call
    def calculate_income_expenses(user_id: int) -> Dict[str, Any]:
        """
        Рассчитывает доходы и расходы страны.

        Args:
            user_id: ID пользователя

        Returns:
            Dict[str, Any]: Словарь с информацией о доходах и расходах
        """
        # Получаем описание экономики
        economy_state = db.get_country_state(user_id, "экономика").get("экономика", "")

        # Извлекаем информацию о доходах и расходах из описания
        income = Economy._extract_income(economy_state)
        expenses = Economy._extract_expenses(economy_state)

        # Если не удалось извлечь, используем LLM для оценки
        if not income or not expenses:
            income, expenses = Economy._estimate_income_expenses_with_llm(user_id, economy_state)

        # Рассчитываем баланс
        balance = income - expenses

        return {
            "income": income,
            "expenses": expenses,
            "balance": balance
        }

    @staticmethod
    @log_function_call
    def _extract_income(economy_description: str) -> int:
        """
        Извлекает информацию о доходах из описания экономики.

        Args:
            economy_description: Описание экономики

        Returns:
            int: Оценка доходов
        """
        # Ищем упоминания доходов
        income_patterns = [
            r'доход[а-я]*\s*[-:]?\s*(\d+)',
            r'прибыль[а-я]*\s*[-:]?\s*(\d+)',
            r'поступлени[а-я]*\s*[-:]?\s*(\d+)',
            r'казна\s*пополняется\s*на\s*(\d+)'
        ]

        for pattern in income_patterns:
            matches = re.findall(pattern, economy_description, re.IGNORECASE)
            if matches:
                for match in matches:
                    try:
                        return int(match)
                    except ValueError:
                        continue

        return 0

    @staticmethod
    @log_function_call
    def _extract_expenses(economy_description: str) -> int:
        """
        Извлекает информацию о расходах из описания экономики.

        Args:
            economy_description: Описание экономики

        Returns:
            int: Оценка расходов
        """
        # Ищем упоминания расходов
        expense_patterns = [
            r'расход[а-я]*\s*[-:]?\s*(\d+)',
            r'затрат[а-я]*\s*[-:]?\s*(\d+)',
            r'трат[а-я]*\s*[-:]?\s*(\d+)',
            r'из\s*казны\s*уходит\s*(\d+)'
        ]

        for pattern in expense_patterns:
            matches = re.findall(pattern, economy_description, re.IGNORECASE)
            if matches:
                for match in matches:
                    try:
                        return int(match)
                    except ValueError:
                        continue

        return 0

    @staticmethod
    @log_function_call
    def _estimate_income_expenses_with_llm(user_id: int, economy_description: str) -> Tuple[int, int]:
        """
        Оценивает доходы и расходы страны с помощью LLM.

        Args:
            user_id: ID пользователя
            economy_description: Описание экономики

        Returns:
            Tuple[int, int]: (доходы, расходы)
        """
        # Получаем информацию о стране
        player_info = db.get_player_info(user_id)
        if not player_info:
            return 0, 0

        country_name = player_info.get('country_name', 'Неизвестная страна')

        # Формируем промпт для LLM
        prompt = f"""Ты - казначей древнего государства {country_name}, отвечающий за финансы.

Вот описание экономики этого государства:
{economy_description}

На основе этого описания оцени годовые доходы и расходы государства в золотых монетах.
Учитывай уровень развития, размер территории, численность населения, торговлю и прочие факторы.

Ответь в следующем формате:
ДОХОДЫ: [сумма в золотых монетах]
РАСХОДЫ: [сумма в золотых монетах]
БАЛАНС: [разница между доходами и расходами]
"""

        # Получаем ответ LLM
        response = model.generate_response(prompt, max_tokens=300, temperature=0.7)

        # Парсим ответ
        income = 0
        expenses = 0

        # Ищем доходы
        income_match = re.search(r"ДОХОДЫ:\s*(\d+)", response)
        if income_match:
            try:
                income = int(income_match.group(1))
            except ValueError:
                pass

        # Ищем расходы
        expenses_match = re.search(r"РАСХОДЫ:\s*(\d+)", response)
        if expenses_match:
            try:
                expenses = int(expenses_match.group(1))
            except ValueError:
                pass

        return income, expenses

    @staticmethod
    @log_function_call
    def update_resources(user_id: int, resource_changes: Dict[str, int]) -> Dict[str, int]:
        """
        Обновляет ресурсы страны на основе изменений.

        Args:
            user_id: ID пользователя
            resource_changes: Словарь {ресурс: изменение}

        Returns:
            Dict[str, int]: Обновленные ресурсы
        """
        # Получаем текущие ресурсы
        current_resources = Economy.extract_resources(user_id)

        # Получаем описание экономики
        economy_state = db.get_country_state(user_id, "экономика").get("экономика", "")

        # Применяем изменения
        updated_resources = current_resources.copy()
        for resource, change in resource_changes.items():
            updated_resources[resource] = max(0, updated_resources.get(resource, 0) + change)

        # Формируем обновленное описание экономики
        updated_economy = Economy._update_economy_description(
            economy_state, current_resources, updated_resources)

        # Сохраняем обновленное описание
        db.save_country_state(user_id, "экономика", updated_economy)

        return updated_resources

    @staticmethod
    @log_function_call
    def _update_economy_description(economy_description: str,
                                    old_resources: Dict[str, int],
                                    new_resources: Dict[str, int]) -> str:
        """
        Обновляет описание экономики на основе изменений ресурсов.

        Args:
            economy_description: Текущее описание экономики
            old_resources: Старые ресурсы
            new_resources: Новые ресурсы

        Returns:
            str: Обновленное описание экономики
        """
        # Создаем копию описания для обновления
        updated_description = economy_description

        # Для каждого ресурса, который изменился
        for resource, new_amount in new_resources.items():
            old_amount = old_resources.get(resource, 0)

            # Если ресурс не изменился, пропускаем
            if new_amount == old_amount:
                continue

            # Шаблоны для поиска упоминаний ресурса
            patterns = [
                fr'{resource}[а-я]*\s*[-:]?\s*\d+',
                fr'\d+\s*{resource}[а-я]*',
                fr'{resource}[а-я]*\s*в\s*количестве\s*\d+',
                fr'запас[а-я]*\s*{resource}[а-я]*\s*[-:]?\s*\d+'
            ]

            # Флаг, указывающий, было ли обновлено описание ресурса
            updated = False

            # Пытаемся обновить существующее упоминание ресурса
            for pattern in patterns:
                if re.search(pattern, updated_description, re.IGNORECASE):
                    # Обновляем все упоминания ресурса
                    for match in re.finditer(pattern, updated_description, re.IGNORECASE):
                        updated_text = match.group(0)
                        # Заменяем число на новое значение
                        updated_text = re.sub(r'\d+', str(new_amount), updated_text)
                        # Обновляем описание
                        updated_description = updated_description[:match.start()] + updated_text + updated_description[match.end():]

                    updated = True
                    break

            # Если ресурс не был найден в описании, добавляем новую информацию
            if not updated:
                if "Ресурсы:" in updated_description:
                    # Если есть секция с ресурсами, добавляем туда
                    updated_description = updated_description.replace(
                        "Ресурсы:", f"Ресурсы:\n{resource}: {new_amount},")
                else:
                    # Иначе добавляем в конец
                    updated_description += f"\n\nРесурсы:\n{resource}: {new_amount}"

        return updated_description

    @staticmethod
    @log_function_call
    def initiate_trade(from_user_id: int, to_user_id: int,
                       offered_resources: Dict[str, int],
                       requested_resources: Dict[str, int]) -> Dict[str, Any]:
        """
        Инициирует торговую сделку между двумя странами.

        Args:
            from_user_id: ID пользователя, предлагающего сделку
            to_user_id: ID пользователя, которому предлагается сделка
            offered_resources: Словарь {ресурс: количество} предлагаемых ресурсов
            requested_resources: Словарь {ресурс: количество} запрашиваемых ресурсов

        Returns:
            Dict[str, Any]: Результаты торговой сделки
        """
        # Получаем информацию о странах
        from_info = db.get_player_info(from_user_id)
        to_info = db.get_player_info(to_user_id)

        if not from_info or not to_info:
            return {"error": "Не удалось получить информацию о странах"}

        from_country = from_info.get('country_name', 'Страна-отправитель')
        to_country = to_info.get('country_name', 'Страна-получатель')

        # Проверяем, есть ли у отправителя предлагаемые ресурсы
        from_resources = Economy.extract_resources(from_user_id)

        for resource, amount in offered_resources.items():
            if from_resources.get(resource, 0) < amount:
                return {
                    "success": False,
                    "message": f"Недостаточно ресурса '{resource}' для торговли"
                }

        # Проверяем, есть ли у получателя запрашиваемые ресурсы
        to_resources = Economy.extract_resources(to_user_id)

        for resource, amount in requested_resources.items():
            if to_resources.get(resource, 0) < amount:
                return {
                    "success": False,
                    "message": f"У получателя недостаточно ресурса '{resource}' для торговли"
                }

        # Оцениваем справедливость сделки
        trade_evaluation = Economy._evaluate_trade(
            offered_resources, requested_resources, from_country, to_country)

        # Если сделка несправедлива, возвращаем результат оценки
        if not trade_evaluation.get("fair", True):
            return {
                "success": False,
                "message": trade_evaluation.get("message", "Несправедливая сделка"),
                "evaluation": trade_evaluation
            }

        # Выполняем обмен ресурсами
        # Отправитель теряет предлагаемые ресурсы и получает запрашиваемые
        from_changes = {}
        for resource, amount in offered_resources.items():
            from_changes[resource] = -amount

        for resource, amount in requested_resources.items():
            from_changes[resource] = from_changes.get(resource, 0) + amount

        # Получатель получает предлагаемые ресурсы и теряет запрашиваемые
        to_changes = {}
        for resource, amount in offered_resources.items():
            to_changes[resource] = amount

        for resource, amount in requested_resources.items():
            to_changes[resource] = to_changes.get(resource, 0) - amount

        # Применяем изменения
        Economy.update_resources(from_user_id, from_changes)
        Economy.update_resources(to_user_id, to_changes)

        # Обновляем описания внешней политики
        Economy._update_diplomacy_after_trade(
            from_user_id, to_user_id, from_country, to_country,
            offered_resources, requested_resources)

        # Формируем результат
        return {
            "success": True,
            "message": "Торговая сделка успешно выполнена",
            "evaluation": trade_evaluation,
            "from_changes": from_changes,
            "to_changes": to_changes
        }

    @staticmethod
    @log_function_call
    def _evaluate_trade(offered_resources: Dict[str, int],
                        requested_resources: Dict[str, int],
                        from_country: str, to_country: str) -> Dict[str, Any]:
        """
        Оценивает справедливость торговой сделки.

        Args:
            offered_resources: Словарь {ресурс: количество} предлагаемых ресурсов
            requested_resources: Словарь {ресурс: количество} запрашиваемых ресурсов
            from_country: Название страны-отправителя
            to_country: Название страны-получателя

        Returns:
            Dict[str, Any]: Результаты оценки
        """
        # Формируем промпт для LLM
        prompt = f"""Ты - опытный торговец древнего мира, оценивающий справедливость торговой сделки.

ТОРГОВАЯ СДЕЛКА:
Государство {from_country} предлагает:
{", ".join([f"{amount} {resource}" for resource, amount in offered_resources.items()])}

Государство {to_country} предлагает:
{", ".join([f"{amount} {resource}" for resource, amount in requested_resources.items()])}

Оцени справедливость этой сделки, учитывая относительную ценность ресурсов в древнем мире.
Золото считается универсальной валютой. Редкие металлы и специи ценятся выше, чем дерево или камень.
Железо ценнее меди. При оценке учитывай также объемы ресурсов.

Ответь в следующем формате:
СПРАВЕДЛИВОСТЬ: [да/нет]
ОЦЕНКА ПРЕДЛОЖЕНИЯ {from_country}: [сумма в золотых монетах]
ОЦЕНКА ПРЕДЛОЖЕНИЯ {to_country}: [сумма в золотых монетах]
РАЗНИЦА: [разница в процентах]
КОММЕНТАРИЙ: [объяснение оценки]
"""

        # Получаем ответ LLM
        response = model.generate_response(prompt, max_tokens=400, temperature=0.7)

        # Парсим ответ
        result = {
            "fair": True,
            "from_value": 0,
            "to_value": 0,
            "difference_percent": 0,
            "message": ""
        }

        # Извлекаем справедливость
        fair_match = re.search(r"СПРАВЕДЛИВОСТЬ:\s*(да|нет)", response, re.IGNORECASE)
        if fair_match:
            result["fair"] = fair_match.group(1).lower() == "да"

        # Извлекаем оценку предложения отправителя
        from_value_match = re.search(r"ОЦЕНКА ПРЕДЛОЖЕНИЯ.*?:\s*(\d+)", response)
        if from_value_match:
            try:
                result["from_value"] = int(from_value_match.group(1))
            except ValueError:
                pass

        # Извлекаем оценку предложения получателя
        to_value_match = re.search(r"ОЦЕНКА ПРЕДЛОЖЕНИЯ.*?:\s*(\d+)", response)
        if to_value_match and to_value_match != from_value_match:
            try:
                result["to_value"] = int(to_value_match.group(1))
            except ValueError:
                pass

        # Извлекаем разницу
        diff_match = re.search(r"РАЗНИЦА:\s*(\d+)", response)
        if diff_match:
            try:
                result["difference_percent"] = int(diff_match.group(1))
            except ValueError:
                pass

        # Извлекаем комментарий
        comment_match = re.search(r"КОММЕНТАРИЙ:\s*(.+?)(?=$)", response, re.DOTALL)
        if comment_match:
            result["message"] = comment_match.group(1).strip()

        return result

    @staticmethod
    @log_function_call
    def _update_diplomacy_after_trade(from_user_id: int, to_user_id: int,
                                      from_country: str, to_country: str,
                                      offered_resources: Dict[str, int],
                                      requested_resources: Dict[str, int]) -> None:
        """
        Обновляет дипломатические отношения после торговой сделки.

        Args:
            from_user_id: ID пользователя-отправителя
            to_user_id: ID пользователя-получателя
            from_country: Название страны-отправителя
            to_country: Название страны-получателя
            offered_resources: Предложенные ресурсы
            requested_resources: Запрошенные ресурсы
        """
        # Формируем описание сделки
        trade_description = f"""
Состоялась торговая сделка между {from_country} и {to_country}.

{from_country} отправил:
{", ".join([f"{amount} {resource}" for resource, amount in offered_resources.items()])}

{to_country} отправил:
{", ".join([f"{amount} {resource}" for resource, amount in requested_resources.items()])}

Сделка успешно завершена.
"""

        # Получаем текущее состояние внешней политики
        from_diplomacy = db.get_country_state(from_user_id, "внешняя политика").get("внешняя политика", "")
        to_diplomacy = db.get_country_state(to_user_id, "внешняя политика").get("внешняя политика", "")

        # Обновляем описания
        from_update = f"Заключена торговая сделка с государством {to_country}. "
        from_update += f"Отправлено: {', '.join([f'{amount} {resource}' for resource, amount in offered_resources.items()])}. "
        from_update += f"Получено: {', '.join([f'{amount} {resource}' for resource, amount in requested_resources.items()])}."

        to_update = f"Заключена торговая сделка с государством {from_country}. "
        to_update += f"Получено: {', '.join([f'{amount} {resource}' for resource, amount in offered_resources.items()])}. "
        to_update += f"Отправлено: {', '.join([f'{amount} {resource}' for resource, amount in requested_resources.items()])}."

        # Генерируем обновленные описания внешней политики
        updated_from_diplomacy = rag_system.update_aspect_state(
            from_user_id, from_country, "внешняя политика", from_diplomacy, from_update)

        updated_to_diplomacy = rag_system.update_aspect_state(
            to_user_id, to_country, "внешняя политика", to_diplomacy, to_update)

        # Сохраняем обновленные описания
        db.save_country_state(from_user_id, "внешняя политика", updated_from_diplomacy)
        db.save_country_state(to_user_id, "внешняя политика", updated_to_diplomacy)

        # Обновляем также экономику, указывая торговые отношения
        from_economy = db.get_country_state(from_user_id, "экономика").get("экономика", "")
        to_economy = db.get_country_state(to_user_id, "экономика").get("экономика", "")

        from_eco_update = f"Установлены торговые отношения с {to_country}."
        to_eco_update = f"Установлены торговые отношения с {from_country}."

        updated_from_economy = rag_system.update_aspect_state(
            from_user_id, from_country, "экономика", from_economy, from_eco_update)

        updated_to_economy = rag_system.update_aspect_state(
            to_user_id, to_country, "экономика", to_economy, to_eco_update)

        db.save_country_state(from_user_id, "экономика", updated_from_economy)
        db.save_country_state(to_user_id, "экономика", updated_to_economy)


# Экспортируем функции для удобного доступа
extract_resources = Economy.extract_resources
calculate_income_expenses = Economy.calculate_income_expenses
update_resources = Economy.update_resources
initiate_trade = Economy.initiate_trade
