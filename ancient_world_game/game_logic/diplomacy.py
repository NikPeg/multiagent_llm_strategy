"""
diplomacy.py - Модуль для управления дипломатическими отношениями между странами.
Отвечает за договоры, союзы, вассалитеты и взаимодействие между государствами.
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


class Diplomacy:
    """
    Класс для управления дипломатическими отношениями между странами.
    Предоставляет методы для заключения договоров, создания союзов и управления взаимоотношениями.
    """

    # Типы дипломатических отношений
    RELATION_TYPES = {
        "война": -3,          # Открытый военный конфликт
        "враждебные": -2,      # Сильная неприязнь, возможны провокации
        "напряженные": -1,     # Нестабильные отношения, риск конфликта
        "нейтральные": 0,      # Отсутствие явных предпочтений
        "дружественные": 1,    # Позитивные отношения, возможна кооперация
        "союзные": 2,          # Формальный союз, военная/экономическая помощь
        "вассальные": 3        # Подчиненное положение одного государства другому
    }

    @staticmethod
    @log_function_call
    def get_relations(user_id: int) -> Dict[int, Dict[str, Any]]:
        """
        Получает информацию о дипломатических отношениях страны со всеми другими странами.

        Args:
            user_id: ID пользователя

        Returns:
            Dict[int, Dict[str, Any]]: Словарь {ID страны: информация о отношениях}
        """
        # Получаем описание внешней политики
        diplomacy_state = db.get_country_state(user_id, "внешняя политика").get("внешняя политика", "")

        # Получаем информацию о всех странах
        all_players = db.get_all_players()

        # Словарь для хранения результатов
        relations = {}

        # Для каждой страны (кроме текущей) определяем тип отношений
        for player in all_players:
            other_id = player.get('user_id')

            # Пропускаем текущего пользователя
            if other_id == user_id:
                continue

            country_name = player.get('country_name', 'Неизвестная страна')

            # Определяем тип отношений
            relation_type, relation_details = Diplomacy._extract_relation_with_country(
                diplomacy_state, country_name)

            # Добавляем в результаты
            relations[other_id] = {
                "country_name": country_name,
                "relation_type": relation_type,
                "relation_value": Diplomacy.RELATION_TYPES.get(relation_type, 0),
                "details": relation_details
            }

        return relations

    @staticmethod
    @log_function_call
    def _extract_relation_with_country(diplomacy_text: str, country_name: str) -> Tuple[str, str]:
        """
        Извлекает информацию о типе отношений с конкретной страной из текста.

        Args:
            diplomacy_text: Текст внешней политики
            country_name: Название страны

        Returns:
            Tuple[str, str]: (тип отношений, детали отношений)
        """
        # Ищем упоминания страны в тексте
        country_pattern = fr"(?i){re.escape(country_name)}"
        if not re.search(country_pattern, diplomacy_text):
            return "нейтральные", "Нет явных отношений"

        # Извлекаем контекст вокруг упоминания страны
        context_pattern = fr".{{0,200}}{country_pattern}.{{0,200}}"
        contexts = re.findall(context_pattern, diplomacy_text)

        if not contexts:
            return "нейтральные", "Нет явных отношений"

        # Объединяем все контексты
        combined_context = " ".join(contexts)

        # Ищем ключевые слова, указывающие на тип отношений
        relation_keywords = {
            "война": ["война", "военн конфликт", "воюем", "в состоянии войны"],
            "враждебные": ["враждебн", "неприязн", "угроз", "противник", "недруг"],
            "напряженные": ["напряжен", "нестабильн", "проблемн", "ухудш", "осложн"],
            "нейтральные": ["нейтрал", "безразлич", "равнодуш", "отсутств отношен"],
            "дружественные": ["дружествен", "дружб", "хорош отношен", "добрососед", "сотруднич"],
            "союзные": ["союз", "альянс", "соглашени", "договор о взаимопомощи", "военный пакт"],
            "вассальные": ["вассал", "сюзерен", "подчинен", "данник", "зависим"]
        }

        # Определяем тип отношений по наличию ключевых слов
        found_relation = "нейтральные"
        highest_value = -1000  # Для отслеживания "силы" найденной связи

        for relation_type, keywords in relation_keywords.items():
            for keyword in keywords:
                if keyword.lower() in combined_context.lower():
                    relation_value = Diplomacy.RELATION_TYPES.get(relation_type, 0)
                    if relation_value > highest_value:
                        found_relation = relation_type
                        highest_value = relation_value

        return found_relation, combined_context

    @staticmethod
    @log_function_call
    def change_relations(user_id: int, other_user_id: int,
                         new_relation_type: str, description: str = "") -> Dict[str, Any]:
        """
        Изменяет дипломатические отношения между двумя странами.

        Args:
            user_id: ID пользователя, инициирующего изменение
            other_user_id: ID другого пользователя
            new_relation_type: Новый тип отношений
            description: Дополнительное описание

        Returns:
            Dict[str, Any]: Результаты изменения отношений
        """
        # Проверяем, существует ли указанный тип отношений
        if new_relation_type not in Diplomacy.RELATION_TYPES:
            return {
                "success": False,
                "message": f"Неизвестный тип отношений: {new_relation_type}"
            }

        # Получаем информацию о странах
        from_info = db.get_player_info(user_id)
        to_info = db.get_player_info(other_user_id)

        if not from_info or not to_info:
            return {
                "success": False,
                "message": "Не удалось получить информацию о странах"
            }

        from_country = from_info.get('country_name', 'Инициатор')
        to_country = to_info.get('country_name', 'Цель')

        # Получаем текущие отношения
        relations = Diplomacy.get_relations(user_id)
        current_relation = "нейтральные"
        if other_user_id in relations:
            current_relation = relations[other_user_id].get("relation_type", "нейтральные")

        # Если отношения не меняются, просто возвращаем успех
        if current_relation == new_relation_type:
            return {
                "success": True,
                "message": f"Отношения с {to_country} уже {new_relation_type}"
            }

        # Формируем описание изменения отношений
        relation_change_description = description
        if not relation_change_description:
            relation_change_description = f"Отношения с государством {to_country} изменились с '{current_relation}' на '{new_relation_type}'."

        # Обновляем описания внешней политики обеих стран
        success_from = Diplomacy._update_diplomatic_description(
            user_id, from_country, to_country, new_relation_type, relation_change_description)

        # Для второй страны меняем направление отношений (вассал->сюзерен, и т.д.)
        reciprocal_relation = Diplomacy._get_reciprocal_relation(new_relation_type)
        reciprocal_description = f"Отношения с государством {from_country} изменились с '{current_relation}' на '{reciprocal_relation}'."

        success_to = Diplomacy._update_diplomatic_descriptionuser_id, to_country, from_country, reciprocal_relation, reciprocal_description)

        if not success_from or not success_to:
            return {
                "success": False,
                "message": "Не удалось обновить информацию о дипломатических отношениях"
            }

        return {
            "success": True,
            "message": f"Отношения с {to_country} изменены на '{new_relation_type}'",
            "from_country": from_country,
            "to_country": to_country,
            "previous_relation": current_relation,
            "new_relation": new_relation_type,
            "reciprocal_relation": reciprocal_relation
        }

    @staticmethod
    @log_function_call
    def _update_diplomatic_description(user_id: int, country_name: str,
                                       other_country: str, relation_type: str,
                                       change_description: str) -> bool:
        """
        Обновляет описание внешней политики страны.

        Args:
            user_id: ID пользователя
            country_name: Название страны
            other_country: Название другой страны
            relation_type: Тип отношений
            change_description: Описание изменения

        Returns:
            bool: True, если обновление успешно, иначе False
        """
        # Получаем текущее описание внешней политики
        diplomacy_state = db.get_country_state(user_id, "внешняя политика").get("внешняя политика", "")

        # Генерируем обновленное описание
        updated_diplomacy = rag_system.update_aspect_state(
            user_id, country_name, "внешняя политика", diplomacy_state, change_description)

        # Сохраняем обновленное описание
        return db.save_country_state(user_id, "внешняя политика", updated_diplomacy)

    @staticmethod
    @log_function_call
    def _get_reciprocal_relation(relation_type: str) -> str:
        """
        Возвращает обратный тип отношений.

        Args:
            relation_type: Исходный тип отношений

        Returns:
            str: Обратный тип отношений
        """
        reciprocal_map = {
            "война": "война",
            "враждебные": "враждебные",
            "напряженные": "напряженные",
            "нейтральные": "нейтральные",
            "дружественные": "дружественные",
            "союзные": "союзные",
            "вассальные": "сюзеренные"  # Особый случай: вассал->сюзерен
        }

        return reciprocal_map.get(relation_type, relation_type)

    @staticmethod
    @log_function_call
    def create_treaty(user_id: int, other_user_id: int,
                      treaty_type: str, terms: str) -> Dict[str, Any]:
        """
        Создает дипломатический договор между двумя странами.

        Args:
            user_id: ID пользователя-инициатора
            other_user_id: ID другого пользователя
            treaty_type: Тип договора (торговый, военный, мирный и т.д.)
            terms: Условия договора

        Returns:
            Dict[str, Any]: Результаты создания договора
        """
        # Получаем информацию о странах
        from_info = db.get_player_info(user_id)
        to_info = db.get_player_info(other_user_id)

        if not from_info or not to_info:
            return {
                "success": False,
                "message": "Не удалось получить информацию о странах"
            }

        from_country = from_info.get('country_name', 'Инициатор')
        to_country = to_info.get('country_name', 'Цель')

        # Генерируем текст договора
        treaty_text = Diplomacy._generate_treaty_text(
            from_country, to_country, treaty_type, terms)

        # Генерируем уникальный ID договора
        treaty_id = str(uuid.uuid4())

        # Создаем запись о договоре
        treaty_data = {
            "id": treaty_id,
            "from_user_id": user_id,
            "to_user_id": other_user_id,
            "from_country": from_country,
            "to_country": to_country,
            "treaty_type": treaty_type,
            "terms": terms,
            "treaty_text": treaty_text,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "game_year": get_current_game_year()
        }

        # Обновляем описание внешней политики инициатора
        treaty_description = f"Предложен {treaty_type} договор государству {to_country} со следующими условиями: {terms}"
        Diplomacy._update_diplomatic_description(
            user_id, from_country, to_country, "pending_treaty", treaty_description)

        # TODO: Сохранение договора в базу данных
        # В текущей версии мы не имеем оторов,
        # поэтому просто возвращаем данные договора. В полной реализации здесь будет
        # сохранение в соответствующую таблицу.

        return {
            "success": True,
            "message": f"{treaty_type} договор предложен {to_country}",
            "treaty": treaty_data
        }

    @staticmethod
    @log_function_call
    def _generate_treaty_text(from_country: str, to_country: str,
                              treaty_type: str, terms: str) -> str:
        """
        Генерирует формальный текст договора с помощью LLM.

        Args:
            from_country: Название страны-инициатора
            to_country: Название страны-получателя
            treaty_type: Тип договора
            terms: Условия договора

        Returns:
            str: Формальный текст договора
        """
        # Формируем промпт для LLM
        prompt = f"""Ты - опытный дипломат древнего мира, составляющий официальный договор между двумя государствами.

