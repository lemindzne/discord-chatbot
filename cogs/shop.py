import discord
from discord import app_commands
from discord.ext import commands
import database as db

DATE_LOCATIONS = {
    "truong_hoc": {"name": "Hành lang trường", "points": 0},
    "cong_vien": {"name": "Công viên (Tập luyện)", "points": 600},
    "sieu_thi": {"name": "Siêu thị", "points": 1000},
    "quan_cafe": {"name": "Quán Cafe", "points": 1500},
    "nha_rieng": {"name": "Nhà riêng", "points": 2500}
}

# Class tạo Menu chọn món đồ
class ItemSelect(discord.ui.Select):
    def __init__(self, items):
        options = [
            discord.SelectOption(label=info['name'], value=key, description=f"Giá: {info['price']} 💰")
            for key, info in items.items()
        ]
        super().__init__(placeholder="Chọn một món quà muốn mua...", options=options)

    async def callback(self, interaction: discord.Interaction):
        item_id = self.values[0]
        item_info = self.view.items[item_id]
        user_coins = db.get_user_coins(interaction.user.id)

        if user_coins < item_info['price']:
            return await interaction.response.send_message(f"Cậu không đủ tiền mua {item_info['name']} rồi!", ephemeral=True)

        # Xử lý mua đồ
        db.update_user_coins(interaction.user.id, -item_info['price'])
        db.add_to_inventory(interaction.user.id, item_id, 1)
        
        await interaction.response.send_message(f"📦 Đã mua **{item_info['name']}** thành công! Cậu có thể kiểm tra trong `/bag`.", ephemeral=True)

class DateSelect(discord.ui.Select):
    def __init__(self, user_points):
        options = [
            discord.SelectOption(label=info['name'], value=key)
            for key, info in DATE_LOCATIONS.items() 
            if user_points >= info['points'] # CHỈ HIỆN NẾU ĐỦ ĐIỂM
        ]
        super().__init__(placeholder="Rủ Mahiru đi đâu đó...", options=options)

    async def callback(self, interaction: discord.Interaction):
        loc_id = self.values[0]
        db.set_user_context(interaction.user.id, loc_id)
        await interaction.response.send_message(f"Mahiru: 'Được chứ, mình đi đến **{DATE_LOCATIONS[loc_id]['name']}** nhé!~'", ephemeral=True)
        
# Class chứa giao diện Shop
class ShopView(discord.ui.View):
    def __init__(self, items):
        super().__init__(timeout=60)
        self.items = items
        self.add_item(ItemSelect(items))

class Shop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.items = {
            "pudding": {"name": "Bánh Pudding 🍮", "price": 50, "buff": 25, "msg": "Mahiru mỉm cười: 'Cậu nhớ cả món mình thích sao?'"},
            "tea": {"name": "Trà đen ☕", "price": 30, "buff": 10, "msg": "Mahiru nhấp một ngụm trà: 'Hương vị thật nhẹ nhàng...'"},
            "ribbon": {"name": "Ruy băng đỏ 🎀", "price": 150, "buff": 80, "msg": "Mahiru đỏ mặt: 'Tặng mình món đồ xinh thế này thật sao?'"}
        }

    @app_commands.command(name="shop", description="Mở cửa hàng quà tặng Mahiru")
    async def shop(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🏪 Tiệm Tạp Hóa Mahiru", 
            description="Hãy chọn món đồ cậu muốn mua từ menu bên dưới nhé!",
            color=0xffd700
        )
        for key, info in self.items.items():
            embed.add_field(name=info['name'], value=f"Giá: **{info['price']}** 💰\nThân mật: **+{info['buff']}** ❤️", inline=True)
        
        await interaction.response.send_message(embed=embed, view=ShopView(self.items))

    @app_commands.command(name="bag", description="Xem túi đồ và tặng quà")
    async def bag(self, interaction: discord.Interaction):
        inventory = db.get_inventory(interaction.user.id)
        coins = db.get_user_coins(interaction.user.id)
        
        embed = discord.Embed(title=f"🎒 Túi đồ của {interaction.user.name}", color=0x98fb98)
        embed.add_field(name="Số dư:", value=f"**{coins}** 💰", inline=False)
        
        if not inventory:
            embed.description = "Túi đồ trống rỗng..."
            await interaction.response.send_message(embed=embed)
        else:
            items_str = ""
            for item_id, qty in inventory:
                name = self.items[item_id]['name'] if item_id in self.items else item_id
                items_str += f"• **{name}**: {qty} món (ID: `{item_id}`)\n"
            embed.add_field(name="Vật phẩm:", value=items_str, inline=False)
            embed.set_footer(text="Dùng /gift [id] để tặng quà nhé!")
            await interaction.response.send_message(embed=embed)

    @app_commands.command(name="gift", description="Tặng quà cho Mahiru")
    async def gift(self, interaction: discord.Interaction, item_id: str):
        item_id = item_id.lower()
        inventory = dict(db.get_inventory(interaction.user.id))
        
        if item_id not in inventory or inventory[item_id] <= 0:
            return await interaction.response.send_message("Cậu không có món này trong túi!", ephemeral=True)

        item_info = self.items[item_id]
        db.remove_from_inventory(interaction.user.id, item_id, 1)
        db.add_affinity(interaction.user.id, interaction.guild.id, item_info['buff'])

        await interaction.response.send_message(
            f"🎁 Cậu tặng **{item_info['name']}** cho Mahiru.\n"
            f"Mahiru: *\"{item_info['msg']}\"*\n"
            f"Thân mật **+{item_info['buff']}** ❤️"
        )

    @app_commands.command(name="date", description="đổi địa điểm trò chuyện cùng Mahiru")
    async def date(self, interaction: discord.Interaction):
        points = db.get_affinity(interaction.user.id, interaction.guild.id)
        view = discord.ui.View()
        view.add_item(DateSelect(points))
        await interaction.response.send_message("Cậu muốn rủ mình đi đâu?", view=view, ephemeral=False)

async def setup(bot):
    await bot.add_cog(Shop(bot))
