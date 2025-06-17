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
    - Если есть <think>...</think> или &lt;think&gt;...&lt;/think&gt;, вернуть только то, что между ними.
    - Если есть только <think> или &lt;think&gt;, текст после этого тега.
    - Если только </think> или &lt;/think&gt;, текст до него.
    - После этого обрезать по первым ключевым словам User:/Игрок:/Player:.
    - Если ничего не найдено — вернуть исходный текст (или с минимальной чисткой).
    """
    # Сначала обработаем оба варианта тегов
    # for open_tag, close_tag in [('&lt;think&gt;', '&lt;/think&gt;'), ('<think>', '</think>')]:
    #     open_idx = text.find(open_tag)
    #     close_idx = text.find(close_tag)
    #     if open_idx != -1 and close_idx != -1 and open_idx < close_idx:
    #         text = text[open_idx + len(open_tag):close_idx].strip()
    #         break
    #     if open_idx != -1:
    #         text = text[open_idx + len(open_tag):].strip()
    #         break
    #     if close_idx != -1:
    #         text = text[:close_idx].strip()
    #         break
    #
    # # Далее стандартная обрезка по спец-словам
    # pattern = re.compile(r'(User:|Игрок:|Player:)', re.IGNORECASE)
    # match = pattern.search(text)
    # if match:
    #     text = text[:match.start()].rstrip()

    return text.strip()

def stars_to_bold(text):
    # Заменяем все **text** на <b>text</b>
    return re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
