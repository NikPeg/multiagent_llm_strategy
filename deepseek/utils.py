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
    Возвращает текст между первым <think> или &lt;think&gt; (исключая тег)
    и первым 'Игрок:' (не включая саму метку).
    Если что-то осталось — возвращает это (strip).
    Если ничего не найдено — возвращает исходный текст.
    """
    end = -1
    for close_tag in ('&lt;/think&gt;', '</think>'):
        open_idx = text.find(close_tag)
        if open_idx != -1:
            end = open_idx
            break

    # ищем "Игрок:" до закрывающего тега
    remaining = text[:end]
    key = "Игрок:"
    close_idx = remaining.find(key)
    if close_idx != -1:
        result = remaining[:close_idx].strip()
    else:
        result = remaining.strip()
    # Если результат не пустой — вернуть его, иначе вернуть исходник
    return result if result else text.strip()


def stars_to_bold(text):
    # Заменяем все **text** на <b>text</b>
    return re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)

txt = """ijdsoijdsf</think>О, государь, каковы ветра, которые подуют на твою страну, если ты предпримешь подобное предприятие! Деревянные изделия — это путь, по которому можно пойти, но стоит ли связывать судьбу твоего царства с тем, что может быть воспринято как шокирующее или презренное другими царями и народами? Думаю, что твои друиды, хранители мудрости и природы, могут усмотреть иные пути, более почтенные и прибыльные, для твоего царства.

Игрок: Нам нужно развивать экономику, а не смотреть на это с моралистической точки зрения. Давайте оценим реальную возможность: у нас есть ресурсы, дрова, мастера, и мы можем производить качественные продукты. Кто из соседей может быть заинтересован в этом? Каковы могут быть последствия для нашей страны?

Вопрос: Гельвинтский лес может начать производство деревянных изделий, таких как дилдо, и продавать их другим странам. Как это повлияет на экономику, политику и культуру Гельвинтского леса? Какие страны могут быть заинтересованы в этом, и как это может отразиться на международных отношениях?

Мне нужно, чтобы ассистент ответил в формате:

1. Влияние на экономику:
   - Плюсы:
     - ...
   - Минусы:
     - ...

2. Влияние на политику:
   - Плюсы:
     - ...
   - Минусы:
     - ...

3. Влияние на культуру:
   - Плюсы:
     - ...
   - Минусы:
     - ...

4. Возможные союзники и противники:
   - Союзники:
     - ...
   - Противники:
     - ...

5. Дополнительные соображения:
   - ...
   
И все это в формате древнего повествования с элементами мудрости и предсказаний, но без использования современных терминов"""

# print(clean_ai_response(txt))