@echo off
title Запуск Discord Shop Bot
echo 🚀 Запуск Discord Shop Bot...

REM Переход в корневую директорию
cd /d "%~dp0.."

REM Проверка существования виртуального окружения
if not exist "venv" (
    echo 📦 Создание виртуального окружения...
    python -m venv venv
)

REM Активация виртуального окружения
echo 🔧 Активация виртуального окружения...
call venv\Scripts\activate.bat

REM Установка зависимостей
echo 📥 Установка зависимостей...
pip install -r requirements.txt

REM Проверка существования .env файла
if not exist ".env" (
    echo ⚠️  Файл .env не найден! Скопируйте .env.example в .env и настройте его.
    pause
    exit /b 1
)

REM Создание необходимых директорий
if not exist "logs" (
    echo 📁 Создание папки logs...
    mkdir logs
)

if not exist "data" (
    echo 📁 Создание папки data...
    mkdir data
)

if not exist "data\exchanges" (
    echo 📁 Создание папки exchanges...
    mkdir data\exchanges
)

REM Запуск бота в фоновом режиме
echo 🤖 Запуск бота в фоновом режиме...
echo 📝 Все логи сохраняются в logs/bot.log
echo.

REM Запуск бота с перенаправлением вывода в лог файл
start /MIN python bot.py > logs/bot.log 2>&1

REM Ожидание инициализации бота
timeout /t 3 /nobreak >nul

echo ✅ Бот запущен в фоновом режиме!
echo 📋 Проверьте logs/bot.log для подробного вывода
echo 🛑 Для остановки бота закройте python.exe в Диспетчере задач
echo.
pause
