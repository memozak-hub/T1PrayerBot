import os
import requests
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram import ReplyKeyboardMarkup, KeyboardButton

# =====================================================
#  إعداد التوكن من المتغير البيئي
# =====================================================
TOKEN = os.getenv("TELEGRAM_TOKEN", "PUT_LOCAL_TOKEN_HERE")

# =====================================================
#  قائمة الدول والمدن العربية
# =====================================================
ARAB_COUNTRIES = {
    "لبنان": {
        "api_country": "Lebanon",
        "cities": {
            "طرابلس": "Tripoli",
            "بيروت": "Beirut",
            "صيدا": "Sidon",
        },
    },
    "سوريا": {
        "api_country": "Syria",
        "cities": {
            "دمشق": "Damascus",
            "حلب": "Aleppo",
            "حمص": "Homs",
        },
    },
    "الأردن": {
        "api_country": "Jordan",
        "cities": {
            "عمان": "Amman",
            "إربد": "Irbid",
            "الزرقاء": "Zarqa",
        },
    },
    "السعودية": {
        "api_country": "Saudi Arabia",
        "cities": {
            "الرياض": "Riyadh",
            "جدة": "Jeddah",
            "مكة": "Mecca",
        },
    },
    "مصر": {
        "api_country": "Egypt",
        "cities": {
            "القاهرة": "Cairo",
            "الإسكندرية": "Alexandria",
            "الجيزة": "Giza",
        },
    },
    "قطر": {
        "api_country": "Qatar",
        "cities": {
            "الدوحة": "Doha",
        },
    },
    "الإمارات": {
        "api_country": "United Arab Emirates",
        "cities": {
            "دبي": "Dubai",
            "أبو ظبي": "Abu Dhabi",
            "الشارقة": "Sharjah",
        },
    },
    "فلسطين": {
        "api_country": "Palestine",
        "cities": {
            "القدس": "Jerusalem",
            "غزة": "Gaza",
            "الخليل": "Hebron",
        },
    },
    "المغرب": {
        "api_country": "Morocco",
        "cities": {
            "الرباط": "Rabat",
            "الدار البيضاء": "Casablanca",
            "مراكش": "Marrakesh",
            "فاس": "Fes",
            "طنجة": "Tangier",
        },
    },
    "الجزائر": {
        "api_country": "Algeria",
        "cities": {
            "الجزائر العاصمة": "Algiers",
            "وهران": "Oran",
            "قسنطينة": "Constantine",
            "سطيف": "Setif",
            "عنابة": "Annaba",
        },
    },
}

# =====================================================
#  تخزين بيانات المستخدمين
# =====================================================
# users: chat_id -> {
#   city_api, country_api, city, country, notify(bool)
# }
users = {}

# user_states: حالة اختيار الدولة/المدينة من القوائم
# chat_id -> {"step": "country"|"city", "country_name": "لبنان"}
user_states = {}

# notify_jobs: وظائف التنبيهات لكل مستخدم
# chat_id -> [job1, job2, ...]
notify_jobs = {}

# =====================================================
#  Scheduler لتنبيهات الأذان
# =====================================================
scheduler = BackgroundScheduler(timezone=pytz.utc)
scheduler.start()

# =====================================================
#  الكيبوردات
# =====================================================
def main_keyboard():
    return ReplyKeyboardMarkup(
        [
            ["🕌 مواقيت اليوم", "🧭 تغيير المدينة"],
            [KeyboardButton("📍 إرسال موقعي", request_location=True), "🔔 تنبيهات الأذان"],
        ],
        resize_keyboard=True,
    )


def countries_keyboard():
    names = list(ARAB_COUNTRIES.keys())
    rows = []
    for i in range(0, len(names), 3):
        rows.append(names[i:i + 3])

    rows.append(["✏️ مدينة غير موجودة في القائمة"])
    rows.append(["⬅️ رجوع"])

    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def cities_keyboard(country_name: str):
    cities = list(ARAB_COUNTRIES[country_name]["cities"].keys())
    rows = []
    for i in range(0, len(cities), 3):
        rows.append(cities[i:i + 3])

    rows.append(["✏️ مدينة غير موجودة في القائمة"])
    rows.append(["⬅️ رجوع للدول"])

    return ReplyKeyboardMarkup(rows, resize_keyboard=True)

