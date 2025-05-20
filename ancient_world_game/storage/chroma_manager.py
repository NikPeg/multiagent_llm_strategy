"""
chroma_manager.py - Модуль для взаимодействия с векторной базой данных Chroma.
Предоставляет функции для сохранения, поиска и управления векторными представлениями
данных игровых стран.
"""

import os
from typing import Dict, List, Tuple, Any, Optional, Union
import json
import re
from datetime import datetime
import chromadb
from chromadb.utils import embedding_functions
from chromadb.config import Settings

from config import config
from utils import logger, log_function_call, clean_text_for_storage
from .schemas import Player, PlayerStats, CountryState


class ChromaManager:
    """
    Класс для управления базой данных Chroma.
    Реализует паттерн Singleton для обеспечения единственного экземпляра.
    """
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ChromaManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.persist_directory = config.CHROMA_PERSIST_DIRECTORY

        # Создаем директорию, если она не существует
        if not os.path.exists(self.persist_directory):
            os.makedirs(self.persist_directory)

        # Настройка клиента Chroma
        self.client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

        # Используем встроенную модель для эмбеддингов (по умолчанию sentence-transformers)
        # Можно заменить на custom функцию, если используется внешняя модель
        self.embedding_function = embedding_functions.DefaultEmbeddingFunction()

        # Создаем или получаем коллекции
        self._create_collections()

        self._initialized = True

    @log_function_call
    def _create_collections(self):
        """
        Создает необходимые коллекции в Chroma DB, если они не существуют.
        """
        # Коллекция для стран
        self.countries_collection = self.client.get_or_create_collection(
            name="countries",
            embedding_function=self.embedding_function,
            metadata={"description": "Основная информация о странах"}
        )

        # Коллекция для аспектов стран
        self.aspects_collection = self.client.get_or_create_collection(
            name="country_aspects",
            embedding_function=self.embedding_function,
            metadata={"description": "Детальная информация об аспектах стран"}
        )

        # Коллекция для проектов
        self.projects_collection = self.client.get_or_create_collection(
            name="projects",
            embedding_function=self.embedding_function,
            metadata={"description": "Информация о проектах стран"}
        )

        # Коллекция для событий
        self.events_collection = self.client.get_or_create_collection(
            name="events",
            embedding_function=self.embedding_function,
            metadata={"description": "История событий в странах"}
        )

    @log_function_call
    def save_country(self, player: Player) -> bool:
        """
        Сохраняет основную информацию о стране в Chroma DB.

        Args:
            player: Объект Player с информацией о стране

        Returns:
            bool: True если информация успешно сохранена, иначе False
        """
        try:
            # Создаем уникальный идентификатор документа для страны
            doc_id = f"country_{player.user_id}"

            # Создаем текстовое описание для векторизации
            description_text = f"""
            Страна: {player.country_name}
            
            Общее описание:
            {player.description}
            
            Характеристики:
            Экономика: {player.stats.economy}
            Военное дело: {player.stats.military}
            Религия и культура: {player.stats.religion}
            Управление и право: {player.stats.governance}
            Строительство и инфраструктура: {player.stats.construction}
            Внешняя политика: {player.stats.diplomacy}
            Общественные отношения: {player.stats.society}
            Территория: {player.stats.territory}
            Технологичность: {player.stats.technology}
            
            Проблемы:
            {'. '.join(player.problems) if player.problems else 'Нет серьезных проблем'}
            """

            # Очищаем текст от лишних пробелов
            clean_description = clean_text_for_storage(description_text)

            # Метаданные для документа
            metadata = {
                "user_id": player.user_id,
                "country_name": player.country_name,
                "last_updated": datetime.now().isoformat()
            }

            # Проверяем, существует ли уже документ с таким ID
            result = self.countries_collection.get(ids=[doc_id])

            if result and result['ids']:
                # Обновляем существующий документ
                self.countries_collection.update(
                    ids=[doc_id],
                    documents=[clean_description],
                    metadatas=[metadata]
                )
            else:
                # Добавляем новый документ
                self.countries_collection.add(
                    ids=[doc_id],
                    documents=[clean_description],
                    metadatas=[metadata]
                )

            # Сохраняем также детальную информацию об аспектах
            self._save_country_aspects(player)

            return True
        except Exception as e:
            logger.error(f"Ошибка при сохранении страны в Chroma DB: {e}")
            return False

    @log_function_call
    def _save_country_aspects(self, player: Player) -> bool:
        """
        Сохраняет детальную информацию о каждом аспекте страны.

        Args:
            player: Объект Player с информацией о стране

        Returns:
            bool: True если информация успешно сохранена, иначе False
        """
        try:
            # Маппинг между русскими названиями и английскими полями
            aspect_mapping = {
                "economy": "экономика",
                "military": "военное дело",
                "religion": "религия и культура",
                "governance": "управление и право",
                "construction": "строительство и инфраструктура",
                "diplomacy": "внешняя политика",
                "society": "общественные отношения",
                "territory": "территория",
                "technology": "технологичность"
            }

            # Получаем словарь состояния страны
            state_dict = player.state.to_dict()

            # Получаем словарь характеристик
            stats_dict = player.stats.to_dict()

            # Для каждого аспекта создаем отдельный документ
            for eng_name, rus_name in aspect_mapping.items():
                # Формируем ID документа
                doc_id = f"aspect_{player.user_id}_{eng_name}"

                # Получаем описание аспекта и значение характеристики
                aspect_description = state_dict.get(rus_name, "")
                stat_value = stats_dict.get(rus_name, 1)

                # Формируем текст документа
                doc_text = f"""
                Страна: {player.country_name}
                Аспект: {rus_name}
                Значение: {stat_value}/5
                
                Описание:
                {aspect_description}
                """

                # Очищаем текст
                clean_text = clean_text_for_storage(doc_text)

                # Метаданные
                metadata = {
                    "user_id": player.user_id,
                    "country_name": player.country_name,
                    "aspect": rus_name,
                    "aspect_eng": eng_name,
                    "value": stat_value,
                    "last_updated": datetime.now().isoformat()
                }

                # Проверяем, существует ли уже документ
                result = self.aspects_collection.get(ids=[doc_id])

                if result and result['ids']:
                    # Обновляем существующий документ
                    self.aspects_collection.update(
                        ids=[doc_id],
                        documents=[clean_text],
                        metadatas=[metadata]
                    )
                else:
                    # Добавляем новый документ
                    self.aspects_collection.add(
                        ids=[doc_id],
                        documents=[clean_text],
                        metadatas=[metadata]
                    )

            return True
        except Exception as e:
            logger.error(f"Ошибка при сохранении аспектов страны в Chroma DB: {e}")
            return False

    @log_function_call
    def save_project(self, user_id: int, project_data: Dict[str, Any]) -> bool:
        """
        Сохраняет информацию о проекте в Chroma DB.

        Args:
            user_id: ID пользователя Telegram
            project_data: Словарь с данными проекта

        Returns:
            bool: True если проект успешно сохранен, иначе False
        """
        try:
            # Генерируем ID документа
            project_id = project_data.get('id')
            if not project_id:
                # Если ID не предоставлен, генерируем на основе времени
                project_id = f"proj_{user_id}_{int(datetime.now().timestamp())}"

            doc_id = f"project_{project_id}"

            # Формируем текст проекта
            project_text = f"""
            Проект: {project_data.get('name', 'Неизвестный проект')}
            Категория: {project_data.get('category', 'Общий проект')}
            Прогресс: {project_data.get('progress', 0)}%
            Оставшееся время: {project_data.get('remaining_years', 0)} лет
            
            Описание:
            {project_data.get('description', '')}
            """

            # Очищаем текст
            clean_text = clean_text_for_storage(project_text)

            # Метаданные
            metadata = {
                "user_id": user_id,
                "project_id": project_id,
                "name": project_data.get('name', 'Неизвестный проект'),
                "category": project_data.get('category', 'Общий проект'),
                "progress": project_data.get('progress', 0),
                "duration": project_data.get('duration', 0),
                "remaining_years": project_data.get('remaining_years', 0),
                "start_year": project_data.get('start_year', 0),
                "last_updated": datetime.now().isoformat()
            }

            # Проверяем, существует ли уже документ
            result = self.projects_collection.get(ids=[doc_id])

            if result and result['ids']:
                # Обновляем существующий документ
                self.projects_collection.update(
                    ids=[doc_id],
                    documents=[clean_text],
                    metadatas=[metadata]
                )
            else:
                # Добавляем новый документ
                self.projects_collection.add(
                    ids=[doc_id],
                    documents=[clean_text],
                    metadatas=[metadata]
                )

            return True
        except Exception as e:
            logger.error(f"Ошибка при сохранении проекта в Chroma DB: {e}")
            return False

    @log_function_call
    def save_event(self, user_id: int, event_data: Dict[str, Any]) -> bool:
        """
        Сохраняет информацию о событии в Chroma DB.

        Args:
            user_id: ID пользователя Telegram
            event_data: Словарь с данными события

        Returns:
            bool: True если событие успешно сохранено, иначе False
        """
        try:
            # Генерируем ID документа
            event_id = event_data.get('id')
            if not event_id:
                # Если ID не предоставлен, генерируем на основе времени
                event_id = f"evt_{user_id}_{int(datetime.now().timestamp())}"

            doc_id = f"event_{event_id}"

            # Формируем текст события
            event_text = f"""
            Тип события: {event_data.get('type', 'нейтральное')}
            Дата: {event_data.get('timestamp', datetime.now().isoformat())}
            
            Описание:
            {event_data.get('description', '')}
            
            Эффекты:
            {json.dumps(event_data.get('effects', {}), ensure_ascii=False, indent=2)}
            """

            # Очищаем текст
            clean_text = clean_text_for_storage(event_text)

            # Метаданные
            metadata = {
                "user_id": user_id,
                "event_id": event_id,
                "type": event_data.get('type', 'нейтральное'),
                "timestamp": event_data.get('timestamp', datetime.now().isoformat()),
                "last_updated": datetime.now().isoformat()
            }

            # Добавляем новый документ (события не обновляются)
            self.events_collection.add(
                ids=[doc_id],
                documents=[clean_text],
                metadatas=[metadata]
            )

            return True
        except Exception as e:
            logger.error(f"Ошибка при сохранении события в Chroma DB: {e}")
            return False

    @log_function_call
    def get_country_context(self, user_id: int, query: str, limit: int = 3) -> str:
        """
        Получает релевантный контекст о стране для заданного запроса.

        Args:
            user_id: ID пользователя Telegram
            query: Текстовый запрос
            limit: Максимальное количество фрагментов для возврата

        Returns:
            str: Релевантный контекст о стране
        """
        try:
            # Ищем в общей информации о стране
            country_results = self.countries_collection.query(
                query_texts=[query],
                where={"user_id": user_id},
                n_results=1
            )

            # Ищем в аспектах страны
            aspects_results = self.aspects_collection.query(
                query_texts=[query],
                where={"user_id": user_id},
                n_results=min(limit, 5)  # Максимум 5 аспектов
            )

            # Ищем в проектах
            projects_results = self.projects_collection.query(
                query_texts=[query],
                where={"user_id": user_id},
                n_results=min(limit, 3)  # Максимум 3 проекта
            )

            # Собираем все контексты
            contexts = []

            # Добавляем общую информацию о стране
            if country_results['documents'] and country_results['documents'][0]:
                contexts.append("ОБЩАЯ ИНФОРМАЦИЯ О СТРАНЕ:")
                contexts.append(country_results['documents'][0][0])

            # Добавляем релевантные аспекты
            if aspects_results['documents'] and aspects_results['documents'][0]:
                contexts.append("\nРЕЛЕВАНТНЫЕ АСПЕКТЫ СТРАНЫ:")
                for i, doc in enumerate(aspects_results['documents'][0]):
                    if i < limit:
                        contexts.append(doc)

            # Добавляем релевантные проекты
            if projects_results['documents'] and projects_results['documents'][0]:
                contexts.append("\nТЕКУЩИЕ ПРОЕКТЫ:")
                for i, doc in enumerate(projects_results['documents'][0]):
                    if i < limit:
                        contexts.append(doc)

            return "\n\n".join(contexts)
        except Exception as e:
            logger.error(f"Ошибка при получении контекста о стране: {e}")
            return ""

    @log_function_call
    def get_other_countries_context(self, user_id: int, query: str, limit: int = 3) -> str:
        """
        Получает релевантный контекст о других странах для заданного запроса.

        Args:
            user_id: ID пользователя Telegram (текущий пользователь)
            query: Текстовый запрос
            limit: Максимальное количество фрагментов для возврата

        Returns:
            str: Релевантный контекст о других странах
        """
        try:
            # Ищем в общей информации о странах, исключая текущего пользователя
            countries_results = self.countries_collection.query(
                query_texts=[query],
                where={"user_id": {"$ne": user_id}},  # Не равно текущему пользователю
                n_results=limit
            )

            # Если нужно, можно добавить поиск по аспектам и проектам других стран

            # Собираем контексты
            contexts = []

            if countries_results['documents'] and countries_results['documents'][0]:
                contexts.append("ИНФОРМАЦИЯ О ДРУГИХ СТРАНАХ:")
                for i, doc in enumerate(countries_results['documents'][0]):
                    if i < limit:
                        # Получаем название страны из метаданных
                        if countries_results['metadatas'] and countries_results['metadatas'][0]:
                            country_name = countries_results['metadatas'][0][i].get('country_name', 'Неизвестная страна')
                            contexts.append(f"--- {country_name.upper()} ---")
                        contexts.append(doc)

            return "\n\n".join(contexts) if contexts else ""
        except Exception as e:
            logger.error(f"Ошибка при получении контекста о других странах: {e}")
            return ""

    @log_function_call
    def get_all_country_data(self, user_id: int) -> Dict[str, Any]:
        """
        Получает полную информацию о стране из Chroma DB.

        Args:
            user_id: ID пользователя Telegram

        Returns:
            Dict[str, Any]: Словарь с данными о стране
        """
        try:
            country_data = {}

            # Получаем основную информацию о стране
            country_doc = self.countries_collection.get(
                ids=[f"country_{user_id}"]
            )

            if country_doc and country_doc['documents']:
                country_data['main'] = country_doc['documents'][0]
                if country_doc['metadatas'] and country_doc['metadatas'][0]:
                    country_data['country_name'] = country_doc['metadatas'][0].get('country_name', 'Неизвестная страна')

            # Получаем все аспекты страны
            aspects_docs = self.aspects_collection.get(
                where={"user_id": user_id}
            )

            if aspects_docs and aspects_docs['documents']:
                country_data['aspects'] = {}
                for i, doc in enumerate(aspects_docs['documents']):
                    if aspects_docs['metadatas'] and i < len(aspects_docs['metadatas']):
                        aspect_name = aspects_docs['metadatas'][i].get('aspect', 'неизвестный аспект')
                        country_data['aspects'][aspect_name] = doc

            # Получаем все проекты страны
            projects_docs = self.projects_collection.get(
                where={"user_id": user_id}
            )

            if projects_docs and projects_docs['documents']:
                country_data['projects'] = []
                for i, doc in enumerate(projects_docs['documents']):
                    if projects_docs['metadatas'] and i < len(projects_docs['metadatas']):
                        project_data = {
                            'text': doc,
                            'metadata': projects_docs['metadatas'][i]
                        }
                        country_data['projects'].append(project_data)

            # Получаем последние события страны
            events_docs = self.events_collection.get(
                where={"user_id": user_id},
                limit=10  # Ограничиваем количество событий
            )

            if events_docs and events_docs['documents']:
                country_data['events'] = []
                for i, doc in enumerate(events_docs['documents']):
                    if events_docs['metadatas'] and i < len(events_docs['metadatas']):
                        event_data = {
                            'text': doc,
                            'metadata': events_docs['metadatas'][i]
                        }
                        country_data['events'].append(event_data)

            return country_data
        except Exception as e:
            logger.error(f"Ошибка при получении полной информации о стране: {e}")
            return {}

    @log_function_call
    def search_all_countries(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Ищет по всем странам документы, релевантные запросу.

        Args:
            query: Текстовый запрос
            limit: Максимальное количество результатов

        Returns:
            List[Dict[str, Any]]: Список найденных документов с метаданными
        """
        try:
            # Ищем в общей информации о странах
            countries_results = self.countries_collection.query(
                query_texts=[query],
                n_results=limit
            )

            # Собираем результаты
            results = []

            if countries_results['documents'] and countries_results['documents'][0]:
                for i, doc in enumerate(countries_results['documents'][0]):
                    if i < limit and countries_results['metadatas'] and countries_results['metadatas'][0]:
                        metadata = countries_results['metadatas'][0][i]
                        result = {
                            'text': doc,
                            'metadata': metadata,
                            'type': 'country',
                            'country_name': metadata.get('country_name', 'Неизвестная страна'),
                            'user_id': metadata.get('user_id', 0)
                        }
                        results.append(result)

            return results
        except Exception as e:
            logger.error(f"Ошибка при поиске по всем странам: {e}")
            return []

    @log_function_call
    def delete_country_data(self, user_id: int) -> bool:
        """
        Удаляет все данные о стране из Chroma DB.

        Args:
            user_id: ID пользователя Telegram

        Returns:
            bool: True если данные успешно удалены, иначе False
        """
        try:
            # Удаляем основную информацию о стране
            self.countries_collection.delete(
                ids=[f"country_{user_id}"]
            )

            # Удаляем все аспекты страны
            self.aspects_collection.delete(
                where={"user_id": user_id}
            )

            # Удаляем все проекты страны
            self.projects_collection.delete(
                where={"user_id": user_id}
            )

            # Удаляем все события страны
            self.events_collection.delete(
                where={"user_id": user_id}
            )

            return True
        except Exception as e:
            logger.error(f"Ошибка при удалении данных о стране: {e}")
            return False

    @log_function_call
    def get_collection_stats(self) -> Dict[str, int]:
        """
        Получает статистику по коллекциям в Chroma DB.

        Returns:
            Dict[str, int]: Словарь с количеством документов в каждой коллекции
        """
        try:
            stats = {}

            # Получаем количество документов в каждой коллекции
            stats['countries'] = len(self.countries_collection.get()['ids']) if self.countries_collection.count() > 0 else 0
            stats['aspects'] = len(self.aspects_collection.get()['ids']) if self.aspects_collection.count() > 0 else 0
            stats['projects'] = len(self.projects_collection.get()['ids']) if self.projects_collection.count() > 0 else 0
            stats['events'] = len(self.events_collection.get()['ids']) if self.events_collection.count() > 0 else 0

            # Общее количество документов
            stats['total'] = stats['countries'] + stats['aspects'] + stats['projects'] + stats['events']

            return stats
        except Exception as e:
            logger.error(f"Ошибка при получении статистики Chroma DB: {e}")
            return {"error": str(e)}


# Создаем экземпляр менеджера Chroma при импорте модуля
chroma = ChromaManager()


def get_chroma() -> ChromaManager:
    """
    Функция для получения экземпляра менеджера Chroma DB.

    Returns:
        ChromaManager: Экземпляр менеджера Chroma DB
    """
    return chroma
