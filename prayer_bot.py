import os
import logging
from datetime import datetime

import requests
from telegram import (
    Bot,
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Updater,
    CallbackContext,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    Filters,
)

# ============ الإعدادات العامة ============

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise RuntimeError(
        "Environment variable TELEGRAM_TOKEN is missing. "
        "Please set it in Render."
    )

# عنوان الخدمة على Render (يفضل وضعه في متغير بيئة BASE_URL)
DEFAULT_BASE_URL = "https://t1prayerbot.onrender.com"

# ============ بيانات الدول والمدن ============

# مفتاح المعجم هو كود الدولة (اختيار داخلي لنا)
COUNTRIES = {
    "LB": {
        "name_ar": "لبنان",
        "api_country": "Lebanon",
        "cities": {
            "beirut": {"name_ar": "بيروت", "api_city": "Beirut"},
            "tripoli": {"name_ar": "طرابلس", "api_city": "Tripoli"},
            "saida": {"name_ar": "صيدا", "api_city": "Sidon"},
        },
    },
    "SY": {
        "name_ar": "سوريا",
        "api_country": "Syria",
        "cities": {
            "damascus": {"name_ar": "دمشق", "api_city": "Damascus"},
            "aleppo": {"name_ar": "حلب", "api_city": "Aleppo"},
        },
    },
    "JO": {
        "name_ar": "الأردن",
        "api_country": "Jordan",
        "cities": {
            "amman": {"name_ar": "عمّان", "api_city": "Amman"},
            "irbid": {"name_ar": "إربد", "api_city": "Irbid"},
        },
    },
    "SA": {
        "name_ar": "السعودية",
        "api_country": "Saudi Arabia",
        "cities": {
            "riyadh": {"name_ar": "الرياض", "api_city": "Riyadh"},
            "jeddah": {"name_ar": "جدّة", "api_city": "Jeddah"},
            "makkah": {"name_ar": "مكة", "api_city": "Makkah"},
            "madinah": {"name_ar": "المدينة المنوّرة", "api_city": "Medina"},
        },
    },
    "QA": {
        "name_ar": "قطر",
        "api_country": "Qatar",
        "cities": {
            "doha": {"name_ar": "الدوحة", "api_city": "Doha"},
        },
    },
    "AE": {
        "name_ar": "الإمارات",
        "api_country": "United Arab Emirates",
        "cities": {
            "dubai": {"name_ar": "دبي", "api_city": "Dubai"},
            "abudhabi": {"name_ar": "أبوظبي", "api_city": "Abu Dhabi"},
        },
    },
    "KW": {
        "name_ar": "الكويت",
        "api_country": "Kuwait",
        "cities": {
            "kuwaitcity": {"name_ar": "مدينة الكويت", "api_city": "Kuwait City"},
        },
    },
    "BH": {
        "name_ar": "البحرين",
        "api_country": "Bahrain",
        "cities": {
            "manama": {"name_ar": "المنامة", "api_city": "Manama"},
        },
    },
    "OM": {
        "name_ar": "عُمان",
        "api_country": "Oman",
        "cities": {
            "muscat": {"name_ar": "مسقط", "api_city": "Muscat"},
        },
    },
    "YE": {
        "name_ar": "اليمن",
        "api_country": "Yemen",
        "cities": {
            "sanaa": {"name_ar": "صنعاء", "api_city": "Sanaa"},
            "aden": {"name_ar": "عدن", "api_city": "Aden"},
        },
    },
    "EG": {
        "name_ar": "مصر",
        "api_country": "Egypt",
        "cities": {
            "cairo": {"name_ar": "القاهرة", "api_city": "Cairo"},
            "alexandria": {"name_ar": "الإسكندرية", "api_city": "Alexandria"},
        },
    },
    "PS": {
        "name_ar": "فلسطين",
        "api_country": "Palestine",
        "cities": {
            "gaza": {"name_ar": "غزة", "api_city": "Gaza"},
            "jerusalem": {"name_ar": "القدس", "api_city": "Jerusalem"},
        },
    },
    "IQ": {
        "name_ar": "العراق",
        "api_country": "Iraq",
        "cities": {
            "baghdad": {"name_ar": "بغداد", "api_city": "Baghdad"},
            "basra": {"name_ar": "البصرة", "api_city": "Basrah"},
        },
    },
    "SD": {
        "name_ar": "السودان",
        "api_country": "Sudan",
        "cities": {
            "khartoum": {"name_ar": "الخرطوم", "api_city": "Khartoum"},
        },
    },
    "MA": {
        "name_ar": "المغرب",
        "api_country": "Morocco",
        "cities": {
            "rabat": {"name_ar": "الرباط", "api_city": "Rabat"},
            "casablanca": {"name_ar": "الدار البيضاء", "api_city": "Casablanca"},
        },
    },
    "DZ": {
        "name_ar": "الجزائر",
        "api_country": "Algeria",
        "cities": {
            "algiers": {"name_ar": "الجزائر العاصمة", "api_city": "Algiers"},
            "oran": {"name_ar": "وهران", "api_city": "Oran"},
        },
    },
    "TN": {
        "name_ar": "تونس",
        "api_country": "Tunisia",
        "cities": {
            "tunis": {"name_ar": "تونس", "api_city": "Tunis"},
        },
    },
    "LY": {
        "name_ar": "ليبيا",
        "api_country": "Libya",
        "cities": {
            "tripolily": {"name_ar": "طرابلس", "api_city": "Tripoli"},
        },
    },
}

