import asyncio
import sqlite3
import re
from datetime import date, time
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    CallbackContext,
    filters
)

# 📁 База данных
conn = sqlite3.connect("sobriety.db", check_same_thread=False)
c = conn.cursor()

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

c.execute('''
CREATE TABLE IF NOT EXISTS settings (
    chat_id INTEGER PRIMARY KEY,
    notify_hour INTEGER,
    notify_minute INTEGER
)
''')
conn.commit()

# 🛠 Утилиты БД
def init_user(user_id):
    c.execute("INSERT OR IGNORE INTO progress (user_id, start_date) VALUES (?, ?)", (user_id, date.today().isoformat()))
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
    c.execute("REPLACE INTO settings (chat_id, notify_hour, notify_minute) VALUES (?, ?, ?)", (chat_id, hour, minute))
    conn.commit()

def get_all_notify_times():
    c.execute("SELECT chat_id, notify_hour, notify_minute FROM settings")
    return c.fetchall()

# 🎛 Состояния
user_states = {}
user_jobs = {}
keyboard = ReplyKeyboardMarkup([["✅ Нет", "❌ Да"]], one_time_keyboard=True)

def is_valid_time_format(text):
    return re.match(r'^\d{1,2}:\d{2}$', text)

# 🔔 Ежедневное напоминание
async def daily_prompt(context: CallbackContext):
    chat_id = context.job.chat_id
    await context.bot.send_message(chat_id=chat_id, text="Ты сегодня употреблял алкоголь?", reply_markup=keyboard)

# 👋 Старт
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    init_user(user_id)
    user_states[user_id] = "waiting_time"
    await update.message.reply_text("👋 Введи время напоминания в формате HH:MM (например 19:30)")

# 🕒 Обработка времени
async def handle_time_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    text = update.message.text.strip()

    if not is_valid_time_format(text):
        await update.message.reply_text("⏰ Формат должен быть HH:MM, например 20:00")
        return

    hour, minute = map(int, text.split(":"))
    save_notify_time(chat_id, hour, minute)
    time_obj = time(hour=hour, minute=minute)
    job = context.application.job_queue.run_daily(daily_prompt, time_obj, chat_id=chat_id)
    user_jobs[chat_id] = job
    user_states[user_id] = "waiting_spend"
    await update.message.reply_text("✅ Время установлено!\nТеперь введи сумму, которую ты обычно тратишь на алкоголь в день (например 10)")

# 💸 Обработка суммы
async def handle_spend_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    try:
        amount = float(text.replace(",", "."))
        set_daily_spend(user_id, amount)
        user_states[user_id] = None
        await update.message.reply_text("👍 Спасибо! Я буду присылать напоминания каждый день.")
    except:
        await update.message.reply_text("🚫 Пожалуйста, введи число (например: 12.5)")

# 📥 Ответ пользователя
async def handle_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    state = user_states.get(user_id)

    if state == "waiting_time":
        await handle_time_input(update, context)
        return
    if state == "waiting_spend":
        await handle_spend_input(update, context)
        return

    if text in ["✅ Нет", "❌ Да", "Нет", "Да"]:
        is_sober = "Нет" in text
        update_stats(user_id, is_sober)
        start_date, sober_days, total_days, saved_money = get_stats(user_id)
        await update.message.reply_text(
            f"📊 Твоя статистика:\n"
            f"📅 С начала: {start_date}\n"
            f"🚫 Трезвых дней: {sober_days} из {total_days}\n"
            f"💰 Сэкономлено: €{saved_money:.2f}"
        )
    else:
        await update.message.reply_text("🤔 Не понял сообщение. Используй кнопки или следуй инструкции.")

# 🚀 Запуск
async def main():
    app = Application.builder().token("7567781159:AAHzuKX2mRfkqTX_1kt8XTD2BGqiQjy57W4").build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_response))

    for chat_id, hour, minute in get_all_notify_times():
        time_obj = time(hour=hour, minute=minute)
        app.job_queue.run_daily(daily_prompt, time_obj, chat_id=chat_id)

    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