# =====================================================
#  دوال API مواقيت الصلاة (Aladhan)
# =====================================================
def get_prayer_full(api_city: str, api_country: str = ""):
    """ترجع: (timings, timezone_name, raw_data) أو (None, None, None) عند الفشل."""
    url = "https://api.aladhan.com/v1/timingsByCity"
    params = {"city": api_city, "country": api_country, "method": 4}
    try:
        r = requests.get(url, params=params, timeout=10)
        data = r.json()
        if data.get("code") != 200:
            return None, None, None
        timings = data["data"]["timings"]
        tz = data["data"]["meta"]["timezone"]
        return timings, tz, data
    except Exception as e:
        print("get_prayer_full error:", e)
        return None, None, None


def get_prayer(api_city: str, api_country: str = ""):
    timings, _, _ = get_prayer_full(api_city, api_country)
    return timings


def format_prayer(display_city: str, display_country: str, t: dict) -> str:
    loc = display_city if not display_country else f"{display_city}, {display_country}"
    return (
        f"🕌 مواقيت الصلاة اليوم في {loc}\n\n"
        f"الفجر: {t['Fajr']}\n"
        f"الظهر: {t['Dhuhr']}\n"
        f"العصر: {t['Asr']}\n"
        f"المغرب: {t['Maghrib']}\n"
        f"العشاء: {t['Isha']}"
    )

# =====================================================
#  تنبيهات الأذان
# =====================================================
def send_adhan(bot, chat_id, city, country, prayer_name, time_str):
    loc = city if not country else f"{city}, {country}"
    text = f"🔔 حان الآن وقت صلاة {prayer_name} في {loc}\n⏰ ({time_str})"
    try:
        bot.send_message(chat_id=chat_id, text=text)
    except Exception as e:
        print("send_adhan error:", e)


def clear_notifications(chat_id):
    jobs = notify_jobs.get(chat_id, [])
    for job in jobs:
        try:
            job.remove()
        except Exception:
            pass
    notify_jobs[chat_id] = []


def schedule_notifications(chat_id, context):
    """تفعيل تنبيهات الأذان لهذا المستخدم (يوميًا حسب توقيت المدينة)."""
    loc = users.get(chat_id)
    if not loc:
        return

    timings, tzname, _ = get_prayer_full(loc["city_api"], loc["country_api"])
    if not timings or not tzname:
        return

    tz = pytz.timezone(tzname)
    prayers = [
        ("Fajr", "الفجر"),
        ("Dhuhr", "الظهر"),
        ("Asr", "العصر"),
        ("Maghrib", "المغرب"),
        ("Isha", "العشاء"),
    ]

    clear_notifications(chat_id)

    jobs = []
    for key, name in prayers:
        hh, mm = map(int, timings[key].split(":")[:2])
        job = scheduler.add_job(
            send_adhan,
            "cron",
            hour=hh,
            minute=mm,
            timezone=tz,
            args=[context.bot, chat_id, loc["city"], loc["country"], name, timings[key]],
        )
        jobs.append(job)

    notify_jobs[chat_id] = jobs

# =====================================================
#  أوامر البوت
# =====================================================
def start(update, context):
    chat = update.effective_chat.id
    context.bot.send_message(
        chat_id=chat,
        text=(
            "وعليكم السلام ورحمة الله وبركاته 🤍\n\n"
            "أرسل اسم مدينتك مثل:\n"
            "Doha, Qatar\n\n"
            "أو اضغط 🧭 تغيير المدينة لاختيار الدولة والمدينة من القوائم.\n"
            "يمكنك أيضًا الضغط على 📍 إرسال موقعي ليتم تحديد المدينة تلقائيًا.\n"
            "وزر 🔔 تنبيهات الأذان لتفعيل الإشعارات لكل صلاة."
        ),
        reply_markup=main_keyboard(),
    )


def change(update, context):
    """حذف المدينة وبدء اختيار جديد من القوائم."""
    chat = update.effective_chat.id
    users.pop(chat, None)
    clear_notifications(chat)
    user_states[chat] = {"step": "country"}

    context.bot.send_message(
        chat_id=chat,
        text="اختر الدولة من القائمة التالية 👇",
        reply_markup=countries_keyboard(),
    )

