#!/bin/bash
echo "🚀 Запуск Discord Shop Bot..."

# Переход в корневую директорию
cd "$(dirname "$0")/.."

# Проверка существования виртуального окружения
if [ ! -d "venv" ]; then
    echo "📦 Создание виртуального окружения..."
    python3 -m venv venv
fi

# Активация виртуального окружения
echo "🔧 Активация виртуального окружения..."
source venv/bin/activate

# Установка зависимостей
echo "📥 Установка зависимостей..."
pip install -r requirements.txt

# Проверка существования .env файла
if [ ! -f ".env" ]; then
    echo "⚠️  Файл .env не найден! Скопируйте .env.example в .env и настройте его."
    exit 1
fi

# Создание необходимых директорий
if [ ! -d "logs" ]; then
    echo "📁 Создание папки logs..."
    mkdir -p logs
fi

if [ ! -d "data" ]; then
    echo "📁 Создание папки data..."
    mkdir -p data
fi

if [ ! -d "data/exchanges" ]; then
    echo "📁 Создание папки exchanges..."
    mkdir -p data/exchanges
fi

# Запуск бота в фоновом режиме
echo "🤖 Запуск бота в фоновом режиме..."
echo "📝 Все логи сохраняются в logs/bot.log"
echo ""

# Запуск бота в фоне и сохранение PID
nohup python bot.py > logs/bot.log 2>&1 &
BOT_PID=$!

# Сохранение PID в файл
echo $BOT_PID > logs/bot.pid

# Ожидание инициализации бота
sleep 3

# Проверка, что процесс все еще работает
if kill -0 $BOT_PID 2>/dev/null; then
    echo "✅ Бот запущен в фоновом режиме!"
    echo "📋 ID процесса: $BOT_PID"
    echo "📝 Проверьте logs/bot.log для подробного вывода"
    echo "🛑 Для остановки бота выполните: kill $BOT_PID"
    echo ""
    echo "📊 Последние логи запуска:"
    echo "----------------------------------------"
    tail -n 5 logs/bot.log 2>/dev/null || echo "Бот все еще инициализируется..."
else
    echo "❌ Не удалось запустить бота! Проверьте logs/bot.log для ошибок"
    cat logs/bot.log 2>/dev/null | tail -n 10
    exit 1
fi
