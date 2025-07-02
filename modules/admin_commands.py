import discord
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput, Select
import json
import os
import asyncio

#Импорт данных из модуля магазина
from modules.shop_system import shop_items, save_shop_data, update_shop

class AdminPanelView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Добавить товар", style=discord.ButtonStyle.green)
    async def add_item(self, interaction: discord.Interaction, button: Button):
        modal = AddItemModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Редактировать товар", style=discord.ButtonStyle.primary)
    async def edit_item(self, interaction: discord.Interaction, button: Button):
        if not shop_items:
            await interaction.response.send_message("❗ В магазине нет товаров для редактирования.", ephemeral=True)
            return

        select_view = EditItemSelectView()
        await interaction.response.send_message("Выберите товар для редактирования:", view=select_view, ephemeral=True)

    @discord.ui.button(label="Удалить товар", style=discord.ButtonStyle.danger)
    async def delete_item(self, interaction: discord.Interaction, button: Button):
        if not shop_items:
            await interaction.response.send_message("❗ В магазине нет товаров для удаления.", ephemeral=True)
            return

        select_view = DeleteItemSelectView()
        await interaction.response.send_message("Выберите товар для удаления:", view=select_view, ephemeral=True)

    @discord.ui.button(label="Показать ID товаров", style=discord.ButtonStyle.secondary)
    async def show_item_ids(self, interaction: discord.Interaction, button: Button):
        if not shop_items:
            await interaction.response.send_message("❗ В магазине нет товаров.", ephemeral=True)
            return

        item_list = "\n".join([f"🔹 {item['name']} — ID: {item['id']}, Канал: {item.get('channel_id', 'Основной')}" for item in shop_items])
        embed = discord.Embed(title="📜 Список товаров", description=item_list, color=discord.Color.blue())
        await interaction.response.send_message(embed=embed, ephemeral=True)

class EditItemSelectView(View):
    def __init__(self):
        super().__init__()
        self.add_item(EditItemSelect())

class EditItemSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=item["name"], value=str(item["id"]), description=f"ID: {item['id']}")
            for item in shop_items
        ]
        super().__init__(placeholder="Выберите товар", options=options)

    async def callback(self, interaction: discord.Interaction):
        item_id = int(self.values[0])
        item = next((item for item in shop_items if item["id"] == item_id), None)
        if item:
            modal = EditItemModal(item)
            await interaction.response.send_modal(modal)

class DeleteItemSelectView(View):
    def __init__(self):
        super().__init__()
        self.add_item(DeleteItemSelect())

class DeleteItemSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=item["name"], value=str(item["id"]), description=f"ID: {item['id']}")
            for item in shop_items
        ]
        super().__init__(placeholder="Выберите товар для удаления", options=options)

    async def callback(self, interaction: discord.Interaction):
        item_id = int(self.values[0])
        item = next((item for item in shop_items if item["id"] == item_id), None)
        
        if item:
            # Создание подтверждающего сообщения
            embed = discord.Embed(
                title="⚠️ Подтверждение удаления",
                description=f"Вы уверены, что хотите удалить товар **{item['name']}** (ID: {item['id']})?",
                color=discord.Color.red()
            )
            
            # Создаение кнопки подтверждения
            confirm_view = ConfirmDeleteView(item_id)
            await interaction.response.send_message(embed=embed, view=confirm_view, ephemeral=True)

