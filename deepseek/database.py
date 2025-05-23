import aiosqlite
from typing import List

async def init_db():
    async with aiosqlite.connect("chats.db") as db:
        await db.execute(
            """CREATE TABLE IF NOT EXISTS chats (
                user_id INTEGER PRIMARY KEY,
                history TEXT
            )"""
        )
        await db.commit()

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
    history.extend([f"User: {message}", f"Assistant: {response}"])
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

