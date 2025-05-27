import logging
import asyncio

logger = logging.getLogger(__name__)

async def try_send_html(message, text: str, **kwargs):
    """
    Безопасная отправка сообщения с parse_mode="HTML".
    Если возникает ошибка (например, некорректные теги), повторно отправляет текст без форматирования.
    """
    try:
        await message.answer(text, parse_mode="HTML", **kwargs)
    except Exception as e:
        logger.warning(f"Не удалось отправить сообщение в HTML: {str(e)}. Пробуем отправить без форматирования.")
        await message.answer(text, **kwargs)

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
