"""
time_utils.py - Утилиты для работы с игровым временем.
Предоставляет функции для управления игровыми годами, отслеживания
и расчета длительности проектов и игровых событий.
"""

import time
import os
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Tuple, List, Optional, Union
import calendar
from functools import wraps
import threading
import heapq

# Константы для работы с игровым временем
REAL_DAY_TO_GAME_YEAR = 1  # 1 реальный день = 1 игровой год
START_GAME_YEAR = -3000  # Начальный год для игры (3000 г. до н.э.)

# Путь к базе данных
DB_PATH = 'game_data.db'


def _init_time_db():
    """
    Инициализирует базу данных для хранения игрового времени.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Создаем таблицу для хранения временных меток
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS game_time (
        key TEXT PRIMARY KEY,
        timestamp TEXT NOT NULL
    )
    ''')

    # Проверяем, существует ли запись о начале игры
    cursor.execute("SELECT timestamp FROM game_time WHERE key = 'game_start_time'")
    result = cursor.fetchone()

    # Если записи нет, добавляем ее с текущим временем
    if not result:
        cursor.execute(
            "INSERT INTO game_time (key, timestamp) VALUES (?, ?)",
            ('game_start_time', datetime.now().isoformat())
        )

    # Проверяем, существует ли запись о последнем игровом дне
    cursor.execute("SELECT timestamp FROM game_time WHERE key = 'last_game_day'")
    result = cursor.fetchone()

    # Если записи нет, добавляем ее с текущим временем
    if not result:
        cursor.execute(
            "INSERT INTO game_time (key, timestamp) VALUES (?, ?)",
            ('last_game_day', datetime.now().isoformat())
        )

    conn.commit()
    conn.close()


def get_current_game_year() -> int:
    """
    Возвращает текущий игровой год, рассчитанный на основе
    времени с момента запуска игры.

    Returns:
        Текущий игровой год (отрицательные значения для периода до н.э.)
    """
    # Получаем дату начала игры из базы данных
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT timestamp FROM game_time WHERE key = 'game_start_time'")
    result = cursor.fetchone()
    conn.close()

    if result:
        game_start_time = datetime.fromisoformat(result[0])
    else:
        # Если запись не найдена, инициализируем базу и пробуем снова
        _init_time_db()
        return get_current_game_year()

    # Разница в днях между текущей датой и датой начала игры
    days_diff = (datetime.now() - game_start_time).days

    # Рассчитываем текущий игровой год
    current_game_year = START_GAME_YEAR + (days_diff * REAL_DAY_TO_GAME_YEAR)

    return current_game_year


def format_game_year(year: int) -> str:
    """
    Форматирует игровой год в читаемый вид.

    Args:
        year: Игровой год

    Returns:
        Отформатированная строка с годом
    """
    if year < 0:
        return f"{abs(year)} г. до н.э."
    else:
        return f"{year} г. н.э."


def calculate_project_duration(project_type: str, scale: int,
                               technology_level: int) -> int:
    """
    Рассчитывает продолжительность проекта в игровых годах.

    Args:
        project_type: Тип проекта (строительство, исследование и т.д.)
        scale: Масштаб проекта (1-5)
        technology_level: Уровень технологического развития (1-5)

    Returns:
        Количество игровых лет для завершения проекта
    """
    # Базовые длительности для разных типов проектов
    base_durations = {
        "строительство": 10,      # Базовое время строительства
        "исследование": 5,        # Базовое время исследования
        "военная подготовка": 3,  # Базовое время военной подготовки
        "религиозный проект": 7,  # Базовое время религиозного проекта
        "инфраструктура": 8,      # Базовое время инфраструктурного проекта
        "экономический проект": 6, # Базовое время экономического проекта
    }

    # Если тип проекта не известен, используем среднее значение
    base_duration = base_durations.get(project_type.lower(), 7)

    # Масштаб увеличивает время, технологический уровень уменьшает
    # Формула: базовое_время * (масштаб/2) / (тех_уровень/3)
    duration = base_duration * (scale / 2) / (technology_level / 3)

    # Округляем до целого числа лет и обеспечиваем минимальную длительность
    return max(1, round(duration))


def estimate_project_completion_year(start_year: int, duration: int) -> int:
    """
    Рассчитывает год завершения проекта.

    Args:
        start_year: Год начала проекта
        duration: Продолжительность проекта в годах

    Returns:
        Год завершения проекта
    """
    return start_year + duration


def calculate_project_progress(start_year: int, total_duration: int) -> Tuple[int, int]:
    """
    Рассчитывает текущий прогресс проекта и оставшиеся годы.

    Args:
        start_year: Год начала проекта
        total_duration: Общая продолжительность проекта в годах

    Returns:
        Кортеж (процент завершения, оставшиеся годы)
    """
    current_year = get_current_game_year()
    years_passed = current_year - start_year

    if years_passed >= total_duration:
        return 100, 0

    remaining_years = total_duration - years_passed
    progress_percent = min(100, int((years_passed / total_duration) * 100))

    return progress_percent, remaining_years


class GameScheduler:
    """
    Планировщик задач на основе игрового времени.
    Позволяет планировать события на определенные игровые годы.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """
        Реализует паттерн Singleton для планировщика.
        """
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(GameScheduler, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        """
        Инициализирует планировщик, если он еще не инициализирован.
        """
        if self._initialized:
            return

        self._event_queue = []  # Очередь (в виде кучи) для событий
        self._events_by_id = {}  # Словарь для быстрого доступа к событиям по ID
        self._last_event_id = 0  # Счетчик для генерации уникальных ID
        self._stop_flag = False  # Флаг для остановки потока
        self._thread = None  # Поток для проверки событий

        # Инициализируем базу данных для хранения событий
        self._init_db()

        self._initialized = True

    def _init_db(self):
        """
        Инициализирует таблицу для хранения запланированных событий.
        """
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Создаем таблицу для хранения событий
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS scheduled_events (
            id INTEGER PRIMARY KEY,
            year INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            params TEXT,
            created_at TEXT NOT NULL,
            executed BOOLEAN DEFAULT 0
        )
        ''')

        # Получаем последний использованный ID
        cursor.execute("SELECT MAX(id) FROM scheduled_events")
        last_id = cursor.fetchone()[0]
        if last_id:
            self._last_event_id = last_id

        conn.commit()
        conn.close()

    def start(self):
        """
        Запускает планировщик в отдельном потоке.
        """
        if self._thread is not None and self._thread.is_alive():
            return

        self._stop_flag = False
        self._thread = threading.Thread(target=self._check_events_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """
        Останавливает планировщик.
        """
        self._stop_flag = True
        if self._thread is not None:
            self._thread.join(timeout=1.0)

    def schedule_event(self, event_year: int, event_type: str, **params) -> int:
        """
        Планирует событие на определенный игровой год.

        Args:
            event_year: Игровой год для события
            event_type: Тип события (например, 'project_complete', 'population_growth')
            **params: Параметры события в формате ключ-значение

        Returns:
            ID запланированного события
        """
        import json

        with self._lock:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

            # Увеличиваем счетчик ID
            self._last_event_id += 1
            event_id = self._last_event_id

            # Сохраняем событие в базе данных
            cursor.execute(
                "INSERT INTO scheduled_events (id, year, event_type, params, created_at) VALUES (?, ?, ?, ?, ?)",
                (event_id, event_year, event_type, json.dumps(params), datetime.now().isoformat())
            )

            conn.commit()
            conn.close()

            # Добавляем в очередь
            heapq.heappush(self._event_queue, (event_year, event_id))

            return event_id

    def cancel_event(self, event_id: int) -> bool:
        """
        Отменяет запланированное событие по его ID.

        Args:
            event_id: ID события

        Returns:
            True если событие было найдено и отменено, иначе False
        """
        with self._lock:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

            # Проверяем, существует ли событие
            cursor.execute("SELECT id FROM scheduled_events WHERE id = ? AND executed = 0", (event_id,))
            if not cursor.fetchone():
                conn.close()
                return False

            # Удаляем событие из базы
            cursor.execute("DELETE FROM scheduled_events WHERE id = ?", (event_id,))
            conn.commit()
            conn.close()

            # Событие остается в очереди, но будет пропущено при проверке
            return True

    def _check_events_loop(self):
        """
        Цикл проверки событий, запускается в отдельном потоке.
        """
        import json

        while not self._stop_flag:
            current_year = get_current_game_year()

            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

            # Получаем все события, которые должны быть выполнены
            cursor.execute(
                "SELECT id, event_type, params FROM scheduled_events WHERE year <= ? AND executed = 0",
                (current_year,)
            )
            events_to_execute = cursor.fetchall()

            # Обрабатываем каждое событие
            for event_id, event_type, params_json in events_to_execute:
                # Отмечаем событие как выполненное
                cursor.execute(
                    "UPDATE scheduled_events SET executed = 1 WHERE id = ?",
                    (event_id,)
                )

                # Выполняем соответствующее действие в зависимости от типа события
                try:
                    params = json.loads(params_json) if params_json else {}
                    # Здесь должна быть логика обработки разных типов событий
                    # В реальном коде нужно заменить print на вызов соответствующих функций
                    print(f"Executing event {event_type} with params {params}")

                    # TODO: Добавить обработчики для разных типов событий
                    # Например: if event_type == 'project_complete': handle_project_completion(**params)

                except Exception as e:
                    print(f"Error executing scheduled event {event_id}: {e}")

            conn.commit()
            conn.close()

            # Спим перед следующей проверкой
            time.sleep(60)  # Проверяем каждую минуту

    def get_pending_events(self) -> List[Dict]:
        """
        Возвращает список ожидающих событий.

        Returns:
            Список словарей с информацией о событиях
        """
        import json

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id, year, event_type, params FROM scheduled_events WHERE executed = 0 ORDER BY year"
        )
        events = cursor.fetchall()

        conn.close()

        result = []
        for event_id, year, event_type, params_json in events:
            params = json.loads(params_json) if params_json else {}
            result.append({
                'id': event_id,
                'year': year,
                'event_type': event_type,
                'params': params
            })

        return result


def format_time_period(years: int) -> str:
    """
    Форматирует период времени в игровых годах.

    Args:
        years: Количество лет

    Returns:
        Отформатированная строка с периодом
    """
    if years <= 0:
        return "менее года"

    if years == 1:
        return "1 год"
    elif years < 5:
        return f"{years} года"
    else:
        return f"{years} лет"


def days_since_real_start() -> int:
    """
    Возвращает количество дней с момента фактического начала игры.

    Returns:
        Количество дней
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT timestamp FROM game_time WHERE key = 'game_start_time'")
    result = cursor.fetchone()

    conn.close()

    if not result:
        # Если запись не найдена, инициализируем базу и возвращаем 0
        _init_time_db()
        return 0

    game_start_time = datetime.fromisoformat(result[0])
    # Разница в днях
    days_diff = (datetime.now() - game_start_time).days
    return days_diff


def is_new_game_day() -> bool:
    """
    Проверяет, наступил ли новый игровой день/год.
    Используется для запуска ежедневных обновлений.

    Returns:
        True если сегодня новый игровой день
    """
    current_date = datetime.now().date()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT timestamp FROM game_time WHERE key = 'last_game_day'")
    result = cursor.fetchone()

    if not result:
        # Если запись не найдена, инициализируем базу
        conn.close()
        _init_time_db()
        return True

    last_day = datetime.fromisoformat(result[0]).date()

    if current_date > last_day:
        # Обновляем дату последнего дня
        cursor.execute(
            "UPDATE game_time SET timestamp = ? WHERE key = 'last_game_day'",
            (datetime.now().isoformat(),)
        )
        conn.commit()
        conn.close()
        return True

    conn.close()
    return False


def measure_execution_time(func):
    """
    Декоратор для измерения времени выполнения функции.

    Args:
        func: Декорируемая функция

    Returns:
        Обертка, измеряющая время выполнения
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        execution_time = (end_time - start_time) * 1000  # в миллисекундах
        print(f"Функция {func.__name__} выполнилась за {execution_time:.2f} мс")
        return result
    return wrapper


def reset_game_time():
    """
    Сбрасывает игровое время, начиная новую игру с текущего момента.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    current_time = datetime.now().isoformat()

    # Обновляем время начала игры
    cursor.execute(
        "UPDATE game_time SET timestamp = ? WHERE key = 'game_start_time'",
        (current_time,)
    )

    # Обновляем время последнего игрового дня
    cursor.execute(
        "UPDATE game_time SET timestamp = ? WHERE key = 'last_game_day'",
        (current_time,)
    )

    # Очищаем все запланированные события
    cursor.execute("DELETE FROM scheduled_events")

    conn.commit()
    conn.close()

    print(f"Игровое время сброшено. Новый игровой год: {format_game_year(get_current_game_year())}")


# Инициализация при импорте
if __name__ != "__main__":
    # Проверяем, существует ли база данных, и инициализируем таблицы
    _init_time_db()
