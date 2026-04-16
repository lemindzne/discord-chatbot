import os
import json
import random
import re
import asyncio
import discord
import database as db
import prompts
from discord.ext import commands
from discord import app_commands
from groq import Groq
from dotenv import load_dotenv
from collections import defaultdict, deque

# =====================
# LOAD CONFIG
# =====================
load_dotenv() 
TOKEN = os.getenv("DISCORD_TOKEN")
GROQ_KEY = os.getenv("GROQ_API_KEY") # Đảm bảo biến này khớp với .env
DB_PATH = os.getenv("DB_PATH", "mahiru.db") # Đường dẫn lưu file database

client = Groq(api_key=GROQ_KEY)

# ID user đặc biệt
SPECIAL_USER_ID = 695215402187489350
lover_nickname = "min-kun"

# =====================
# BOT SETUP
# =====================
intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.message_content = True
intents.reactions = True
bot = commands.Bot(command_prefix="$", intents=intents, help_command=None)

server_channels = {}
processing_lock = asyncio.Lock()
conversation_history = defaultdict(lambda: deque(maxlen=6))

# =====================
# AI FUNCTIONS (Giữ nguyên của bạn)
# =====================
async def get_ai_response(system_prompt, user_message):
    try:
        chat_completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=1.0,
            presence_penalty=0.4,  
            frequency_penalty=0.6,
            top_p=0.9,
            max_tokens=150
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        print(f"Lỗi Groq API: {e}")
        return None

def split_sentences(text: str):
    if text is None: return []
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s.strip() for s in sentences if s.strip()]

def limit_exact_sentences(text: str, is_special_user: bool = False):
    sentences = split_sentences(text)
    target_count = random.choice([4, 6]) if is_special_user else random.choice([2, 3])
    return " ".join(sentences[:target_count]) if len(sentences) >= target_count else " ".join(sentences)

# =====================
# ON MESSAGE (Logic chính)
# =====================
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot: return

    if bot.user in message.mentions:
        user_id = message.author.id
        
        # 1. Quản lý kênh chat (Giữ logic cũ của bạn)
        target_channel_id = server_channels.get(message.guild.id)
        if target_channel_id and message.channel.id != target_channel_id:
            return

        user_message = message.content.replace(f"<@{bot.user.id}>", "").strip()
        if not user_message: user_message = "Em ơi!"

        bonus = 1
        if len(user_message) > 50: 
            bonus = 3
        elif len(user_message) > 20: 
            bonus = 2

        # 2. Xử lý độ thân mật
        db.add_affinity(user_id, message.guild.id, bonus) 
        points = db.get_affinity(user_id, message.guild.id)

        history = conversation_history[user_id]
        history_text = "\n".join([f"{'Anh' if h['role']=='user' else 'Em'}: {h['content']}" for h in history])

        # 3. Thiết lập Prompt dựa trên độ thân mật
        if user_id == SPECIAL_USER_ID:
            is_special = True
            system_prompt = prompts.get_special_prompt(lover_nickname, history_text)
        else:
            is_special = False
            system_prompt = prompts.get_normal_prompt(points, history_text)
    
        async with processing_lock:
            ai_reply = await get_ai_response(system_prompt, user_message)
        
            if ai_reply:
            # 1. Dọn dẹp định dạng (Chỉ giữ lại 1 dấu ngã, xóa các dấu xuống dòng thừa của AI)
                ai_reply = re.sub(r'~+', '~', ai_reply)
                ai_reply = re.sub(r'(\*.*?\*)', r'|\1|', ai_reply)
                messages_to_send = [m.strip() for m in re.split(r'[|\n]', ai_reply) if m.strip()]
            
                # 3. Gửi từng tin với hiệu ứng gõ phím riêng biệt
                for i, msg in enumerate(messages_to_send):
                    async with message.channel.typing():
                        base_speed = len(msg) * random.uniform(0.05, 0.1)
                        thinking_time = random.uniform(0.5, 1.5)
                        total_sleep = min(base_speed + thinking_time, 4.0)
                        await asyncio.sleep(total_sleep)
                        
                        if i == 0:
                        # Tin đầu tiên reply lại người dùng
                            await message.reply(msg)
                        else:
                        # Các tin sau gửi như tin nhắn mới trong kênh
                            await message.channel.send(msg)
            
            # 4. Lưu lịch sử (Lưu bản sạch không có ký hiệu phân tách)
                full_reply_clean = " ".join(messages_to_send)
                history.append({"role": "user", "content": user_message})
                history.append({"role": "assistant", "content": full_reply_clean})
            
            else:
                await message.reply("Hic, em đang hơi chóng mặt... Anh đợi em xíu nhé~")

    await bot.process_commands(message)