# تخزين تفضيلات المستخدمين في الذاكرة (يُمسح عند إعادة التشغيل، لكنه يكفي الآن)
USER_PREFS = {}  # user_id -> dict(country_code, city_key)


# ============ دوال مساعدة ============

def build_countries_keyboard():
    """لوحة اختيار الدول بشكل مربعات جميلة."""
    buttons = []
    row = []
    for code, info in COUNTRIES.items():
        row.append(
            InlineKeyboardButton(
                info["name_ar"], callback_data=f"country|{code}"
            )
        )
        # كل صف فيه 3 أزرار
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    # زر "دولة / مدينة غير موجودة"
    buttons.append(
        [InlineKeyboardButton("🌍 دولة/مدينة غير موجودة", callback_data="manual_location")]
    )

    return InlineKeyboardMarkup(buttons)


def build_cities_keyboard(country_code: str):
    """لوحة اختيار المدن داخل دولة معينة."""
    country = COUNTRIES[country_code]
    cities = country["cities"]
    buttons = []
    row = []
    for key, info in cities.items():
        row.append(
            InlineKeyboardButton(
                info["name_ar"], callback_data=f"city|{country_code}|{key}"
            )
        )
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    buttons.append(
        [InlineKeyboardButton("🏙 مدينة غير موجودة", callback_data=f"manual_city|{country_code}")]
    )

    buttons.append(
        [InlineKeyboardButton("⬅️ رجوع لاختيار دولة أخرى", callback_data="back_to_countries")]
    )

    return InlineKeyboardMarkup(buttons)


