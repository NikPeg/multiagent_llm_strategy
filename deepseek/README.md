# 🤖 Telegram Bot для локальной модели DeepSeek-R1-Distill-Qwen-32B

Асинхронный бот на **aiogram 3**, который использует **локальную языковую модель** для генерации ответов. Поддерживает диалог с контекстом и сброс истории.

## 📋 Требования
- Python 3.12+
- NVIDIA GPU (рекомендуется) или CPU
- 16+ ГБ ОЗУ (для работы модели)

## ⚙️ Установка
1. Клонируйте репозиторий:
   ```bash
   git clone https://github.com/ваш-репозиторий.git
   cd ваш-репозиторий
   ```
## Установите зависимости:

```bash
pip install -r requirements.txt
```
Для GPU (CUDA 11.8):

```bash
pip install torch==2.1.2 --index-url https://download.pytorch.org/whl/cu118
```
## 🔧 Решение возможных проблем при установке

Если при установке возникает ошибка сборки `aiohttp` (например, `Failed building wheel for aiohttp`), выполните следующие действия:

1. **Для Linux (Ubuntu/Debian)** установите системные зависимости:
   ```bash
   sudo apt-get update && sudo apt-get install python3-dev python3-pip python3-aiohttp
   ```

2. Обновите инструменты Python:

```bash
pip install --upgrade pip setuptools wheel
```
3. Попробуйте альтернативные способы установки:
```bash
pip install aiohttp --no-binary :all:
```
или

```bash
pip install --force-reinstall -v aiohttp
```

Создайте файл .env и добавьте токен бота:

```env
BOT_TOKEN=ваш_токен_от_BotFather
```
## 🚀 Запуск
```bash
python bot.py
```
## 🎛 Команды
/start – Приветствие и инструкция

/new – Сбросить историю диалога

Любой текст – Получить ответ от модели

## ⚠️ Важно
Модель автоматически загрузится при первом запуске (требуется ~60 ГБ дискового пространства).

Для работы на CPU скорость генерации будет низкой.

Бот поддерживает многопользовательский режим (история хранится в памяти).

## 📌 Пример работы
```
User: Привет! Как дела?
Assistant: Привет! Я всего лишь ИИ, но у меня всё отлично. Чем могу помочь?
```
Разработано с использованием:
- Transformers (Hugging Face)
- Aiogram 3 (Telegram Bot Framework)
- DeepSeek-R1 (Языковая модель)

