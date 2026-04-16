import sqlite3
import os

DB_PATH = os.getenv("DB_PATH", "mahiru.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Tạo bảng nếu chưa có
    c.execute('''CREATE TABLE IF NOT EXISTS affinity 
                 (user_id INTEGER, guild_id INTEGER, points INTEGER DEFAULT 0,
                  PRIMARY KEY (user_id, guild_id))''')
    
    # KIỂM TRA VÀ NÂNG CẤP CỘT (Fix lỗi no such column)
    try:
        c.execute("SELECT guild_id FROM affinity LIMIT 1")
    except sqlite3.OperationalError:
        # Nếu lỗi nghĩa là chưa có cột guild_id, tiến hành thêm vào
        print("Đang nâng cấp database: Thêm cột guild_id...")
        c.execute("ALTER TABLE affinity ADD COLUMN guild_id INTEGER DEFAULT 0")
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
