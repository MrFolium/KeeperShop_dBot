import discord
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput
import json
import os
import asyncio

SHOP_DATA_FILE = "data/shop_data.json"
CART_DATA_FILE = "data/user_carts.json"

# Загрузка данных магазина
if os.path.exists(SHOP_DATA_FILE):
    try:
        with open(SHOP_DATA_FILE, "r") as f:
            content = f.read().strip()
            if content:
                shop_items = json.loads(content)
            else:
                shop_items = []
    except (json.JSONDecodeError, FileNotFoundError):
        shop_items = []
else:
    shop_items = []

# Инициализация товаров магазина
for index, item in enumerate(shop_items, start=1):
    if "id" not in item:
        item["id"] = index
    if "discount" not in item:
        item["discount"] = 0
    if "channel_id" not in item:
        item["channel_id"] = None

# Сохранение данных магазина
os.makedirs("data", exist_ok=True)
with open(SHOP_DATA_FILE, "w") as f:
    json.dump(shop_items, f, ensure_ascii=False, indent=4)

# Загрузка данных корзин
if os.path.exists(CART_DATA_FILE):
    try:
        with open(CART_DATA_FILE, "r") as f:
            content = f.read().strip()
            if content:
                user_carts = json.loads(content)
            else:
                user_carts = {}
    except (json.JSONDecodeError, FileNotFoundError):
        user_carts = {}
else:
    user_carts = {}

def save_cart_data():
    """Сохранение данных корзин пользователей в файл"""
    os.makedirs("data", exist_ok=True)
    with open(CART_DATA_FILE, "w") as f:
        json.dump(user_carts, f, ensure_ascii=False, indent=4)

def save_shop_data():
    """Сохранение данных магазина в файл"""
    for index, item in enumerate(shop_items, start=1):
        item["id"] = index
    os.makedirs("data", exist_ok=True)
    with open(SHOP_DATA_FILE, "w") as f:
        json.dump(shop_items, f, ensure_ascii=False, indent=4)

class ShopItemView(View):
    def __init__(self, item_name, price):
        super().__init__(timeout=None)
        self.item_name = item_name
        self.price = price

    @discord.ui.button(label="✔ Добавить", style=discord.ButtonStyle.green)
    async def add_to_cart(self, interaction: discord.Interaction, button: Button):
        user_id = str(interaction.user.id)
        if user_id not in user_carts:
            user_carts[user_id] = []
        user_carts[user_id].append({"name": self.item_name, "price": self.price})
        save_cart_data()
        await interaction.response.send_message(f'✅ {self.item_name} добавлен в корзину!', ephemeral=True, delete_after=10)

    @discord.ui.button(label="✖ Убрать", style=discord.ButtonStyle.red)
    async def remove_from_cart(self, interaction: discord.Interaction, button: Button):
        user_id = str(interaction.user.id)
        if user_id in user_carts:
            for item in user_carts[user_id]:
                if item["name"] == self.item_name:
                    user_carts[user_id].remove(item)
                    save_cart_data()
                    await interaction.response.send_message(f'❌ {self.item_name} убран из корзины.', ephemeral=True, delete_after=10)
                    return
        await interaction.response.send_message(f'❗ {self.item_name} нет в вашей корзине.', ephemeral=True, delete_after=10)

class CartManagerView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="👁️‍🗨️ Посмотреть", style=discord.ButtonStyle.primary)
    async def show_cart(self, interaction: discord.Interaction, button: Button):
        user_id = str(interaction.user.id)
        user_cart = user_carts.get(user_id, [])
        if not user_cart:
            await interaction.response.send_message('❗ Ваша корзина пуста.', ephemeral=True)
            return
        cart_description = "\n".join([f"- {item['name']}: {item['price']}р" for item in user_cart])
        total_price = sum(item['price'] for item in user_cart)
        embed = discord.Embed(title="🛒 Ваша корзина", description=cart_description, color=discord.Color.blue())
        embed.add_field(name="Итого", value=f'{total_price}р', inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="🗑 Очистить", style=discord.ButtonStyle.danger)
    async def clear_cart(self, interaction: discord.Interaction, button: Button):
        user_id = str(interaction.user.id)
        user_carts[user_id] = []
        save_cart_data()
        await interaction.response.send_message("🗑 Корзина очищена!", ephemeral=True)

    @discord.ui.button(label="📝 К покупке", style=discord.ButtonStyle.success)
    async def order(self, interaction: discord.Interaction, button: Button):
        user_id = str(interaction.user.id)
        user_cart = user_carts.get(user_id, [])
        if not user_cart:
            await interaction.response.send_message("❗ Ваша корзина пуста! Добавьте товары перед оформлением заказа.", ephemeral=True)
            return
        await interaction.response.send_modal(OrderForm())

