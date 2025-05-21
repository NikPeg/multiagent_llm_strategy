from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import logging
import random
from io import BytesIO
import matplotlib.pyplot as plt
import numpy as np

from storage import (
    get_player_data,
    get_player_by_username,
    update_player_goals,
    get_player_goals
)

# Команда для получения информации о своей стране
async def cmd_who(message: types.Message):
    """Показывает информацию о стране игрока"""
    # Определяем, запрашивается ли информация о другом игроке
    command_parts = message.text.split()

    # Проверяем, есть ли после команды имя пользователя
    target_username = None
    if len(command_parts) > 1:
        target_username = command_parts[1].lstrip('@')

    if target_username:
        # Получаем данные о стране указанного игрока
        player = get_player_by_username(target_username)
        if not player:
            await message.reply(f"Игрок @{target_username} не найден или не является участником игры.")
            return
    else:
        # Получаем данные о стране автора сообщения
        player = get_player_data(message.from_user.id)
        if not player:
            await message.reply("Вы не являетесь участником игры. Зарегистрируйтесь через личные сообщения с ботом.")
            return

    # Получаем данные о стране
    country_name = player.get('country_name', 'Неизвестная страна')
    economy = player.get('economy', 50)
    military = player.get('military', 50)
    diplomacy = player.get('diplomacy', 50)
    stability = player.get('stability', 50)
    innovation = player.get('innovation', 50)

    # Генерируем векторную диаграмму
    img_bytes = generate_radar_chart(
        country_name,
        [economy, military, diplomacy, stability, innovation]
    )

    # Формируем краткое описание страны
    description = player.get('description', 'Описание отсутствует')

    # Отправляем изображение с описанием
    await message.reply_photo(
        img_bytes,
        caption=f"🌍 **{country_name}**\n\n"
                f"{description}\n\n"
                f"💰 Экономика: {economy}/100\n"
                f"🔫 Военная мощь: {military}/100\n"
                f"🤝 Дипломатия: {diplomacy}/100\n"
                f"⚖️ Стабильность: {stability}/100\n"
                f"🔬 Инновации: {innovation}/100"
    )

# Функция для генерации радарной диаграммы
def generate_radar_chart(title, values):
    """Создает радарную диаграмму и возвращает её как BytesIO объект"""
    # Создаем категории
    categories = ['Экономика', 'Военная мощь', 'Дипломатия', 'Стабильность', 'Инновации']

    # Количество переменных
    N = len(categories)

    # Углы для каждой оси
    angles = np.linspace(0, 2*np.pi, N, endpoint=False).tolist()

    # Замкнуть график
    values = values + [values[0]]
    angles = angles + [angles[0]]

    # Создаем фигуру
    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))

    # Рисуем график
    ax.plot(angles, values, 'o-', linewidth=2)
    ax.fill(angles, values, alpha=0.25)

    # Устанавливаем лейблы
    ax.set_thetagrids(np.degrees(angles[:-1]), categories)

    # Устанавливаем пределы
    ax.set_ylim(0, 100)

    # Устанавливаем заголовок
    ax.set_title(title, size=15, y=1.1)

    # Сохраняем в буфер
    buf = BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()

    return buf

# Команда для предсказания будущего
async def cmd_future(message: types.Message):
    """Отправляет предсказание о будущем страны"""
    # Получаем данные о стране игрока
    player = get_player_data(message.from_user.id)

    if not player:
        await message.reply("Вы не являетесь участником игры. Зарегистрируйтесь через личные сообщения с ботом.")
        return

    # Получаем название и характеристики страны
    country_name = player.get('country_name', 'Неизвестная страна')
    government_type = player.get('government_type', 'демократия')
    economy_type = player.get('economy_type', 'рыночная')

    # Генерируем предсказание будущего на основе характеристик страны
    future_prediction = generate_future_prediction(country_name, government_type, economy_type, player)

    # Отправляем предсказание
    await message.reply(
        f"🔮 **Предсказание будущего для {country_name}**\n\n"
        f"{future_prediction}"
    )

