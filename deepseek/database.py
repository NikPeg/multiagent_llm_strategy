import aiosqlite
from typing import List, Optional

async def init_db():
    async with aiosqlite.connect("chats.db") as db:
        # Таблица для истории чатов
        await db.execute(
            """CREATE TABLE IF NOT EXISTS chats (
                user_id INTEGER PRIMARY KEY,
                history TEXT
            )"""
        )
        # Таблица для хранения состояния пользователя
        await db.execute(
            """CREATE TABLE IF NOT EXISTS user_states (
                user_id INTEGER PRIMARY KEY,
                state TEXT,
                country TEXT,
                country_desc TEXT
            )"""
        )
        await db.commit()

# ==== История чатов ====

async def get_history(user_id: int) -> List[str]:
    async with aiosqlite.connect("chats.db") as db:
        async with db.execute(
                "SELECT history FROM chats WHERE user_id = ?",
                (user_id,)
        ) as cursor:
            result = await cursor.fetchone()
            return eval(result[0]) if result else []

async def update_history(user_id: int, message: str, response: str, history_limit: int):
    history = await get_history(user_id)
    history.extend([f"Игрок: {message}", f"Ассистент: {response}"])
    history = history[-history_limit:]

    async with aiosqlite.connect("chats.db") as db:
        await db.execute(
            "INSERT OR REPLACE INTO chats (user_id, history) VALUES (?, ?)",
            (user_id, str(history))
        )
        await db.commit()

async def clear_history(user_id: int):
    async with aiosqlite.connect("chats.db") as db:
        await db.execute("DELETE FROM chats WHERE user_id = ?", (user_id,))
        await db.commit()

# ==== Состояние пользователя (user_state, user_country, user_country_desc) ====

async def get_user_state(user_id: int) -> Optional[str]:
    async with aiosqlite.connect("chats.db") as db:
        async with db.execute(
                "SELECT state FROM user_states WHERE user_id = ?",
                (user_id,)
        ) as cursor:
            result = await cursor.fetchone()
            return result[0] if result else None

async def set_user_state(user_id: int, state: Optional[str]):
    async with aiosqlite.connect("chats.db") as db:
        # Если state is None, удалить строку
        if state is None:
            await db.execute("UPDATE user_states SET state = NULL WHERE user_id = ?", (user_id,))
        else:
            await db.execute(
                """INSERT INTO user_states (user_id, state)
                   VALUES (?, ?)
                   ON CONFLICT(user_id) DO UPDATE SET state=excluded.state""",
                (user_id, state)
            )
        await db.commit()

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

async def clear_user_state(user_id: int):
    async with aiosqlite.connect("chats.db") as db:
        await db.execute("DELETE FROM user_states WHERE user_id = ?", (user_id,))
        await db.commit()
