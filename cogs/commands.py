import discord
import os
from discord.ext import commands
from discord import app_commands
import database as db 

SPECIAL_USER_ID = 695215402187489350

class HelpSelect(discord.ui.Select):
    def __init__(self, author_id, bot):
        self.author_id = author_id
        self.bot = bot
        options = [
            discord.SelectOption(label="💖 Cơ chế Thân mật", description="Cách Mahiru đối xử với cậu theo điểm số.", emoji="💖"),
            discord.SelectOption(label="💰 Hệ thống Coin (€)", description="Cách kiếm và sử dụng xu mua quà.", emoji="💰"),
            discord.SelectOption(label="📜 Lệnh người dùng", description="Các lệnh dành cho tất cả mọi người.", emoji="📜"),
            discord.SelectOption(label="⚙️ Lệnh quản trị", description="Dành riêng cho Owner & Admin.", emoji="⚙️")
        ]
        super().__init__(placeholder="Cậu muốn tìm hiểu về phần nào?...", options=options)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            return await interaction.response.send_message(
                "Menu này không phải dành cho cậu đâu nhé!~ (súc vật đòi bấm ké)", 
                ephemeral=True
            )
            
        selection = self.values[0]
        embed = discord.Embed(color=0xffc0cb)
        embed.title = selection
        embed.description = "Đang tải dữ liệu..."
        
        if selection == "💖 Cơ chế Thân mật":
            embed.title = "💖 Cơ chế Độ thân mật (Affinity)"
            embed.description = (
                "• **Dưới 100:** Người dưng - Mahiru lạnh lùng, giữ khoảng cách.\n"
                "• **100 - 300:** Bạn cùng lớp - Lịch sự xã giao.\n"
                "• **300 - 600:** Người quen - Bắt đầu dịu dàng hơn.\n"
                "• **600 - 1000:** Bạn tốt - Mở lòng và quan tâm.\n"
                "• **1000 - 1500:** Bạn thân thiết - Nũng nịu và chăm sóc.\n"
                "• **1500 - 2500:** Người quan trọng - Quấn quýt, ỷ lại.\n"
                "• **Trên 2500:** Tri kỷ trọn đời - Mức độ cao nhất. ✨"
            )

        elif selection == "💰 Hệ thống Coin (€)":
            embed.title = "💰 Hệ thống Kinh tế của Mahiru"
            embed.description = (
                "Trong thế giới của Mahiru, coin (€) được dùng để mua các món quà ngọt ngào.\n\n"
                "**1. Cách kiếm Xu:**\n"
                "• Trò chuyện cùng Mahiru: Mỗi tin nhắn cậu gửi sẽ có cơ hội nhận được xu ngẫu nhiên.\n"
                "**2. Cách sử dụng:**\n"
                "• Dùng lệnh `/shop` để xem các món đồ đang bán.\n"
                "• Mua vật phẩm để tặng qua `/gift`, giúp tăng nhanh điểm thân mật.\n"
                "• Tích lũy để mở khóa các địa điểm hẹn hò đặc biệt.\n\n"
                "**3. Kiểm tra số dư:**\n"
                "• Số xu hiện tại của cậu luôn hiển thị ở dòng đầu tiên khi dùng lệnh `/bag`."
            )
        
        elif selection == "📜 Lệnh người dùng":
            embed.title = "📜 Danh sách lệnh hệ thống"
            embed.add_field(name="Trò chuyện", value="`$affinity`: Check điểm\n`$leaderboard`: Bảng xếp hạng\n`resetmemory`: Reset chat", inline=False)
            embed.add_field(name="Hẹn hò & Quà tặng", value="`$shop`: Mua quà\n`$bag`: Túi đồ\n`$gift`: Tặng quà\n`$date`: Đổi địa điểm\n`$give`:nhận thưởng hàng ngày", inline=False)

        elif selection == "⚙️ Lệnh quản trị":
            embed.title = "⚙️ Lệnh Owner & Admin"
            embed.description = (
                "`/setchannel`: Cố định kênh hoạt động.\n"
                "`/setlovername`: (Owner) Đổi nickname em gọi anh.\n"
                "`/sync`: Cập nhật hệ thống.\n"
                "`/get_db`: Lấy file dữ liệu."
            )

        # Cập nhật lại tin nhắn cũ với nội dung mới
        await interaction.response.send_message(embed=embed, ephemeral=True)

class HelpView(discord.ui.View):
    def __init__(self, author_id, bot):
        super().__init__(timeout=120)
        self.add_item(HelpSelect(bot, author_id))
        
class MahiruCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.conversation_history = {}
        self.server_channels = {}

    @commands.command(name="help")
    async def help_command(self, ctx):
        embed = discord.Embed(
            title="🌸 Hướng dẫn sử dụng Mahiru-chan",
            description="Chào cậu! Mình là Mahiru. Cậu muốn mình hướng dẫn về phần nào dưới đây?",
            color=0xffc0cb
        )
        
        # Thêm ảnh GIF cho sinh động
        embed.set_image(url="https://media.tenor.com/BqAF9L-2EjAAAAAC/mahiru.gif")
        
        await ctx.send(embed=embed, view=HelpView(self.bot, ctx.author.id))
        
    @commands.command(name="affinity")
    async def check_affinity(self, ctx):
        points = db.get_affinity(ctx.author.id, ctx.guild.id)
        
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
        
        await ctx.send(embed=embed)
        
    
    @app_commands.command(name="setlovername", description="Đổi nickname đặc biệt cho người yêu 💕")
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
    
    @commands.command(name="setchannel")
    async def setchannel(self, ctx, channel: discord.TextChannel = None):
        if ctx.author.id != SPECIAL_USER_ID:
            embed_error = discord.Embed(
                title="🚫 U have no perm kiddo",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed_error, ephemeral=True)
            return

        try:
            # 2. Lưu dữ liệu
            self.bot.server_channels[interaction.guild.id] = channel.id
            db.update_server_channel(interaction.guild.id, channel.id)
            
            # 3. Tạo Embed thông báo thành công
            embed_success = discord.Embed(
                title=f"**Từ giờ em sẽ chỉ hoạt động và trò chuyện tại kênh {channel.mention} này thôi nhé! :3**",
                color=discord.Color.from_rgb(255, 182, 193) # Màu hồng nhạt
            )

            await ctx.send(embed=embed_success)

        except Exception as e:
            await ctx.send(f"❌ Có lỗi xảy ra: {e}", ephemeral=True)
        
    @commands.command(name="clearchannel")
    async def clearchannel(self, ctx):
        global server_channels
        if ctx.guild_id in server_channels:
            del self.bot.server_channels[ctx.guild_id]
            await ctx.send(" Đã reset! Giờ em sẽ chat ở bất cứ kênh nào anh tag em.")
        else:
            await ctx.send("Server này vốn ko có gì để lưu r ạ :3!", ephemeral=False)
    
    @commands.command(name="resetmemory")
    async def resetmemory(self, ctx):
        user_id = ctx.user.id
        if user_id in conversation_history:
            self.conversation_history[user_id].clear()
            await ctx.send("🧹 Lịch sử hội thoại của bạn đã được xoá sạch!", ephemeral=True)
        else:
            await ctx.send("❌ Bạn chưa có lịch sử hội thoại nào để xoá.", ephemeral=True)
    
    @app_commands.command(name="resetallmemory", description="Xoá toàn bộ lịch sử hội thoại (owner only)")
    async def resetallmemory(self, interaction: discord.Interaction):
        # Thay đổi điều kiện: Chỉ cho phép người có ID là SPECIAL_USER_ID
        if interaction.user.id != SPECIAL_USER_ID:
            return await interaction.response.send_message(
                "❌ chỉ owner ms được dùng thôi bn hiền", 
                ephemeral=True
            )
        
        self.conversation_history.clear()
        await interaction.response.send_message("🧹 Toàn bộ lịch sử hội thoại đã được xoá sạch!", ephemeral=True)
    # ... Các lệnh setchannel, clearchannel, resetmemory giữ nguyên như code cũ của bạn ...
    
    @app_commands.command(name="sync", description="Cập nhật lệnh (Chủ bot)")
    async def sync(self, interaction: discord.Interaction):
        if interaction.user.id == SPECIAL_USER_ID:
            await interaction.response.defer()
            synced = await self.bot.tree.sync()
            await interaction.followup.send(f"✅ Đã sync {len(synced)} lệnh.")
        else:
            await interaction.response.send_message("Quyền đâu mà sync?")
    
    
    @commands.command(name="leaderboard", aliases=["lb"])
    async def leaderboard(self, ctx):
        # Truyền guild ID vào hàm lấy top
        top_users = db.get_leaderboard(ctx.guild.id, 10)
        
        if not top_users:
            return await ctx.send("Server này chưa ai làm quen với em cả... :<", ephemeral=True)
        
        embed = discord.Embed(
            title=f"🏆 BẢNG XẾP HẠNG THÂN MẬT - {interaction.guild.name} 🏆",
            color=0xffc0cb
        )
    
        leaderboard_text = ""
        for index, (user_id, points) in enumerate(top_users, start=1):
            user = self.bot.get_user(user_id)
            name = f"**{user.name}**" if user else f"Thành viên ẩn danh (`{user_id}`)"
            
            medal = "🥇" if index == 1 else "🥈" if index == 2 else "🥉" if index == 3 else f"**#{index}**"
            leaderboard_text += f"{medal} {name} — `{points} điểm` \n"
    
        embed.add_field(name="Top điểm thân mật", value=leaderboard_text, inline=False)
        await ctx.send(embed=embed)
    
    @app_commands.command(name="clear_database_data", description="Xóa sạch toàn bộ database (Owner Only)")
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
    
    @app_commands.command(name="get_db", description="Gửi file database về máy (owner only)")
    async def get_db(self, interaction: discord.Interaction):
        if interaction.user.id == SPECIAL_USER_ID:
            if os.path.exists(db.DB_PATH):
                # Gửi file dưới dạng đính kèm trong Discord
                file = discord.File(db.DB_PATH)
                await interaction.response.send_message("Đây là file database của anh nè~", file=file, ephemeral=True)
            else:
                await interaction.response.send_message("Em không tìm thấy file database đâu cả... :<", ephemeral=False)
        else:
            await interaction.response.send_message("❌ Lệnh này nguy hiểm lắm, chỉ tao(owner) ms đc dùng thôi nhóc", ephemeral=False )
    

async def setup(bot):
    await bot.add_cog(MahiruCommands(bot))
