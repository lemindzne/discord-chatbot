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
GROQ_KEY = os.getenv("GROQ_API_KEY") 
DB_PATH = os.getenv("DB_PATH", "mahiru.db") 

client = Groq(api_key=GROQ_KEY)

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

        db.add_affinity(user_id, message.guild.id, bonus) 
        points = db.get_affinity(user_id, message.guild.id)

        history = conversation_history[user_id]
        history_text = "\n".join([f"{'Anh' if h['role']=='user' else 'Em'}: {h['content']}" for h in history])

        if user_id == SPECIAL_USER_ID:
            is_special = True
            system_prompt = prompts.get_special_prompt(lover_nickname, history_text)
        else:
            is_special = False
            system_prompt = prompts.get_normal_prompt(points, history_text)
    
        async with processing_lock:
            ai_reply = await get_ai_response(system_prompt, user_message)
        
            if ai_reply:
                ai_reply = re.sub(r'~+', '~', ai_reply)
                ai_reply = re.sub(r'(\*.*?\*)', r'|\1|', ai_reply)
                messages_to_send = [m.strip() for m in re.split(r'[|\n]', ai_reply) if m.strip()]
            
                for i, msg in enumerate(messages_to_send):
                    async with message.channel.typing():
                        base_speed = len(msg) * random.uniform(0.05, 0.1)
                        thinking_time = random.uniform(0.5, 1.5)
                        total_sleep = min(base_speed + thinking_time, 4.0)
                        await asyncio.sleep(total_sleep)
                        
                        if i == 0:
                            await message.reply(msg)
                        else:
                            await message.channel.send(msg)
            
                full_reply_clean = " ".join(messages_to_send)
                history.append({"role": "user", "content": user_message})
                history.append({"role": "assistant", "content": full_reply_clean})
            
            else:
                await message.reply("Hic, em đang hơi chóng mặt... Anh đợi em xíu nhé~")

    await bot.process_commands(message)
    

@bot.event
async def on_ready():
    print(f"✅ Mahiru online: {bot.user}")
    try:
        await bot.load_extension("cogs.commands")
        print("✅ Đã kết nối file lệnh thành công!")
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        
bot.run(TOKEN)
