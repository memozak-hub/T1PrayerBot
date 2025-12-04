import os
import requests
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram import ReplyKeyboardMarkup
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

TOKEN = os.getenv("TELEGRAM_TOKEN", "PUT_LOCAL_TOKEN_HERE")

# =====================================================
# بيانات الدول والمدن (عرض بالعربي + أسماء API بالإنجليزي)
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
}

# =====================================================
# تخزين المستخدمين + حالة اختيار الدولة/المدينة
# =====================================================
users = {}       # chat_id -> {"city_api", "country_api", "city", "country"}
user_states = {} # chat_id -> {"step": "country"|"city", "country_name": "لبنان"}

# =====================================================
# كيبوردات
# =====================================================
def main_keyboard():
    return ReplyKeyboardMarkup(
        [["🕌 مواقيت اليوم", "🧭 تغيير المدينة"]],
        resize_keyboard=True
    )


def countries_keyboard():
    # نقسم الدول على صفوف
    names = list(ARAB_COUNTRIES.keys())
    rows = []
    row = []
    for name in names:
        row.append(name)
        if len(row) == 3:
            rows.append(row)
            row = []
    if row:
        rows.append(row)

    rows.append(["✏️ مدينة غير موجودة في القائمة", "⬅️ رجوع"])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def cities_keyboard(country_name):
    data = ARAB_COUNTRIES[country_name]["cities"]
    names = list(data.keys())
    rows = []
    row = []
    for name in names:
        row.append(name)
        if len(row) == 3:
            rows.append(row)
            row = []
    if row:
        rows.append(row)

    rows.append(["✏️ مدينة غير موجودة في القائمة", "⬅️ رجوع للدول"])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)

# =====================================================
# API مواقيت الصلاة
# =====================================================
def get_prayer(api_city, api_country=""):
    url = "https://api.aladhan.com/v1/timingsByCity"
    params = {"city": api_city, "country": api_country, "method": 4}
    try:
        r = requests.get(url, params=params, timeout=10)
        data = r.json()
        if data["code"] != 200:
            return None
        return data["data"]["timings"]
    except:
        return None


def format_prayer(display_city, display_country, t):
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
# أوامر
# =====================================================
def start(update, context):
    chat = update.effective_chat.id
    context.bot.send_message(
        chat_id=chat,
        text=(
            "وعليكم السلام ورحمة الله وبركاته 🤍\n\n"
            "أرسل اسم مدينتك مباشرة مثل:\n"
            "Doha, Qatar\n\n"
            "أو اضغط زر 🧭 تغيير المدينة ثم اختر الدولة والمدينة من القوائم."
        ),
        reply_markup=main_keyboard(),
    )


def change(update, context):
    """حذف المدينة وبدء اختيار جديد"""
    chat = update.effective_chat.id
    users.pop(chat, None)
    user_states[chat] = {"step": "country"}
    context.bot.send_message(
        chat_id=chat,
        text="اختر الدولة من القائمة التالية 👇",
        reply_markup=countries_keyboard(),
    )

# =====================================================
# هاندلر الرسائل
# =====================================================
def handle(update, context):
    chat = update.effective_chat.id
    text = (update.message.text or "").strip()

    lower = text.lower()
    greetings = ["السلام", "سلام", "مرحبا", "اهلا", "أهلا", "hi", "hello", "هلا", "صباح", "مساء"]

    # زر تغيير المدينة أو كلمة "غير"
    if text in ["🧭 تغيير المدينة", "غير", "تغيير"]:
        change(update, context)
        return

    # زر مواقيت اليوم
    if text == "🕌 مواقيت اليوم":
        if chat not in users:
            context.bot.send_message(
                chat_id=chat,
                text="لم يتم حفظ مدينة بعد.\nاضغط 🧭 تغيير المدينة أو أرسل المدينة هكذا: Tripoli, Lebanon",
                reply_markup=main_keyboard(),
            )
            return

        loc = users[chat]
        t = get_prayer(loc["city_api"], loc["country_api"])
        if not t:
            context.bot.send_message(chat_id=chat, text="❌ حدث خطأ في جلب المواقيت.", reply_markup=main_keyboard())
            return

        msg = format_prayer(loc["city"], loc["country"], t)
        context.bot.send_message(chat_id=chat, text=msg, reply_markup=main_keyboard())
        return

    # إذا المستخدم داخل وضع اختيار دولة/مدينة
    if chat in user_states:
        state = user_states[chat]

        # رجوع عام
        if text in ["⬅️ رجوع", "⬅️ رجوع للدول"]:
            user_states.pop(chat, None)
            context.bot.send_message(
                chat_id=chat,
                text="تم الإلغاء.\nيمكنك الضغط على 🧭 تغيير المدينة من جديد.",
                reply_markup=main_keyboard(),
            )
            return

        # خيار مدينة غير موجودة
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

                t = get_prayer(api_city, api_country)
                if not t:
                    context.bot.send_message(
                        chat_id=chat,
                        text="لم أستطع جلب المواقيت لهذه المدينة، جرّب مدينة أخرى أو الإدخال اليدوي.",
                        reply_markup=cities_keyboard(country_name),
                    )
                    return

                users[chat] = {
                    "city_api": api_city,
                    "country_api": api_country,
                    "city": text,              # عرض بالعربي
                    "country": country_name,   # عرض بالعربي
                }

                user_states.pop(chat, None)

                msg = format_prayer(text, country_name, t)
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

    # لو ليس في حالة اختيار دولة/مدينة:
    # تحية بدون مدينة محفوظة
    if chat not in users and any(g in lower for g in greetings):
        start(update, context)
        return

    # إدخال مدينة يدوي (City, Country)
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
                text=(
                    "❌ لم أتمكن من التعرف على هذه المدينة.\n"
                    "اكتب مثالاً مثل: Tripoli, Lebanon أو استخدم زر 🧭 تغيير المدينة لاختيار من القوائم."
                ),
                reply_markup=main_keyboard(),
            )
            return

        users[chat] = {
            "city_api": city,
            "country_api": country,
            "city": city,
            "country": country,
        }

        msg = format_prayer(city, country, t)
        context.bot.send_message(chat_id=chat, text=msg, reply_markup=main_keyboard())
        return

    # لو عنده مدينة محفوظة وأرسل أي نص آخر → أعطه المواقيت الحالية
    loc = users[chat]
    t = get_prayer(loc["city_api"], loc["country_api"])
    if not t:
        context.bot.send_message(chat_id=chat, text="❌ حدث خطأ في جلب المواقيت.", reply_markup=main_keyboard())
        return

    msg = format_prayer(loc["city"], loc["country"], t)
    context.bot.send_message(chat_id=chat, text=msg, reply_markup=main_keyboard())

# =====================================================
# سيرفر HTTP بسيط علشان Render
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
# MAIN
# =====================================================
def main():
    # تشغيل سيرفر HTTP في خلفية
    threading.Thread(target=run_http_server, daemon=True).start()

    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("change", change))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
