import discord
from discord.ext import commands
import asyncio
import json
import os
from datetime import datetime

# Файл хранения данных о сделках
EXCHANGES_FILE = "data/exchanges/exchanges.json"

# Проверка, что директория существует
os.makedirs(os.path.dirname(EXCHANGES_FILE), exist_ok=True)

# Загрузка данных о сделках
def load_exchanges():
    if os.path.exists(EXCHANGES_FILE):
        with open(EXCHANGES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"exchanges": [], "active_tickets": {}}

# Сохранение данных о сделках
def save_exchanges(data):
    with open(EXCHANGES_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# Класс создания выпадающего меню выбора пользователя
class UserSelect(discord.ui.UserSelect):
    def __init__(self, author_id):
        self.author_id = author_id
        super().__init__(
            placeholder="Выберите пользователя для сделки",
            min_values=1,
            max_values=1,
        )

    async def callback(self, interaction: discord.Interaction):
        # Проверка, что выбор сделал автор запроса
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("Только автор запроса может выбрать пользователя для сделки.", ephemeral=True)
            return
        
        selected_user = self.values[0]
        
        # Проверка, что пользователь не выбрал себя
        if selected_user.id == self.author_id:
            await interaction.response.send_message("Вы не можете выбрать себя для сделки.", ephemeral=True)
            return
        
        # Проверка, что выбранный пользователь не бот
        if selected_user.bot:
            await interaction.response.send_message("Вы не можете выбрать бота для сделки.", ephemeral=True)
            return
        
        # Создание тикета сделки
        await create_exchange_ticket(interaction, selected_user)

# Класс кнопки создания сделки
class ExchangeButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)  # Кнопка будет активна всегда
    
    @discord.ui.button(label="Создать сделку", style=discord.ButtonStyle.primary, custom_id="create_exchange", emoji="🔄")
    async def create_exchange(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Создание выпадающее меню выбора пользователя
        view = discord.ui.View(timeout=60)
        view.add_item(UserSelect(interaction.user.id))
        
        await interaction.response.send_message(
            "Выберите пользователя, с которым хотите совершить сделку:",
            view=view,
            ephemeral=True
        )

# Функция создания тикета сделки
async def create_exchange_ticket(interaction, partner):
    guild = interaction.guild
    author = interaction.user
    
    # Получение ID категории тикетов из .env
    ticket_category_id = int(os.getenv("TICKET_CATEGORY_ID"))
    category = guild.get_channel(ticket_category_id)
    
    if not category:
        await interaction.response.send_message("Ошибка: категория для тикетов не найдена.", ephemeral=True)
        return
    
    # Создание имени канала тикета
    ticket_name = f"сделка-{author.name}-{partner.name}"
    
    # Создание канала тикета
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        author: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        partner: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
    }
    
    # Добавление прав у администраторов
    for role in guild.roles:
        if role.permissions.administrator:
            overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
    
    # Создание канала тикета
    ticket_channel = await guild.create_text_channel(
        name=ticket_name,
        category=category,
        overwrites=overwrites,
        topic=f"Сделка между {author.name} и {partner.name}"
    )
    
    # Сохранение информации о тикете
    exchanges = load_exchanges()
    exchanges["active_tickets"][str(ticket_channel.id)] = {
        "author_id": author.id,
        "partner_id": partner.id,
        "created_at": datetime.now().isoformat(),
        "status": "open"
    }
    save_exchanges(exchanges)
    
    # Получение ID роли администратора из .env
    admin_role_id = os.getenv("ADMIN_ROLE_ID", "0")
    admin_mention = f"<@&{admin_role_id}>" if admin_role_id != "0" else ""
    
    # Отправление сообщения в канал тикета
    embed = discord.Embed(
        title="🔄 Новый запрос на сделку",
        description=f"Сделка между {author.mention} и {partner.mention}",
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name="📝 Инструкция",
        value=(
            "1. Опишите предметы, которые хотите обменять\n"
            "2. Дождитесь подтверждения от партнера\n"
            "3. Администратор проверит и подтвердит сделку\n"
            "4. После завершения сделки тикет будет закрыт"
        ),
        inline=False
    )
    
    embed.add_field(
        name="⚠️ Важно",
        value=(
            "- Будьте вежливы и терпеливы\n"
            "- Четко описывайте предметы сделки\n"
            "- Дождитесь подтверждения администратора перед сделкой\n"
            "- Используйте команду `!closeexchange` для закрытия тикета"
        ),
        inline=False
    )
    
    embed.set_footer(text=f"ID тикета: {ticket_channel.id}")
    
    # Создание кнопки управления тикетом
    view = discord.ui.View(timeout=None)
    
    # Кнопка закрытия тикета
    close_button = discord.ui.Button(
        style=discord.ButtonStyle.danger,
        label="Закрыть тикет",
        emoji="🔒",
        custom_id=f"close_exchange_{ticket_channel.id}"
    )
    view.add_item(close_button)
    
    await ticket_channel.send(
        content=f"{author.mention} {partner.mention} {admin_mention}",
        embed=embed,
        view=view
    )
    
    # Отправление подтверждения пользователю
    await interaction.edit_original_response(
        content=f"✅ Тикет для сделки создан! Перейдите в канал {ticket_channel.mention}",
        view=None
    )

