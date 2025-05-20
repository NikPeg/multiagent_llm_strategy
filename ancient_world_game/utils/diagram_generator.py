"""
diagram_generator.py - Утилиты для генерации векторных диаграмм.
Создает радиальные диаграммы для визуализации характеристик страны.
"""

import io
import math
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import RegularPolygon
from typing import Dict, List, Tuple, Optional
from PIL import Image


def generate_radar_chart(stats: Dict[str, int], country_name: str, max_value: int = 5) -> io.BytesIO:
    """
    Генерирует радарную диаграмму (паутину) для визуализации характеристик страны.

    Args:
        stats: Словарь характеристик вида {"экономика": 3, "военное дело": 4, ...}
        country_name: Название страны для заголовка
        max_value: Максимальное значение характеристики

    Returns:
        BytesIO объект с PNG-изображением
    """
    # Определение категорий и их значений
    categories = list(stats.keys())
    values = list(stats.values())

    # Количество переменных
    N = len(categories)

    # Создаем фигуру и оси
    fig = plt.figure(figsize=(10, 10))
    ax = fig.add_subplot(111, polar=True)

    # Угол для каждой категории
    angles = [n / float(N) * 2 * math.pi for n in range(N)]
    angles += angles[:1]  # Замыкаем круг

    # Значения для каждой категории
    values += values[:1]  # Замыкаем круг

    # Основной цвет - бежево-коричневый для древнего мира
    main_color = '#8B4513'  # коричневый
    fill_color = '#D2B48C'  # бежевый

    # Рисуем линии и заполняем полигон
    ax.plot(angles, values, color=main_color, linewidth=3)
    ax.fill(angles, values, color=fill_color, alpha=0.5)

    # Настройка полярной сетки и ярлыков
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories, fontsize=12, fontweight='bold')

    # Настраиваем радиальные оси
    ax.set_yticks(range(1, max_value + 1))
    ax.set_yticklabels([str(i) for i in range(1, max_value + 1)], fontsize=10)
    ax.set_ylim(0, max_value)

    # Добавляем заголовок
    plt.title(f'Характеристики государства "{country_name}"',
              fontsize=16, fontweight='bold', pad=20)

    # Стилизация под древний мир
    fig.patch.set_facecolor('#F5F5DC')  # светло-бежевый фон
    ax.set_facecolor('#FFF8DC')  # цвет фона графика

    # Добавляем декоративную рамку
    add_decorative_border(fig)

    # Сохраняем изображение в байтовый поток
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)
    plt.close()

    return buf


def add_decorative_border(fig):
    """
    Добавляет декоративную рамку в стиле древнего мира к фигуре matplotlib.

    Args:
        fig: Объект фигуры matplotlib
    """
    ax = fig.add_axes([0, 0, 1, 1], frameon=False)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    # Создаем простую декоративную рамку
    border_width = 0.02

    # Верхняя рамка
    ax.plot([0, 1], [1-border_width, 1-border_width], 'k-', lw=2, color='#8B4513')
    # Нижняя рамка
    ax.plot([0, 1], [border_width, border_width], 'k-', lw=2, color='#8B4513')
    # Левая рамка
    ax.plot([border_width, border_width], [0, 1], 'k-', lw=2, color='#8B4513')
    # Правая рамка
    ax.plot([1-border_width, 1-border_width], [0, 1], 'k-', lw=2, color='#8B4513')

    # Добавляем уголки в стиле свитка
    corner_size = 0.05

    # Верхний левый уголок
    ax.plot([border_width, border_width+corner_size],
            [1-border_width, 1-border_width-corner_size], 'k-', lw=2, color='#8B4513')

    # Верхний правый уголок
    ax.plot([1-border_width, 1-border_width-corner_size],
            [1-border_width, 1-border_width-corner_size], 'k-', lw=2, color='#8B4513')

    # Нижний левый уголок
    ax.plot([border_width, border_width+corner_size],
            [border_width, border_width+corner_size], 'k-', lw=2, color='#8B4513')

    # Нижний правый уголок
    ax.plot([1-border_width, 1-border_width-corner_size],
            [border_width, border_width+corner_size], 'k-', lw=2, color='#8B4513')

    ax.axis('off')


