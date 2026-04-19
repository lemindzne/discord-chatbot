import sqlite3
import os
import time

DB_PATH = os.getenv("DB_PATH", "mahiru.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS affinity 
                 (user_id INTEGER,
                 guild_id INTEGER,
                 points INTEGER DEFAULT 0,
                 PRIMARY KEY (user_id, guild_id))''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            user_id INTEGER,
            item_id TEXT,
            quantity INTEGER,
            PRIMARY KEY (user_id, item_id)
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            coins INTEGER DEFAULT 0
        )
    ''')

    c.execute('''CREATE TABLE IF NOT EXISTS server_settings (guild_id INTEGER PRIMARY KEY, channel_id INTEGER)''')
    
    try:
        c.execute("SELECT guild_id FROM affinity LIMIT 1")
    except sqlite3.OperationalError:
        print("Đang nâng cấp database: Thêm cột guild_id...")
        c.execute("ALTER TABLE affinity ADD COLUMN guild_id INTEGER DEFAULT 0")
        conn.commit()

    try:
        c.execute("SELECT last_give FROM users LIMIT 1")
    except sqlite3.OperationalError:
        print("Đang nâng cấp: Thêm cột last_give vào bảng users...")
        c.execute("ALTER TABLE users ADD COLUMN last_give INTEGER DEFAULT 0")
        conn.commit()
    
    conn.close()

def init_settings_table():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Tạo bảng lưu channel ID cho từng server
    c.execute('''CREATE TABLE IF NOT EXISTS server_settings 
                 (guild_id INTEGER PRIMARY KEY, channel_id INTEGER)''')
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

def clear_all_data():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM affinity")
        conn.commit()

def get_user_coins(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT coins FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0

def update_user_coins(user_id, amount):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Kiểm tra user tồn tại chưa, chưa thì tạo
    cursor.execute('INSERT OR IGNORE INTO users (user_id, coins) VALUES (?, 0)', (user_id,))
    cursor.execute('UPDATE users SET coins = coins + ? WHERE user_id = ?', (amount, user_id))
    conn.commit()
    conn.close()

def add_to_inventory(user_id, item_id, qty):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO inventory (user_id, item_id, quantity) VALUES (?, ?, 0)', (user_id, item_id))
    cursor.execute('UPDATE inventory SET quantity = quantity + ? WHERE user_id = ? AND item_id = ?', (qty, user_id, item_id))
    conn.commit()
    conn.close()

def get_inventory(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT item_id, quantity FROM inventory WHERE user_id = ? AND quantity > 0', (user_id,))
    results = cursor.fetchall()
    conn.close()
    return results

def remove_from_inventory(user_id, item_id, qty):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE inventory SET quantity = quantity - ? WHERE user_id = ? AND item_id = ?', (qty, user_id, item_id))
    conn.commit()
    conn.close()

def update_server_channel(guild_id, channel_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO server_settings (guild_id, channel_id) VALUES (?, ?)", (guild_id, channel_id))
    conn.commit()
    conn.close()

def get_all_server_channels():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT guild_id, channel_id FROM server_settings")
    rows = c.fetchall()
    conn.close()
    return {row[0]: row[1] for row in rows}

def set_user_context(user_id, location_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("UPDATE users SET current_context = ? WHERE user_id = ?", (location_id, user_id))
    except sqlite3.OperationalError:
        c.execute("ALTER TABLE users ADD COLUMN current_context TEXT DEFAULT 'truong_hoc'")
        c.execute("UPDATE users SET current_context = ? WHERE user_id = ?", (location_id, user_id))
    conn.commit()
    conn.close()

def check_give_cooldown(user_id):
    import time # Đảm bảo có import time
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    current_time = int(time.time())
    
    # Đảm bảo user tồn tại trong bảng users
    c.execute("INSERT OR IGNORE INTO users (user_id, coins, last_give) VALUES (?, 0, 0)", (user_id,))
    conn.commit()

    # Lấy thời gian lần cuối
    c.execute("SELECT last_give FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    
    # Mặc định là 0 nếu không có dữ liệu
    last_val = result[0] if result and result[0] is not None else 0
    
    if last_val > 0:
        elapsed = current_time - last_val
        if elapsed < 43200:
            conn.close()
            return 43200 - elapsed
            
    # Nếu được phép nhận, cập nhật thời gian mới
    c.execute("UPDATE users SET last_give = ? WHERE user_id = ?", (current_time, user_id))
    conn.commit()
    conn.close()
    return 0
    
init_db()