ДОГОВОР между {from_country} и {to_country}
Тип договора: {treaty_type}
Основные условия: {terms}

Составь формальный текст договора в стиле древнего мира. Договор должен включать:
1. Вступительную часть с обращением к богам/правителям
2. Четкое изложение взаимных обязательств сторон
3. Условия нарушения договора и последствия
4. Заключительную часть с клятвами сторон

Текст должен быть торжественным, формальным и соответствовать реалиям древнего мира.
"""

        # Получаем ответ LLM
        response = model.generate_response(prompt, max_tokens=800, temperature=0.7)

        return response.strip()

    @staticmethod
    @log_function_call
    def respond_to_treaty(treaty_id: str, response: str,
                          counter_terms: Optional[str] = None) -> Dict[str, Any]:
        """
        Отвечает на предложенный договор.

        Args:
            treaty_id: ID договора
            response: Ответ ("accept", "reject", "counter")
            counter_terms: Встречные условия (для "counter")

        Returns:
            Dict[str, Any]: Результаты ответа на договор
        """
        # TODO: Загрузка информации о договоре из базы данных
        # В текущей версии мы не имеем отдельной таблицы для договоров,
        # поэтому возвращаем заглушку. В полной реализации здесь будет
        # загрузка из соответствующей таблицы.

        return {
            "success": False,
            "message": "Функциональность ответа на договор будет реализована в будущем"
        }

    @staticmethod
    @log_function_call
    def get_active_treaties(user_id: int) -> List[Dict[str, Any]]:
        """
        Получает список активных договоров страны.

        Args:
            user_id: ID пользователя

        Returns:
            List[Dict[str, Any]]: Список активных договоров
        """
        # TODO: Загрузка договоров из базы данных
        # В текущей версии мы не имеем отдельной таблицы для договоров,
        # поэтому возвращаем пустой список. В полной реализации здесь будет
        # загрузка из соответствующей таблицы.

        return []

    @staticmethod
    @log_function_call
    def analyze_diplomatic_position(user_id: int) -> Dict[str, Any]:
        """
        Анализирует дипломатическое положение страны в мире.

        Args:
            user_id: ID пользователя

        Returns:
            Dict[str, Any]: Результаты анализа
        """
        # Получаем информацию о стране
        player_info = db.get_player_info(user_id)
        if not player_info:
            return {
                "success": False,
                "message": "Не удалось получить информацию о стране"
            }

        country_name = player_info.get('country_name', 'Анализируемая страна')

        # Получаем описание внешней политики
        diplomacy_state = db.get_country_state(user_id, "внешняя политика").get("внешняя политика", "")

        # Получаем отношения со всеми странами
        relations = Diplomacy.get_relations(user_id)

        # Формируем контекст для LLM
        relations_text = ""
        for relation in relations.values():
            relations_text += f"{relation['country_name']}: {relation['relation_type']}. "

        # Формируем промпт для LLM
        prompt = f"""Ты - опытный дипломатический советник правителя государства {country_name} в древнем мире.

