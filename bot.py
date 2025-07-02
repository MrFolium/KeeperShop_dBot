import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import asyncio
import traceback
import datetime
import sys
import logging
import importlib
import time
import fcntl

# Настройка логирования
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/bot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("bot")

# Загрузка переменных окружения
load_dotenv()

# Настройка бота
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# Время запуска отслеживания времени в игре
start_time = int(time.time())

# Импорт модулей
sys.path.append('modules')
from modules import shop_system
from modules import admin_commands
from modules import exchange_system

# Инициализация всех модулей
async def initialize_modules():
    try:
        logger.info("Инициализация модулей...")
        
        # Вызов функций инициализации из модулей
        await shop_system.setup_shop(bot)
        await admin_commands.setup_admin_commands(bot)
        await exchange_system.setup_exchange_system(bot)
        
        logger.info("Все модули успешно загружены!")
    except Exception as e:
        logger.error(f"Ошибка при инициализации модулей: {e}")
        traceback.print_exc()

# Обработчик события готовности
@bot.event
async def on_ready():
    logger.info(f"Бот {bot.user.name} успешно запущен!")
    
    # Инициализация модулей
    await initialize_modules()
    
    # Установка статуса с временем начала активности
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.playing,
            name="mioclient.me",
            start=start_time
        )
    )
    
    logger.info("Статус бота установлен")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    
    logger.error(f"Ошибка при выполнении команды {ctx.command}: {error}")
    await ctx.send(f"❌ Произошла ошибка: {error}")

@bot.event
async def on_error(event, *args, **kwargs):
    logger.error(f"Ошибка в событии {event}: {traceback.format_exc()}")

@bot.command(name="adminhelp")
@commands.has_permissions(administrator=True)
async def admin_help_command(ctx):
    """Список команд администратора"""
    embed = discord.Embed(
        title="📚 Команды администратора",
        description="Список доступных команд администраторов",
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name="🛠️ Управление ботом",
        value="!restart - Перезапустить модули бота\n"
              "!close - Закрыть тикет\n"
              "!embed <заголовок> | <описание> - Создать эмбед\n"
              "!say <сообщение> - Отправить сообщение от имени бота",
        inline=False
    )
    
    # Раздел системы обмена
    embed.add_field(
        name="🔄 Система обмена",
        value="!createexchange <ID канала> <Заголовок> | <Описание> - Создать пост с кнопкой обмена\n"
              "!closeexchange - Закрыть тикет обмена",
        inline=False
    )
    
    embed.set_footer(text=f"Запрошено {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
    
    await ctx.send(embed=embed)

# Команда перезапуска модулей
@bot.command(name="restart")
@commands.has_permissions(administrator=True)
async def restart_modules(ctx):
    """Перезапуск модулей бота"""
    try:
        message = await ctx.send("🔄 Перезапуск модулей...")
        
        # Перезагрузка модулей
        importlib.reload(sys.modules['modules.shop_system'])
        importlib.reload(sys.modules['modules.admin_commands'])
        importlib.reload(sys.modules['modules.exchange_system'])
        
        # Инициализация модулей заново
        await initialize_modules()
        
        await message.edit(content="✅ Модули успешно перезапущены!")
        logger.info("Модули успешно перезапущены администратором")
    except Exception as e:
        logger.error(f"Ошибка при перезапуске модулей: {e}")
        traceback.print_exc()
        await ctx.send(f"❌ Ошибка при перезапуске модулей: {e}")

# Запуск бота
if __name__ == "__main__":
    try:
        # Проверка, запущен ли уже другой экземпляр
        pid_file = 'bot.pid'
        fp = open(pid_file, 'w')
        try:
            fcntl.lockf(fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except IOError:
            # Другой экземпляр уже запущен
            logger.error("Другой экземпляр бота уже запущен. Завершение работы.")
            print("❌ Ошибка: Другой экземпляр бота уже запущен.")
            sys.exit(1)
        
        # Проверка наличия токена
        token = os.getenv("TOKEN")
        if not token:
            logger.error("Токен бота не найден в файле .env")
            print("❌ Ошибка: Токен бота не найден в файле .env")
            sys.exit(1)
        
        # Создание необходимых директорий
        os.makedirs("data", exist_ok=True)
        os.makedirs("logs", exist_ok=True)
        os.makedirs("texts", exist_ok=True)
        os.makedirs("data/exchanges", exist_ok=True)
        
        logger.info("Запуск бота...")
        bot.run(token)
    except Exception as e:
        logger.critical(f"Критическая ошибка при запуске бота: {e}")
        print(f"❌ Критическая ошибка: {e}")
        traceback.print_exc()
