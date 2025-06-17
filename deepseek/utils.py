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

def clean_ai_response(text: str, drop='Шшвшв') -> str:
    """
    Очищает ответ от спец-тегов <think>...</think> (или &lt;think&gt;...&lt;/think&gt;),
    а также по ключевым словам User: Player: Игрок: и двойному переводу строки (\n\n)
    """
    # Удалить блоки между (экранированными) <think> и </think> (многострочно!)
    # Удаляет и с <think>...</think> и с &lt;think&gt;...&lt;/think&gt;
    text = re.sub(r'(<think>.*?</think>|&lt;think&gt;.*?&lt;/think&gt;)', '', text, flags=re.DOTALL | re.IGNORECASE)

    cuts = []

    # Ключевые слова для отсечения
    pattern = re.compile(r'(User:|Игрок:|Player:)', re.IGNORECASE)
    match = pattern.search(text)
    if match:
        cuts.append(match.start())
    # Двойной перенос строки как граница ответа
    double_newline = text.find(drop)
    if double_newline != -1:
        cuts.append(double_newline)

    # Если найдено хотя бы одно ключевое слово или перенос
    cut_pos = None
    if cuts:
        cut_pos = min(cuts)
    if cut_pos is not None:
        text = text[:cut_pos].rstrip()

    return text.strip()

def stars_to_bold(text):
    # Заменяем все **text** на <b>text</b>
    return re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
