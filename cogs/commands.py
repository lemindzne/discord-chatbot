import discord
from discord.ext import commands
from discord import app_commands
import database as db # Đảm bảo file database.py có trong repo

class MahiruCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Ví dụ 1 lệnh từ file main của bạn
    @bot.tree.command(name="help", description="có thêm thông tin cơ bản về bot")
    async def help_command(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="Tổng Quan Về Mahiru-chan 🌸",
            color=0xffc0cb
        )
    
        # Giải thích cơ chế độ thân mật
        embed.add_field(
            name="💖 Cơ chế Độ thân mật (Affinity)",
        value=(
            "Mỗi khi bạn tag và trò chuyện, bạn sẽ nhận được điểm thân mật.\n\n"
            "• **Dưới 100:** Mahiru lạnh lùng, giữ khoảng cách tuyệt đối.\n"
            "• **100 - 300:** Bắt đầu nhận diện bạn học, lịch sự xã giao.\n"
            "• **300 - 600:** Người quen, bớt cảnh giác và dịu dàng hơn.\n"
            "• **600 - 1000:** Bạn tốt, bắt đầu mở lòng và chia sẻ nhiều hơn.\n"
            "• **1000 - 1500:** Bạn thân thiết, nũng nịu và quan tâm sâu sắc.\n"
            "• **1500 - 2500:** Tình cảm bùng nổ, quấn quýt và ỷ lại vào bạn.\n"
            "• **Trên 2500:** Tri kỷ trọn đời, mức độ thân mật cao nhất."
        ),
            inline=False
        )
    
        # Danh sách lệnh cho người dùng
        embed.add_field(
            name="📜 command ",
            value=(
                "`/check_affinity`: check độ thân mật hiện tại\n"
                "`/leaderboard`: bảng xếp hạng điểm thân mật\n"
                "`/resetmemory`: reset cuộc trò chuyện gần nhất của mahiru"
            ),
            inline=True
        )
    
        # Danh sách lệnh quản trị
        embed.add_field(
            name="⚙️ Owner & Administrator only",
            value=(
                "`/setchannel`: Cố định nơi em sẽ xuất hiện.\n"
                "`/setlovername`: (Owner) Đổi nickname em gọi anh.\n"
                "`/resetallmemory`: (Owner) Xóa sạch ký ức của em.\n"
                "`/sync`: (Owner) Cập nhật hệ thống của em."
            ),
            inline=True
        )
    
        embed.set_footer(text="tag hoặc reply để trò chuyện với bot ")
        
        if bot.user.avatar:
            embed.set_thumbnail(url="https://media4.giphy.com/media/v1.Y2lkPTZjMDliOTUyand2NWJ1eGp6OGY1dHR4N3NydHRqcTA4Mzk1cHM1cjl1NHNsM3ZrYiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/x2aO0plLdV7wGNzQxt/giphy.gif")
    
        await interaction.response.send_message(embed=embed)
        
    @bot.tree.command(name="check_affinity", description="Xem độ thân mật của bạn")
    async def check_affinity(self, interaction: discord.Interaction):
        points = db.get_affinity(interaction.user.id, interaction.guild.id)
        
        # 7 mốc danh hiệu
        if points < 100:
            rank, color = "Người lạ từng quen ❄️", 0x95a5a6
        elif points < 300:
            rank, color = "Bạn cùng lớp 📚", 0x3498db
        elif points < 600:
            rank, color = "Người quen xã giao 🍃", 0x2ecc71
        elif points < 1000:
            rank, color = "Bạn tốt chân thành 🌤️", 0xf1c40f
        elif points < 1500:
            rank, color = "Bạn thân thiết 💖", 0xe91e63
        elif points < 2500:
            rank, color = "Người quan trọng nhất ✨", 0x9b59b6
        else:
            rank, color = "Tri kỷ trọn đời 💍", 0xffc0cb
    
        embed = discord.Embed(title="💓 Mức Độ Thân Mật 💓", color=color)
        embed.add_field(name="Điểm thân mật", value=f"**{points}**", inline=True)
        embed.add_field(name="Trạng thái", value=rank, inline=True)
        
        # Thanh tiến trình: mỗi 250 điểm được 1 tim (đầy thanh ở 2500 điểm)
        progress = min(points // 250, 10)
        bar = "💖" * progress + "🖤" * (10 - progress)
        embed.add_field(name="Tiến trình", value=bar, inline=False)
        
        await interaction.response.send_message(embed=embed)
        
    
    @bot.tree.command(name="setlovername", description="Đổi nickname đặc biệt cho người yêu 💕")
    async def set_lover_name(self, interaction: discord.Interaction, name: str):
        global lover_nickname
        if interaction.user.id == SPECIAL_USER_ID:
            lover_nickname = name
            # Tạo Embed thông báo thành công
            embed = discord.Embed(
                title="Chỉnh Sửa Thành Công",
                description=f"**Từ giờ em sẽ gọi anh là: `{lover_nickname}` nhé! :3**",
                color=0xffc0cb # Màu hồng dễ thương
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=False)
        else:
            embed = discord.Embed(
                description="❌ th ngu m đéo có quyền dùng lệnh đâu",
                color=0xff0000 # Màu đỏ
            )
            await interaction.response.send_message(embed=embed, ephemeral=False)
    
    @bot.tree.command(name="setchannel", description="Chọn kênh để bot chat khi được tag")
    async def setchannel(self interaction: discord.Interaction, channel: discord.TextChannel):
        global server_channels
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("❌ Bạn không có quyền dùng lệnh này.", ephemeral=False)
        
        # Lưu ID kênh cho server hiện tại
        server_channels[interaction.guild.id] = channel.id
        
        await interaction.response.send_message(f"✅ em sẽ chỉ chat trong kênh: {channel.mention} :3")
        
    @bot.tree.command(name="clearchannel", description="Cho phép bot chat mọi kênh ở server này")
    async def clearchannel(self, interaction: discord.Interaction):
        global server_channels
        if interaction.guild_id in server_channels:
            del server_channels[interaction.guild_id]
            await interaction.response.send_message(" Đã reset! Giờ em sẽ chat ở bất cứ kênh nào anh tag em.")
        else:
            await interaction.response.send_message("Server này vốn ko có gì để lưu r ạ :3!", ephemeral=False)
    
    @bot.tree.command(name="resetmemory", description="Xoá lịch sử hội thoại của bạn với bot")
    async def resetmemory(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        if user_id in conversation_history:
            conversation_history[user_id].clear()
            await interaction.response.send_message("🧹 Lịch sử hội thoại của bạn đã được xoá sạch!", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Bạn chưa có lịch sử hội thoại nào để xoá.", ephemeral=True)
    
    @bot.tree.command(name="resetallmemory", description="Xoá toàn bộ lịch sử hội thoại (owner only)")
    async def resetallmemory(self, interaction: discord.Interaction):
        # Thay đổi điều kiện: Chỉ cho phép người có ID là SPECIAL_USER_ID
        if interaction.user.id != SPECIAL_USER_ID:
            return await interaction.response.send_message(
                "❌ chỉ owner ms được dùng thôi bn hiền", 
                ephemeral=True
            )
        
        conversation_history.clear()
        await interaction.response.send_message("🧹 Toàn bộ lịch sử hội thoại đã được xoá sạch!", ephemeral=True)
    # ... Các lệnh setchannel, clearchannel, resetmemory giữ nguyên như code cũ của bạn ...
    
    @bot.tree.command(name="sync", description="Cập nhật lệnh (Chủ bot)")
    async def sync(self, interaction: discord.Interaction):
        if interaction.user.id == SPECIAL_USER_ID:
            await interaction.response.defer()
            synced = await bot.tree.sync()
            await interaction.followup.send(f"✅ Đã sync {len(synced)} lệnh.")
        else:
            await interaction.response.send_message("Quyền đâu mà sync?")
    
    
    @bot.tree.command(name="leaderboard", description="Xem top 10 xp trong server")
    async def leaderboard(self, interaction: discord.Interaction):
        # Truyền guild ID vào hàm lấy top
        top_users = db.get_leaderboard(interaction.guild.id, 10)
        
        if not top_users:
            return await interaction.response.send_message("Server này chưa ai làm quen với em cả... :<", ephemeral=True)
    
        embed = discord.Embed(
            title=f"🏆 BẢNG XẾP HẠNG THÂN MẬT - {interaction.guild.name} 🏆",
            color=0xffc0cb
        )
    
        leaderboard_text = ""
        for index, (user_id, points) in enumerate(top_users, start=1):
            user = bot.get_user(user_id)
            name = f"**{user.name}**" if user else f"Thành viên ẩn danh (`{user_id}`)"
            
            medal = "🥇" if index == 1 else "🥈" if index == 2 else "🥉" if index == 3 else f"**#{index}**"
            leaderboard_text += f"{medal} {name} — `{points} điểm` \n"
    
        embed.add_field(name="Top điểm thân mật", value=leaderboard_text, inline=False)
        await interaction.response.send_message(embed=embed)
    
    @bot.tree.command(name="clear_database_data", description="Xóa sạch toàn bộ database (Owner Only)")
    async def clear_database_data(self, interaction: discord.Interaction):
        if interaction.user.id == SPECIAL_USER_ID:
            try:
                db.clear_all_data()
                # Xóa lịch sử chat trong bộ nhớ tạm
                conversation_history.clear()
                
                await interaction.response.send_message("✅ Đã xóa sạch toàn bộ điểm số và lịch sử chat rồi ạ~", ephemeral=True)
            except Exception as e:
                await interaction.response.send_message(f"❌ Lỗi rồi anh ơi: {e}", ephemeral=True)
        else:
            await interaction.response.send_message("❌ You have no perm son ", ephemeral=False)
    
    @bot.tree.command(name="get_db", description="Gửi file database về máy (owner only)")
    async def get_db(self, interaction: discord.Interaction):
        if interaction.user.id == SPECIAL_USER_ID:
            if os.path.exists(db.DB_PATH):
                # Gửi file dưới dạng đính kèm trong Discord
                file = discord.File(db.DB_PATH)
                await interaction.response.send_message("Đây là file database của anh nè~", file=file, ephemeral=True)
            else:
                await interaction.response.send_message("Em không tìm thấy file database đâu cả... :<", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Lệnh này nguy hiểm lắm, chỉ chồng em mới được dùng thôi!", ephemeral=False )
    

async def setup(bot):
    await bot.add_cog(MahiruCommands(bot))
