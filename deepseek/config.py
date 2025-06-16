import os
from dotenv import load_dotenv

load_dotenv()

# Токен Telegram-бота
BOT_TOKEN = os.getenv("BOT_TOKEN")

# ID чата администратора (целое число)
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", 0))

# Лимит истории сообщений для диалога с ИИ
HISTORY_LIMIT = int(os.getenv("HISTORY_LIMIT", 4))

# Максимальное количество новых токенов для длинных и коротких ответов модели
MAX_NEW_TOKENS = int(os.getenv("MAX_NEW_TOKENS", 512))
SHORT_NEW_TOKENS = int(os.getenv("SHORT_NEW_TOKENS", 250))

# Базовые игровые промпты
GAME_PROMPT = (
    "Ты — нейтральный ведущий ролевой текстовой игры в стиле геополитики древнего мира. "
    "Каждый игрок управляет страной, развивает её экономику, дипломатию "
    "и армию, строит отношения с соседями и принимает решения. "
)
RPG_PROMPT = (
    f"{GAME_PROMPT}"
    "Ты рассказываешь, что происходит, "
    "отвечаешь только от лица мастера игры, четко следуя сеттингу древнего мира, "
    "никогда не отступаешь от выбранной роли."
)

# Для проверки наличия токена при запуске приложения
if not BOT_TOKEN:
    raise ValueError("Токен бота не найден в .env!")
