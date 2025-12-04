import os
import logging
from typing import Optional, Dict, Tuple

import requests
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Updater,
    CallbackContext,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackQueryHandler,
)

# ---------------- إعداد اللوج ----------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ---------------- المتغيرات من Environment ----------------
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
BASE_URL = os.environ.get("BASE_URL", "https://t1prayerbot.onrender.com").rstrip("/")
PORT = int(os.environ.get("PORT", "10000"))  # Render يمرّر هذا تلقائيًا

WEBHOOK_PATH = TELEGRAM_TOKEN
WEBHOOK_URL = f"{BASE_URL}/{WEBHOOK_PATH}"  # مهم: بدون :PORT في الرابط

# ---------------- البيانات: الدول والمدن ----------------
ARAB_COUNTRIES = [
    "لبنان",
    "سوريا",
    "الأردن",
    "فلسطين",
    "مصر",
    "السعودية",
    "الإمارات",
    "قطر",
    "الكويت",
    "البحرين",
    "عُمان",
    "العراق",
    "اليمن",
    "السودان",
    "تونس",
    "المغرب",
    "الجزائر",
]

# مدن رئيسية لكل دولة (يمكنك إضافة/تعديل كما تحب)
COUNTRY_CITIES = {
    "لبنان": ["بيروت", "طرابلس", "صيدا", "صور", "غير ذلك"],
    "سوريا": ["دمشق", "حلب", "حمص", "حماة", "غير ذلك"],
    "الأردن": ["عمّان", "إربد", "الزرقاء", "العقبة", "غير ذلك"],
    "فلسطين": ["القدس", "غزة", "الخليل", "نابلس", "غير ذلك"],
    "مصر": ["القاهرة", "الإسكندرية", "الجيزة", "أسيوط", "غير ذلك"],
    "السعودية": ["الرياض", "مكة", "المدينة", "جدة", "غير ذلك"],
    "الإمارات": ["دبي", "أبوظبي", "الشارقة", "عجمان", "غير ذلك"],
    "قطر": ["الدوحة", "الريان", "الوكرة", "الخوير", "غير ذلك"],
    "الكويت": ["مدينة الكويت", "حولي", "الفروانية", "الجهراء", "غير ذلك"],
    "البحرين": ["المنامة", "المحرق", "سترة", "عيسى", "غير ذلك"],
    "عُمان": ["مسقط", "صلالة", "نزوى", "صحار", "غير ذلك"],
    "العراق": ["بغداد", "البصرة", "أربيل", "الموصل", "غير ذلك"],
    "اليمن": ["صنعاء", "عدن", "تعز", "الحديدة", "غير ذلك"],
    "السودان": ["الخرطوم", "أم درمان", "بحري", "بور سودان", "غير ذلك"],
    "تونس": ["تونس", "صفاقس", "سوسة", "بنزرت", "غير ذلك"],
    "المغرب": ["الرباط", "الدار البيضاء", "فاس", "مراكش", "غير ذلك"],
    "الجزائر": ["الجزائر", "وهران", "قسنطينة", "عنابة", "غير ذلك"],
}

# أسماء الدول الإنجليزية لـ API
COUNTRY_API_NAMES = {
    "لبنان": "Lebanon",
    "سوريا": "Syria",
    "الأردن": "Jordan",
    "فلسطين": "Palestine",
    "مصر": "Egypt",
    "السعودية": "Saudi Arabia",
    "الإمارات": "United Arab Emirates",
    "قطر": "Qatar",
    "الكويت": "Kuwait",
    "البحرين": "Bahrain",
    "عُمان": "Oman",
    "العراق": "Iraq",
    "اليمن": "Yemen",
    "السودان": "Sudan",
    "تونس": "Tunisia",
    "المغرب": "Morocco",
    "الجزائر": "Algeria",
}