class ConfirmDeleteView(View):
    def __init__(self, item_id):
        super().__init__(timeout=60)
        self.item_id = item_id

    @discord.ui.button(label="Да, удалить", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: Button):
        item = next((i for i in shop_items if i["id"] == self.item_id), None)
        
        if not item:
            await interaction.response.send_message(f"❗ Ошибка: товар с ID {self.item_id} не найден!", ephemeral=True)
            return
        
        item_name = item['name']
        shop_items.remove(item)
        save_shop_data()
        await update_shop(interaction.client)
        
        await interaction.response.send_message(f"✅ Товар **{item_name}** (ID: {self.item_id}) удалён!", ephemeral=True)
        self.stop()

    @discord.ui.button(label="Отмена", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("❌ Удаление отменено.", ephemeral=True)
        self.stop()

class AddItemModal(Modal, title="Добавить товар"):
    def __init__(self):
        super().__init__()
        self.name = TextInput(label="Название товара", placeholder="Введите название", required=True)
        self.price = TextInput(label="Цена", placeholder="Введите цену", required=True)
        self.discount = TextInput(label="Скидка в рублях", placeholder="Введите сумму скидки", required=False)
        self.description = TextInput(label="Описание", placeholder="Введите описание товара", required=False)
        # Объединение поля изображения и ID канала в одно поле
        self.image_and_channel = TextInput(
            label="URL изображения | ID канала",
            placeholder="URL изображения | ID канала (необязательно)",
            required=False
        )
        self.add_item(self.name)
        self.add_item(self.price)
        self.add_item(self.discount)
        self.add_item(self.description)
        self.add_item(self.image_and_channel)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            price = int(self.price.value)
            discount = int(self.discount.value) if self.discount.value.strip() else 0
            if discount >= price:
                raise ValueError("Скидка не может быть больше или равна цене товара")

            # Разделение URL изображения и ID канала
            image_url = None
            channel_id = None
            if "|" in self.image_and_channel.value:
                parts = self.image_and_channel.value.split("|", 1)
                image_url = parts[0].strip() if parts[0].strip() else None
                if parts[1].strip() and parts[1].strip().lower() != "none":
                    channel_id = int(parts[1].strip())
                    # Проверяем существование канала
                    channel = interaction.client.get_channel(channel_id)
                    if not channel:
                        raise ValueError(f"Канал с ID {channel_id} не найден")
            else:
                # Если разделитель не найден,то это URL изображения
                image_url = self.image_and_channel.value.strip() if self.image_and_channel.value.strip() else None
        except ValueError as e:
            await interaction.response.send_message(f"❗ Ошибка: {str(e)}", ephemeral=True)
            return

        # Генерация ID товара
        new_id = 1
        if shop_items:
            new_id = max(item["id"] for item in shop_items) + 1

        new_item = {
            "id": new_id,
            "name": self.name.value,
            "price": price,
            "discount": discount,
            "description": self.description.value if self.description.value.strip() else None,
            "image": image_url,
            "channel_id": channel_id
        }

        shop_items.append(new_item)
        save_shop_data()
        await update_shop(interaction.client)

        channel_info = f" в канал с ID {channel_id}" if channel_id else ""
        await interaction.response.send_message(f"✅ Товар **{self.name.value}** добавлен{channel_info}!", ephemeral=True)

class EditItemModal(Modal, title="Редактировать товар"):
    def __init__(self, item):
        super().__init__()
        self.name = TextInput(label="Название", default=item["name"], required=True)
        self.price = TextInput(label="Цена", default=str(item["price"]), required=True)
        self.discount = TextInput(label="Скидка в рублях", default=str(item.get("discount", 0)), required=False)
        self.description = TextInput(label="Описание", default=item.get("description", ""), required=False)
        
        # Объединение поля изображения и ID канала
        image_value = item.get("image", "") or ""  # Убедимся, что None превратится в пустую строку
        channel_id = item.get("channel_id")
        channel_value = str(channel_id) if channel_id is not None else ""
        combined_value = f"{image_value} | {channel_value}" if channel_value else image_value
        
        self.image_and_channel = TextInput(
            label="URL изображения | ID канала",
            default=combined_value,
            placeholder="URL изображения | ID канала (необязательно)",
            required=False
        )
        
        self.item_id = item["id"]
        
        self.add_item(self.name)
        self.add_item(self.price)
        self.add_item(self.discount)
        self.add_item(self.description)
        self.add_item(self.image_and_channel)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            price = int(self.price.value)
            discount = int(self.discount.value) if self.discount.value.strip() else 0
            if discount >= price:
                raise ValueError("Скидка не может быть больше или равна цене товара")

            # Разделение URL изображения и ID канала
            image_url = None
            channel_id = None
            if "|" in self.image_and_channel.value:
                parts = self.image_and_channel.value.split("|", 1)
                image_url = parts[0].strip() if parts[0].strip() else None
                if parts[1].strip() and parts[1].strip().lower() != "none":
                    channel_id = int(parts[1].strip())
                    # Проверяем существование канала
                    channel = interaction.client.get_channel(channel_id)
                    if not channel:
                        raise ValueError(f"Канал с ID {channel_id} не найден")
            else:
                # Если разделитель не найден,то это URL изображения
                image_url = self.image_and_channel.value.strip() if self.image_and_channel.value.strip() else None
        except ValueError as e:
            await interaction.response.send_message(f"❗ Ошибка: {str(e)}", ephemeral=True)
            return

        item = next((i for i in shop_items if i["id"] == self.item_id), None)
        if item:
            item["name"] = self.name.value
            item["price"] = price
            item["discount"] = discount
            item["description"] = self.description.value if self.description.value.strip() else None
            item["image"] = image_url
            item["channel_id"] = channel_id
            
            save_shop_data()
            await update_shop(interaction.client)
            
            channel_info = f" в канал с ID {channel_id}" if channel_id else ""
            await interaction.response.send_message(f"✅ Товар **{self.name.value}** обновлён{channel_info}!", ephemeral=True)

async def update_admin_panel(bot):
    """Обновление админ-панели"""
    admin_channel_id = int(os.getenv("ADMIN_CHANNEL_ID"))
    channel = bot.get_channel(admin_channel_id)
    
    if not channel:
        return
    
    await channel.purge()
    embed = discord.Embed(
        title="🔧 Админ-меню", 
        description="Управление магазином", 
        color=discord.Color.red()
    )
    embed.set_footer(text="✨ Powered by MrFolium ✨")
    
    view = AdminPanelView()
    await channel.send(embed=embed, view=view)


async def setup_admin_commands(bot):
    """Настройка админ-команд"""
    await update_admin_panel(bot)

    @bot.command(name="say")
    @commands.has_permissions(administrator=True)
    async def say(ctx, channel: discord.TextChannel, *, message):
        await ctx.message.delete()
        await channel.send(message)

    @bot.command(name="embed")
    @commands.has_permissions(administrator=True)
    async def embed_say(ctx, channel: discord.TextChannel, *, message):
        await ctx.message.delete()
        # Разделение сообщения на заголовок и описание
        if "|" in message:
            title, description = message.split("|", 1)
        else:
            title = ""
            description = message

        embed = discord.Embed(
            title=title.strip(),
            description=description.strip(),
            color=discord.Color.green()
        )
        await channel.send(embed=embed)

    @bot.command(name="close")
    @commands.has_permissions(administrator=True)
    async def close_ticket(ctx):
        if not ctx.channel.name.startswith('заказ-'):
            await ctx.send("❗ Эта команда работает только в тикетах!")
            return

        review_channel_id = int(os.getenv("REVIEW_CHANNEL_ID"))
        review_channel = bot.get_channel(review_channel_id)

        ticket_user = ctx.guild.get_member_named(ctx.channel.name.replace('заказ-', ''))

        if ticket_user and review_channel:
            try:
                member_role = discord.utils.get(ctx.guild.roles, name="Участник")
                if member_role:
                    await ticket_user.add_roles(member_role)
                    await ctx.send(f"✅ Роль 'Участник' выдана пользователю {ticket_user.mention}")
                else:
                    await ctx.send("❌ Роль 'Участник' не найдена на сервере!")
            except Exception as e:
                await ctx.send(f"❌ Ошибка при выдаче роли: {e}")

            await review_channel.send(
                f"{ticket_user.mention}, спасибо за покупку! "
                "Теперь вы можете оставить отзыв о нашем сервисе."
            )

            await ctx.send("✅ Тикет закрывается через 5 секунд...")
            await asyncio.sleep(5)
            await ctx.channel.delete()

    @close_ticket.error
    async def close_ticket_error(ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ У вас нет прав на выполнение этой команды!")


        @close_ticket.error
        async def close_ticket_error(ctx, error):
            if isinstance(error, commands.MissingPermissions):
                await ctx.send("❌ У вас нет прав на выполнение этой команды!")

    @bot.command(name="itemids")
    @commands.has_permissions(administrator=True)
    async def show_item_ids(ctx):
        await ctx.message.delete()
        
        if not shop_items:
            await ctx.send("❗ В магазине нет товаров.", delete_after=5)
            return

        item_list = "\n".join([
            f"🔹 {item['name']} — ID: {item['id']}, Канал: {item.get('channel_id', 'Основной')}"
            for item in shop_items
        ])
        
        embed = discord.Embed(title="📜 Список товаров", description=item_list, color=discord.Color.blue())
        
        message = await ctx.send(embed=embed)
        await asyncio.sleep(30)
        await message.delete()


    # Команда обновления магазина
    @bot.command(name="updateshop")
    @commands.has_permissions(administrator=True)
    async def update_shop_command(ctx):
        await ctx.message.delete()
        await update_shop(bot)
        await ctx.send("✅ Магазин обновлен!", delete_after=5)

    # Команда обновления админ-панели
    @bot.command(name="updateadmin")
    @commands.has_permissions(administrator=True)
    async def update_admin_command(ctx):
        await ctx.message.delete()
        await update_admin_panel(bot)
        await ctx.send("✅ Админ-панель обновлена!", delete_after=5)

    # Команда очистки канала
    @bot.command(name="clear")
    @commands.has_permissions(administrator=True)
    async def clear_channel(ctx, amount: int = 100):
        await ctx.message.delete()
        deleted = await ctx.channel.purge(limit=amount)
        message = await ctx.send(f"✅ Удалено {len(deleted)} сообщений!")
        await asyncio.sleep(5)
        await message.delete()

    @clear_channel.error
    async def clear_channel_error(ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ У вас нет прав на выполнение этой команды!", delete_after=5)
        elif isinstance(error, commands.BadArgument):
            await ctx.send("❌ Укажите корректное число сообщений для удаления!", delete_after=5)

    # Команда отправки личного сообщения пользователю
    @bot.command(name="dm")
    @commands.has_permissions(administrator=True)
    async def dm_user(ctx, user: discord.Member, *, message):
        await ctx.message.delete()
        try:
            await user.send(message)
            await ctx.send(f"✅ Сообщение отправлено пользователю {user.mention}!", delete_after=5)
        except discord.Forbidden:
            await ctx.send(f"❌ Не удалось отправить сообщение пользователю {user.mention}. Возможно, у него закрыты личные сообщения.", delete_after=10)

    @dm_user.error
    async def dm_user_error(ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ У вас нет прав на выполнение этой команды!", delete_after=5)
        elif isinstance(error, commands.MemberNotFound):
            await ctx.send("❌ Пользователь не найден!", delete_after=5)
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("❌ Укажите пользователя и сообщение! Пример: !dm @пользователь текст сообщения", delete_after=10)

    # Команда создания объявления
    @bot.command(name="announce")
    @commands.has_permissions(administrator=True)
    async def announce(ctx, channel: discord.TextChannel, *, message):
        await ctx.message.delete()
        embed = discord.Embed(
            title="📢 Объявление",
            description=message,
            color=discord.Color.gold(),
            timestamp=discord.utils.utcnow()
        )
        embed.set_footer(text=f"От {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
        await channel.send(embed=embed)
        await ctx.send(f"✅ Объявление отправлено в канал {channel.mention}!", delete_after=5)

    @announce.error
    async def announce_error(ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ У вас нет прав на выполнение этой команды!", delete_after=5)
        elif isinstance(error, commands.ChannelNotFound):
            await ctx.send("❌ Канал не найден!", delete_after=5)
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("❌ Укажите канал и текст объявления! Пример: !announce #канал текст объявления", delete_after=10)

    # Команда отправки данных оплаты
    @bot.command(name="pay")
    @commands.has_permissions(administrator=True)
    async def send_payment_info(ctx):
        """Отправляет данные для оплаты в текущий канал"""
        await ctx.message.delete()
        
        # Данные оплаты
        card_number = os.getenv("CARD_NUMBER")
        card_holder = os.getenv("CARD_HOLDER")
        bank = os.getenv("BANK_NAME")
        
        # Создаем эмбед с данными оплаты
        embed = discord.Embed(
            title="💳 Данные для оплаты",
            description="Используйте эти данные для оплаты:",
            color=discord.Color.green()
        )
        
        embed.add_field(name="Номер карты", value=f"```\n{card_number}\n```", inline=False)
        embed.add_field(name="Получатель", value=card_holder, inline=False)
        embed.add_field(name="Банк", value=bank, inline=True)
        
        # Инструкция
        embed.add_field(
            name="Что делать",
            value=(
                "1. Переведите деньги на карту\n"
                "2. Скачайте чек\n"
                "3. Отправьте чек в этот канал"
            ),
            inline=False
        )
        
        await ctx.send(embed=embed)

    @send_payment_info.error
    async def payment_info_error(ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ У вас нет прав на эту команду!", delete_after=5)


    print("✅ Модуль админ-команд загружен")        
