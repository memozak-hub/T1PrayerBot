import os
import requests
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram import ReplyKeyboardMarkup
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

TOKEN = os.getenv("TELEGRAM_TOKEN", "PUT_LOCAL_TOKEN_HERE")

# --------------------
users = {}

# --------------------
def keyboard():
    return ReplyKeyboardMarkup(
        [["🕌 مواقيت اليوم", "🧭 تغيير المدينة"]],
        resize_keyboard=True
    )

# --------------------
def get_prayer(city, country=""):
    url = "https://api.aladhan.com/v1/timingsByCity"
    params = {"city": city, "country": country, "method": 4}
    try:
        r = requests.get(url, params=params, timeout=10)
        data = r.json()
        if data["code"] != 200:
            return None
        return data["data"]["timings"]
    except:
        return None

# --------------------
def format_prayer(city, country, t):
    loc = city if not country else f"{city}, {country}"
    return (
        f"🕌 مواقيت الصلاة في {loc}\n\n"
        f"الفجر: {t['Fajr']}\n"
        f"الظهر: {t['Dhuhr']}\n"
        f"العصر: {t['Asr']}\n"
        f"المغرب: {t['Maghrib']}\n"
        f"العشاء: {t['Isha']}"
    )

# --------------------
def start(update, context):
    chat = update.effective_chat.id
    context.bot.send_message(
        chat_id=chat,
        text="وعليكم السلام ورحمة الله وبركاته 🤍\n\n"
             "من فضلك أرسل اسم مدينتك هكذا:\n"
             "Doha, Qatar",
        reply_markup=keyboard()
    )

# --------------------
def change(update, context):
    chat = update.effective_chat.id
    users.pop(chat, None)
    context.bot.send_message(
        chat_id=chat,
        text="✅ تم حذف المدينة.\n\nأرسل المدينة الجديدة:",
        reply_markup=keyboard()
    )

# --------------------
def handle(update, context):
    chat = update.effective_chat.id
    text = update.message.text.strip()

    greetings = [
        "السلام", "مرحبا", "اهلا", "hi", "hello", "هلا", "صباح", "مساء"
    ]

    # زر تغيير المدينة
    if text == "🧭 تغيير المدينة":
        change(update, context)
        return

    # زر مواقيت اليوم
    if text == "🕌 مواقيت اليوم":
        if chat not in users:
            context.bot.send_message(
                chat_id=chat,
                text="⚠️ اكتب اسم مدينتك أولاً:",
                reply_markup=keyboard()
            )
            return

        loc = users[chat]
        t = get_prayer(loc["city"], loc["country"])
        if not t:
            context.bot.send_message(chat_id=chat, text="❌ حدث خطأ")
            return

        context.bot.send_message(
            chat_id=chat,
            text=format_prayer(loc["city"], loc["country"], t),
            reply_markup=keyboard()
        )
        return

    # تحية
    if chat not in users and any(g in text.lower() for g in greetings):
        start(update, context)
        return

    # إدخال المدينة لأول مرة
    if chat not in users:
        city = text
        country = ""

        if "," in text:
            p = [x.strip() for x in text.split(",", 1)]
            city = p[0]
            if len(p) > 1:
                country = p[1]

        t = get_prayer(city, country)
        if not t:
            context.bot.send_message(
                chat_id=chat,
                text="❌ اسم المدينة غير واضح.\nاكتب هكذا: Tripoli, Lebanon",
                reply_markup=keyboard()
            )
            return

        users[chat] = {"city": city, "country": country}
        context.bot.send_message(
            chat_id=chat,
            text=format_prayer(city, country, t),
            reply_markup=keyboard()
        )
        return

    # لاحقًا: أي رسالة → مواقيت المدينة المحفوظة
    loc = users[chat]
    t = get_prayer(loc["city"], loc["country"])
    context.bot.send_message(
        chat_id=chat,
        text=format_prayer(loc["city"], loc["country"], t),
        reply_markup=keyboard()
    )

# --------------------
# سيرفر HTTP بسيط علشان Render
# --------------------
def run_http_server():
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Bot is running")

    port = int(os.environ.get("PORT", "8000"))
    server = HTTPServer(("", port), Handler)
    server.serve_forever()

# --------------------
def main():
    # تشغيل سيرفر HTTP في ثريد منفصل
    threading.Thread(target=run_http_server, daemon=True).start()

    # تشغيل بوت تليجرام
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("change", change))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