# أسماء المدن الإنجليزية لبعض المدن المعروفة
CITY_API_NAMES: Dict[Tuple[str, str], str] = {
    ("لبنان", "بيروت"): "Beirut",
    ("لبنان", "طرابلس"): "Tripoli",
    ("لبنان", "صيدا"): "Sidon",
    ("لبنان", "صور"): "Tyre",

    ("سوريا", "دمشق"): "Damascus",
    ("سوريا", "حلب"): "Aleppo",
    ("سوريا", "حمص"): "Homs",
    ("سوريا", "حماة"): "Hama",

    ("الأردن", "عمّان"): "Amman",
    ("الأردن", "عمان"): "Amman",
    ("الأردن", "إربد"): "Irbid",
    ("الأردن", "الزرقاء"): "Zarqa",
    ("الأردن", "العقبة"): "Aqaba",

    ("فلسطين", "القدس"): "Jerusalem",
    ("فلسطين", "غزة"): "Gaza",
    ("فلسطين", "الخليل"): "Hebron",
    ("فلسطين", "نابلس"): "Nablus",

    ("مصر", "القاهرة"): "Cairo",
    ("مصر", "الإسكندرية"): "Alexandria",
    ("مصر", "الاسكندرية"): "Alexandria",
    ("مصر", "الجيزة"): "Giza",

    ("السعودية", "الرياض"): "Riyadh",
    ("السعودية", "مكة"): "Mecca",
    ("السعودية", "المدينة"): "Medina",
    ("السعودية", "جدة"): "Jeddah",

    ("الإمارات", "دبي"): "Dubai",
    ("الإمارات", "أبوظبي"): "Abu Dhabi",
    ("الإمارات", "ابوظبي"): "Abu Dhabi",

    ("قطر", "الدوحة"): "Doha",

    ("الكويت", "مدينة الكويت"): "Kuwait City",

    ("البحرين", "المنامة"): "Manama",

    ("عُمان", "مسقط"): "Muscat",

    ("العراق", "بغداد"): "Baghdad",
    ("العراق", "البصرة"): "Basra",
    ("العراق", "أربيل"): "Erbil",
    ("العراق", "الموصل"): "Mosul",

    ("اليمن", "صنعاء"): "Sanaa",
    ("اليمن", "عدن"): "Aden",

    ("السودان", "الخرطوم"): "Khartoum",

    ("تونس", "تونس"): "Tunis",

    ("المغرب", "الرباط"): "Rabat",
    ("المغرب", "الدار البيضاء"): "Casablanca",
    ("المغرب", "فاس"): "Fes",
    ("المغرب", "مراكش"): "Marrakesh",

    ("الجزائر", "الجزائر"): "Algiers",
    ("الجزائر", "وهران"): "Oran",
    ("الجزائر", "قسنطينة"): "Constantine",
    ("الجزائر", "عنابة"): "Annaba",
}


# ---------------- دوال مساعدة لبناء الكيبورد ----------------
def build_countries_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    row = []
    for i, country in enumerate(ARAB_COUNTRIES, start=1):
        row.append(InlineKeyboardButton(country, callback_data=f"country|{country}"))
        if i % 2 == 0:  # صفين صفين
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(buttons)


def build_cities_keyboard(country: str) -> InlineKeyboardMarkup:
    cities = COUNTRY_CITIES.get(country, [])
    buttons = []
    row = []
    for i, city in enumerate(cities, start=1):
        row.append(
            InlineKeyboardButton(
                city,
                callback_data=f"city|{country}|{city}"
            )
        )
        if i % 2 == 0:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(buttons)


