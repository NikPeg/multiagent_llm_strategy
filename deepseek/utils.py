import logging
import re
import asyncio

logger = logging.getLogger(__name__)

TELEGRAM_MAX_LENGTH = 4096

def split_long_message(text: str, max_length: int = TELEGRAM_MAX_LENGTH):
    """
    Разбивает длинный текст на части не длиннее max_length символов.
    Ставит разбиение по абзацам, если возможно.
    """
    parts = []
    while len(text) > max_length:
        # Ищем ближайший конец абзаца до лимита
        split_idx = text.rfind('\n', 0, max_length)
        if split_idx == -1 or split_idx < max_length * 0.5:
            # Если абзаца не нашли, рвём в лоб
            split_idx = max_length
        parts.append(text[:split_idx])
        text = text[split_idx:].lstrip('\n')
    parts.append(text)
    return parts

async def answer_html(message, text: str, **kwargs):
    """
    Безопасная отправка сообщения с parse_mode="HTML".
    Если возникает ошибка (например, некорректные теги), повторно отправляет текст без форматирования.
    Разбивает на несколько сообщений, если текст слишком длинный.
    """
    for part in split_long_message(text):
        try:
            await message.answer(part, parse_mode="HTML", **kwargs)
        except Exception as e:
            logger.warning(f"Не удалось отправить сообщение в HTML: {str(e)}. Пробуем отправить без форматирования.")
            await message.answer(part, **kwargs)

async def send_html(bot, chat_id, text: str, **kwargs):
    """
    Безопасная отправка сообщения в чат (канал, группу или user) с parse_mode="HTML".
    Если отправка в HTML не удалась, повторяет без форматирования.
    Разбивает на несколько сообщений, если текст слишком длинный.
    """
    for part in split_long_message(text):
        try:
            await bot.send_message(chat_id, part, parse_mode="HTML", **kwargs)
        except Exception as e:
            logger.warning(f"Не удалось отправить сообщение в HTML (bot.send_message): {str(e)}. Пробуем без форматирования.")
            await bot.send_message(chat_id, part, **kwargs)

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
    1. Вырезает всё ДО первого <think> или &lt;think&gt; (включая сам тег).
    2. Затем ищет "Игрок:" и оставляет весь текст, начиная с этого слова.
    3. Если в конце пусто, возвращает исходный text.
    """
    for open_tag in ('&lt;think&gt;', '<think>'):
        pos = text.find(open_tag)
        if pos != -1:
            text = text[pos + len(open_tag):]
            break

    # Теперь ищем "Игрок:"
    key = "Игрок:"
    idx = text.find(key)
    if idx != -1:
        text = text[idx:]

    text = text.strip()
    if not text:
        return text
    return text

def stars_to_bold(text):
    # Заменяем все **text** на <b>text</b>
    return re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
