import asyncio
import sqlite3
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

# 📦 Подключение к SQLite
conn = sqlite3.connect("stats.db", check_same_thread=False)
cur = conn.cursor()

cur.execute('''
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    hour INTEGER,
    minute INTEGER,
    daily_spend REAL,
    sober_days INTEGER DEFAULT 0,
    total_days INTEGER DEFAULT 0,
    saved REAL DEFAULT 0,
    start_date TEXT
)
''')
conn.commit()

keyboard = ReplyKeyboardMarkup([["✅ Нет", "❌ Да"]], one_time_keyboard=True)

# 🚀 Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["step"] = "time"
    await update.message.reply_text("⏰ Введи время, когда мне напоминать тебе (например 19:30)")

# 📥 Ввод данных
async def handle_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    msg = update.message.text.strip()
    step = context.user_data.get("step")

    if step == "time":
        try:
            h, m = map(int, msg.split(":"))
            context.user_data.update({"hour": h, "minute": m, "step": "spend"})
            await update.message.reply_text("💸 Сколько ты обычно тратишь на алкоголь в день?")
        except:
            await update.message.reply_text("🚫 Введи время как HH:MM")

    elif step == "spend":
        try:
            spend = float(msg.replace(",", "."))
            h, m = context.user_data["hour"], context.user_data["minute"]

            cur.execute("INSERT OR REPLACE INTO users VALUES (?, ?, ?, ?, 0, 0, 0, ?)",
                        (user_id, h, m, spend, date.today().isoformat()))
            conn.commit()

            # Запускаем ежедневное задание
            t = time(hour=h, minute=m)
            context.application.job_queue.run_daily(daily_question, t, chat_id=update.effective_chat.id)
            context.user_data["step"] = None

            await update.message.reply_text("✅ Готово! Я буду спрашивать тебя каждый день 🗓")
        except:
            await update.message.reply_text("🚫 Введи сумму, например: 12.5")

    else:
        await handle_reply(update, context)

# 🔔 Ежедневный вопрос
async def daily_question(context: CallbackContext):
    await context.bot.send_message(chat_id=context.job.chat_id,
                                   text="Ты сегодня пил алкоголь?",
                                   reply_markup=keyboard)

# 📊 Ответ пользователя
async def handle_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    msg = update.message.text

    if msg not in ["✅ Нет", "❌ Да"]:
        await update.message.reply_text("🙃 Используй кнопки 'Нет' или 'Да'")
        return

    is_sober = "Нет" in msg
    cur.execute("SELECT daily_spend, sober_days, total_days, saved, start_date FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()

    if row:
        spend, sober, total, saved, start = row
        total += 1
        if is_sober:
            sober += 1
            saved += spend
        cur.execute("UPDATE users SET sober_days=?, total_days=?, saved=? WHERE user_id=?",
                    (sober, total, saved, user_id))
        conn.commit()
        await update.message.reply_text(
            f"📅 С начала: {start}\n🚫 Трезвых дней: {sober} из {total}\n💰 Сэкономлено: €{saved:.2f}"
        )
    else:
        await update.message.reply_text("❗ Напиши сначала /start")

# ⚙️ Запуск
async def main():
    app = Application.builder().token("7567781159:AAHzuKX2mRfkqTX_1kt8XTD2BGqiQjy57W4").build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_input))
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
