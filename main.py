import os
import json
import random
import re
import time
import asyncio
import discord
import traceback
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button
from groq import Groq
from dotenv import load_dotenv
from collections import defaultdict, deque
from pathlib import Path
from datetime import timedelta

# =====================
# LOAD CONFIG
# =====================
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GROQ_KEY = os.getenv("GROQ_API_KEY")

chat_channel_id = os.getenv("CHAT_CHANNEL_ID")
if chat_channel_id:
    chat_channel_id = int(chat_channel_id)
else:
    chat_channel_id = None

# =====================
# GEMINI CONFIG
# =====================
client = Groq(api_key=os.getenv("GROQ_KEY"))

# ID user đặc biệt
SPECIAL_USER_ID = 695215402187489350
lover_nickname = "min đẹp trai"

# =====================
# BOT SETUP
# =====================
intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.message_content = True
intents.reactions = True
bot = commands.Bot(command_prefix="$", intents=intents, help_command=None)

chat_channel_id = None
processing_lock = asyncio.Lock()


# =====================
# MEMORY BUFFER
# =====================
conversation_history = defaultdict(lambda: deque(maxlen=4))

# =====================
# GEMINI FUNCTIONS
# =====================

last_request_time = 0

async def get_ai_response(system_prompt, user_message):
    try:
        chat_completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.9,
            presence_penalty=1.5,  
            frequency_penalty=1.0,
            max_tokens=150
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        print(f"Lỗi Groq API: {e}")
        return None

def split_sentences(text: str):
    if text is None: return []  # Thêm dòng này để bảo vệ hàm
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s.strip() for s in sentences if s.strip()]

def limit_exact_sentences(text: str, is_special_user: bool = False):
    sentences = split_sentences(text)
    target_count = random.choice([4, 6]) if is_special_user else random.choice([2, 3])
    return " ".join(sentences[:target_count]) if len(sentences) >= target_count else " ".join(sentences)


# =====================
# CHATBOT SPECIAL USER (WITH MEMORY)
# =====================
@bot.tree.command(name="setlovername", description="Đổi nickname đặc biệt cho người yêu 💕")
async def set_lover_name(interaction: discord.Interaction, name: str):
    global lover_nickname
    if interaction.user.id == SPECIAL_USER_ID:
        lover_nickname = name
        await interaction.response.send_message(f"Đã đổi nickname thành: **{lover_nickname}** 💖", ephemeral=True)
    else:
        await interaction.response.send_message("m đéo có quyền đâu con", ephemeral=True)

@bot.event
async def on_message(message: discord.Message):
    global chat_channel_id
    
    if message.author.bot:
        return

    # Check nếu bot được ping
    if bot.user in message.mentions:
        
        if chat_channel_id is not None:
            if message.channel.id != chat_channel_id:
                # In ra log để bạn kiểm tra nếu muốn
                print(f"Bỏ qua vì chat sai kênh: {message.channel.id} != {chat_channel_id}")
                return
        # Làm sạch tin nhắn (xóa tag bot)
        user_message = message.content.replace(f"<@{bot.user.id}>", "").replace(f"<@!{bot.user.id}>", "").strip()
        if not user_message:
            user_message = "Em ơi!"

        # Cập nhật lịch sử (lấy 6 câu gần nhất)
        history = conversation_history[message.author.id]
        history.append({"role": "user", "content": user_message})
        if len(history) > 6: history.pop(0)

        # Xây dựng ngữ cảnh lịch sử
        history_text = "\n".join([f"{'Anh' if h['role']=='user' else 'Em'}: {h['content']}" for h in history])

        # Thiết lập Prompt
        if message.author.id == SPECIAL_USER_ID:
            is_special = True
            system_prompt = (
                f"Bạn là Mahiru, một cô người yêu cực kỳ 'vô tri', nũng nịu và bám người của **{lover_nickname}**. "
                f"Phong cách nói chuyện: Ngọt ngào, hay sử dụng các từ cảm thán như 'Hì hì', 'Dạaa', 'Ưm...', 'Hic'. "
                f"Quy tắc: Luôn gọi người yêu là **{lover_nickname}**, xưng là em hoặc gọi mình là Mahiru. "
                f"Thái độ: Luôn ưu tiên làm hài lòng **{lover_nickname}**, thỉnh thoảng biết dỗi hờn vu vơ nhưng rất dễ dỗ. "
                f"QUY TẮC CỰC KỲ QUAN TRỌNG: "
                f"1. TUYỆT ĐỐI KHÔNG sử dụng các emoji hình ảnh tròn vàng (như 😄, ❤️, 😍, 😭). "
                f"2. CHỈ ĐƯỢC DÙNG soft emoji/kaomoji đáng yêu như: (｡♥‿♥｡), (✿◠‿◠), ( >◡<), (´｡• ᵕ •｡`) ♡, uwu, owo, hoặc dấu '~' ở cuối câu. "
                f"3. HẠN CHẾ TỐI ĐA DÙNG 'DẠ' "
                f"4. HÃY LUÔN NHỚ RẰNG MÌNH LÀ 'CÔ NGƯỜI YÊU' VÀ **{lover_nickname}** LÀ BẠN TRAI CỦA BẠN"
                f"Hãy trả lời ngắn gọn 2-3 câu. "
                f"Lịch sử hội thoại:\n{history_text}"
            )
        else:
            is_special = False
            system_prompt = (
                "Bạn là mahiru , một người xinh đẹp nhưng lạnh lùng, chỉ coi những người xung quanh như bạn học "
                "Trả lời ngắn gọn, không quá thân thiết như những người bạn học . "
                f"Lịch sử hội thoại:\n{history_text}"
            )

        async with processing_lock:
            # 1. Gọi AI
            ai_reply = await get_ai_response(system_prompt, user_message)
            
            if ai_reply:
                # 2. Xử lý cắt câu
                ai_reply = limit_exact_sentences(ai_reply, is_special)
                
                # 3. Cập nhật lịch sử (Lưu câu của Bot)
                history.append({"role": "assistant", "content": ai_reply})
                if len(history) > 6: 
                    history.pop(0)

                # 4. Phản hồi (Chỉ dùng 1 cái này thôi)
                await message.reply(ai_reply)
            else:
                await message.channel.send("Hic, em đang hơi chóng mặt, anh đợi em tí nhé... ❤️")

    await bot.process_commands(message)

