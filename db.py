import sqlite3
from datetime import date

conn = sqlite3.connect("sobriety.db", check_same_thread=False)
c = conn.cursor()

# Прогресс
c.execute('''
CREATE TABLE IF NOT EXISTS progress (
    user_id INTEGER PRIMARY KEY,
    start_date TEXT,
    sober_days INTEGER DEFAULT 0,
    total_days INTEGER DEFAULT 0,
    money_saved REAL DEFAULT 0,
    daily_spend REAL DEFAULT 10
)
''')

# Настройки
c.execute('''
CREATE TABLE IF NOT EXISTS settings (
    chat_id INTEGER PRIMARY KEY,
    notify_hour INTEGER,
    notify_minute INTEGER
)
''')
conn.commit()

# Инициализация нового пользователя
def init_user(user_id):
    c.execute("INSERT OR IGNORE INTO progress (user_id, start_date) VALUES (?, ?)",
              (user_id, date.today().isoformat()))
    conn.commit()

def set_daily_spend(user_id, amount):
    c.execute("UPDATE progress SET daily_spend = ? WHERE user_id = ?", (amount, user_id))
    conn.commit()

def update_stats(user_id, is_sober):
    c.execute("SELECT daily_spend, sober_days, total_days, money_saved FROM progress WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    if not row:
        return
    spend, sober, total, saved = row
    total += 1
    if is_sober:
        sober += 1
        saved += spend
    c.execute("UPDATE progress SET sober_days=?, total_days=?, money_saved=? WHERE user_id=?",
              (sober, total, saved, user_id))
    conn.commit()

def get_stats(user_id):
    c.execute("SELECT start_date, sober_days, total_days, money_saved FROM progress WHERE user_id=?", (user_id,))
    return c.fetchone()

def save_notify_time(chat_id, hour, minute):
    c.execute("REPLACE INTO settings (chat_id, notify_hour, notify_minute) VALUES (?, ?, ?)",
              (chat_id, hour, minute))
    conn.commit()

def load_notify_time(chat_id):
    c.execute("SELECT notify_hour, notify_minute FROM settings WHERE chat_id=?", (chat_id,))
    return c.fetchone()

def get_all_notify_times():
    c.execute("SELECT chat_id, notify_hour, notify_minute FROM settings")
    return c.fetchall()