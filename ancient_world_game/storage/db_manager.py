"""
db_manager.py - Основной модуль для управления SQLite базой данных.
Предоставляет базовые операции CRUD и обеспечивает доступ к базе данных.
"""

import sqlite3
import json
from typing import Dict, List, Tuple, Any, Optional, Union
import os
from datetime import datetime, date
from contextlib import contextmanager

from config import config
from utils import logger, log_function_call


class DBManager:
    """
    Класс для управления операциями с базой данных SQLite.
    Реализует паттерн Singleton для обеспечения единственного экземпляра.
    """
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DBManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.db_path = config.DB_PATH
        self._create_db_if_not_exists()
        self._initialized = True

    @log_function_call
    def _create_db_if_not_exists(self):
        """
        Создает базу данных и необходимые таблицы, если они не существуют.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Таблица игроков (стран)
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS players (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                country_name TEXT NOT NULL,
                created_at TEXT NOT NULL,
                last_active TEXT NOT NULL,
                goals_count INTEGER DEFAULT 0
            )
            ''')

            # Таблица характеристик стран
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS stats (
                user_id INTEGER,
                stat_name TEXT,
                value INTEGER NOT NULL,
                PRIMARY KEY (user_id, stat_name),
                FOREIGN KEY (user_id) REFERENCES players(user_id) ON DELETE CASCADE
            )
            ''')

            # Таблица для хранения игрового времени
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS game_time (
                key TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL
            )
            ''')

            # Таблица для хранения текущего состояния стран
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS country_state (
                user_id INTEGER,
                aspect TEXT,
                description TEXT NOT NULL,
                last_updated TEXT NOT NULL,
                PRIMARY KEY (user_id, aspect),
                FOREIGN KEY (user_id) REFERENCES players(user_id) ON DELETE CASCADE
            )
            ''')

            # Проверяем, существует ли запись о начале игры
            cursor.execute("SELECT timestamp FROM game_time WHERE key = 'game_start_time'")
            result = cursor.fetchone()

            # Если записи нет, добавляем её с текущим временем
            if not result:
                cursor.execute(
                    "INSERT INTO game_time (key, timestamp) VALUES (?, ?)",
                    ('game_start_time', datetime.now().isoformat())
                )

            # Проверяем, существует ли запись о последнем игровом дне
            cursor.execute("SELECT timestamp FROM game_time WHERE key = 'last_game_day'")
            result = cursor.fetchone()

            # Если записи нет, добавляем её с текущим временем
            if not result:
                cursor.execute(
                    "INSERT INTO game_time (key, timestamp) VALUES (?, ?)",
                    ('last_game_day', datetime.now().isoformat())
                )

            conn.commit()

    @contextmanager
    def get_connection(self):
        """
        Контекстный менеджер для подключения к базе данных.

        Yields:
            sqlite3.Connection: Объект подключения к базе данных
        """
        connection = None
        try:
            connection = sqlite3.connect(self.db_path)
            # Настраиваем соединение для возврата строк в виде словарей
            connection.row_factory = sqlite3.Row
            # Автоматическое применение внешних ключей
            connection.execute("PRAGMA foreign_keys = ON")
            yield connection
        except sqlite3.Error as e:
            logger.error(f"Ошибка при подключении к базе данных: {e}")
            raise
        finally:
            if connection:
                connection.close()

    @log_function_call
    def register_player(self, user_id: int, username: str, country_name: str) -> bool:
        """
        Регистрирует нового игрока (страну) в базе данных.

        Args:
            user_id: ID пользователя Telegram
            username: Имя пользователя Telegram
            country_name: Название страны

        Returns:
            bool: True если игрок успешно зарегистрирован, иначе False
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Проверяем, существует ли уже игрок с таким ID
                cursor.execute("SELECT user_id FROM players WHERE user_id = ?", (user_id,))
                if cursor.fetchone():
                    # Игрок уже существует, обновляем данные
                    cursor.execute(
                        "UPDATE players SET country_name = ?, last_active = ? WHERE user_id = ?",
                        (country_name, datetime.now().isoformat(), user_id)
                    )

                    # Удаляем старые статы
                    cursor.execute("DELETE FROM stats WHERE user_id = ?", (user_id,))

                    # Удаляем старое состояние страны
                    cursor.execute("DELETE FROM country_state WHERE user_id = ?", (user_id,))
                else:
                    # Регистрируем нового игрока
                    current_time = datetime.now().isoformat()
                    cursor.execute(
                        "INSERT INTO players (user_id, username, country_name, created_at, last_active) VALUES (?, ?, ?, ?, ?)",
                        (user_id, username, country_name, current_time, current_time)
                    )

                conn.commit()
                return True
        except sqlite3.Error as e:
            logger.error(f"Ошибка при регистрации игрока: {e}")
            return False

    @log_function_call
    def save_player_stats(self, user_id: int, stats: Dict[str, int]) -> bool:
        """
        Сохраняет характеристики страны игрока.

        Args:
            user_id: ID пользователя Telegram
            stats: Словарь характеристик {название: значение}

        Returns:
            bool: True если характеристики успешно сохранены, иначе False
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Удаляем существующие статы
                cursor.execute("DELETE FROM stats WHERE user_id = ?", (user_id,))

                # Добавляем новые статы
                for stat_name, value in stats.items():
                    cursor.execute(
                        "INSERT INTO stats (user_id, stat_name, value) VALUES (?, ?, ?)",
                        (user_id, stat_name.lower(), value)
                    )

                # Обновляем время последней активности
                cursor.execute(
                    "UPDATE players SET last_active = ? WHERE user_id = ?",
                    (datetime.now().isoformat(), user_id)
                )

                conn.commit()
                return True
        except sqlite3.Error as e:
            logger.error(f"Ошибка при сохранении характеристик игрока: {e}")
            return False

    @log_function_call
    def get_player_stats(self, user_id: int) -> Dict[str, int]:
        """
        Получает характеристики страны игрока.

        Args:
            user_id: ID пользователя Telegram

        Returns:
            Dict[str, int]: Словарь характеристик {название: значение}
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT stat_name, value FROM stats WHERE user_id = ?",
                    (user_id,)
                )

                stats = {}
                for row in cursor.fetchall():
                    stats[row['stat_name']] = row['value']

                return stats
        except sqlite3.Error as e:
            logger.error(f"Ошибка при получении характеристик игрока: {e}")
            return {}

    @log_function_call
    def get_player_info(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Получает основную информацию о стране игрока.

        Args:
            user_id: ID пользователя Telegram

        Returns:
            Optional[Dict[str, Any]]: Информация о стране или None, если игрок не найден
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM players WHERE user_id = ?",
                    (user_id,)
                )

                player = cursor.fetchone()
                if not player:
                    return None

                # Преобразуем sqlite3.Row в словарь
                player_dict = dict(player)

                # Получаем характеристики
                stats = self.get_player_stats(user_id)
                player_dict['stats'] = stats

                return player_dict
        except sqlite3.Error as e:
            logger.error(f"Ошибка при получении информации об игроке: {e}")
            return None

    @log_function_call
    def get_player_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Находит игрока по имени пользователя Telegram.

        Args:
            username: Имя пользователя Telegram (без @)

        Returns:
            Optional[Dict[str, Any]]: Информация об игроке или None, если не найден
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                # Ищем как с @, так и без @
                username_clean = username.lstrip('@')
                cursor.execute(
                    "SELECT * FROM players WHERE username = ? OR username = ?",
                    (username_clean, f"@{username_clean}")
                )

                player = cursor.fetchone()
                if not player:
                    return None

                # Преобразуем sqlite3.Row в словарь
                player_dict = dict(player)

                # Получаем характеристики
                stats = self.get_player_stats(player_dict['user_id'])
                player_dict['stats'] = stats

                return player_dict
        except sqlite3.Error as e:
            logger.error(f"Ошибка при поиске игрока по имени пользователя: {e}")
            return None

    @log_function_call
    def save_country_state(self, user_id: int, aspect: str, description: str) -> bool:
        """
        Сохраняет состояние определенного аспекта страны.

        Args:
            user_id: ID пользователя Telegram
            aspect: Название аспекта (экономика, военное дело и т.д.)
            description: Текстовое описание состояния

        Returns:
            bool: True если успешно сохранено, иначе False
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Проверяем, существует ли уже запись для этого аспекта
                cursor.execute(
                    "SELECT user_id FROM country_state WHERE user_id = ? AND aspect = ?",
                    (user_id, aspect)
                )

                current_time = datetime.now().isoformat()

                if cursor.fetchone():
                    # Обновляем существующую запись
                    cursor.execute(
                        "UPDATE country_state SET description = ?, last_updated = ? WHERE user_id = ? AND aspect = ?",
                        (description, current_time, user_id, aspect)
                    )
                else:
                    # Создаем новую запись
                    cursor.execute(
                        "INSERT INTO country_state (user_id, aspect, description, last_updated) VALUES (?, ?, ?, ?)",
                        (user_id, aspect, description, current_time)
                    )

                # Обновляем время последней активности
                cursor.execute(
                    "UPDATE players SET last_active = ? WHERE user_id = ?",
                    (current_time, user_id)
                )

                conn.commit()
                return True
        except sqlite3.Error as e:
            logger.error(f"Ошибка при сохранении состояния страны: {e}")
            return False

    @log_function_call
    def get_country_state(self, user_id: int, aspect: Optional[str] = None) -> Dict[str, str]:
        """
        Получает состояние страны по аспекту или все аспекты.

        Args:
            user_id: ID пользователя Telegram
            aspect: Название аспекта или None для всех аспектов

        Returns:
            Dict[str, str]: Словарь {аспект: описание}
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                if aspect:
                    # Получаем состояние конкретного аспекта
                    cursor.execute(
                        "SELECT aspect, description FROM country_state WHERE user_id = ? AND aspect = ?",
                        (user_id, aspect)
                    )
                else:
                    # Получаем состояние всех аспектов
                    cursor.execute(
                        "SELECT aspect, description FROM country_state WHERE user_id = ?",
                        (user_id,)
                    )

                state = {}
                for row in cursor.fetchall():
                    state[row['aspect']] = row['description']

                return state
        except sqlite3.Error as e:
            logger.error(f"Ошибка при получении состояния страны: {e}")
            return {}

    @log_function_call
    def update_goals_count(self, user_id: int, increment: int = 1) -> bool:
        """
        Обновляет счетчик забитых голов игрока.

        Args:
            user_id: ID пользователя Telegram
            increment: Величина инкремента (по умолчанию 1)

        Returns:
            bool: True если счетчик успешно обновлен, иначе False
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute(
                    "UPDATE players SET goals_count = goals_count + ? WHERE user_id = ?",
                    (increment, user_id)
                )

                conn.commit()
                return True
        except sqlite3.Error as e:
            logger.error(f"Ошибка при обновлении счетчика голов: {e}")
            return False

    @log_function_call
    def get_goals_count(self, user_id: int) -> int:
        """
        Получает количество забитых голов игрока.

        Args:
            user_id: ID пользователя Telegram

        Returns:
            int: Количество забитых голов
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute(
                    "SELECT goals_count FROM players WHERE user_id = ?",
                    (user_id,)
                )

                result = cursor.fetchone()
                return result['goals_count'] if result else 0
        except sqlite3.Error as e:
            logger.error(f"Ошибка при получении счетчика голов: {e}")
            return 0

    @log_function_call
    def is_player_registered(self, user_id: int) -> bool:
        """
        Проверяет, зарегистрирован ли игрок.

        Args:
            user_id: ID пользователя Telegram

        Returns:
            bool: True если игрок зарегистрирован, иначе False
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute(
                    "SELECT user_id FROM players WHERE user_id = ?",
                    (user_id,)
                )

                return cursor.fetchone() is not None
        except sqlite3.Error as e:
            logger.error(f"Ошибка при проверке регистрации игрока: {e}")
            return False

    @log_function_call
    def get_all_players(self) -> List[Dict[str, Any]]:
        """
        Получает список всех зарегистрированных игроков.

        Returns:
            List[Dict[str, Any]]: Список с информацией об игроках
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute("SELECT * FROM players ORDER BY country_name")

                players = []
                for row in cursor.fetchall():
                    player_dict = dict(row)
                    # Получаем характеристики для каждого игрока
                    stats = self.get_player_stats(player_dict['user_id'])
                    player_dict['stats'] = stats
                    players.append(player_dict)

                return players
        except sqlite3.Error as e:
            logger.error(f"Ошибка при получении списка игроков: {e}")
            return []

    @log_function_call
    def update_game_time(self, key: str, timestamp: Optional[datetime] = None) -> bool:
        """
        Обновляет запись о времени в игре.

        Args:
            key: Ключ записи ('game_start_time', 'last_game_day')
            timestamp: Объект datetime или None для текущего времени

        Returns:
            bool: True если время успешно обновлено, иначе False
        """
        if timestamp is None:
            timestamp = datetime.now()

        timestamp_str = timestamp.isoformat()

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute(
                    "UPDATE game_time SET timestamp = ? WHERE key = ?",
                    (timestamp_str, key)
                )

                if cursor.rowcount == 0:
                    cursor.execute(
                        "INSERT INTO game_time (key, timestamp) VALUES (?, ?)",
                        (key, timestamp_str)
                    )

                conn.commit()
                return True
        except sqlite3.Error as e:
            logger.error(f"Ошибка при обновлении игрового времени: {e}")
            return False

    @log_function_call
    def get_game_time(self, key: str) -> Optional[datetime]:
        """
        Получает запись о времени в игре.

        Args:
            key: Ключ записи ('game_start_time', 'last_game_day')

        Returns:
            Optional[datetime]: Объект datetime или None, если запись не найдена
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute(
                    "SELECT timestamp FROM game_time WHERE key = ?",
                    (key,)
                )

                result = cursor.fetchone()
                if result:
                    return datetime.fromisoformat(result['timestamp'])
                return None
        except sqlite3.Error as e:
            logger.error(f"Ошибка при получении игрового времени: {e}")
            return None

    @log_function_call
    def admin_edit_country(self, user_id: int, field: str, value: Any) -> bool:
        """
        Административное редактирование параметров страны.

        Args:
            user_id: ID пользователя Telegram
            field: Название поля для редактирования
            value: Новое значение

        Returns:
            bool: True если редактирование успешно, иначе False
        """
        try:
            # Обработка различных типов полей
            if field.lower() in ['экономика', 'военное дело', 'религия и культура',
                                 'управление и право', 'строительство и инфраструктура',
                                 'внешняя политика', 'общественные отношения',
                                 'территория', 'технологичность']:
                # Это характеристика (стат)
                return self.save_player_stats(user_id, {field.lower(): int(value)})

            elif field.lower() in ['золото', 'goals_count']:
                # Эти поля в таблице players
                with self.get_connection() as conn:
                    cursor = conn.cursor()

                    if field.lower() == 'золото':
                        # Сохраняем золото в описании экономики
                        state = self.get_country_state(user_id, 'экономика')
                        description = state.get('экономика', '')
                        # Добавляем или обновляем информацию о золоте
                        if 'золото:' in description:
                            description = re.sub(r'золото: \d+', f'золото: {value}', description)
                        else:
                            description += f"\nзолото: {value}"

                        return self.save_country_state(user_id, 'экономика', description)
                    else:
                        # Обновляем goals_count
                        cursor.execute(
                            f"UPDATE players SET {field.lower()} = ? WHERE user_id = ?",
                            (value, user_id)
                        )

                        conn.commit()
                        return True

            else:
                # Предполагаем, что это один из аспектов государства
                return self.save_country_state(user_id, field.lower(), str(value))

        except (sqlite3.Error, ValueError) as e:
            logger.error(f"Ошибка при административном редактировании страны: {e}")
            return False


# Создаем экземпляр менеджера БД при импорте модуля
db = DBManager()


def get_db() -> DBManager:
    """
    Функция для получения экземпляра менеджера БД.

    Returns:
        DBManager: Экземпляр менеджера базы данных
    """
    return db