# Функция для генерации предсказания о будущем
def generate_future_prediction(country_name, government_type, economy_type, player):
    """Генерирует предсказание о будущем страны на основе её характеристик"""
    # Получаем показатели страны
    economy = player.get('economy', 50)
    military = player.get('military', 50)
    diplomacy = player.get('diplomacy', 50)
    stability = player.get('stability', 50)
    innovation = player.get('innovation', 50)

    # Список возможных предсказаний в зависимости от показателей
    predictions = []

    # Экономические предсказания
    if economy > 70:
        predictions.append(f"Экономика {country_name} продолжит процветать, привлекая иностранные инвестиции и создавая новые рабочие места.")
    elif economy < 30:
        predictions.append(f"Экономические трудности будут преследовать {country_name}, возможен рост инфляции и безработицы.")
    else:
        predictions.append(f"Экономика {country_name} будет развиваться стабильно, без значительных потрясений.")

    # Военные предсказания
    if military > 70:
        predictions.append(f"Военная мощь {country_name} будет внушать уважение соседям и обеспечивать безопасность границ.")
    elif military < 30:
        predictions.append(f"Слабость вооруженных сил может сделать {country_name} уязвимой перед внешними угрозами.")

    # Дипломатические предсказания
    if diplomacy > 70:
        predictions.append(f"Дипломатическое влияние {country_name} будет расти, способствуя заключению выгодных международных соглашений.")
    elif diplomacy < 30:
        predictions.append(f"Изоляция в международных отношениях может привести к дипломатическим конфликтам для {country_name}.")

    # Предсказания о стабильности
    if stability > 70:
        predictions.append(f"Внутренняя стабильность {country_name} обеспечит спокойное развитие и процветание граждан.")
    elif stability < 30:
        predictions.append(f"Внутренние противоречия могут привести к социальным волнениям в {country_name}.")

    # Предсказания об инновациях
    if innovation > 70:
        predictions.append(f"Технологический прогресс выведет {country_name} в лидеры в области инноваций и научных исследований.")
    elif innovation < 30:
        predictions.append(f"Технологическое отставание может серьезно затормозить развитие {country_name}.")

    # Выбираем случайные предсказания из списка
    random.shuffle(predictions)
    selected_predictions = predictions[:min(3, len(predictions))]

    # Формируем итоговое предсказание
    future = " ".join(selected_predictions)

    # Добавляем заключительную фразу в стиле правительства
    if government_type.lower() == "демократия":
        future += f"\n\nНарод {country_name} своим единством и трудом строит светлое будущее!"
    elif government_type.lower() == "диктатура":
        future += f"\n\nВеликий лидер {country_name} ведет страну к величию и процветанию!"
    elif government_type.lower() == "монархия":
        future += f"\n\nМонарх {country_name} мудро правит, обеспечивая славное будущее государства!"
    else:
        future += f"\n\nИстория {country_name} продолжится, и будущее принесет новые испытания и победы!"

    return future

# Команда для голов
async def cmd_goal(message: types.Message):
    """Регистрирует гол и обновляет статистику игрока"""
    # Получаем ID пользователя
    user_id = message.from_user.id

    # Генерируем случайное количество букв О для "ГОООООЛ"
    o_count = random.randint(1, 7)
    goal_text = f"Г{'О' * o_count}Л!"

    # Обновляем счетчик голов в базе данных
    update_player_goals(user_id, o_count)

    # Отправляем сообщение
    await message.reply(goal_text)

# Команда для просмотра статистики по голам
async def cmd_stat(message: types.Message):
    """Показывает статистику голов игрока"""
    # Определяем, запрашивается ли статистика другого игрока
    command_parts = message.text.split()

    # Проверяем, есть ли после команды имя пользователя
    target_username = None
    if len(command_parts) > 1:
        target_username = command_parts[1].lstrip('@')

    if target_username:
        # Получаем статистику указанного игрока
        player = get_player_by_username(target_username)
        if not player:
            await message.reply(f"Игрок @{target_username} не найден или не является участником игры.")
            return
        user_id = player.get('user_id')
    else:
        # Получаем статистику автора сообщения
        user_id = message.from_user.id
        player = get_player_data(user_id)
        if not player:
            await message.reply("Вы не являетесь участником игры. Зарегистрируйтесь через личные сообщения с ботом.")
            return

    # Получаем статистику голов
    goals_data = get_player_goals(user_id)

    if not goals_data:
        # Если нет данных о голах
        await message.reply(f"{'Вы еще' if user_id == message.from_user.id else 'Этот игрок еще'} не забили ни одного гола!")
        return

    # Получаем данные о голах
    total_goals = goals_data.get('total_goals', 0)
    total_os = goals_data.get('total_os', 0)
    avg_os = total_os / total_goals if total_goals > 0 else 0

    # Отправляем статистику
    await message.reply(
        f"⚽ **Статистика голов**\n\n"
        f"👤 Игрок: {player.get('country_name')}\n"
        f"🥅 Всего голов: {total_goals}\n"
        f"📊 Общее количество букв 'О': {total_os}\n"
        f"📈 Среднее количество букв 'О' на гол: {avg_os:.2f}"
    )