# Функция создания кнопки сделки в форуме
async def create_exchange_post(ctx, channel_id, title, description, image_url=None):
    channel = ctx.guild.get_channel(int(channel_id))
    
    if not channel:
        await ctx.send("❌ Указанный канал не найден.")
        return
    
    # Проверка, является ли канал форумом
    if not isinstance(channel, discord.ForumChannel):
        await ctx.send("❌ Указанный канал не является форумом.")
        return
    
    # Создание эмбеда для сообщения
    embed = discord.Embed(
        title=title,
        description=description,
        color=discord.Color.blue()
    )
    
    # Добавление изображения, если оно предоставлено
    if image_url:
        embed.set_image(url=image_url)
    
    embed.add_field(
        name="Как начать сделку?",
        value="Нажмите на кнопку «Создать сделку» ниже и выберите пользователя, с которым хотите совершить сделку.",
        inline=False
    )
    
    embed.add_field(
        name="Правила сделок",
        value=(
            "1. Сделки происходят только через официальные тикеты\n"
            "2. Администрация выступает гарантом сделки\n"
            "3. Запрещены обманы и мошенничество\n"
            "4. Подробно описывайте предметы сделки"
        ),
        inline=False
    )
    
    embed.set_footer(text="✨ Powered by MrFolium ✨")
    
    # Создание кнопки сделки
    view = ExchangeButton()
    
    # Создание темы в форуме
    thread = await channel.create_thread(
        name=title,
        content="Система сделок",
        embed=embed,
        view=view
    )
    
    await ctx.send(f"✅ Сообщение с кнопкой сделки создано в форуме: {thread.mention}")

# Функция закрытия тикета сделки
async def close_exchange_ticket(interaction, ticket_id):
    channel = interaction.guild.get_channel(int(ticket_id))
    
    if not channel:
        await interaction.response.send_message("❌ Канал тикета не найден.", ephemeral=True)
        return
    
    # Проверка, является ли пользователь участником сделки или администратором
    exchanges = load_exchanges()
    ticket_info = exchanges["active_tickets"].get(str(ticket_id))
    
    if not ticket_info:
        await interaction.response.send_message("❌ Информация о тикете не найдена.", ephemeral=True)
        return
    
    is_admin = interaction.user.guild_permissions.administrator
    is_participant = (interaction.user.id == ticket_info["author_id"] or 
                      interaction.user.id == ticket_info["partner_id"])
    
    if not (is_admin or is_participant):
        await interaction.response.send_message("❌ У вас нет прав на закрытие этого тикета.", ephemeral=True)
        return
    
    # Отправление сообщения о закрытии
    await interaction.response.send_message("🔒 Закрытие тикета сделки...")
    
    # Создание эмбеда с информацией о закрытии
    embed = discord.Embed(
        title="🔒 Тикет сделки закрыт",
        description=f"Тикет был закрыт пользователем {interaction.user.mention}",
        color=discord.Color.red()
    )
    
    embed.add_field(
        name="Участники сделки",
        value=f"<@{ticket_info['author_id']}> и <@{ticket_info['partner_id']}>",
        inline=False
    )
    
    embed.add_field(
        name="Время создания",
        value=f"<t:{int(datetime.fromisoformat(ticket_info['created_at']).timestamp())}:F>",
        inline=True
    )
    
    embed.add_field(
        name="Время закрытия",
        value=f"<t:{int(datetime.now().timestamp())}:F>",
        inline=True
    )
    
    await channel.send(embed=embed)
    
    # Обновление статуса тикета
    ticket_info["status"] = "closed"
    ticket_info["closed_at"] = datetime.now().isoformat()
    ticket_info["closed_by"] = interaction.user.id
    save_exchanges(exchanges)
    
    # Архивация канала через 10 секунд
    await asyncio.sleep(10)
    
    try:
        # Изменение прав доступа, чтобы никто не мог писать
        overwrites = channel.overwrites
        for target, overwrite in overwrites.items():
            overwrite.send_messages = False
            overwrites[target] = overwrite
        
        await channel.edit(overwrites=overwrites)
        
        # Добавление префикса к названию канала
        new_name = f"закрыт-{channel.name}"
        await channel.edit(name=new_name)
        
        # Перемещение в архивную категорию, если она есть
        archive_category_id = os.getenv("ARCHIVE_CATEGORY_ID")
        if archive_category_id:
            archive_category = interaction.guild.get_channel(int(archive_category_id))
            if archive_category:
                await channel.edit(category=archive_category)
    
    except Exception as e:
        print(f"Ошибка при архивации канала: {e}")

