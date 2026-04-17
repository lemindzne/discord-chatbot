import discord
from discord.ext import commands
from discord import app_commands
import database as db # Đảm bảo file database.py có trong repo

class MahiruCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Ví dụ 1 lệnh từ file main của bạn
    @app_commands.command(name="check_affinity", description="Xem độ thân mật của bạn")
    async def check_affinity(self, interaction: discord.Interaction):
        points = db.get_affinity(interaction.user.id, interaction.guild.id)
        # ... copy logic xử lý từ main (8).py vào đây ...
        await interaction.response.send_message(f"Điểm của bạn là: {points}")

async def setup(bot):
    await bot.add_cog(MahiruCommands(bot))