# =====================================================
#  تحديد الموقع من GPS
# =====================================================
def handle_location(update, context):
    chat = update.effective_chat.id
    loc = update.message.location
    lat, lon = loc.latitude, loc.longitude

    try:
        r = requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={
                "format": "json",
                "lat": lat,
                "lon": lon,
                "zoom": 10,
                "addressdetails": 1,
                "accept-language": "en",
            },
            headers={"User-Agent": "T1PrayerBot/1.0"},
            timeout=10,
        )
        data = r.json()
        addr = data.get("address", {})
        city = addr.get("city") or addr.get("town") or addr.get("village")
        country = addr.get("country")
    except Exception as e:
        print("geo error:", e)
        city = country = None

    if not city or not country:
        context.bot.send_message(
            chat_id=chat,
            text="❌ لم أستطع تحديد مدينتك بدقة. من فضلك اكتبها يدويًا مثل: Tripoli, Lebanon",
            reply_markup=main_keyboard(),
        )
        return

    timings = get_prayer(city, country)
    if not timings:
        context.bot.send_message(
            chat_id=chat,
            text=f"لم أتمكن من جلب مواقيت الصلاة لـ {city}, {country}. جرّب الإدخال اليدوي.",
            reply_markup=main_keyboard(),
        )
        return

    clear_notifications(chat)
    users[chat] = {
        "city_api": city,
        "country_api": country,
        "city": city,
        "country": country,
        "notify": False,
    }

    msg = format_prayer(city, country, timings)
    context.bot.send_message(
        chat_id=chat,
        text=f"✅ تم حفظ موقعك: {city}, {country}\n\n{msg}",
        reply_markup=main_keyboard(),
    )