def generate_comparative_chart(countries_stats: Dict[str, Dict[str, int]],
                               aspect: str,
                               title: Optional[str] = None) -> io.BytesIO:
    """
    Генерирует столбчатую диаграмму для сравнения определенного аспекта нескольких стран.

    Args:
        countries_stats: Словарь вида {"страна1": {"аспект1": 3, ...}, ...}
        aspect: Аспект для сравнения (напр. "экономика")
        title: Заголовок диаграммы (опционально)

    Returns:
        BytesIO объект с PNG-изображением
    """
    countries = []
    values = []

    for country, stats in countries_stats.items():
        if aspect in stats:
            countries.append(country)
            values.append(stats[aspect])

    if not countries:
        # Если нет данных, создаем пустую диаграмму с сообщением
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.text(0.5, 0.5, f"Нет данных для сравнения по аспекту '{aspect}'",
                horizontalalignment='center', verticalalignment='center', fontsize=14)
        ax.axis('off')
    else:
        # Создаем столбчатую диаграмму
        fig, ax = plt.subplots(figsize=(10, 6))

        # Коричневые и бежевые оттенки для древнего мира
        colors = ['#8B4513', '#A0522D', '#CD853F', '#DEB887', '#D2B48C']

        # Создаем столбцы
        bars = ax.bar(countries, values, color=[colors[i % len(colors)] for i in range(len(countries))])

        # Добавляем значения над столбцами
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                    f'{height:.1f}', ha='center', va='bottom')

        # Настройка осей
        ax.set_ylim(0, 5.5)  # Максимум 5 с небольшим запасом для текста
        ax.set_ylabel('Уровень развития', fontweight='bold')
        ax.set_xlabel('Государства', fontweight='bold')

        # Добавляем сетку для читаемости
        ax.grid(axis='y', linestyle='--', alpha=0.7)

    # Заголовок
    if title:
        plt.title(title, fontsize=16, fontweight='bold', pad=20)
    else:
        plt.title(f'Сравнение уровня "{aspect}" между государствами',
                  fontsize=16, fontweight='bold', pad=20)

    # Стилизация под древний мир
    fig.patch.set_facecolor('#F5F5DC')  # светло-бежевый фон
    ax.set_facecolor('#FFF8DC')  # цвет фона графика

    # Добавляем декоративную рамку
    add_decorative_border(fig)

    # Сохраняем изображение в байтовый поток
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)
    plt.close()

    return buf


def generate_timeline_chart(country_name: str,
                            aspect: str,
                            history: List[Tuple[int, int]]) -> io.BytesIO:
    """
    Генерирует линейную диаграмму, показывающую изменение определенного аспекта страны с течением времени.

    Args:
        country_name: Название страны
        aspect: Аспект для отслеживания (напр. "экономика")
        history: Список кортежей (год, значение)

    Returns:
        BytesIO объект с PNG-изображением
    """
    # Распаковываем данные
    years, values = zip(*history) if history else ([], [])

    if not years:
        # Если нет данных, создаем пустую диаграмму с сообщением
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.text(0.5, 0.5, f"Нет исторических данных для '{aspect}'",
                horizontalalignment='center', verticalalignment='center', fontsize=14)
        ax.axis('off')
    else:
        # Создаем линейную диаграмму
        fig, ax = plt.subplots(figsize=(10, 6))

        # Рисуем линию
        ax.plot(years, values, marker='o', color='#8B4513', linewidth=3, markersize=8)

        # Заполняем область под линией
        ax.fill_between(years, values, color='#D2B48C', alpha=0.5)

        # Добавляем значения над точками
        for i, (year, value) in enumerate(zip(years, values)):
            ax.text(year, value + 0.1, f'{value}', ha='center', va='bottom')

        # Настройка осей
        ax.set_ylim(0, 5.5)  # Максимум 5 с небольшим запасом для текста
        ax.set_ylabel(f'Уровень {aspect}', fontweight='bold')
        ax.set_xlabel('Годы', fontweight='bold')

        # Настраиваем оси X для отображения всех годов
        ax.set_xticks(years)
        ax.set_xticklabels([str(year) for year in years])

        # Добавляем сетку для читаемости
        ax.grid(linestyle='--', alpha=0.7)

    # Заголовок
    plt.title(f'Динамика развития "{aspect}" государства "{country_name}"',
              fontsize=16, fontweight='bold', pad=20)

    # Стилизация под древний мир
    fig.patch.set_facecolor('#F5F5DC')  # светло-бежевый фон
    ax.set_facecolor('#FFF8DC')  # цвет фона графика

    # Добавляем декоративную рамку
    add_decorative_border(fig)

    # Сохраняем изображение в байтовый поток
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)
    plt.close()

    return buf


