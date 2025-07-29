import asyncio
import sqlite3
from datetime import time
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    CallbackContext,
    filters
)

conn = sqlite3.connect("settings.db", check_same_thread=False)
cur = conn.cursor()
cur.execute("CREATE TABLE IF NOT EXISTS notify (chat_id INTEGER PRIMARY KEY, hour INTEGER, minute INTEGER)")
conn.commit()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["step"] = "ask_time"
    await update.message.reply_text("👋 Привет! Во сколько тебе присылать сообщение каждый день? (формат HH:MM)")

async def handle_time_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text.strip()
    if context.user_data.get("step") == "ask_time":
        try:
            hour, minute = map(int, text.split(":"))
            cur.execute("REPLACE INTO notify VALUES (?, ?, ?)", (chat_id, hour, minute))
            conn.commit()
            t = time(hour=hour, minute=minute)
            context.application.job_queue.run_daily(send_daily_message, t, chat_id=chat_id)
            context.user_data["step"] = None
            await update.message.reply_text(f"✅ Готово! Буду писать тебе каждый день в {text}")
        except:
            await update.message.reply_text("⚠️ Неверный формат. Введи как HH:MM (например 08:30)")
    else:
        await update.message.reply_text("💬 Напиши /start, чтобы настроить время")

async def send_daily_message(context: CallbackContext):
    await context.bot.send_message(chat_id=context.job.chat_id, text="🌞 Доброе утро! Это твоё ежедневное сообщение.")

async def main():
    app = Application.builder().token("7567781159:AAHzuKX2mRfkqTX_1kt8XTD2BGqiQjy57W4").build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_time_input))

    # Восстановление задач из БД
    for row in cur.execute("SELECT chat_id, hour, minute FROM notify"):
        cid, h, m = row
        app.job_queue.run_daily(send_daily_message, time(hour=h, minute=m), chat_id=cid)

    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
