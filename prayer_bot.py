import logging
import os
import requests
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

# ==============================
# إعداد التوكن
# ==============================
# محليًّا: يمكنك وضع التوكن هنا مباشرة
# على Render: اجعل TELEGRAM_TOKEN في Environment Variables
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "PUT_LOCAL_TOKEN_HERE")

# تخزين المدينة لكل مستخدم: chat_id -> {"city": ..., "country": ...}
user_locations = {}

# ==============================
# إعداد نظام اللوجات (اختياري لكنه مفيد)
# ==============================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# ==============================
# دوال مساعدة
# ==============================

def format_prayer_message(city, country, timings):
    """تنسيق رسالة مواقيت الصلاة باللغة العربية"""
    fajr = timings.get("Fajr")
    dhuhr = timings.get("Dhuhr")
    asr = timings.get("Asr")
    maghrib = timings.get("Maghrib")
    isha = timings.get("Isha")

    location_text = city
    if country:
        location_text += f", {country}"

    msg = (
        f"مواقيت الصلاة اليوم في {location_text} 🕌\n\n"
        f"الفجر  🕓 : {fajr}\n"
        f"الظهر  🕛 : {dhuhr}\n"
        f"العصر  🕒 : {asr}\n"
        f"المغرب 🌇 : {maghrib}\n"
        f"العشاء 🌙 : {isha}\n\n"
        "⚠️ قد تختلف الدقائق عن أوقات الأوقاف/المساجد الرسمية في بلدك."
    )
    return msg


def get_prayer_times(city, country=""):
    """
    الاتصال بـ AlAdhan API لجلب مواقيت الصلاة حسب المدينة.
    https://aladhan.com/prayer-times-api
    """
    url = "https://api.aladhan.com/v1/timingsByCity"

    params = {
        "city": city,
        "country": country,
        "method": 4,  # طريقة حساب (أم القرى مثلاً)، يمكنك تعديلها لاحقًا
    }

    try:
        r = requests.get(url, params=params, timeout=10)
    except Exception as e:
        logger.error(f"Error while calling API: {e}")
        return None

    try:
        data = r.json()
    except ValueError:
        logger.error("Response is not JSON")
        return None

    if data.get("code") != 200:
        logger.warning(f"API returned non-200 code: {data}")
        return None

    timings = data["data"]["timings"]
    return timings


# ==============================
# أوامر البوت
# ==============================

def start(update, context):
    """الرسالة الأولى عند استخدام /start"""
    chat_id = update.effective_chat.id

    if chat_id in user_locations:
        loc = user_locations[chat_id]
        text = (
            "👋 أهلاً بك مجددًا في بوت مواقيت الصلاة.\n"
            f"المدينة الحالية المحفوظة لديك هي: {loc['city']}, {loc['country']}\n\n"
            "أرسل أي رسالة للحصول على مواقيت اليوم.\n"
            "ولتغيير المدينة أرسل الأمر: /change"
        )
    else:
        text = (
            "👋 أهلاً بك في بوت مواقيت الصلاة.\n\n"
            "من فضلك اكتب اسم مدينتك بهذا الشكل:\n"
            "Cairo, Egypt أو Doha, Qatar أو Tripoli, Lebanon\n\n"
            "يمكنك لاحقًا تغيير المدينة بالأمر: /change"
        )

    context.bot.send_message(chat_id=chat_id, text=text)


def change_city(update, context):
    """تغيير المدينة المخزنة للمستخدم"""
    chat_id = update.effective_chat.id
    user_locations.pop(chat_id, None)
    context.bot.send_message(
        chat_id=chat_id,
        text=(
            "✅ تم حذف المدينة المحفوظة.\n"
            "اكتب الآن المدينة الجديدة بهذا الشكل:\n"
            "Riyadh, Saudi Arabia أو Amman, Jordan"
        ),
    )


# ==============================
# التعامل مع الرسائل النصية العادية
# ==============================

def handle_message(update, context):
    """التعامل مع أي رسالة نصية يرسلها المستخدم"""
    chat_id = update.effective_chat.id
    text_raw = update.message.text or ""
    text = text_raw.strip()
    normalized = text.lower()

    # كلمات تحية لا نريد اعتبارها كمدينة
    greeting_words = [
        "السلام عليكم",
        "سلام عليكم",
        "سلام",
        "مرحبا",
        "مرحباا",
        "اهلا",
        "أهلا",
        "اهلاً",
        "hi",
        "hello",
    ]

    # لو المستخدم لا يملك مدينة محفوظة وأرسل تحية فقط
    if chat_id not in user_locations and any(word in normalized for word in greeting_words):
        context.bot.send_message(
            chat_id=chat_id,
            text=(
                "👋 وعليكم السلام ورحمة الله\n"
                "من فضلك اكتب اسم مدينتك بهذا الشكل:\n"
                "Cairo, Egypt أو Doha, Qatar أو Tripoli, Lebanon"
            ),
        )
        return

    # إذا لم تكن هناك مدينة محفوظة بعد، نعتبر هذه الرسالة اسم المدينة
    if chat_id not in user_locations:
        city = text
        country = ""

        # لو كتب مدينة + بلد مع فاصلة
        if "," in text:
            parts = [p.strip() for p in text.split(",", 1)]
            city = parts[0]
            if len(parts) > 1:
                country = parts[1]

        timings = get_prayer_times(city, country)
        if timings is None:
            context.bot.send_message(
                chat_id=chat_id,
                text=(
                    "❌ لم أستطع الحصول على مواقيت الصلاة لهذه المدينة.\n"
                    "جرّب كتابة المدينة والبلد بالإنجليزي، مثال:\n"
                    "Tripoli, Lebanon أو Riyadh, Saudi Arabia"
                ),
            )
            return

        # نحفظ المدينة للمستخدم
        user_locations[chat_id] = {"city": city, "country": country}
        msg = format_prayer_message(city, country, timings)
        context.bot.send_message(chat_id=chat_id, text=msg)
        return

    # هنا المستخدم لديه مدينة محفوظة مسبقًا -> نعطيه المواقيت فورًا
    location = user_locations[chat_id]
    city = location["city"]
    country = location["country"]

    timings = get_prayer_times(city, country)
    if timings is None:
        context.bot.send_message(
            chat_id=chat_id,
            text="❌ حدث خطأ في الاتصال بخدمة مواقيت الصلاة. حاول لاحقًا.",
        )
        return

    msg = format_prayer_message(city, country, timings)
    context.bot.send_message(chat_id=chat_id, text=msg)


# ==============================
# تشغيل البوت
# ==============================

def main():
    if not TELEGRAM_TOKEN or TELEGRAM_TOKEN == "PUT_LOCAL_TOKEN_HERE":
        logger.warning(
            "لم يتم ضبط TELEGRAM_TOKEN بشكل صحيح.\n"
            "ضع التوكن يدويًا في الكود أو في متغيّر البيئة TELEGRAM_TOKEN."
        )

    updater = Updater(TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher

    # أوامر
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("change", change_city))

    # أي رسالة نصية عادية
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    # بدء البوت
    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