# Функция настройки модуля
async def setup_exchange_system(bot):
    # Команда создания сообщения с кнопкой сделки
    @bot.command(name="createexchange")
    @commands.has_permissions(administrator=True)
    async def create_exchange_command(ctx, channel_id: str, *, title_and_description: str):
        """Создает сообщение с кнопкой сделки в указанном форуме"""
        try:
            # Проверка наличия изображения
            image_url = None
            if ctx.message.attachments:
                image_url = ctx.message.attachments[0].url
            
            # Разделение заголовока и описания
            parts = title_and_description.split('|', 1)
            if len(parts) < 2:
                await ctx.send("❌ Неверный формат. Используйте: `!createexchange ID_канала Заголовок | Описание`")
                return
            
            title = parts[0].strip()
            description = parts[1].strip()
            
            await create_exchange_post(ctx, channel_id, title, description, image_url)
        
        except Exception as e:
            await ctx.send(f"❌ Произошла ошибка: {e}")
    
    # Команда закрытия тикета сделки
    @bot.command(name="closeexchange")
    async def close_exchange_command(ctx):
        """Закрывает текущий тикет сделки"""
        # Проверка, что команда вызвана в канале тикета
        exchanges = load_exchanges()
        if str(ctx.channel.id) not in exchanges["active_tickets"]:
            await ctx.send("❌ Эта команда может быть использована только в канале тикета сделки.")
            return
        
        # Проверка прав пользователя
        ticket_info = exchanges["active_tickets"][str(ctx.channel.id)]
        is_admin = ctx.author.guild_permissions.administrator
        is_participant = (ctx.author.id == ticket_info["author_id"] or 
                          ctx.author.id == ticket_info["partner_id"])
        
        if not (is_admin or is_participant):
            await ctx.send("❌ У вас нет прав на закрытие этого тикета.")
            return
        
        # Создание объекта взаимодействия для закрытия тикета
        class DummyInteraction:
            def __init__(self, ctx):
                self.guild = ctx.guild
                self.user = ctx.author
                self.response = self
            
            async def send_message(self, content, ephemeral=False):
                await ctx.send(content)
        
        # Закрытие тикета
        await close_exchange_ticket(DummyInteraction(ctx), ctx.channel.id)
    
    # Обработчик кнопки закрытия тикета
    @bot.listen('on_interaction')
    async def exchange_interaction_handler(interaction):
        if interaction.type == discord.InteractionType.component:
            custom_id = interaction.data.get("custom_id", "")
            
            # Обработка кнопки закрытия тикета
            if custom_id.startswith("close_exchange_"):
                ticket_id = custom_id.split("_")[-1]
                await close_exchange_ticket(interaction, ticket_id)

    # Регистрация постоянной кнопки
    bot.add_view(ExchangeButton())
    
    # Добавление информации о модуле в команду !adminhelp
    if hasattr(bot, 'admin_help_info'):
        bot.admin_help_info.append({
            "name": "Система сделок",
            "commands": [
                {"name": "!createexchange <ID_канала> <Заголовок | Описание>", 
                 "description": "Создает сообщение с кнопкой сделки в указанном форуме"},
                {"name": "!closeexchange", 
                 "description": "Закрывает текущий тикет сделки"}
            ]
        })
    
    print("✅ Модуль системы сделок успешно загружен!")
