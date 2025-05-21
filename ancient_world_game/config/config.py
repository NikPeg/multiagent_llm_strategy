"""
config.py - Основные настройки приложения, загружаемые из переменных окружения
"""

import os
from dotenv import load_dotenv
from typing import List

# Загрузка переменных окружения из .env файла
load_dotenv()

# Настройки бота
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("No bot token provided. Please set BOT_TOKEN in .env file")

# Преобразование строки с ID администраторов в список целых чисел
ADMIN_IDS_STR = os.getenv('ADMIN_IDS', '')
ADMIN_IDS = [int(admin_id.strip()) for admin_id in ADMIN_IDS_STR.split(',') if admin_id.strip()]

# Настройки базы данных
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///game.db')

# Настройки webhook (если используется)
WEBHOOK_URL = os.getenv('WEBHOOK_URL', '')
WEBHOOK_PATH = os.getenv('WEBHOOK_PATH', '/webhook')
WEBAPP_HOST = os.getenv('WEBAPP_HOST', '0.0.0.0')
WEBAPP_PORT = int(os.getenv('WEBAPP_PORT', '8000'))

# Настройки для логирования
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = os.getenv('LOG_FILE', 'logs/bot.log')

# Настройки для LLM
LLM_MODEL = os.getenv('LLM_MODEL', 'gpt-3.5-turbo')
LLM_API_KEY = os.getenv('LLM_API_KEY', '')
LLM_API_URL = os.getenv('LLM_API_URL', '')

# Настройки игры
GAME_START_YEAR = int(os.getenv('GAME_START_YEAR', '1'))
MAX_PLAYERS = int(os.getenv('MAX_PLAYERS', '100'))