Вот описание внешней политики государства:
{diplomacy_state}

Отношения с другими государствами:
{relations_text}

Проанализируй дипломатическое положение государства {country_name} в мире.
Оцени его сильные и слабые стороны, возможности и угрозы.

Ответь в следующем формате:
ОБЩЕЕ ПОЛОЖЕНИЕ: [краткая оценка]
СИЛЬНЫЕ СТОРОНЫ: [дипломатические преимущества]
СЛАБЫЕ СТОРОНЫ: [дипломатические недостатки]
ВОЗМОЖНОСТИ: [потенциальные выгоды]
УГРОЗЫ: [потенциальные опасности]
РЕКОМЕНДАЦИИ: [советы по улучшению положения]
"""

        # Получаем ответ LLM
        response = model.generate_response(prompt, max_tokens=800, temperature=0.7)

        # Парсим ответ
        result = {
            "overall": "",
            "strengths": [],
            "weaknesses": [],
            "opportunities": [],
            "threats": [],
            "recommendations": []
        }

        # Извлекаем общее положение
        overall_match = re.search(r"ОБЩЕЕ ПОЛОЖЕНИЕ:\s*(.+?)(?=\n|$)", response, re.DOTALL)
        if overall_match:
            result["overall"] = overall_match.group(1).strip()

        # Извлекаем сильные стороны
        strengths_match = re.search(r"СИЛЬНЫЕ СТОРОНЫ:\s*(.*?)(?=СЛАБЫЕ СТОРОНЫ:|$)", response, re.DOTALL)
        if strengths_match:
            strengths_text = strengths_match.group(1).strip()
            # Разбиваем на отдельные пункты
            strengths = [s.strip() for s in re.split(r'[\n•-]+', strengths_text) if s.strip()]
            result["strengths"] = strengths

        # Извлекаем слабые стороны
        weaknesses_match = re.search(r"СЛАБЫЕ СТОРОНЫ:\s*(.*?)(?=ВОЗМОЖНОСТИ:|$)", response, re.DOTALL)
        if weaknesses_match:
            weaknesses_text = weaknesses_match.group(1).strip()
            # Разбиваем на отдельные пункты
            weaknesses = [w.strip() for w in re.split(r'[\n•-]+', weaknesses_text) if w.strip()]
            result["weaknesses"] = weaknesses

        # Извлекаем возможности
        opportunities_match = re.search(r"ВОЗМОЖНОСТИ:\s*(.*?)(?=УГРОЗЫ:|$)", response, re.DOTALL)
        if opportunities_match:
            opportunities_text = opportunities_match.group(1).strip()
            # Разбиваем на отдельные пункты
            opportunities = [o.strip() for o in re.split(r'[\n•-]+', opportunities_text) if o.strip()]
            result["opportunities"] = opportunities

        # Извлекаем угрозы
        threats_match = re.search(r"УГРОЗЫ:\s*(.*?)(?=РЕКОМЕНДАЦИИ:|$)", response, re.DOTALL)
        if threats_match:
            threats_text = threats_match.group(1).strip()
            # Разбиваем на отдельные пункты
            threats = [t.strip() for t in re.split(r'[\n•-]+', threats_text) if t.strip()]
            result["threats"] = threats

        # Извлекаем рекомендации
        recommendations_match = re.search(r"РЕКОМЕНДАЦИИ:\s*(.*?)(?=$)", response, re.DOTALL)
        if recommendations_match:
            recommendations_text = recommendations_match.group(1).strip()
            # Разбиваем на отдельные пункты
            recommendations = [r.strip() for r in re.split(r'[\n•-]+', recommendations_text) if r.strip()]
            result["recommendations"] = recommendations

        return {
            "success": True,
            "country_name": country_name,
            "analysis": result,
            "relations": relations
        }


# Экспортируем функции для удобного доступа
get_relations = Diplomacy.get_relations
change_relations = Diplomacy.change_relations
create_treaty = Diplomacy.create_treaty
respond_to_treaty = Diplomacy.respond_to_treaty
get_active_treaties = Diplomacy.get_active_treaties
analyze_diplomatic_position = Diplomacy.analyze_diplomatic_position