# =====================================================
#  هاندلر الرسائل النصية
# =====================================================
def handle(update, context):
    chat = update.effective_chat.id
    text = (update.message.text or "").strip()

    lower = text.lower()
    greetings = ["السلام", "سلام", "مرحبا", "مرحبى", "اهلا", "أهلا", "hi", "hello", "هلا", "صباح", "مساء"]

    # تغيير المدينة
    if text in ["🧭 تغيير المدينة", "غير", "تغيير"]:
        change(update, context)
        return

    # تنبيهات الأذان
    if text == "🔔 تنبيهات الأذان":
        if chat not in users:
            context.bot.send_message(
                chat_id=chat,
                text="أولاً اختر مدينة: أرسل اسمها مثل Tripoli, Lebanon أو استخدم 🧭 تغيير المدينة أو 📍 إرسال موقعي.",
                reply_markup=main_keyboard(),
            )
            return

        user = users[chat]
        if not user.get("notify"):
            user["notify"] = True
            schedule_notifications(chat, context)
            context.bot.send_message(
                chat_id=chat,
                text="✅ تم تفعيل تنبيهات الأذان لهذه المدينة.\n(التنبيهات تعمل ما دام البوت مستيقظًا على Render).",
                reply_markup=main_keyboard(),
            )
        else:
            user["notify"] = False
            clear_notifications(chat)
            context.bot.send_message(
                chat_id=chat,
                text="🔕 تم إيقاف تنبيهات الأذان.",
                reply_markup=main_keyboard(),
            )
        return

    # مواقيت اليوم
    if text == "🕌 مواقيت اليوم":
        if chat not in users:
            context.bot.send_message(
                chat_id=chat,
                text="لم يتم حفظ مدينة بعد.\nاضغط 🧭 تغيير المدينة أو أرسل المدينة هكذا: Tripoli, Lebanon",
                reply_markup=main_keyboard(),
            )
            return

        loc = users[chat]
        timings = get_prayer(loc["city_api"], loc["country_api"])
        if not timings:
            context.bot.send_message(
                chat_id=chat,
                text="❌ حدث خطأ في جلب المواقيت.",
                reply_markup=main_keyboard(),
            )
            return

        msg = format_prayer(loc["city"], loc["country"], timings)
        context.bot.send_message(chat_id=chat, text=msg, reply_markup=main_keyboard())
        return

    # لو المستخدم داخل حالة اختيار دولة/مدينة
    if chat in user_states:
        state = user_states[chat]

        if text in ["⬅️ رجوع", "⬅️ رجوع للدول"]:
            user_states.pop(chat, None)
            context.bot.send_message(
                chat_id=chat,
                text="تم الإلغاء.\nيمكنك الضغط على 🧭 تغيير المدينة من جديد.",
                reply_markup=main_keyboard(),
            )
            return

        if text == "✏️ مدينة غير موجودة في القائمة":
            user_states.pop(chat, None)
            context.bot.send_message(
                chat_id=chat,
                text=(
                    "اكتب المدينة والدولة بالصورة التالية:\n"
                    "City, Country\n"
                    "مثال: Tripoli, Lebanon أو Amman, Jordan"
                ),
                reply_markup=main_keyboard(),
            )
            return

        # خطوة اختيار الدولة
        if state["step"] == "country":
            if text in ARAB_COUNTRIES:
                state["step"] = "city"
                state["country_name"] = text
                context.bot.send_message(
                    chat_id=chat,
                    text=f"اختر المدينة داخل {text} 👇",
                    reply_markup=cities_keyboard(text),
                )
                return
            else:
                context.bot.send_message(
                    chat_id=chat,
                    text="من فضلك اختر دولة من الأزرار أو اضغط ✏️ مدينة غير موجودة في القائمة.",
                    reply_markup=countries_keyboard(),
                )
                return

        # خطوة اختيار المدينة
        if state["step"] == "city":
            country_name = state.get("country_name")
            country_data = ARAB_COUNTRIES.get(country_name, {})
            cities = country_data.get("cities", {})

            if text in cities:
                api_city = cities[text]
                api_country = country_data["api_country"]

                timings = get_prayer(api_city, api_country)
                if not timings:
                    context.bot.send_message(
                        chat_id=chat,
                        text="لم أستطع جلب المواقيت لهذه المدينة، جرّب مدينة أخرى أو الإدخال اليدوي.",
                        reply_markup=cities_keyboard(country_name),
                    )
                    return

                clear_notifications(chat)
                users[chat] = {
                    "city_api": api_city,
                    "country_api": api_country,
                    "city": text,
                    "country": country_name,
                    "notify": False,
                }

                user_states.pop(chat, None)

                msg = format_prayer(text, country_name, timings)
                context.bot.send_message(
                    chat_id=chat,
                    text=f"✅ تم حفظ المدينة: {text}, {country_name}\n\n{msg}",
                    reply_markup=main_keyboard(),
                )
                return

            else:
                context.bot.send_message(
                    chat_id=chat,
                    text="اختر مدينة من الأزرار أو اضغط ✏️ مدينة غير موجودة في القائمة.",
                    reply_markup=cities_keyboard(country_name),
                )
                return

    # تحية بدون مدينة محفوظة
    if chat not in users and any(g in lower for g in greetings):
        start(update, context)
        return

    # أول مرة يرسل مدينة يدويًا
    if chat not in users:
        city = text
        country = ""

        if "," in text:
            p = [x.strip() for x in text.split(",", 1)]
            city = p[0]
            if len(p) > 1:
                country = p[1]

        timings = get_prayer(city, country)
        if not timings:
            context.bot.send_message(
                chat_id=chat,
                text=(
                    "❌ لم أتمكن من التعرف على هذه المدينة.\n"
                    "اكتب مثالاً مثل: Tripoli, Lebanon أو استخدم زر 🧭 تغيير المدينة "
                    "أو زر 📍 إرسال موقعي."
                ),
                reply_markup=main_keyboard(),
            )
            return

        clear_notifications(chat)
        users[chat] = {
            "city_api": city,
            "country_api": country,
            "city": city,
            "country": country,
            "notify": False,
        }

        msg = format_prayer(city, country, timings)
        context.bot.send_message(chat_id=chat, text=msg, reply_markup=main_keyboard())
        return

    # لديه مدينة محفوظة وأرسل أي شيء آخر → نرجع له مواقيت مدينته
    loc = users[chat]
    timings = get_prayer(loc["city_api"], loc["country_api"])
    if not timings:
        context.bot.send_message(
            chat_id=chat,
            text="❌ حدث خطأ في جلب المواقيت.",
            reply_markup=main_keyboard(),
        )
        return

    msg = format_prayer(loc["city"], loc["country"], timings)
    context.bot.send_message(chat_id=chat, text=msg, reply_markup=main_keyboard())

# =====================================================
#  سيرفر HTTP بسيط لـ Render (port binding)
# =====================================================
def run_http_server():
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Bot is running")

    port = int(os.environ.get("PORT", "8000"))
    server = HTTPServer(("", port), Handler)
    server.serve_forever()

# =====================================================
#  MAIN
# =====================================================
def main():
    # تشغيل سيرفر HTTP في الخلفية (مهم لـ Render)
    threading.Thread(target=run_http_server, daemon=True).start()

    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("change", change))
    dp.add_handler(MessageHandler(Filters.location, handle_location))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle))

    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
