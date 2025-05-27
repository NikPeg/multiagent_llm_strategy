import logging
import asyncio

logger = logging.getLogger(__name__)

async def answer_html(message, text: str, **kwargs):
    """
    Безопасная отправка сообщения с parse_mode="HTML".
    Если возникает ошибка (например, некорректные теги), повторно отправляет текст без форматирования.
    """
    try:
        await message.answer(text, parse_mode="HTML", **kwargs)
    except Exception as e:
        logger.warning(f"Не удалось отправить сообщение в HTML: {str(e)}. Пробуем отправить без форматирования.")
        await message.answer(text, **kwargs)

async def send_html(bot, chat_id, text: str, **kwargs):
    """
    Безопасная отправка сообщения в чат (канал, группу или user) с parse_mode="HTML".
    Если отправка в HTML не удалась, повторяет без форматирования.
    """
    try:
        await bot.send_message(chat_id, text, parse_mode="HTML", **kwargs)
    except Exception as e:
        logger.warning(f"Не удалось отправить сообщение в HTML (bot.send_message): {str(e)}. Пробуем без форматирования.")
        await bot.send_message(chat_id, text, **kwargs)

async def keep_typing(bot, chat_id):
    """
    Периодически показывает статус "печатает..." для чат-бота.
    """
    try:
        while True:
            await bot.send_chat_action(chat_id=chat_id, action="typing")
            await asyncio.sleep(3)
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"Ошибка в keep_typing: {str(e)}", exc_info=True)