class OrderForm(Modal, title="Форма заказа"):
    def __init__(self):
        super().__init__()
        self.coords = TextInput(label="Координаты", placeholder="Введите координаты...")
        self.dimension = TextInput(label="Измерение", placeholder="Введите измерение...")
        self.username = TextInput(label="Ваш ник", placeholder="Введите ваш ник...")
        self.comment = TextInput(label="Комментарий", placeholder="Необязательно", required=False)
        self.add_item(self.coords)
        self.add_item(self.dimension)
        self.add_item(self.username)
        self.add_item(self.comment)

    async def on_submit(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        if user_id not in user_carts or not user_carts[user_id]:
            await interaction.response.send_message("❗ Ваша корзина пуста! Нельзя оформить заказ.", ephemeral=True)
            return
        await create_ticket(
            interaction,
            coords=self.coords.value,
            dimension=self.dimension.value,
            username=self.username.value,
            comment=self.comment.value,
            cart=user_carts[user_id]
        )
        user_carts[user_id] = []
        save_cart_data()
        await interaction.response.send_message("✅ Заказ оформлен! Тикет создан.", ephemeral=True)

async def create_ticket(interaction, coords, dimension, username, comment, cart):
    bot = interaction.client
    guild_id = int(os.getenv("GUILD_ID"))
    ticket_category_id = int(os.getenv("TICKET_CATEGORY_ID"))
    guild = bot.get_guild(guild_id)
    category = discord.utils.get(guild.categories, id=ticket_category_id)
    if not category:
        await interaction.followup.send("❌ Ошибка: категория тикетов не найдена.", ephemeral=True)
        return

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False, send_messages=False),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }

    admin_role = discord.utils.get(guild.roles, name="Admin")
    if admin_role:
        overwrites[admin_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

    ticket_channel = await category.create_text_channel(
        f'заказ-{interaction.user.name}',
        overwrites=overwrites
    )

    cart_description = "\n".join([f"- {item['name']}: {item['price']}р" for item in cart]) or "Пусто"
    total_price = sum(item['price'] for item in cart)

    embed = discord.Embed(title="📝 Новый заказ", color=discord.Color.orange())
    embed.add_field(name="Координаты", value=coords, inline=False)
    embed.add_field(name="Измерение", value=dimension, inline=False)
    embed.add_field(name="Ник", value=username, inline=False)
    embed.add_field(name="Комментарий", value=comment or "Отсутствует", inline=False)
    embed.add_field(name="Корзина", value=cart_description, inline=False)
    embed.add_field(name="Итого", value=f'{total_price}р', inline=False)
    embed.add_field(name="Покупатель", value=f"{interaction.user.mention}", inline=False)
    embed.timestamp = discord.utils.utcnow()

    await ticket_channel.send(embed=embed)

    # Информация о времени работы магазина
    time_notice_embed = discord.Embed(
        title="⏰ Время работы магазина",
        description="**Обратите внимание!** Магазин работает с 11:00 до 22:00 по МСК.\nЗаказы, оформленные вне рабочего времени, будут обработаны в рабочее время.",
        color=discord.Color.blue()
    )

    # Информация о стоимости доставки по незеру
    delivery_notice_embed = discord.Embed(
        title="🚚 Стоимость доставки по незеру",
        description="**Важная информация!** Доставка свыше 5000 блоков по незеру будет стоить 2р/1000 блоков.\nПервые 5000 блоков включены в стоимость заказа и доставляются бесплатно.",
        color=discord.Color.gold()
    )

    await ticket_channel.send(embed=time_notice_embed)
    await ticket_channel.send(embed=delivery_notice_embed)
    await ticket_channel.send(f"{interaction.user.mention}, ваш заказ оформлен!")

async def update_shop(bot):
    """Обновление канала магазина со всеми товарами"""
    shop_channel_id = int(os.getenv("SHOP_CHANNEL_ID"))
    channel = bot.get_channel(shop_channel_id)
    if not channel:
        print(f"❌ Канал магазина с ID {shop_channel_id} не найден")
        return

    # Получение всех каналов, в которых есть товары
    channel_ids = set([shop_channel_id])
    for item in shop_items:
        if item.get("channel_id"):
            channel_ids.add(int(item.get("channel_id")))

    # Удаление только сообщений бота с товарами в каждом канале
    for channel_id in channel_ids:
        target_channel = bot.get_channel(channel_id)
        if not target_channel:
            print(f"❌ Канал с ID {channel_id} не найден")
            continue
            
        # Удаление только сообщений бота
        async for message in target_channel.history(limit=200):
            # Проверка, что сообщение от бота и содержит эмбед (товар)
            if message.author == bot.user and message.embeds and len(message.embeds) > 0:
                try:
                    await message.delete()
                except Exception as e:
                    print(f"Ошибка при удалении сообщения: {e}")
                    
        print(f"✅ Удалены старые товары в канале {target_channel.name}")

    # Группировка товаров по каналам
    channel_items = {}
    # Основной канал магазина
    channel_items[shop_channel_id] = []
    
    # Группировка товаров по указанным каналам
    for item in shop_items:
        channel_id = item.get("channel_id")
        
        # Если канал указан и он существует, товар добавляется в этот канал
        if channel_id and bot.get_channel(int(channel_id)):
            if int(channel_id) not in channel_items:
                channel_items[int(channel_id)] = []
            channel_items[int(channel_id)].append(item)
        else:
            # Иначе товар добавляется в основной канал магазина
            channel_items[shop_channel_id].append(item)

    # Публикация товаров в соответствующих каналах
    for channel_id, items in channel_items.items():
        target_channel = bot.get_channel(channel_id)
        
        if not target_channel:
            print(f"❌ Канал с ID {channel_id} не найден")
            continue
        
        # Публикация товаров
        for item in items:
            original_price = item["price"]
            discount = item.get("discount", 0)
            final_price = original_price - discount
            
            # Формирование описания с ценой и описанием товара
            price_text = f'Цена: ~~{original_price}р~~ **{final_price}р**\n' if discount > 0 else f'Цена: {original_price}р\n'
            description_text = item.get("description", "") or ""
            full_description = f"{price_text}\n{description_text}" if description_text else price_text
            
            embed = discord.Embed(
                title=item["name"], 
                description=full_description,
                color=discord.Color.green()
            )
            
            if "image" in item and item["image"]:
                embed.set_image(url=item["image"])
            
            view = ShopItemView(item["name"], final_price)
            await target_channel.send(embed=embed, view=view)

        print(f"✅ Товары опубликованы в {len(channel_items)} каналах")

async def update_cart_channel(bot):
    """Обновление канала корзины с менеджером корзины"""
    cart_channel_id = int(os.getenv("CART_CHANNEL_ID"))
    channel = bot.get_channel(cart_channel_id)
    if not channel:
        return

    # Удаление только сообщений бота с управлением корзиной
    async for message in channel.history(limit=50):
        if message.author == bot.user and message.embeds and len(message.embeds) > 0:
            try:
                # Проверка, что это сообщение с управлением корзиной
                if message.embeds[0].title == "🛒 Управление корзиной":
                    await message.delete()
            except Exception as e:
                print(f"Ошибка при удалении сообщения корзины: {e}")

    embed = discord.Embed(title="🛒 Управление корзиной", description="Нажмите кнопку, чтобы взаимодействовать с корзиной", color=discord.Color.gold())
    view = CartManagerView()
    await channel.send(embed=embed, view=view)

async def setup_shop(bot):
    """Инициализация магазина и корзины"""
    await update_shop(bot)
    await update_cart_channel(bot)
    print("✅ Модуль магазина загружен")
