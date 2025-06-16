import aiosqlite
from typing import List, Optional, Any

ASPECT_CODES = [
    "экономика",
    "военное_дело",
    "внеш_политика",
    "территория",
    "технологичность",
    "религия_культура",
    "управление",
    "стройка",
    "общество",
]
# Если меняется порядок или список аспектов — поправь оба файла

async def init_db():
    async with aiosqlite.connect("chats.db") as db:
        # Таблица для истории чатов
        await db.execute(
            """CREATE TABLE IF NOT EXISTS chats (
                user_id INTEGER PRIMARY KEY,
                history TEXT
            )"""
        )
        # Таблица для пользователя и описания страны
        await db.execute(
            f"""CREATE TABLE IF NOT EXISTS user_states (
                user_id INTEGER PRIMARY KEY,
                country TEXT,
                country_desc TEXT,
                aspect_index INTEGER,
                {" ,".join([f'"{a}" TEXT' for a in ASPECT_CODES])}
            )"""
        )
        await db.commit()

# ==== История чатов ====

import json

async def get_history(user_id: int) -> List[str]:
    async with aiosqlite.connect("chats.db") as db:
        async with db.execute(
                "SELECT history FROM chats WHERE user_id = ?",
                (user_id,)
        ) as cursor:
            result = await cursor.fetchone()
            return json.loads(result[0]) if result else []

async def update_history(user_id: int, message: str, response: str, history_limit: int):
    history = await get_history(user_id)
    history.extend([f"Игрок: {message}", f"Ассистент: {response}"])
    history = history[-history_limit:]

    async with aiosqlite.connect("chats.db") as db:
        await db.execute(
            "INSERT OR REPLACE INTO chats (user_id, history) VALUES (?, ?)",
            (user_id, json.dumps(history))
        )
        await db.commit()

async def clear_history(user_id: int):
    async with aiosqlite.connect("chats.db") as db:
        await db.execute("DELETE FROM chats WHERE user_id = ?", (user_id,))
        await db.commit()

# ==== Страна, описание, индекс аспекта ====

async def get_user_country(user_id: int) -> Optional[str]:
    async with aiosqlite.connect("chats.db") as db:
        async with db.execute(
                "SELECT country FROM user_states WHERE user_id = ?",
                (user_id,)
        ) as cursor:
            result = await cursor.fetchone()
            return result[0] if result else None

async def set_user_country(user_id: int, country: Optional[str]):
    async with aiosqlite.connect("chats.db") as db:
        if country is None:
            await db.execute("UPDATE user_states SET country = NULL WHERE user_id = ?", (user_id,))
        else:
            await db.execute(
                """INSERT INTO user_states (user_id, country)
                   VALUES (?, ?)
                   ON CONFLICT(user_id) DO UPDATE SET country=excluded.country""",
                (user_id, country)
            )
        await db.commit()

async def get_user_country_desc(user_id: int) -> Optional[str]:
    async with aiosqlite.connect("chats.db") as db:
        async with db.execute(
                "SELECT country_desc FROM user_states WHERE user_id = ?",
                (user_id,)
        ) as cursor:
            result = await cursor.fetchone()
            return result[0] if result else None

async def set_user_country_desc(user_id: int, country_desc: Optional[str]):
    async with aiosqlite.connect("chats.db") as db:
        if country_desc is None:
            await db.execute("UPDATE user_states SET country_desc = NULL WHERE user_id = ?", (user_id,))
        else:
            await db.execute(
                """INSERT INTO user_states (user_id, country_desc)
                   VALUES (?, ?)
                   ON CONFLICT(user_id) DO UPDATE SET country_desc=excluded.country_desc""",
                (user_id, country_desc)
            )
        await db.commit()

# ==== Индекс текущего аспекта для опроса ====
async def get_aspect_index(user_id: int) -> Optional[int]:
    async with aiosqlite.connect("chats.db") as db:
        async with db.execute(
                "SELECT aspect_index FROM user_states WHERE user_id = ?",
                (user_id,)
        ) as cursor:
            result = await cursor.fetchone()
            return result[0] if result and result[0] is not None else None

async def set_aspect_index(user_id: int, index: Optional[int]):
    async with aiosqlite.connect("chats.db") as db:
        if index is None:
            await db.execute("UPDATE user_states SET aspect_index = NULL WHERE user_id = ?", (user_id,))
        else:
            await db.execute(
                """INSERT INTO user_states (user_id, aspect_index)
                   VALUES (?, ?)
                   ON CONFLICT(user_id) DO UPDATE SET aspect_index=excluded.aspect_index""",
                (user_id, index)
            )
        await db.commit()

# ==== Запись и чтение аспектов ====
async def set_user_aspect(user_id: int, aspect_code: str, value: Optional[str]):
    if aspect_code not in ASPECT_CODES:
        raise ValueError(f"Недопустимый код аспекта: {aspect_code}")
    async with aiosqlite.connect("chats.db") as db:
        if value is None:
            await db.execute(
                f"UPDATE user_states SET {aspect_code} = NULL WHERE user_id = ?",
                (user_id,)
            )
        else:
            await db.execute(
                f"""INSERT INTO user_states (user_id, {aspect_code})
                    VALUES (?, ?)
                    ON CONFLICT(user_id) DO UPDATE SET {aspect_code}=excluded.{aspect_code}""",
                (user_id, value)
            )
        await db.commit()

async def get_user_aspect(user_id: int, aspect_code: str) -> Optional[str]:
    if aspect_code not in ASPECT_CODES:
        raise ValueError(f"Недопустимый код аспекта: {aspect_code}")
    async with aiosqlite.connect("chats.db") as db:
        async with db.execute(
                f"SELECT {aspect_code} FROM user_states WHERE user_id = ?",
                (user_id,)
        ) as cursor:
            result = await cursor.fetchone()
            return result[0] if result else None

async def clear_user_aspects(user_id: int):
    async with aiosqlite.connect("chats.db") as db:
        # Сбросить все аспекты пользователя (кроме country и country_desc)
        columns = ", ".join([f"{a} = NULL" for a in ASPECT_CODES] + ["aspect_index = NULL"])
        await db.execute(
            f"UPDATE user_states SET {columns} WHERE user_id = ?", (user_id,)
        )
        await db.commit()

# ==== Получить всех игроков ====
async def get_all_active_countries():
    """
    Возвращает список кортежей:
    (user_id, country, country_desc, экономика, военное_дело, ..., общество)
    """
    async with aiosqlite.connect("chats.db") as db:
        async with db.execute(
                f"""SELECT user_id, country, country_desc,
                {", ".join(ASPECT_CODES)}
                FROM user_states
                WHERE country IS NOT NULL
            """
        ) as cursor:
            countries = await cursor.fetchall()
            return countries

async def get_user_id_by_country(country: str) -> Optional[int]:
    async with aiosqlite.connect("chats.db") as db:
        async with db.execute(
                "SELECT user_id FROM user_states WHERE LOWER(country) = LOWER(?)",
                (country,)
        ) as cursor:
            result = await cursor.fetchone()
            return result[0] if result else None

