"""
player.py - Модуль, содержащий классы для управления игроками и их странами.
Отвечает за хранение и обработку информации о состоянии стран в игре.
"""

from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime
import json
import re

from config import config, STATS
from utils import logger, log_function_call, format_game_year, get_current_game_year
from storage import db, chroma, Player as PlayerSchema, PlayerStats, CountryState
from ai import model, rag_system, response_parser
from ai import get_initial_country_description_prompt, get_aspect_details_prompt


class Player:
    """
    Класс, представляющий игрока и его страну.
    Объединяет данные из базы данных и Chroma DB, предоставляя методы для
    управления состоянием страны.
    """

    def __init__(self, user_id: int, username: Optional[str] = None):
        """
        Инициализирует объект игрока.

        Args:
            user_id: ID пользователя Telegram
            username: Имя пользователя Telegram (опционально)
        """
        self.user_id = user_id
        self.username = username
        self.country_name = ""
        self.created_at = datetime.now()
        self.last_active = datetime.now()
        self.goals_count = 0
        self.stats = {}
        self.state = {}
        self.description = ""
        self.problems = []

        # Загружаем данные игрока из БД, если они существуют
        self._load_from_db()

    @log_function_call
    def _load_from_db(self) -> bool:
        """
        Загружает данные игрока из базы данных.

        Returns:
            bool: True, если данные успешно загружены, иначе False
        """
        player_data = db.get_player_info(self.user_id)
        if not player_data:
            return False

        # Обновляем атрибуты из базы данных
        self.country_name = player_data.get('country_name', "")
        self.username = player_data.get('username', self.username)
        self.goals_count = player_data.get('goals_count', 0)

        # Преобразуем строковые даты в datetime
        if 'created_at' in player_data:
            self.created_at = datetime.fromisoformat(player_data['created_at'])
        if 'last_active' in player_data:
            self.last_active = datetime.fromisoformat(player_data['last_active'])

        # Загружаем статы
        self.stats = player_data.get('stats', {})

        # Загружаем состояние из Chroma
        self._load_from_chroma()

        return True

    @log_function_call
    def _load_from_chroma(self) -> bool:
        """
        Загружает расширенные данные о стране из Chroma DB.

        Returns:
            bool: True, если данные успешно загружены, иначе False
        """
        country_data = chroma.get_all_country_data(self.user_id)
        if not country_data:
            return False

        # Загружаем описание страны
        if 'main' in country_data:
            # Извлекаем описание из основного документа
            main_doc = country_data['main']
            # Ищем общее описание между "Общее описание:" и следующим заголовком
            description_match = re.search(r"Общее описание:\s*(.*?)(?=\n\n[А-Я]|$)", main_doc, re.DOTALL)
            if description_match:
                self.description = description_match.group(1).strip()

        # Загружаем состояние аспектов
        if 'aspects' in country_data:
            self.state = country_data['aspects']

        # Загружаем проблемы
        if 'main' in country_data:
            # Ищем проблемы в основном документе
            problems_match = re.search(r"Проблемы:\s*(.*?)(?=\n\n[А-Я]|$)", country_data['main'], re.DOTALL)
            if problems_match:
                problems_text = problems_match.group(1).strip()
                # Разбиваем на отдельные проблемы
                self.problems = [problem.strip() for problem in problems_text.split('.') if problem.strip()]

        return True

    @log_function_call
    def register_country(self, country_name: str, stats: Dict[str, int], description: str = "") -> bool:
        """
        Регистрирует новую страну для игрока.

        Args:
            country_name: Название страны
            stats: Начальные характеристики страны
            description: Дополнительное описание от игрока

        Returns:
            bool: True, если страна успешно зарегистрирована, иначе False
        """
        # Сохраняем базовую информацию в базе данных
        if not db.register_player(self.user_id, self.username, country_name):
            logger.error(f"Ошибка при регистрации игрока {self.user_id} в базе данных")
            return False

        # Сохраняем характеристики
        if not db.save_player_stats(self.user_id, stats):
            logger.error(f"Ошибка при сохранении характеристик для игрока {self.user_id}")
            return False

        # Обновляем атрибуты объекта
        self.country_name = country_name
        self.stats = stats
        self.created_at = datetime.now()
        self.last_active = datetime.now()

        # Генерируем начальное описание страны с помощью LLM
        result = self._generate_initial_description(country_name, stats, description)
        if not result:
            logger.error(f"Ошибка при генерации начального описания для страны {country_name}")
            return False

        # Загружаем полные данные после создания
        self._load_from_db()

        return True

    @log_function_call
    def _generate_initial_description(self, country_name: str, stats: Dict[str, int],
                                      description: str) -> bool:
        """
        Генерирует начальное описание страны с помощью LLM.

        Args:
            country_name: Название страны
            stats: Характеристики страны
            description: Дополнительное описание от игрока

        Returns:
            bool: True, если описание успешно сгенерировано и сохранено, иначе False
        """
        try:
            # Создаем промпт для генерации описания
            prompt = get_initial_country_description_prompt(country_name, stats, description)

            # Генерируем ответ
            response = model.generate_response(prompt, max_tokens=1000, temperature=0.7)

            # Парсим результат
            result = response_parser.parse(response, "initial_description")

            # Извлекаем описание и проблемы
            self.description = result.get("description", "")
            self.problems = result.get("problems", [])

            # Создаем объект Player для сохранения в Chroma
            player_schema = PlayerSchema(
                user_id=self.user_id,
                username=self.username,
                country_name=country_name,
                created_at=self.created_at,
                last_active=self.last_active,
                goals_count=self.goals_count,
                stats=PlayerStats.from_dict(stats),
                description=self.description,
                problems=self.problems
            )

            # Сохраняем в Chroma
            if not chroma.save_country(player_schema):
                logger.error(f"Ошибка при сохранении страны {country_name} в Chroma")
                return False

            # Генерируем начальные описания для каждого аспекта
            self._generate_initial_aspects(country_name, stats, self.description)

            return True
        except Exception as e:
            logger.error(f"Ошибка при генерации начального описания: {e}")
            return False

    @log_function_call
    def _generate_initial_aspects(self, country_name: str, stats: Dict[str, int],
                                  country_description: str) -> None:
        """
        Генерирует начальные описания для каждого аспекта страны.

        Args:
            country_name: Название страны
            stats: Характеристики страны
            country_description: Общее описание страны
        """
        # Аспекты страны
        aspects = [
            "экономика", "военное дело", "религия и культура",
            "управление и право", "строительство и инфраструктура",
            "внешняя политика", "общественные отношения",
            "территория", "технологичность"
        ]

        for aspect in aspects:
            try:
                # Создаем промпт для генерации описания аспекта
                prompt = f"""Ты - летописец древнего мира, описывающий страну {country_name}.

Общее описание страны:
{country_description}

Характеристики:
{', '.join([f"{key}: {value}" for key, value in stats.items()])}

Напиши подробное описание аспекта "{aspect}" для этой страны.
Учитывай общее описание и то, что у этого аспекта оценка {stats.get(aspect, 1)}/5.
Ответ должен быть в 2-3 абзаца без заголовков и дополнительного форматирования."""

                # Генерируем ответ
                response = model.generate_response(prompt, max_tokens=500, temperature=0.7)

                # Сохраняем описание аспекта
                self.state[aspect] = response.strip()

                # Сохраняем в базу данных
                db.save_country_state(self.user_id, aspect, response.strip())

            except Exception as e:
                logger.error(f"Ошибка при генерации описания аспекта {aspect}: {e}")
                # Устанавливаем базовое описание при ошибке
                default_description = f"Уровень развития {aspect} в стране {country_name} оценивается в {stats.get(aspect, 1)} из 5."
                self.state[aspect] = default_description
                db.save_country_state(self.user_id, aspect, default_description)

        # Создаем объект CountryState
        state_obj = CountryState(
            economy=self.state.get("экономика", ""),
            military=self.state.get("военное дело", ""),
            religion=self.state.get("религия и культура", ""),
            governance=self.state.get("управление и право", ""),
            construction=self.state.get("строительство и инфраструктура", ""),
            diplomacy=self.state.get("внешняя политика", ""),
            society=self.state.get("общественные отношения", ""),
            territory=self.state.get("территория", ""),
            technology=self.state.get("технологичность", "")
        )

        # Обновляем схему игрока
        player_schema = PlayerSchema(
            user_id=self.user_id,
            username=self.username,
            country_name=country_name,
            created_at=self.created_at,
            last_active=self.last_active,
            goals_count=self.goals_count,
            stats=PlayerStats.from_dict(stats),
            state=state_obj,
            description=self.description,
            problems=self.problems
        )

        # Сохраняем обновленную информацию в Chroma
        chroma.save_country(player_schema)

    @log_function_call
    def process_command(self, command: str) -> Dict[str, Any]:
        """
        Обрабатывает команду игрока с помощью RAG и LLM.

        Args:
            command: Текст команды

        Returns:
            Dict[str, Any]: Результат обработки команды
        """
        # Обновляем время последней активности
        self.last_active = datetime.now()
        db.save_player_stats(self.user_id, self.stats)

        # Получаем результат обработки команды через RAG-систему
        result = rag_system.process_player_action(self.user_id, self.country_name, command)

        # Извлекаем анализ
        analysis = result.get("analysis", {})

        # Обновляем состояние страны на основе результатов
        self._update_country_state(analysis)

        # Формируем ответ
        response = {
            "command": command,
            "execution": analysis.get("execution", ""),
            "result": analysis.get("result", ""),
            "consequences": analysis.get("consequences", ""),
            "changes": analysis.get("changes", {})
        }

        return response

    @log_function_call
    def _update_country_state(self, analysis: Dict[str, Any]) -> None:
        """
        Обновляет состояние страны на основе результатов анализа команды.

        Args:
            analysis: Результат анализа команды
        """
        # Получаем изменения по аспектам
        changes = analysis.get("changes", {})

        # Обновляем каждый затронутый аспект
        for aspect, change_description in changes.items():
            # Нормализуем название аспекта
            aspect = aspect.lower().strip()

            # Получаем текущее описание аспекта
            current_description = self.state.get(aspect, "")

            # Генерируем обновленное описание
            updated_description = rag_system.update_aspect_state(
                self.user_id,
                self.country_name,
                aspect,
                current_description,
                change_description
            )

            # Сохраняем обновленное описание
            self.state[aspect] = updated_description
            db.save_country_state(self.user_id, aspect, updated_description)

        # Обновляем оценки характеристик
        self._update_stats()

        # Обновляем проблемы
        self._update_problems()

        # Создаем объекты для сохранения в Chroma
        state_obj = CountryState(
            economy=self.state.get("экономика", ""),
            military=self.state.get("военное дело", ""),
            religion=self.state.get("религия и культура", ""),
            governance=self.state.get("управление и право", ""),
            construction=self.state.get("строительство и инфраструктура", ""),
            diplomacy=self.state.get("внешняя политика", ""),
            society=self.state.get("общественные отношения", ""),
            territory=self.state.get("территория", ""),
            technology=self.state.get("технологичность", "")
        )

        player_schema = PlayerSchema(
            user_id=self.user_id,
            username=self.username,
            country_name=self.country_name,
            created_at=self.created_at,
            last_active=self.last_active,
            goals_count=self.goals_count,
            stats=PlayerStats.from_dict(self.stats),
            state=state_obj,
            description=self.description,
            problems=self.problems
        )

        # Сохраняем обновленную информацию в Chroma
        chroma.save_country(player_schema)

    @log_function_call
    def _update_stats(self) -> None:
        """
        Обновляет числовые характеристики страны на основе текстовых описаний аспектов.
        """
        # Получаем обновленные статы через RAG-систему
        updated_stats = rag_system.update_country_stats(self.user_id, self.country_name)

        # Если статы успешно получены, обновляем
        if updated_stats:
            self.stats = updated_stats
            db.save_player_stats(self.user_id, updated_stats)

    @log_function_call
    def _update_problems(self) -> None:
        """
        Обновляет список проблем страны.
        """
        # Получаем обновленные проблемы через RAG-систему
        updated_problems = rag_system.generate_country_problems(self.user_id, self.country_name)

        # Если проблемы успешно получены, обновляем
        if updated_problems:
            self.problems = updated_problems

    @log_function_call
    def get_aspect_details(self, aspect: str) -> str:
        """
        Получает подробное описание аспекта страны.

        Args:
            aspect: Название аспекта

        Returns:
            str: Подробное описание аспекта
        """
        # Получаем текущее описание аспекта
        current_description = self.state.get(aspect, "")

        # Генерируем подробное описание
        prompt = get_aspect_details_prompt(self.country_name, aspect, current_description)

        response = model.generate_response(prompt, max_tokens=800, temperature=0.7)

        return response.strip()

    @log_function_call
    def predict_future(self) -> str:
        """
        Генерирует предсказание о будущем страны.

        Returns:
            str: Текст предсказания
        """
        return rag_system.predict_country_future(self.user_id, self.country_name)

    @log_function_call
    def score_goal(self) -> int:
        """
        Увеличивает счетчик голов и возвращает новое значение.

        Returns:
            int: Новое количество голов
        """
        # Увеличиваем счетчик
        self.goals_count += 1

        # Сохраняем в БД
        db.update_goals_count(self.user_id)

        return self.goals_count

    @log_function_call
    def get_goal_count(self) -> int:
        """
        Возвращает текущее количество голов.

        Returns:
            int: Количество голов
        """
        return self.goals_count

    @log_function_call
    def is_registered(self) -> bool:
        """
        Проверяет, зарегистрирован ли игрок.

        Returns:
            bool: True, если игрок зарегистрирован, иначе False
        """
        return bool(self.country_name)

    @log_function_call
    def get_info(self) -> Dict[str, Any]:
        """
        Возвращает полную информацию о стране.

        Returns:
            Dict[str, Any]: Информация о стране
        """
        return {
            "user_id": self.user_id,
            "username": self.username,
            "country_name": self.country_name,
            "created_at": self.created_at.isoformat(),
            "last_active": self.last_active.isoformat(),
            "goals_count": self.goals_count,
            "stats": self.stats,
            "state": self.state,
            "description": self.description,
            "problems": self.problems,
            "current_game_year": get_current_game_year()
        }

    @log_function_call
    def receive_event(self, event_type: str) -> Dict[str, Any]:
        """
        Генерирует и применяет случайное событие к стране.

        Args:
            event_type: Тип события (очень плохое, плохое, нейтральное, хорошее, очень хорошее)

        Returns:
            Dict[str, Any]: Информация о событии
        """
        # Генерируем событие через RAG-систему
        event = rag_system.generate_event_with_context(self.user_id, self.country_name, event_type)

        # Применяем влияние события на страну
        self._apply_event_effects(event)

        return event

    @log_function_call
    def _apply_event_effects(self, event: Dict[str, Any]) -> None:
        """
        Применяет эффекты события к стране.

        Args:
            event: Информация о событии
        """
        # Получаем затронутые аспекты
        affected_aspects = event.get("affected_aspects", {})

        # Обновляем каждый затронутый аспект
        for aspect, impact in affected_aspects.items():
            # Нормализуем название аспекта
            aspect = aspect.lower().strip()

            # Получаем текущее описание аспекта
            current_description = self.state.get(aspect, "")

            # Генерируем обновленное описание
            updated_description = rag_system.update_aspect_state(
                self.user_id,
                self.country_name,
                aspect,
                current_description,
                impact
            )

            # Сохраняем обновленное описание
            self.state[aspect] = updated_description
            db.save_country_state(self.user_id, aspect, updated_description)

        # Обновляем оценки характеристик
        self._update_stats()

        # Обновляем проблемы
        self._update_problems()

        # Обновляем информацию в Chroma
        self._update_chroma()

    @log_function_call
    def _update_chroma(self) -> None:
        """
        Обновляет информацию о стране в Chroma DB.
        """
        # Создаем объекты для сохранения
        state_obj = CountryState(
            economy=self.state.get("экономика", ""),
            military=self.state.get("военное дело", ""),
            religion=self.state.get("религия и культура", ""),
            governance=self.state.get("управление и право", ""),
            construction=self.state.get("строительство и инфраструктура", ""),
            diplomacy=self.state.get("внешняя политика", ""),
            society=self.state.get("общественные отношения", ""),
            territory=self.state.get("территория", ""),
            technology=self.state.get("технологичность", "")
        )

        player_schema = PlayerSchema(
            user_id=self.user_id,
            username=self.username,
            country_name=self.country_name,
            created_at=self.created_at,
            last_active=self.last_active,
            goals_count=self.goals_count,
            stats=PlayerStats.from_dict(self.stats),
            state=state_obj,
            description=self.description,
            problems=self.problems
        )

        # Сохраняем обновленную информацию в Chroma
        chroma.save_country(player_schema)

    @log_function_call
    def daily_update(self) -> Dict[str, Any]:
        """
        Выполняет ежедневное обновление страны.

        Returns:
            Dict[str, Any]: Результаты обновления
        """
        # Получаем результаты обновления через RAG-систему
        update_results = rag_system.process_daily_update(self.user_id, self.country_name)

        # Применяем изменения к стране
        aspect_changes = update_results.get("aspect_changes", {})

        # Обновляем каждый аспект
        for aspect, change in aspect_changes.items():
            # Нормализуем название аспекта
            aspect = aspect.lower().strip()

            # Получаем текущее описание аспекта
            current_description = self.state.get(aspect, "")

            # Генерируем обновленное описание
            updated_description = rag_system.update_aspect_state(
                self.user_id,
                self.country_name,
                aspect,
                current_description,
                change
            )

            # Сохраняем обновленное описание
            self.state[aspect] = updated_description
            db.save_country_state(self.user_id, aspect, updated_description)

        # Обновляем оценки характеристик
        self._update_stats()

        # Обновляем проблемы
        self._update_problems()

        # Обновляем информацию в Chroma
        self._update_chroma()

        return update_results

    @log_function_call
    def add_project(self, project_name: str, project_category: str,
                    description: str, duration: int) -> Dict[str, Any]:
        """
        Добавляет новый проект для страны.

        Args:
            project_name: Название проекта
            project_category: Категория проекта
            description: Описание проекта
            duration: Продолжительность в годах

        Returns:
            Dict[str, Any]: Информация о созданном проекте
        """
        # Получаем текущий игровой год
        current_game_year = get_current_game_year()

        # Создаем проект
        project_data = {
            "name": project_name,
            "category": project_category,
            "description": description,
            "start_year": current_game_year,
            "duration": duration,
            "progress": 0,
            "remaining_years": duration
        }

        # Сохраняем проект в Chroma
        chroma.save_project(self.user_id, project_data)

        return project_data

    @log_function_call
    def check_project_progress(self) -> Dict[str, Any]:
        """
        Проверяет прогресс проектов страны.

        Returns:
            Dict[str, Any]: Информация о проектах
        """
        # Проверяем через RAG-систему
        return rag_system.check_projects_progress(self.user_id, self.country_name)

    @log_function_call
    def handle_project_completion(self, project_name: str,
                                  project_category: str) -> Dict[str, Any]:
        """
        Обрабатывает завершение проекта.

        Args:
            project_name: Название проекта
            project_category: Категория проекта

        Returns:
            Dict[str, Any]: Результат завершения проекта
        """
        # Получаем контекст страны
        country_context = rag_system.get_country_context(self.user_id, project_name)

        # Создаем промпт для описания завершения проекта
        prompt = f"""Ты - летописец древнего мира, записывающий историю страны {self.country_name}.

Проект "{project_name}" категории "{project_category}" был завершен!

Вот текущая информация о стране:
{country_context}

Опиши, как завершение этого проекта повлияло на страну. Включи информацию о:
1. Церемонии открытия/завершения проекта
2. Реакции населения
3. Конкретных выгодах для государства
4. Влиянии на различные аспекты жизни страны

Ответь в следующем формате:
СОБЫТИЕ: [описание завершения проекта]
ВЛИЯНИЕ: [описание влияния на страну]
ИЗМЕНЕНИЯ В АСПЕКТАХ:
- [аспект]: [изменения]
"""

        # Генерируем описание завершения
        response = model.generate_response(prompt, max_tokens=800, temperature=0.7)

        # Парсим результат
        result = response_parser.parse(response, "project_completion")

        # Применяем изменения к стране
        aspect_changes = result.get("aspect_changes", {})

        # Обновляем каждый затронутый аспект
        for aspect, change in aspect_changes.items():
            # Нормализуем название аспекта
            aspect = aspect.lower().strip()

            # Получаем текущее описание аспекта
            current_description = self.state.get(aspect, "")

            # Генерируем обновленное описание
            updated_description = rag_system.update_aspect_state(
                self.user_id,
                self.country_name,
                aspect,
                current_description,
                change
            )

            # Сохраняем обновленное описание
            self.state[aspect] = updated_description
            db.save_country_state(self.user_id, aspect, updated_description)

        # Обновляем оценки характеристик
        self._update_stats()

        # Обновляем проблемы
        self._update_problems()

        # Обновляем информацию в Chroma
        self._update_chroma()

        return result


