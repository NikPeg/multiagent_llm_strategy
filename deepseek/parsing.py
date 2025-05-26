import re

def clean_ai_response(text: str, drop_double=True) -> str:
    """
    Очищает ответ от спец-тегов и по ключевым словам User: Player: Игрок: и двойному переводу строки (\n\n)
    """
    # Удаляем все </think> и &lt;/think&gt;
    text = text.replace("</think>", "").replace("&lt;/think&gt;", "")

    # Поиск позиций ключевых слов
    cuts = []

    # Ключевые слова для отсечения
    pattern = re.compile(r'(User:|Игрок:|Player:)', re.IGNORECASE)
    match = pattern.search(text)
    if match:
        cuts.append(match.start())
    if drop_double:
        # Двойной перенос строки как граница ответа
        double_newline = text.find('\n\n')
        if double_newline != -1:
            cuts.append(double_newline)

    # Если найдено хотя бы одно ключевое слово или перенос
    cut_pos = None
    if cuts:
        cut_pos = min(cuts)
    text = text[:cut_pos].rstrip()

    return text.strip()

def stars_to_bold(text):
    # Заменяем все **text** на <b>text</b>
    return re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
