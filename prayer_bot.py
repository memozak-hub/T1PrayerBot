import os
import requests
import logging
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

# ===============================
# TOKEN
# ===============================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "PUT_LOCAL_TOKEN_HERE")

# ===============================
# STORAGE
# ===============================
user_locations = {}

# ===============================
# LOGGING
# ===============================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# ===============================
# API
# ===============================
def get_prayer_times(city, country=""):
    url = "https://api.aladhan.com/v1/timingsByCity"
    params = {
        "city": city,
        "country": country,
        "method": 4,
    }

    try:
        res = requests.get(url, params=params, timeout=10)
        data = res.json()
        if data.get("code") != 200:
            return None
        return data["data"]["timings"]
    except:
        return None


# ===============================
# FORMATTING MESSAGE
# ===============================
def format_prayer_message(city, country, t):
    loc = city if not country else f"{city}, {country}"

    return (
        f"🕌 مواقيت الصلاة اليوم في {loc}\n\n"
        f"الفجر 🕓 : {t['Fajr']}\n"
        f"الظهر 🕛 : {t['Dhuhr']}\n"
        f"العصر 🕒 : {t['Asr']}\n"
        f"المغرب 🌇 : {t['Maghrib']}\n"
        f"العشاء 🌙 : {t['Isha']}"
    )


# ===============================
# COMMANDS
# ===============================
def start(update, context):
    chat_id = update.effective_chat.id

    context.bot.send_message(
        chat_id=chat_id,
        text=(
            "وعليكم السلام ورحمة الله وبركاته 🤍\n\n"
            "من فضلك اكتب اسم مدينتك بالشكل التالي:\n"
            "Cairo, Egypt أو Doha, Qatar"
        )
    )


def change(update, context):
    chat_id = update.effective_chat.id
    user_locations.pop(chat_id, None)

    context.bot.send_message(
        chat_id=chat_id,
        text=(
            "✅ تم حذف المدينة المحفوظة\n\n"
            "اكتب المدينة الجديدة:\n"
            "Riyadh, Saudi Arabia"
        )
    )


# ===============================
# MAIN MESSAGE HANDLER
# ===============================
def handle_message(update, context):
    chat_id = update.effective_chat.id
    text = update.message.text.strip()
    text_l = text.lower()

    greetings = [
        "السلام",
        "مرحبا",
        "أهلا",
        "اهلا",
        "hello",
        "hi",
        "يا هلا",
        "هلا",
        "مرحبتين",
        "مساء الخير",
        "صباح الخير"
    ]

    # ----------------------------------
    # إذا كانت تحية → اسأل عن المدينة
    # ----------------------------------
    if chat_id not in user_locations and any(g in text_l for g in greetings):
        context.bot.send_message(
            chat_id=chat_id,
            text=(
                "وعليكم السلام ورحمة الله وبركاته 🤍\n\n"
                "من فضلك اكتب اسم مدينتك مثال:\n"
                "Tripoli, Lebanon أو Doha, Qatar"
            )
        )
        return

    # ----------------------------------
    # إدخال المدينة لأول مرة
    # ----------------------------------
    if chat_id not in user_locations:
        city = text
        country = ""

        if "," in text:
            p = [x.strip() for x in text.split(",", 1)]
            city = p[0]
            country = p[1]

        t = get_prayer_times(city, country)

    if not t:
            context.bot.send_message(
                chat_id=chat_id,
                text=(
                    "❌ لم أتمكن من التعرف على المدينة.\n\n"
                    "جرّب كتابة المدينة هكذا:\n"
                    "Tripoli, Lebanon"
                )
            )
            return

        user_locations[chat_id] = {
            "city": city,
            "country": country
        }

        msg = format_prayer_message(city, country, t)
        context.bot.send_message(chat_id=chat_id, text=msg)
        return

    # ----------------------------------
    # المستخدم لديه مدينة محفوظة
    # ----------------------------------
    loc = user_locations[chat_id]
    t = get_prayer_times(loc["city"], loc["country"])

    if not t:
        context.bot.send_message(
            chat_id=chat_id,
            text="❌ حدث خطأ مؤقت في جلب المواقيت"
        )
        return

    msg = format_prayer_message(loc["city"], loc["country"], t)
    context.bot.send_message(chat_id=chat_id, text=msg)


# ===============================
# RUN
# ===============================
def main():
    updater = Updater(TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("change", change))
    dp.add_handler(
        MessageHandler(Filters.text & ~Filters.command, handle_message)
    )

    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