def fetch_prayer_times(city: str, country: str):
    """جلب مواقيت الصلاة من API موقع AlAdhan."""
    url = "https://api.aladhan.com/v1/timingsByCity"
    params = {
        "city": city,
        "country": country,
        "method": 2,  # أم القرى تقريباً
        "school": 0,
        "iso8601": True,
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        if data.get("code") != 200:
            return None
        timings = data["data"]["timings"]
        date_info = data["data"]["date"]["gregorian"]
        readable_date = f"{date_info['day']}-{date_info['month']['number']}-{date_info['year']}"
        return timings, readable_date
    except Exception as e:
        logger.error("Error fetching prayer times: %s", e)
        return None


def format_prayer_message(city_ar: str, country_ar: str, timings, date_str: str):
    """تنسيق رسالة مواقيت الصلاة بشكل جميل."""
    fajr = timings["Fajr"]
    dhuhr = timings["Dhuhr"]
    asr = timings["Asr"]
    maghrib = timings["Maghrib"]
    isha = timings["Isha"]

    message = (
        f"🕌 مواقيت الصلاة اليوم في {city_ar} - {country_ar}\n"
        f"📅 التاريخ: {date_str}\n\n"
        f"🌅 الفجر : {fajr}\n"
        f"☀️ الظهر : {dhuhr}\n"
        f"🌇 العصر : {asr}\n"
        f"🌆 المغرب : {maghrib}\n"
        f"🌙 العشاء : {isha}\n"
    )
    return message


# ============ Handlers ============

def start(update: Update, context: CallbackContext):
    """معالجة أمر /start أو أول رسالة."""
    user = update.effective_user
    text = (
        f"وعليكم السلام ورحمة الله وبركاته يا {user.first_name or 'أخي الكريم'} 🌹\n\n"
        "أنا بوت مواقيت الصلاة.\n"
        "اختر الدولة أولاً من الأزرار التالية:"
    )
    keyboard = build_countries_keyboard()
    if update.message:
        update.message.reply_text(text, reply_markup=keyboard)
    else:
        # في حال نادى /start من زر
        update.callback_query.message.reply_text(text, reply_markup=keyboard)


def ask_for_country(update: Update, context: CallbackContext):
    """إرسال لوحة الدول فقط."""
    keyboard = build_countries_keyboard()
    text = "اختر الدولة من الأزرار التالية:"
    if update.message:
        update.message.reply_text(text, reply_markup=keyboard)
    else:
        update.callback_query.message.reply_text(text, reply_markup=keyboard)


def handle_text(update: Update, context: CallbackContext):
    """أي رسالة نصية عادية من المستخدم."""
    user_id = update.effective_user.id
    text = (update.message.text or "").strip()

    # لو كان ينتظر إدخال يدوي للدولة والمدينة
    if context.user_data.get("awaiting_manual_location"):
        handle_manual_location(update, context)
        return

    # تحيات / طلب تغيير مدينة
    norm = text.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").lower()
    if (
        "سلام" in norm
        or text == "/start"
        or "hi" in norm
        or "hello" in norm
    ):
        start(update, context)
        return

    if "تغيير" in norm and "مدين" in norm:
        ask_for_country(update, context)
        return

    # إن كان له مدينة محفوظة، اعرض المواقيت مباشرة
    prefs = USER_PREFS.get(user_id)
    if prefs:
        country_code = prefs["country_code"]
        city_key = prefs["city_key"]
        country = COUNTRIES.get(country_code)
        if country:
            city_info = country["cities"][city_key]
            timings_data = fetch_prayer_times(
                city_info["api_city"], country["api_country"]
            )
            if timings_data:
                timings, date_str = timings_data
                msg = format_prayer_message(
                    city_info["name_ar"],
                    country["name_ar"],
                    timings,
                    date_str,
                )
                update.message.reply_text(msg)
                return

    # لو لم يكن عنده مدينة محفوظة
    update.message.reply_text(
        "أهلاً بك 🌹\nاختر الدولة من الأزرار أو اكتب: تغيير المدينة",
        reply_markup=build_countries_keyboard(),
    )


def handle_callback(update: Update, context: CallbackContext):
    """معالجة ضغط الأزرار (InlineKeyboard)."""
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id

    query.answer()

    if data.startswith("country|"):
        # اختيار دولة → نعرض المدن
        country_code = data.split("|", 1)[1]
        country = COUNTRIES.get(country_code)
        if not country:
            query.edit_message_text("حدث خطأ في اختيار الدولة، جرّب مرة أخرى.")
            return

        keyboard = build_cities_keyboard(country_code)
        query.edit_message_text(
            text=f"اختر المدينة داخل {country['name_ar']}:",
            reply_markup=keyboard,
        )

    elif data.startswith("city|"):
        # اختيار مدينة → جلب المواقيت وحفظ التفضيل
        _, country_code, city_key = data.split("|")
        country = COUNTRIES.get(country_code)
        if not country:
            query.edit_message_text("حدث خطأ في اختيار الدولة، جرّب مرة أخرى.")
            return
        city_info = country["cities"].get(city_key)
        if not city_info:
            query.edit_message_text("حدث خطأ في اختيار المدينة، جرّب مرة أخرى.")
            return

        timings_data = fetch_prayer_times(
            city_info["api_city"], country["api_country"]
        )
        if not timings_data:
            query.edit_message_text(
                "تعذر الحصول على مواقيت الصلاة حالياً، حاول بعد قليل."
            )
            return

        timings, date_str = timings_data
        msg = format_prayer_message(
            city_info["name_ar"], country["name_ar"], timings, date_str
        )

        # حفظ التفضيل
        USER_PREFS[user_id] = {
            "country_code": country_code,
            "city_key": city_key,
        }

        msg += "\n🔁 لاختيار مدينة أخرى أرسل: تغيير المدينة"

        query.edit_message_text(msg)

    elif data == "manual_location":
        # يختار دولة/مدينة غير موجودة
        context.user_data["awaiting_manual_location"] = True
        query.edit_message_text(
            "حسناً 👌\n"
            "أرسل لي اسم الدولة والمدينة بهذا الشكل:\n"
            "مثال: `Lebanon - Tripoli`\n"
            "أو: `Saudi Arabia - Riyadh`\n"
            "ويفضّل أن تكون بالأحرف الإنجليزية.\n",
            parse_mode="Markdown",
        )

    elif data.startswith("manual_city|"):
        # مدينة غير موجودة لكن الدولة معروفة
        country_code = data.split("|", 1)[1]
        country = COUNTRIES.get(country_code)
        context.user_data["awaiting_manual_location"] = True
        context.user_data["manual_country_fixed"] = country_code

        query.edit_message_text(
            f"اكتب اسم المدينة داخل {country['name_ar']} (بالإنجليزية لو أمكن)، "
            "مثال: Riyadh\n"
            "وسأحاول جلب المواقيت لها.",
        )

    elif data == "back_to_countries":
        keyboard = build_countries_keyboard()
        query.edit_message_text(
            "اختر الدولة من جديد:", reply_markup=keyboard
        )


def handle_manual_location(update: Update, context: CallbackContext):
    """استقبال إدخال يدوي للدولة والمدينة."""
    text = (update.message.text or "").strip()
    user_id = update.effective_user.id

    fixed_country_code = context.user_data.get("manual_country_fixed")
    if fixed_country_code:
        # الدولة ثابتة، المستخدم يرسل فقط اسم المدينة
        country = COUNTRIES.get(fixed_country_code)
        api_country = country["api_country"]
        country_ar = country["name_ar"]
        city_input = text
    else:
        # نتوقع: COUNTRY - CITY
        if "-" in text:
            parts = text.split("-", 1)
        elif "—" in text:
            parts = text.split("—", 1)
        else:
            update.message.reply_text(
                "الرجاء إرسال الدولة والمدينة بهذا الشكل:\n"
                "`Saudi Arabia - Riyadh`",
                parse_mode="Markdown",
            )
            return

        api_country = parts[0].strip()
        city_input = parts[1].strip()
        country_ar = api_country  # ما عندنا ترجمة عربية هنا

    timings_data = fetch_prayer_times(city_input, api_country)
    if not timings_data:
        update.message.reply_text(
            "لم أستطع العثور على مواقيت لهذه المدينة، تأكد من الكتابة بالأحرف الإنجليزية "
            "أو جرّب مدينة أخرى."
        )
        return

    timings, date_str = timings_data
    msg = format_prayer_message(city_input, country_ar, timings, date_str)
    msg += "\n\n🔁 لاختيار مدينة أخرى أرسل: تغيير المدينة"
    update.message.reply_text(msg)

    # حفظ تفضيل بسيط (لن يكون مرتبطاً بواحدة من الدول المعرفة لدينا)
    USER_PREFS[user_id] = {
        "country_code": fixed_country_code or "",
        "city_key": "",
        "manual_city": city_input,
        "manual_country": api_country,
    }

    # مسح حالة الإدخال اليدوي
    context.user_data["awaiting_manual_location"] = False
    context.user_data.pop("manual_country_fixed", None)


# ============ تشغيل البوت بالـ Webhook ============

def main():
    updater = Updater(TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher

    # Handlers
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CallbackQueryHandler(handle_callback))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))

    # إعداد الـ webhook
    port = int(os.environ.get("PORT", 8443))
    base_url = os.environ.get("BASE_URL", DEFAULT_BASE_URL)

    logger.info("Starting webhook on port %s", port)

    updater.start_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=TELEGRAM_TOKEN,
    )

    webhook_url = f"{base_url}/{TELEGRAM_TOKEN}"
    bot: Bot = updater.bot
    bot.set_webhook(webhook_url)

    logger.info("Webhook set to %s", webhook_url)

    updater.idle()


if __name__ == "__main__":
    main()
