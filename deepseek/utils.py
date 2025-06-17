import logging
import re
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

def clean_ai_response(text: str) -> str:
    """
    Возвращает текст до первого &lt;/think&gt; (этот тег не включается),
    либо весь текст, если такого тега нет.
    """
    close_tag = '&lt;/think&gt;'
    idx = text.find(close_tag)
    if idx != -1:
        return text[:idx].strip()
    return text.strip()

def stars_to_bold(text):
    # Заменяем все **text** на <b>text</b>
    return re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