class PlayerManager:
    """
    Класс для управления игроками и доступа к ним.
    """
    _players_cache = {}

    @classmethod
    @log_function_call
    def get_player(cls, user_id: int, username: Optional[str] = None) -> Player:
        """
        Получает объект игрока по его ID, при необходимости создает новый.

        Args:
            user_id: ID пользователя Telegram
            username: Имя пользователя Telegram (опционально)

        Returns:
            Player: Объект игрока
        """
        # Проверяем, есть ли игрок в кэше
        if user_id in cls._players_cache:
            player = cls._players_cache[user_id]
            # Обновляем имя пользователя, если оно изменилось
            if username and player.username != username:
                player.username = username
            return player

        # Создаем нового игрока
        player = Player(user_id, username)

        # Добавляем в кэш
        cls._players_cache[user_id] = player

        return player

    @classmethod
    @log_function_call
    def get_player_by_username(cls, username: str) -> Optional[Player]:
        """
        Получает объект игрока по его имени пользователя.

        Args:
            username: Имя пользователя Telegram

        Returns:
            Optional[Player]: Объект игрока или None, если не найден
        """
        # Проверяем, есть ли игрок с таким именем в кэше
        for player in cls._players_cache.values():
            if player.username and player.username.lower() == username.lower():
                return player

        # Если в кэше нет, ищем в базе данных
        player_data = db.get_player_by_username(username)
        if player_data:
            user_id = player_data.get('user_id')
            if user_id:
                return cls.get_player(user_id, username)

        return None

    @classmethod
    @log_function_call
    def get_all_players(cls) -> List[Player]:
        """
        Получает список всех зарегистрированных игроков.

        Returns:
            List[Player]: Список объектов игроков
        """
        # Получаем данные всех игроков из базы
        players_data = db.get_all_players()

        players = []
        for data in players_data:
            user_id = data.get('user_id')
            username = data.get('username')

            # Проверяем, есть ли игрок в кэше
            if user_id in cls._players_cache:
                players.append(cls._players_cache[user_id])
            else:
                # Создаем нового игрока и добавляем в кэш
                player = Player(user_id, username)
                cls._players_cache[user_id] = player
                players.append(player)

        return players

    @classmethod
    @log_function_call
    def clear_cache(cls) -> None:
        """
        Очищает кэш игроков.
        """
        cls._players_cache.clear()

    @classmethod
    @log_function_call
    def reload_player(cls, user_id: int) -> Optional[Player]:
        """
        Перезагружает данные игрока из базы данных.

        Args:
            user_id: ID пользователя Telegram

        Returns:
            Optional[Player]: Обновленный объект игрока или None, если не найден
        """
        # Удаляем из кэша, если есть
        if user_id in cls._players_cache:
            del cls._players_cache[user_id]

        # Проверяем, существует ли игрок в базе
        if db.is_player_registered(user_id):
            # Создаем нового игрока и загружаем данные
            player = Player(user_id)
            cls._players_cache[user_id] = player
            return player

        return None

    @classmethod
    @log_function_call
    def daily_update_all(cls) -> Dict[int, Dict[str, Any]]:
        """
        Выполняет ежедневное обновление для всех игроков.

        Returns:
            Dict[int, Dict[str, Any]]: Словарь с результатами обновления для каждого игрока
        """
        players = cls.get_all_players()
        results = {}

        for player in players:
            try:
                # Пропускаем игроков, неактивных более 7 дней
                days_inactive = (datetime.now() - player.last_active).days
                if days_inactive > 7:
                    continue

                # Выполняем обновление
                update_result = player.daily_update()

                # Проверяем прогресс проектов
                project_progress = player.check_project_progress()

                # Обрабатываем завершенные проекты
                completed_projects = project_progress.get("completed", [])
                for project in completed_projects:
                    project_name = project.get("name", "Неизвестный проект")
                    project_category = project.get("category", "Общий проект")
                    player.handle_project_completion(project_name, project_category)

                # Сохраняем результаты
                results[player.user_id] = {
                    "update": update_result,
                    "project_progress": project_progress
                }
            except Exception as e:
                logger.error(f"Ошибка при ежедневном обновлении игрока {player.user_id}: {e}")
                results[player.user_id] = {"error": str(e)}

        return results


# Экспортируем функции для удобного доступа
get_player = PlayerManager.get_player
get_player_by_username = PlayerManager.get_player_by_username
get_all_players = PlayerManager.get_all_players
reload_player = PlayerManager.reload_player