# ---------------- دالة جلب مواقيت الصلاة من API ----------------
def get_prayer_times(country_ar: str, city_ar: str) -> Optional[Dict]:
    """يرجع dict فيه المواقيت أو None في حال الفشل."""
    country_en = COUNTRY_API_NAMES.get(country_ar, country_ar)
    city_en = CITY_API_NAMES.get((country_ar, city_ar), city_ar)

    try:
        url = "http://api.aladhan.com/v1/timingsByCity"
        params = {
            "city": city_en,
            "country": country_en,
            "method": 2,   # جامعة العلوم الإسلامية بكراتشي
            "school": 0,
        }
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        if data.get("code") != 200:
            logger.warning(f"API error: {data}")
            return None

        timings = data["data"]["timings"]
        date_info = data["data"]["date"]
        gregorian = date_info["readable"]
        hijri = date_info["hijri"]["date"]

        return {
            "Fajr": timings.get("Fajr"),
            "Dhuhr": timings.get("Dhuhr"),
            "Asr": timings.get("Asr"),
            "Maghrib": timings.get("Maghrib"),
            "Isha": timings.get("Isha"),
            "gregorian": gregorian,
            "hijri": hijri,
        }
    except Exception as e:
        logger.exception(f"Error fetching prayer times: {e}")
        return None


def format_prayer_message(country_ar: str, city_ar: str, times: Dict) -> str:
    return (
        f"🕌 *مواقيت الصلاة اليوم*\n"
        f"📍 *المدينة:* {city_ar}\n"
        f"🌍 *الدولة:* {country_ar}\n\n"
        f"📅 *التاريخ الميلادي:* {times['gregorian']}\n"
        f"🗓 *التاريخ الهجري:* {times['hijri']}\n\n"
        f"الفجر: {times['Fajr']}\n"
        f"الظهر: {times['Dhuhr']}\n"
        f"العصر: {times['Asr']}\n"
        f"المغرب: {times['Maghrib']}\n"
        f"العشاء: {times['Isha']}\n\n"
        f"🤍 نسأل الله أن يتقبّل منّا ومنكم."
    )


# ---------------- Handlers ----------------
def send_country_menu(update: Update, context: CallbackContext):
    text = (
        "وعليكم السلام ورحمة الله وبركاته 🤍\n\n"
        "اختَر الدولة أولًا من القائمة التالية، ثم اختر مدينتك للحصول على مواقيت الصلاة."
    )
    if update.message:
        update.message.reply_text(
            text,
            reply_markup=build_countries_keyboard(),
        )
    else:
        # لو نداء من كولباك
        query = update.callback_query
        query.answer()
        query.edit_message_text(
            text,
            reply_markup=build_countries_keyboard(),
        )


def start_command(update: Update, context: CallbackContext):
    send_country_menu(update, context)


def text_handler(update: Update, context: CallbackContext):
    text = (update.message.text or "").strip().lower()

    # لو كان ينتظر اسم مدينة غير موجودة في القائمة
    if context.user_data.get("awaiting_city_name"):
        data = context.user_data["awaiting_city_name"]
        country_ar = data["country"]
        city_ar = update.message.text.strip()

        times = get_prayer_times(country_ar, city_ar)
        if not times:
            update.message.reply_text(
                "❌ لم أستطع العثور على مواقيت الصلاة لهذه المدينة.\n"
                "حاول كتابة الاسم بالإنجليزية أو باسم مختلف، أو اختر مدينة من القائمة."
            )
            return

        # حفظ آخر مدينة للمستخدم
        context.user_data["saved_country"] = country_ar
        context.user_data["saved_city"] = city_ar
        context.user_data["awaiting_city_name"] = None

        msg = format_prayer_message(country_ar, city_ar, times)
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔁 مواقيت اليوم من جديد", callback_data="repeat_last")]]
        )
        update.message.reply_markdown(msg, reply_markup=keyboard)
        return

    # تحية أو أي نص ترحيبي
    if "سلام" in text or "السلام" in text or "/start" in text or "hi" in text or "hello" in text:
        send_country_menu(update, context)
    else:
        update.message.reply_text(
            "👋 أهلًا بك.\n"
            "اكتب *السلام عليكم* أو أرسل الأمر /start لاختيار الدولة والمدينة لمواقيت الصلاة.",
            parse_mode="Markdown",
        )