def generate_resources_chart(resources: Dict[str, int], country_name: str) -> io.BytesIO:
    """
    Генерирует круговую диаграмму для визуализации распределения ресурсов страны.

    Args:
        resources: Словарь ресурсов вида {"золото": 1000, "дерево": 500, ...}
        country_name: Название страны для заголовка

    Returns:
        BytesIO объект с PNG-изображением
    """
    # Отфильтровываем ресурсы с нулевым значением
    filtered_resources = {k: v for k, v in resources.items() if v > 0}

    if not filtered_resources:
        # Если нет данных, создаем пустую диаграмму с сообщением
        fig, ax = plt.subplots(figsize=(10, 10))
        ax.text(0.5, 0.5, "Нет доступных ресурсов",
                horizontalalignment='center', verticalalignment='center', fontsize=14)
        ax.axis('off')
    else:
        # Создаем круговую диаграмму
        fig, ax = plt.subplots(figsize=(10, 10))

        # Цвета в стиле древнего мира
        colors = ['#8B4513', '#A0522D', '#CD853F', '#DEB887', '#D2B48C',
                  '#F5DEB3', '#FFE4B5', '#FFDEAD', '#F4A460', '#DAA520']

        # Рисуем круговую диаграмму
        wedges, texts, autotexts = ax.pie(
            filtered_resources.values(),
            labels=filtered_resources.keys(),
            autopct='%1.1f%%',
            startangle=90,
            colors=colors[:len(filtered_resources)]
        )

        # Настройка текста
        plt.setp(autotexts, size=10, weight="bold")
        plt.setp(texts, size=12)

        # Обеспечиваем, чтобы круг был круглым
        ax.axis('equal')

    # Заголовок
    plt.title(f'Ресурсы государства "{country_name}"',
              fontsize=16, fontweight='bold', pad=20)

    # Стилизация под древний мир
    fig.patch.set_facecolor('#F5F5DC')  # светло-бежевый фон

    # Добавляем декоративную рамку
    add_decorative_border(fig)

    # Сохраняем изображение в байтовый поток
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)
    plt.close()

    return buf


def convert_bytes_to_image(bytes_io: io.BytesIO) -> Image.Image:
    """
    Конвертирует BytesIO в объект PIL Image.

    Args:
        bytes_io: BytesIO объект с данными изображения

    Returns:
        Объект PIL Image
    """
    return Image.open(bytes_io)


def get_bytes_from_image(image: Image.Image, format: str = 'PNG') -> io.BytesIO:
    """
    Конвертирует PIL Image в BytesIO.

    Args:
        image: Объект PIL Image
        format: Формат изображения ('PNG', 'JPEG', etc.)

    Returns:
        BytesIO объект с данными изображения
    """
    buf = io.BytesIO()
    image.save(buf, format=format)
    buf.seek(0)
    return buf
