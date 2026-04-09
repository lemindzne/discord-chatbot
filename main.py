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
import google.generativeai as genai
from dotenv import load_dotenv
from collections import defaultdict, deque
from pathlib import Path
from datetime import timedelta

# =====================
# LOAD CONFIG
# =====================
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")


# =====================
# GEMINI CONFIG
# =====================
genai.configure(api_key=GEMINI_KEY)

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
bot = commands.Bot(command_prefix="?", intents=intents, help_command=None)

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

async def get_ai_response(prompt: str) -> str:
    global last_request_time
    try:
        now = time.time()
        if now - last_request_time < 6:  # 10 req/phút ≈ 1 req/6 giây
            await asyncio.sleep(6 - (now - last_request_time))

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: genai.GenerativeModel("gemini-2.5-flash").generate_content(prompt)
        )
        last_request_time = time.time()
        return response.text.strip()
    except Exception as e:
        print("❌ Gemini error:", e)
        return 

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
    global lover_nickname
    if message.author.bot:
        return

    if bot.user in message.mentions:
        if chat_channel_id and message.channel.id != chat_channel_id:
            return

        user_message = message.content.replace(f"<@{bot.user.id}>", "").strip()[:300]

        # Lưu lịch sử user
        conversation_history[message.author.id].append(("user", user_message))

        # Ghép lịch sử hội thoại
        history_text = ""
        for role, text in conversation_history[message.author.id]:
            if role == "user":
                name = lover_nickname if message.author.id == SPECIAL_USER_ID else "Người dùng"
                history_text += f"{name}: {text}\n"
            else:
                history_text += f"Bot: {text}\n"

        # Prompt
        if message.author.id == SPECIAL_USER_ID:
            prompt = (
                f"bạn là shiina mahiru - cô người yêu ngọt ngào của min, hay nũng nịu và làm những vẻ mặt cute , lâu lâu hay dỗi nhưng sau đó lại làm lành"
            )
            is_special = True
        else:
            prompt = (
                " bạn là mahiru shiina ,Mahiru luôn giữ một nụ cười mỉm nhẹ nhàng nhưng vô hồn trên môi. trò chuyện với mọi người với tư cách bạn bè .Tuy nhiên, đằng sau sự tử tế đó là một bức tường thép; bạn không bao giờ để ai bước vào không gian riêng tư của mình. bạn từ chối mọi lời tỏ tình một cách khéo léo nhưng dứt khoát, không để lại chút hy vọng nào."
                "Hãy trả lời ngắn (2-3 câu).\n\n"
                f"Lịch sử hội thoại:\n{history_text}"
            )
            is_special = False

        async with processing_lock:
            ai_reply = await get_ai_response(prompt)
            ai_reply = limit_exact_sentences(ai_reply, is_special)

            # Lưu reply bot
            conversation_history[message.author.id].append(("bot", ai_reply))

            await message.channel.send(ai_reply)

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