def callback_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data

    # اختيار دولة
    if data.startswith("country|"):
        _, country_ar = data.split("|", 1)
        context.user_data["selected_country"] = country_ar

        cities_keyboard = build_cities_keyboard(country_ar)
        query.answer()
        query.edit_message_text(
            f"🌍 الدولة المختارة: *{country_ar}*\n\n"
            f"✅ اختر مدينتك من القائمة:",
            reply_markup=cities_keyboard,
            parse_mode="Markdown",
        )
        return

    # اختيار مدينة
    if data.startswith("city|"):
        _, country_ar, city_ar = data.split("|", 2)
        if city_ar == "غير ذلك":
            # طلب إدخال مدينة يدويًا
            context.user_data["awaiting_city_name"] = {"country": country_ar}
            query.answer()
            query.edit_message_text(
                f"✏️ اكتب الآن اسم المدينة داخل *{country_ar}* (يمكن أن تكتبها بالعربية أو الإنجليزية):",
                parse_mode="Markdown",
            )
            return

        # مدينة موجودة في القائمة
        times = get_prayer_times(country_ar, city_ar)
        if not times:
            query.answer()
            query.edit_message_text(
                "❌ لم أستطع العثور على مواقيت الصلاة لهذه المدينة.\n"
                "حاول اختيار (غير ذلك) وكتابة اسم المدينة يدويًا."
            )
            return

        # حفظ آخر مدينة للمستخدم
        context.user_data["saved_country"] = country_ar
        context.user_data["saved_city"] = city_ar

        msg = format_prayer_message(country_ar, city_ar, times)
        keyboard = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("🔁 مواقيت اليوم من جديد", callback_data="repeat_last")],
                [InlineKeyboardButton("🌍 تغيير الدولة", callback_data="change_country")],
            ]
        )
        query.answer()
        query.edit_message_markdown(msg, reply_markup=keyboard)
        return

    # إعادة آخر مواقيت محفوظة
    if data == "repeat_last":
        country_ar = context.user_data.get("saved_country")
        city_ar = context.user_data.get("saved_city")

        if not country_ar or not city_ar:
            query.answer()
            query.edit_message_text(
                "⚠️ لا توجد مدينة محفوظة لك بعد.\n"
                "ابدأ باختيار الدولة والمدينة من جديد عن طريق /start."
            )
            return

        times = get_prayer_times(country_ar, city_ar)
        if not times:
            query.answer()
            query.edit_message_text(
                "❌ حدث خطأ أثناء جلب مواقيت الصلاة.\n"
                "حاول مرة أخرى لاحقًا."
            )
            return

        msg = format_prayer_message(country_ar, city_ar, times)
        keyboard = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("🔁 مواقيت اليوم من جديد", callback_data="repeat_last")],
                [InlineKeyboardButton("🌍 تغيير الدولة", callback_data="change_country")],
            ]
        )
        query.answer()
        query.edit_message_markdown(msg, reply_markup=keyboard)
        return

    # تغيير الدولة
    if data == "change_country":
        context.user_data.pop("selected_country", None)
        context.user_data.pop("saved_country", None)
        context.user_data.pop("saved_city", None)

        query.answer()
        query.edit_message_text(
            "اختر الدولة من جديد 🌍:",
            reply_markup=build_countries_keyboard(),
        )
        return


# ---------------- Main ----------------
def main():
    logger.info("Starting bot with webhook mode...")

    updater = Updater(TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher

    # أوامر و هاندلرز
    dp.add_handler(CommandHandler("start", start_command))
    dp.add_handler(CallbackQueryHandler(callback_handler))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, text_handler))

    # تشغيل Webhook على Render
    logger.info(f"Using BASE_URL={BASE_URL}, PORT={PORT}")
    logger.info(f"Setting webhook to {WEBHOOK_URL}")

    updater.start_webhook(
        listen="0.0.0.0",
        port=PORT,                # البورت الداخلي من Render
        url_path=WEBHOOK_PATH,    # مسار الويبهوك (التوكن)
        webhook_url=WEBHOOK_URL,  # URL الخارجي بدون بورت
    )

    updater.idle()


if __name__ == "__main__":
    main()
