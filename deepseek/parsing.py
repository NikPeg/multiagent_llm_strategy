import re

def clean_ai_response(text: str) -> str:
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

    # Двойной перенос строки как граница ответа
    double_newline = text.find('\n\n')
    if double_newline != -1:
        cuts.append(double_newline)

    # Если найдено хотя бы одно ключевое слово или перенос
    if cuts:
        cut_pos = min(cuts)
        text = text[:cut_pos].rstrip()

    return text.strip()
