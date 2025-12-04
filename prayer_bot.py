import os
import requests
import logging
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram import ReplyKeyboardMarkup

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
logger = logging.getLogger(__name__)


# ===============================
# PRAYER API
# ===============================
def get_prayer_times(city, country=""):
    url = "https://api.aladhan.com/v1/timingsByCity"
    params = {
        "city": city,
        "country": country,
        "method": 4,  # طريقة الحساب (يمكن تعديلها لاحقاً)
    }

    try:
        res = requests.get(url, params=params, timeout=10)
        data = res.json()
        if data.get("code") != 200:
            return None
        return data["data"]["timings"]
    except Exception as e:
        logger.error("Error calling API: %s", e)
        return None


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
# KEYBOARD
# ===============================
def get_main_keyboard():
    keyboard = [
        ["🕌 مواقيت اليوم", "🧭 تغيير المدينة"],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


# ===============================
# COMMANDS
# ===============================
def start(update, context):
    chat_id = update.effective_chat.id

    if chat_id in user_locations:
        loc = user_locations[chat_id]
        text = (
            "وعليكم السلام ورحمة الله وبركاته 🤍\n\n"
            f"المدينة الحالية المحفوظة لديك هي: {loc['city']}, {loc['country']}\n\n"
            "اضغط زر 🕌 مواقيت اليوم أو أرسل أي رسالة للحصول على المواقيت.\n"
            "ولتغيير المدينة اضغط زر 🧭 تغيير المدينة أو أرسل الأمر /change"
        )
    else:
        text = (
            "وعليكم السلام ورحمة الله وبركاته 🤍\n\n"
            "من فضلك اكتب اسم مدينتك بالشكل التالي:\n"
            "Cairo, Egypt أو Doha, Qatar أو Tripoli, Lebanon\n\n"
            "بعد حفظ المدينة يمكنك استخدام الأزرار في الأسفل."
        )

    context.bot.send_message(chat_id=chat_id, text=text, reply_markup=get_main_keyboard())


def change_city(update, context):
    chat_id = update.effective_chat.id
    user_locations.pop(chat_id, None)

    context.bot.send_message(
        chat_id=chat_id,
        text=(
            "✅ تم حذف المدينة المحفوظة.\n\n"
            "اكتب الآن المدينة الجديدة بهذا الشكل:\n"
            "Riyadh, Saudi Arabia أو Amman, Jordan"
        ),
        reply_markup=get_main_keyboard(),
    )


# ===============================
# MAIN MESSAGE HANDLER
# ===============================
def handle_message(update, context):
    chat_id = update.effective_chat.id
    text_raw = update.message.text or ""
    text = text_raw.strip()
    text_l = text.lower()

    greetings = [
        "السلام", "سلام", "السلام عليكم", "سلام عليكم",
        "مرحبا", "مرحباا", "اهلا", "أهلا", "اهلاً",
        "hi", "hello", "هلا", "يا هلا",
        "مساء الخير", "صباح الخير",
    ]

    # -------- أزرار الكيبورد --------

    # زر تغيير المدينة
    if text == "🧭 تغيير المدينة":
        change_city(update, context)
        return

    # زر مواقيت اليوم
    if text == "🕌 مواقيت اليوم":
        if chat_id not in user_locations:
            context.bot.send_message(
                chat_id=chat_id,
                text=(
                    "لم تقم بتحديد مدينة بعد.\n"
                    "من فضلك اكتب اسم مدينتك أولاً، مثال:\n"
                    "Doha, Qatar"
                ),
                reply_markup=get_main_keyboard(),
            )
            return

        loc = user_locations[chat_id]
        t = get_prayer_times(loc["city"], loc["country"])
        if not t:
            context.bot.send_message(
                chat_id=chat_id,
                text="❌ حدث خطأ مؤقت في جلب المواقيت، حاول لاحقاً.",
                reply_markup=get_main_keyboard(),
            )
            return

        msg = format_prayer_message(loc["city"], loc["country"], t)
        context.bot.send_message(chat_id=chat_id, text=msg, reply_markup=get_main_keyboard())
        return

    # -------- تحيات بدون مدينة محفوظة --------
    if chat_id not in user_locations and any(g in text_l for g in greetings):
        context.bot.send_message(
            chat_id=chat_id,
            text=(
                "وعليكم السلام ورحمة الله وبركاته 🤍\n\n"
                "من فضلك اكتب اسم مدينتك مثال:\n"
                "Tripoli, Lebanon أو Doha, Qatar"
            ),
            reply_markup=get_main_keyboard(),
        )
        return

    # -------- إدخال المدينة لأول مرة --------
    if chat_id not in user_locations:
        city = text
        country = ""

        if "," in text:
            p = [x.strip() for x in text.split(",", 1)]
            city = p[0]
            if len(p) > 1:
                country = p[1]

        t = get_prayer_times(city, country)
        if not t:
            context.bot.send_message(
                chat_id=chat_id,
                text=(
                    "❌ لم أتمكن من التعرف على المدينة.\n\n"
                    "جرّب كتابة المدينة هكذا:\n"
                    "Tripoli, Lebanon أو Riyadh, Saudi Arabia"
                ),
                reply_markup=get_main_keyboard(),
            )
            return

        user_locations[chat_id] = {"city": city, "country": country}
        msg = format_prayer_message(city, country, t)
        context.bot.send_message(chat_id=chat_id, text=msg, reply_markup=get_main_keyboard())
        return

    # -------- يوجد مدينة محفوظة مسبقاً --------
    loc = user_locations[chat_id]
    t = get_prayer_times(loc["city"], loc["country"])
    if not t:
        context.bot.send_message(
            chat_id=chat_id,
            text="❌ حدث خطأ مؤقت في جلب المواقيت، حاول لاحقاً.",
            reply_markup=get_main_keyboard(),
        )
        return

    msg = format_prayer_message(loc["city"], loc["country"], t)
    context.bot.send_message(chat_id=chat_id, text=msg, reply_markup=get_main_keyboard())


# ===============================
# RUN BOT
# ===============================
def main():
    if not TELEGRAM_TOKEN or TELEGRAM_TOKEN == "PUT_LOCAL_TOKEN_HERE":
        logger.warning("تحذير: لم يتم ضبط TELEGRAM_TOKEN بشكل صحيح.")

    updater = Updater(TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("change", change_city))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