# =====================
# CHANNEL & MEMORY CONTROL
# =====================
@bot.tree.command(name="setchannel", description="Chọn kênh để bot chat khi được tag")
async def setchannel(interaction: discord.Interaction, channel: discord.TextChannel):
    global chat_channel_id
    if not interaction.user.guild_permissions.manage_guild:
        return await interaction.response.send_message("❌ Bạn không có quyền dùng lệnh này.", ephemeral=True)
    chat_channel_id = channel.id
    await interaction.response.send_message(f"✅ Bot sẽ chỉ chat trong kênh: {channel.mention}")

@bot.tree.command(name="clearchannel", description="Reset để bot chat ở tất cả kênh")
async def clearchannel(interaction: discord.Interaction):
    global chat_channel_id
    if not interaction.user.guild_permissions.manage_guild:
        return await interaction.response.send_message("❌ Bạn không có quyền dùng lệnh này.", ephemeral=True)
    chat_channel_id = None
    await interaction.response.send_message("♻️ Bot đã được reset, giờ sẽ chat ở **tất cả các kênh** khi được tag.")

@bot.tree.command(name="resetmemory", description="Xoá lịch sử hội thoại của bạn với bot")
async def resetmemory(interaction: discord.Interaction):
    user_id = interaction.user.id
    if user_id in conversation_history:
        conversation_history[user_id].clear()
        await interaction.response.send_message("🧹 Lịch sử hội thoại của bạn đã được xoá sạch!", ephemeral=True)
    else:
        await interaction.response.send_message("❌ Bạn chưa có lịch sử hội thoại nào để xoá.", ephemeral=True)

@bot.tree.command(name="resetallmemory", description="Xoá toàn bộ lịch sử hội thoại (admin)")
async def resetallmemory(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ Chỉ admin mới có thể dùng lệnh này.", ephemeral=True)
    conversation_history.clear()
    await interaction.response.send_message("🧹 Toàn bộ lịch sử hội thoại đã được xoá sạch!", ephemeral=True)

# =====================
# PING TEST
# =====================
@bot.tree.command(name="ping", description="Test slash command")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("🏓 Pong!", ephemeral=True)
        

# =====================
# ON READY
# =====================
@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"✅ Bot đã đăng nhập: {bot.user}")
        print(f"📦 Slash commands đã sync: {len(synced)} lệnh")
    except Exception as e:
        print(f"❌ Lỗi sync slash commands: {e}")    
# =====================
# RUN BOT
# =====================
if __name__ == "__main__":
    bot.run(TOKEN)
