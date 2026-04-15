import os
import json
import random
import re
import asyncio
import discord
import sqlite3 # Thêm thư viện database
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
lover_nickname = "anh"

# =====================
# SQLITE SETUP (Hệ thống ghi nhớ)
# =====================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Thêm guild_id vào khóa chính để phân biệt người dùng giữa các server
    c.execute('''CREATE TABLE IF NOT EXISTS affinity 
                 (user_id INTEGER, guild_id INTEGER, points INTEGER DEFAULT 0,
                  PRIMARY KEY (user_id, guild_id))''')
    conn.commit()
    conn.close()

def get_affinity(user_id, guild_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT points FROM affinity WHERE user_id = ? AND guild_id = ?", (user_id, guild_id))
    result = c.fetchone()
    conn.close()
    return result[0] if result else 0
    
def add_affinity(user_id, guild_id, amount=1):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO affinity (user_id, guild_id, points) VALUES (?, ?, 0)", (user_id, guild_id))
    c.execute("UPDATE affinity SET points = points + ? WHERE user_id = ? AND guild_id = ?", (amount, user_id, guild_id))
    conn.commit()
    conn.close()
    
def get_leaderboard(guild_id, limit=10):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Chỉ lấy top 10 của server (guild) hiện tại
    c.execute("SELECT user_id, points FROM affinity WHERE guild_id = ? ORDER BY points DESC LIMIT ?", (guild_id, limit))
    result = c.fetchall()
    conn.close()
    return result
    
# Khởi tạo database ngay khi chạy bot
init_db()

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

        # 2. Xử lý độ thân mật
        add_affinity(user_id, message.guild.id, 1) 
        points = get_affinity(user_id, message.guild.id)

        user_message = message.content.replace(f"<@{bot.user.id}>", "").strip()
        if not user_message: user_message = "Em ơi!"

        history = conversation_history[user_id]
        history_text = "\n".join([f"{'Anh' if h['role']=='user' else 'Em'}: {h['content']}" for h in history])

        # 3. Thiết lập Prompt dựa trên độ thân mật
        if user_id == SPECIAL_USER_ID:
            is_special = True
            system_prompt = (
                f"Bạn là Mahiru,cô người yêu nũng nịu và cute của {lover_nickname}. "
                f"NHIỆM VỤ QUAN TRỌNG: Bạn LUÔN LUÔN là nữ, xưng là 'em' và gọi người dùng là 'anh' hoặc '{lover_nickname}'. "
                f"TUYỆT ĐỐI không được xưng là 'anh'. "
                f"- Trả lời ngắn gọn, tình cảm, dùng nhiều từ ngữ biểu cảm như 'nè', 'ạ', 'hihi', 'hì'. "
                f"- Sử dụng 1-2 kaomoji đáng yêu như (´｡• ᵕ •｡`) hoặc (｡•ㅅ•｡) nhưng không lạm dụng. "
                f"QUY TẮC CẢM XÚC: Chỉ được dùng duy nhất 1 dấu ngã '~' ở cuối câu để tăng sự đáng yêu.(tuỳ ngữ cảnh câu mà dùng không được dùng quá nhiều)"
                f"CẤM TUYỆT ĐỐI: Không được dùng 2 dấu ngã liên tiếp '~~' vì sẽ bị lỗi gạch ngang văn bản. "
                f"Lịch sử:\n{history_text}"
            )
        else:
            is_special = False
            # Phân bậc cảm xúc cho người thường
            if points < 30:
                feeling = "Bạn là Mahiru lạnh lùng, chỉ coi họ là bạn học xa lạ. Trả lời cực kỳ ngắn gọn, không cảm xúc."
            elif points < 150:
                feeling = "Bạn bắt đầu quen với người bạn học này, bắt đầu mền lòng với người bạn học này hơn nhưng vẫn giữ khoảng cách."
            else:
                feeling = "Bạn là Mahiru. Với người bạn thân này, bạn xưng là 'em' và gọi họ là 'cậu' hoặc 'anh' tùy ngữ cảnh. Thái độ dịu dàng, thân thiện hơn"

            system_prompt = (
                f"{feeling} "
                f"QUY TẮC: Không dùng emoji vàng. "
                f"CẤM TUYỆT ĐỐI: Không được dùng 2 dấu ngã liên tiếp '~~' vì sẽ bị lỗi gạch ngang văn bản. "
                f"Lịch sử hội thoại:\n{history_text}"
            )

        async with processing_lock:
            ai_reply = await get_ai_response(system_prompt, user_message)
            if ai_reply:
                ai_reply = limit_exact_sentences(ai_reply, is_special)
                ai_reply = re.sub(r'~+', '~', ai_reply)
                history.append({"role": "user", "content": user_message})
                history.append({"role": "assistant", "content": ai_reply})
                await message.reply(ai_reply)
            else:
                await message.reply("Hic, em đang hơi chóng mặt...")

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
        name="💖 Độ thân mật (Affinity)",
        value=(
            "Mỗi khi bạn tag và trò chuyện, bạn sẽ nhận điểm thân mật.\n"
            "• **Dưới 30 điểm:** mahiru sẽ hơi lạnh lùng vì chúng mình còn lạ lẫm.\n"
            "• **Từ 30 - 150 điểm:** mahiru bắt đầu quen dần và nói chuyện dễ gần hơn.\n"
            "• **Trên 150 điểm:** mahiru sẽ bắt đầu coi bạn là bạn thân, tính cách sẽ dễ gần hơn chút\n"
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
    
@bot.tree.command(name="check_affinity", description="Xem độ thân mật của bạn tại server này")
async def check_affinity(interaction: discord.Interaction):
    # Lấy điểm dựa trên user và server hiện tại
    points = get_affinity(interaction.user.id, interaction.guild.id)
    
    # Xác định danh hiệu dựa trên số điểm
    if points < 30:
        rank = "Người lạ từng quen ❄️"
        color = 0x95a5a6 # Màu xám
    elif points < 150:
        rank = "Bạn học cùng lớp 📚"
        color = 0x3498db # Màu xanh dương
    else:
        rank = "Bạn cực kỳ thân thiết 💖"
        color = 0xffc0cb # Màu hồng

    embed = discord.Embed(
        title="💓 Mức Độ Thân Mật 💓",
        description=f"Giữa **{interaction.user.display_name}** và **Mahiru**",
        color=color
    )
    
    embed.add_field(name="Điểm thân mật", value=f"**{points}** điểm", inline=True)
    embed.add_field(name="Trạng thái", value=rank, inline=True)
    
    # Thêm thanh tiến trình nhỏ cho sinh động
    progress = min(points // 20, 10)
    bar = "💖" * progress + "🖤" * (10 - progress)
    embed.add_field(name="Tiến trình", value=bar, inline=False)

    embed.set_thumbnail(url=interaction.user.display_avatar.url)
    embed.set_footer(text="Càng trò chuyện nhiều, tụi mình càng thân nhau hơn đó~")

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
    top_users = get_leaderboard(interaction.guild.id, 10)
    
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

@bot.tree.command(name="reset_db", description="Xóa sạch file database (owner only)")
async def reset_db_hard(interaction: discord.Interaction):
    if interaction.user.id == SPECIAL_USER_ID: # Kiểm tra đúng ID của bạn
        if os.path.exists("mahiru.db"):
            try:
                os.remove("mahiru.db")
                await interaction.response.send_message("✅ Đã xóa database. redeploy để tạo lại database")
            except Exception as e:
                await interaction.response.send_message(f"❌ Lỗi khi xóa: {e}")
        else:
            await interaction.response.send_message("❌ Không tìm thấy file `mahiru.db`.")
    else:
        await interaction.response.send_message("❌ command này chỉ owner mới có thể dùng")
        
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