# =====================
# COMMANDS (Giữ cũ + Thêm mới)
# =====================
@bot.tree.command(name="help", description="có thêm thông tin cơ bản về bot")
async def help_command(interaction: discord.Interaction):
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
        embed.set_thumbnail(url=bot.user.avatar.url)

    await interaction.response.send_message(embed=embed)
    
@bot.tree.command(name="check_affinity", description="Xem độ thân mật của bạn")
async def check_affinity(interaction: discord.Interaction):
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
async def set_lover_name(interaction: discord.Interaction, name: str):
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
async def setchannel(interaction: discord.Interaction, channel: discord.TextChannel):
    global server_channels
    if not interaction.user.guild_permissions.manage_guild:
        return await interaction.response.send_message("❌ Bạn không có quyền dùng lệnh này.", ephemeral=False)
    
    # Lưu ID kênh cho server hiện tại
    server_channels[interaction.guild.id] = channel.id
    
    await interaction.response.send_message(f"✅ em sẽ chỉ chat trong kênh: {channel.mention} :3")
    
@bot.tree.command(name="clearchannel", description="Cho phép bot chat mọi kênh ở server này")
async def clearchannel(interaction: discord.Interaction):
    global server_channels
    if interaction.guild_id in server_channels:
        del server_channels[interaction.guild_id]
        await interaction.response.send_message(" Đã reset! Giờ em sẽ chat ở bất cứ kênh nào anh tag em.")
    else:
        await interaction.response.send_message("Server này vốn ko có gì để lưu r ạ :3!", ephemeral=False)

@bot.tree.command(name="resetmemory", description="Xoá lịch sử hội thoại của bạn với bot")
async def resetmemory(interaction: discord.Interaction):
    user_id = interaction.user.id
    if user_id in conversation_history:
        conversation_history[user_id].clear()
        await interaction.response.send_message("🧹 Lịch sử hội thoại của bạn đã được xoá sạch!", ephemeral=True)
    else:
        await interaction.response.send_message("❌ Bạn chưa có lịch sử hội thoại nào để xoá.", ephemeral=True)

@bot.tree.command(name="resetallmemory", description="Xoá toàn bộ lịch sử hội thoại (owner only)")
async def resetallmemory(interaction: discord.Interaction):
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
async def sync(interaction: discord.Interaction):
    if interaction.user.id == SPECIAL_USER_ID:
        await interaction.response.defer()
        synced = await bot.tree.sync()
        await interaction.followup.send(f"✅ Đã sync {len(synced)} lệnh.")
    else:
        await interaction.response.send_message("Quyền đâu mà sync?")


@bot.tree.command(name="leaderboard", description="Xem top 10 xp trong server")
async def leaderboard(interaction: discord.Interaction):
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
async def clear_database_data(interaction: discord.Interaction):
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
async def get_db(interaction: discord.Interaction):
    if interaction.user.id == SPECIAL_USER_ID:
        if os.path.exists(db.DB_PATH):
            # Gửi file dưới dạng đính kèm trong Discord
            file = discord.File(db.DB_PATH)
            await interaction.response.send_message("Đây là file database của anh nè~", file=file, ephemeral=True)
        else:
            await interaction.response.send_message("Em không tìm thấy file database đâu cả... :<", ephemeral=True)
    else:
        await interaction.response.send_message("❌ Lệnh này nguy hiểm lắm, chỉ chồng em mới được dùng thôi!", ephemeral=False )
        
@bot.command()
async def force_sync(ctx):
    if ctx.author.id == SPECIAL_USER_ID:
        await bot.tree.sync()
        await ctx.send("✅ Đã ép buộc đồng bộ lệnh Slash!")

@bot.event
async def on_ready():
    # Tắt tự động sync để tránh lỗi Rate Limit (429)
    print(f"✅ Mahiru online: {bot.user}")
    
bot.run(TOKEN)
