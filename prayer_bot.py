import logging
import requests
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

import os
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# تخزين المدينة لكل مستخدم
user_locations = {}

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def start(update, context):
    chat_id = update.effective_chat.id
    text = (
        "👋 أهلاً بك في بوت مواقيت الصلاة\n\n"
        "اكتب اسم مدينتك مثال:\n"
        "Tripoli, Lebanon\n\n"
        "لتغيير المدينة لاحقاً أرسل الأمر:\n"
        "/change"
    )
    context.bot.send_message(chat_id=chat_id, text=text)


def change_city(update, context):
    chat_id = update.effective_chat.id
    user_locations.pop(chat_id, None)
    context.bot.send_message(
        chat_id=chat_id,
        text="✅ تم حذف المدينة\nاكتب المدينة الجديدة:"
    )


def get_prayer_times(city, country=""):
    url = "https://api.aladhan.com/v1/timingsByCity"

    params = {
        "city": city,
        "country": country,
        "method": 2
    }

    r = requests.get(url, params=params)
    data = r.json()

    if data.get("code") != 200:
        return None

    t = data["data"]["timings"]

    return (
        f"🕌 مواقيت الصلاة اليوم في {city} {country}\n\n"
        f"الفجر 🕓 : {t['Fajr']}\n"
        f"الظهر 🕛 : {t['Dhuhr']}\n"
        f"العصر 🕒 : {t['Asr']}\n"
        f"المغرب 🌇 : {t['Maghrib']}\n"
        f"العشاء 🌙 : {t['Isha']}"
    )


def handle_message(update, context):
    chat_id = update.effective_chat.id
    text = update.message.text.strip().lower()

# كلمات تحية لا تعتبر مدن
ignore_words = [
    "السلام عليكم", "مرحبا", "اهلا", "أهلا", "hello", "hi"
]

for word in ignore_words:
    if word in text:
        context.bot.send_message(
            chat_id=chat_id,
            text="👋 مرحبًا بك\nمن فضلك اكتب اسم مدينتك مثال:\nCairo, Egypt أو Doha, Qatar"
        )
        return


    if chat_id not in user_locations:

        city = text
        country = ""

        if "," in text:
            p = text.split(",", 1)
            city = p[0].strip()
            country = p[1].strip()

        msg = get_prayer_times(city, country)

        if msg is None:
            context.bot.send_message(
                chat_id=chat_id,
                text="❌ لم أتعرف على المدينة.\nأكتب مثلاً:\nTripoli, Lebanon"
            )
            return

        user_locations[chat_id] = {
            "city": city,
            "country": country
        }

        context.bot.send_message(chat_id=chat_id, text=msg)
        return

    loc = user_locations[chat_id]
    msg = get_prayer_times(loc["city"], loc["country"])

    context.bot.send_message(chat_id=chat_id, text=msg)


def main():
    updater = Updater(TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("change", change_city))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()


