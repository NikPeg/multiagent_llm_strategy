"""
model_interface.py - Интерфейс для взаимодействия с локальной моделью DeepSeek.
Обеспечивает унифицированный доступ к языковой модели для всего приложения.
"""

import os
import time
from typing import Dict, List, Optional, Any, Union, Tuple
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
import numpy as np
from concurrent.futures import ThreadPoolExecutor
import threading

from config import config
from utils import logger, log_function_call, measure_execution_time


class DeepSeekModel:
    """
    Класс для взаимодействия с моделью DeepSeek-R1-Distill-Qwen-32B.
    Реализует паттерн Singleton для обеспечения единственного экземпляра модели.
    """
    _instance = None
    _lock = threading.Lock()
    _model = None
    _tokenizer = None
    _generation_pipe = None
    _embedding_pipe = None

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(DeepSeekModel, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.model_path = config.MODEL_PATH
        self.max_tokens = config.MODEL_MAX_TOKENS
        self.temperature = config.MODEL_TEMPERATURE
        self.threads = config.THREADS
        self.gpu_layers = config.GPU_LAYERS

        self._initialize_model()
        self._initialized = True

    @log_function_call
    def _initialize_model(self):
        """
        Инициализирует модель DeepSeek с использованием HuggingFace Transformers.
        """
        logger.info(f"Инициализация модели DeepSeek из {self.model_path}")
        try:
            # Проверяем доступность GPU
            if torch.cuda.is_available():
                logger.info(f"Обнаружен GPU: {torch.cuda.get_device_name(0)}")
                device = "cuda"
            else:
                logger.info("GPU не обнаружен, используем CPU")
                device = "cpu"

            # Загружаем токенизатор
            self._tokenizer = AutoTokenizer.from_pretrained(
                self.model_path,
                trust_remote_code=True
            )

            # Загружаем модель
            self._model = AutoModelForCausalLM.from_pretrained(
                self.model_path,
                device_map="auto",  # Автоматически распределяет модель между доступными устройствами
                torch_dtype=torch.float16,  # Используем half precision для экономии памяти
                trust_remote_code=True
            )

            # Создаем pipeline для генерации текста
            self._generation_pipe = pipeline(
                "text-generation",
                model=self._model,
                tokenizer=self._tokenizer,
                device=device
            )

            logger.info("Модель успешно инициализирована")
        except Exception as e:
            logger.error(f"Ошибка при инициализации модели: {e}")
            raise

    @measure_execution_time
    @log_function_call
    def generate_response(self, prompt: str, max_tokens: Optional[int] = None,
                          temperature: Optional[float] = None) -> str:
        """
        Генерирует ответ модели на заданный промпт.

        Args:
            prompt: Текстовый промпт для модели
            max_tokens: Максимальное количество токенов для генерации (опционально)
            temperature: Температура генерации (опционально)

        Returns:
            str: Сгенерированный моделью ответ
        """
        try:
            # Используем дефолтные значения, если не указаны явно
            max_tokens = max_tokens or self.max_tokens
            temperature = temperature or self.temperature

            start_time = time.time()

            # Генерируем ответ
            outputs = self._generation_pipe(
                prompt,
                max_new_tokens=max_tokens,
                temperature=temperature,
                num_return_sequences=1,
                do_sample=temperature > 0.1,  # Используем sampling только при ненулевой температуре
                pad_token_id=self._tokenizer.eos_token_id
            )

            generation_time = time.time() - start_time
            logger.info(f"Генерация ответа заняла {generation_time:.2f} секунд")

            # Извлекаем ответ модели, обычно это часть после промпта
            generated_text = outputs[0]['generated_text']

            # Удаляем исходный промпт из ответа
            if generated_text.startswith(prompt):
                response = generated_text[len(prompt):].strip()
            else:
                response = generated_text.strip()

            return response
        except Exception as e:
            logger.error(f"Ошибка при генерации ответа: {e}")
            return f"Произошла ошибка при генерации ответа: {str(e)}"

    @measure_execution_time
    @log_function_call
    def check_era_compatibility(self, message: str) -> Tuple[bool, str]:
        """
        Проверяет, соответствует ли сообщение игрока эпохе древнего мира.

        Args:
            message: Сообщение игрока

        Returns:
            Tuple[bool, str]: (соответствует ли сообщение эпохе, комментарий)
        """
        prompt = f"""Ты - исторический консультант игры, действие которой происходит в древнем мире (примерно 3000 г. до н.э. - 500 г. н.э.).
        
Проверь, соответствует ли следующее сообщение игрока эпохе древнего мира:

"{message}"

Ответь в формате:
СООТВЕТСТВУЕТ: да/нет
КОММЕНТАРИЙ: [объяснение, почему сообщение соответствует или не соответствует эпохе]
"""

        response = self.generate_response(prompt, max_tokens=300, temperature=0.3)

        # Парсим ответ
        lines = response.strip().split('\n')
        is_compatible = False
        comment = "Не удалось определить соответствие эпохе"

        for line in lines:
            if line.lower().startswith("соответствует:"):
                answer = line.split(":", 1)[1].strip().lower()
                is_compatible = answer == "да"
            elif line.lower().startswith("комментарий:"):
                comment = line.split(":", 1)[1].strip()

        return is_compatible, comment

    @measure_execution_time
    @log_function_call
    def analyze_player_action(self, user_id: int, country_name: str, action: str,
                              country_context: str) -> Dict[str, Any]:
        """
        Анализирует действие игрока и определяет его влияние на страну.

        Args:
            user_id: ID пользователя
            country_name: Название страны
            action: Текст действия игрока
            country_context: Контекст о текущем состоянии страны из RAG

        Returns:
            Dict[str, Any]: Словарь с результатами анализа и влиянием на аспекты страны
        """
        prompt = f"""Ты - игровой мастер исторической стратегии, действие которой происходит в древнем мире.
        
Вот текущая информация о стране:
{country_context}

Игрок, правитель страны {country_name}, отдал следующий приказ:
"{action}"

Проанализируй, как этот приказ повлияет на разные аспекты страны.

Ответь в следующем формате:
ВЫПОЛНЕНИЕ: [краткое описание того, как приказ был выполнен]
РЕЗУЛЬТАТ: [описание непосредственного результата]
ПОСЛЕДСТВИЯ: [описание долгосрочных последствий]
ИЗМЕНЕНИЯ:
- экономика: [краткое описание изменений в экономике]
- военное дело: [краткое описание изменений в военном деле]
- религия и культура: [краткое описание изменений в религии и культуре]
- управление и право: [краткое описание изменений в управлении и праве]
- строительство и инфраструктура: [краткое описание изменений в строительстве и инфраструктуре]
- внешняя политика: [краткое описание изменений во внешней политике]
- общественные отношения: [краткое описание изменений в общественных отношениях]
- территория: [краткое описание изменений в территории]
- технологичность: [краткое описание изменений в технологиях]
"""

        response = self.generate_response(prompt, max_tokens=1000, temperature=0.7)

        # Парсим ответ
        result = {
            "execution": "",
            "result": "",
            "consequences": "",
            "changes": {}
        }

        current_section = None
        changes_section = False

        for line in response.strip().split("\n"):
            line = line.strip()
            if not line:
                continue

            if line.startswith("ВЫПОЛНЕНИЕ:"):
                current_section = "execution"
                result[current_section] = line.split(":", 1)[1].strip()
            elif line.startswith("РЕЗУЛЬТАТ:"):
                current_section = "result"
                result[current_section] = line.split(":", 1)[1].strip()
            elif line.startswith("ПОСЛЕДСТВИЯ:"):
                current_section = "consequences"
                result[current_section] = line.split(":", 1)[1].strip()
            elif line.startswith("ИЗМЕНЕНИЯ:"):
                changes_section = True
                current_section = None
            elif changes_section and line.startswith("-"):
                # Парсим изменения в аспектах
                parts = line[1:].strip().split(":", 1)
                if len(parts) == 2:
                    aspect = parts[0].strip()
                    change = parts[1].strip()
                    result["changes"][aspect] = change
            elif current_section:
                # Добавляем текст к текущему разделу
                result[current_section] += " " + line

        return result

    @measure_execution_time
    @log_function_call
    def update_country_state(self, user_id: int, country_name: str, aspect: str,
                             current_state: str, action_impact: str) -> str:
        """
        Обновляет состояние определенного аспекта страны на основе воздействия действия.

        Args:
            user_id: ID пользователя
            country_name: Название страны
            aspect: Название аспекта (экономика, военное дело и т.д.)
            current_state: Текущее состояние аспекта
            action_impact: Описание воздействия действия на аспект

        Returns:
            str: Обновленное состояние аспекта
        """
        prompt = f"""Ты - летописец древнего мира, записывающий историю страны {country_name}.

Текущее состояние {aspect} страны:
{current_state if current_state else "Нет данных"}

Недавно произошли следующие изменения:
{action_impact}

Напиши обновленное состояние {aspect} страны, учитывая текущее состояние и произошедшие изменения.
Отвечай только обновленным состоянием без дополнительных комментариев и заголовков.
"""

        response = self.generate_response(prompt, max_tokens=500, temperature=0.5)
        return response.strip()

    @measure_execution_time
    @log_function_call
    def evaluate_country_stats(self, user_id: int, country_name: str,
                               country_state: Dict[str, str]) -> Dict[str, int]:
        """
        Оценивает числовые характеристики страны на основе текстовых описаний.

        Args:
            user_id: ID пользователя
            country_name: Название страны
            country_state: Словарь с текстовыми описаниями аспектов

        Returns:
            Dict[str, int]: Словарь с оценками характеристик от 1 до 5
        """
        # Формируем единый текст с описаниями всех аспектов
        state_text = ""
        for aspect, description in country_state.items():
            state_text += f"\n\n{aspect.upper()}:\n{description}"

        prompt = f"""Ты - мудрый советник, оценивающий могущество страны {country_name}.

На основе следующей информации о стране, оцени каждый аспект по шкале от 1 до 5, где 1 - очень слабо, 5 - очень сильно:

{state_text}

Дай свою оценку в следующем формате (только цифры от 1 до 5):

экономика: [оценка]
военное дело: [оценка]
религия и культура: [оценка]
управление и право: [оценка]
строительство и инфраструктура: [оценка]
внешняя политика: [оценка]
общественные отношения: [оценка]
территория: [оценка]
технологичность: [оценка]
"""

        response = self.generate_response(prompt, max_tokens=300, temperature=0.3)

        # Парсим оценки из ответа
        stats = {}

        for line in response.strip().split("\n"):
            line = line.strip()
            if ":" in line:
                parts = line.split(":", 1)
                aspect = parts[0].strip().lower()

                # Извлекаем числовое значение
                try:
                    value_str = parts[1].strip()
                    # Ищем первую цифру в строке
                    for char in value_str:
                        if char.isdigit() and int(char) >= 1 and int(char) <= 5:
                            stats[aspect] = int(char)
                            break
                    else:
                        # Если не нашли подходящую цифру, используем значение 3
                        stats[aspect] = 3
                except:
                    stats[aspect] = 3

        # Проверяем, что все аспекты получили оценку
        for aspect in ["экономика", "военное дело", "религия и культура",
                       "управление и право", "строительство и инфраструктура",
                       "внешняя политика", "общественные отношения",
                       "территория", "технологичность"]:
            if aspect not in stats:
                stats[aspect] = 3  # Значение по умолчанию

        return stats

    @measure_execution_time
    @log_function_call
    def generate_country_problems(self, user_id: int, country_name: str,
                                  country_context: str) -> List[str]:
        """
        Генерирует список текущих проблем страны на основе контекста.

        Args:
            user_id: ID пользователя
            country_name: Название страны
            country_context: Контекст о стране

        Returns:
            List[str]: Список проблем
        """
        prompt = f"""Ты - советник правителя страны {country_name} в древнем мире.

Вот информация о состоянии страны:
{country_context}

Определи 3-5 наиболее острых проблем, с которыми сталкивается страна в данный момент.
Перечисли их в виде списка, каждая проблема должна быть на отдельной строке и начинаться с тире (-).
"""

        response = self.generate_response(prompt, max_tokens=500, temperature=0.7)

        # Извлекаем проблемы из ответа
        problems = []
        for line in response.strip().split("\n"):
            line = line.strip()
            if line.startswith("-"):
                problem = line[1:].strip()
                if problem:
                    problems.append(problem)

        # Если не нашли проблем в нужном формате, пробуем извлечь их по-другому
        if not problems:
            for line in response.strip().split("\n"):
                line = line.strip()
                if len(line) > 10 and not line.lower().startswith(("вот", "проблемы", "основные", "главные")):
                    problems.append(line)

        # Ограничиваем количество проблем
        return problems[:5]

    @measure_execution_time
    @log_function_call
    def generate_event(self, user_id: int, country_name: str, event_type: str,
                       country_context: str) -> Dict[str, Any]:
        """
        Генерирует случайное событие для страны.

        Args:
            user_id: ID пользователя
            country_name: Название страны
            event_type: Тип события (очень плохое, плохое, нейтральное, хорошее, очень хорошее)
            country_context: Контекст о стране

        Returns:
            Dict[str, Any]: Словарь с информацией о событии
        """
        event_descriptions = {
            "очень плохую": "катастрофическое событие, которое серьезно негативно повлияет на страну",
            "плохую": "негативное событие, которое создаст проблемы для страны",
            "нейтральную": "событие, которое имеет как положительные, так и отрицательные аспекты",
            "хорошую": "позитивное событие, которое принесет пользу стране",
            "очень хорошую": "чрезвычайно благоприятное событие, которое значительно улучшит положение страны"
        }

        event_description = event_descriptions.get(event_type, "нейтральное событие")

        prompt = f"""Ты - оракул древнего мира, предсказывающий события для страны {country_name}.

Вот текущая информация о стране:
{country_context}

Создай {event_type} новость для страны. Это должно быть {event_description}.
Убедись, что событие соответствует реалиям древнего мира и текущему состоянию страны.

Ответь в следующем формате:
ЗАГОЛОВОК: [краткий заголовок события]
СОБЫТИЕ: [подробное описание события]
ПОСЛЕДСТВИЯ: [как это событие повлияет на страну]
ЗАТРОНУТЫЕ АСПЕКТЫ:
- [название аспекта]: [как именно затронут аспект]
"""

        response = self.generate_response(prompt, max_tokens=800, temperature=0.8)

        # Парсим ответ
        event = {
            "title": "",
            "description": "",
            "consequences": "",
            "affected_aspects": {}
        }

        current_section = None
        affected_aspects_section = False

        for line in response.strip().split("\n"):
            line = line.strip()
            if not line:
                continue

            if line.startswith("ЗАГОЛОВОК:"):
                current_section = "title"
                event[current_section] = line.split(":", 1)[1].strip()
            elif line.startswith("СОБЫТИЕ:"):
                current_section = "description"
                event[current_section] = line.split(":", 1)[1].strip()
            elif line.startswith("ПОСЛЕДСТВИЯ:"):
                current_section = "consequences"
                event[current_section] = line.split(":", 1)[1].strip()
            elif line.startswith("ЗАТРОНУТЫЕ АСПЕКТЫ:"):
                affected_aspects_section = True
                current_section = None
            elif affected_aspects_section and line.startswith("-"):
                # Парсим затронутые аспекты
                parts = line[1:].strip().split(":", 1)
                if len(parts) == 2:
                    aspect = parts[0].strip()
                    impact = parts[1].strip()
                    event["affected_aspects"][aspect] = impact
            elif current_section:
                # Добавляем текст к текущему разделу
                event[current_section] += " " + line

        # Добавляем тип события
        event["type"] = event_type

        # Если не удалось распарсить заголовок, используем дефолтный
        if not event["title"]:
            event_titles = {
                "очень плохую": "Катастрофа обрушилась на страну",
                "плохую": "Проблемы настигли страну",
                "нейтральную": "Новые события в стране",
                "хорошую": "Благоприятные вести для страны",
                "очень хорошую": "Великая удача улыбнулась стране"
            }
            event["title"] = event_titles.get(event_type, "Новое событие в стране")

        return event

    @measure_execution_time
    @log_function_call
    def predict_future(self, user_id: int, country_name: str, country_context: str) -> str:
        """
        Генерирует предсказание о будущем страны.

        Args:
            user_id: ID пользователя
            country_name: Название страны
            country_context: Контекст о состоянии страны

        Returns:
            str: Предсказание о будущем страны
        """
        prompt = f"""Ты - провидец древнего мира, способный заглянуть в будущее страны {country_name}.

Вот информация о текущем состоянии страны:
{country_context}

Составь краткое поэтическое предсказание о том, что ждет страну в ближайшее время.
Предсказание должно быть туманным и загадочным, как и положено настоящему оракулу,
но содержать намеки на возможные события, основанные на текущем положении дел.

Ответ дай от первого лица, как будто ты вещаешь правителю этой страны.
"""

        response = self.generate_response(prompt, max_tokens=400, temperature=0.9)
        return response.strip()


# Создаем экземпляр модели при импорте модуля
model = DeepSeekModel()


def get_model() -> DeepSeekModel:
    """
    Функция для получения экземпляра модели.

    Returns:
        DeepSeekModel: Экземпляр модели DeepSeek
    """
    return model
