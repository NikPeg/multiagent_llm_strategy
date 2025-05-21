# Ancient World Game Bot
Бот для игровой симуляции древнего мира в Telegram. Позволяет игрокам управлять своими странами, развивать их и взаимодействовать друг с другом.

### Требования
Python 3.9
CUDA-совместимая видеокарта NVIDIA (для ускорения моделей AI)
PostgreSQL или SQLite
### Установка
1. Установка Python 3.9  
   Рекомендуется использовать Python 3.9, так как он обеспечивает наилучшую совместимость с используемыми библиотеками.

#### Linux:
```bash
# Установка зависимостей для сборки Python
sudo apt-get update
sudo apt-get install -y build-essential libssl-dev zlib1g-dev libbz2-dev \
libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev libncursesw5-dev \
xz-utils tk-dev libffi-dev liblzma-dev python-openssl git

# Установка Python 3.9 через pyenv
curl https://pyenv.run | bash
pyenv install 3.9.18
pyenv global 3.9.18

# или через apt (Ubuntu 20.04+)
sudo apt-get install python3.9 python3.9-venv python3.9-dev
```
#### Windows:
Скачайте и установите Python 3.9 с официального сайта.

#### macOS:
```bash
brew install python@3.9
```
2. Создание виртуального окружения
```bash
# Linux/macOS
python3.9 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```
3. Установка PyTorch с поддержкой CUDA  
   Перед установкой других зависимостей, необходимо установить PyTorch с поддержкой вашей версии CUDA:

```bash
# Проверьте версию CUDA на вашей системе
nvidia-smi

# Установите PyTorch под вашу версию CUDA (замените XX.X на вашу версию)
# Для CUDA 12.8
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128

# Для CUDA 12.1
# pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Для CUDA 11.8
# pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```
4. Установка остальных зависимостей
```bash
   pip install -r requirements.txt
```
5. Установка языковых моделей
```
   bash
   python -m spacy download en_core_web_sm
   python -m nltk.downloader punkt
```
6. Настройка конфигурации  
   Создайте файл .env в корневой директории проекта и заполните его:

```text
# Токен вашего Telegram бота
BOT_TOKEN=your_bot_token_here

# Настройки базы данных
DATABASE_URL=sqlite:///game.db
# или для PostgreSQL
# DATABASE_URL=postgresql://username:password@localhost/dbname

# ID администраторов (через запятую)
ADMIN_IDS=123456789,987654321

# Настройки webhook (если нужно)
# WEBHOOK_URL=https://your-domain.com/webhook
# WEBHOOK_PATH=/webhook
# WEBAPP_HOST=0.0.0.0
# WEBAPP_PORT=8000
```
Запуск бота
```bash
# Запуск в режиме polling
python main.py
```

### Проверка установки PyTorch с CUDA
```bash
python -c "import torch; print(f'PyTorch version: {torch.__version__}'); print(f'CUDA available: {torch.cuda.is_available()}'); print(f'CUDA version: {torch.version.cuda if torch.cuda.is_available() else \"Not available\"}'); print(f'GPU device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"None\"}')"
```
Структура проекта
```csharp
ancient_world_game/
├── ai/                     # Модуль для работы с LLM моделями
├── bot/                    # Основной модуль бота
│   └── bot_instance.py     # Инициализация и настройка бота
├── config/                 # Конфигурация
│   ├── config.py           # Основные настройки
│   └── game_constants.py   # Игровые константы
├── db/                     # Работа с базой данных
├── handlers/               # Обработчики команд
├── keyboards/              # Клавиатуры для взаимодействия
├── middlewares/            # Промежуточные обработчики
├── tasks/                  # Периодические задачи
│   ├── daily_update.py     # Ежедневные обновления (смена года)
│   ├── projects_progress.py# Обновление прогресса проектов
│   └── scheduler.py        # Планировщик задач
├── utils/                  # Вспомогательные утилиты
│   ├── chroma_manager.py   # Управление ChromaDB
│   └── logger.py           # Настройка логирования
├── main.py                 # Точка входа
├── requirements.txt        # Зависимости проекта
└── README.md               # Документация
```
## Функциональность бота
- Управление страной: создание и развитие собственных стран
- Отдача приказов: управление своей страной через текстовые команды
- Взаимодействие с другими игроками: дипломатия, союзы и конфликты
- Проекты развития: строительство и исследовательские проекты
- Случайные события: влияющие на игровой мир
- Автоматическое обновление мира: смена игровых годов и развитие мира
## Особенности реализации
- Использование локальной LLM для генерации уникальных описаний и игровых событий
- Векторное хранилище ChromaDB для сохранения состояния игрового мира
- Периодические задачи для автоматического обновления игры
- Административный интерфейс для управления игровым процессом
## Используемые технологии
- aiogram: фреймворк для создания Telegram ботов
- PyTorch: для работы с моделями машинного обучения
- LangChain: для работы с языковыми моделями
- SQLAlchemy: ORM для работы с базой данных
- ChromaDB: векторная база данных для хранения состояния игрового мира
- Transformers: для использования моделей обработки естественного языка
## Требования к серверу
Для комфортной работы бота рекомендуется сервер со следующими характеристиками:

- Не менее 4 ядер CPU
- От 8 ГБ RAM
- Видеокарта NVIDIA с поддержкой CUDA и не менее 4 ГБ VRAM
- 20 ГБ свободного места на диске
## Устранение неполадок
- Проблемы с CUDA
- Убедитесь, что драйвера NVIDIA установлены и актуальны
```bash
nvidia-smi
Если PyTorch не видит CUDA, проверьте версию CUDA и переустановите PyTorch с соответствующей версией
```
Проблемы с зависимостями
Если некоторые пакеты не устанавливаются, попробуйте установить их отдельно с флагом --no-deps:

```bash
pip install problematic_package --no-deps
```
### Лицензия
MIT

### Автор
NikPeg

### Контакты
Для вопросов и предложений: t.me/nikpeg