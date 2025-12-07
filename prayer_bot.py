import os
import logging
from typing import Optional, Dict, Tuple

from datetime import datetime
import requests
import pytz

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from telegram.ext import (
    Updater,
    CallbackContext,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackQueryHandler,
)

# ================= إعداد اللوج =================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ================= متغيرات البيئة =================
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
BASE_URL = os.environ.get("BASE_URL", "https://t1prayerbot.onrender.com").rstrip("/")
PORT = int(os.environ.get("PORT", "10000"))

WEBHOOK_PATH = TELEGRAM_TOKEN
WEBHOOK_URL = f"{BASE_URL}/{WEBHOOK_PATH}"  # بدون رقم بورت في الرابط

# ================= الدول / المدن =================
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

COUNTRY_CITIES = {
    "لبنان": ["بيروت", "طرابلس", "صيدا", "صور", "غير ذلك"],
    "سوريا": ["دمشق", "حلب", "حمص", "حماة", "غير ذلك"],
    "الأردن": ["عمّان", "إربد", "الزرقاء", "العقبة", "غير ذلك"],
    "فلسطين": ["القدس", "غزة", "الخليل", "نابلس", "غير ذلك"],
    "مصر": ["القاهرة", "الإسكندرية", "الجيزة", "أسيوط", "غير ذلك"],
    "السعودية": ["الرياض", "مكة", "المدينة", "جدة", "غير ذلك"],
    "الإمارات": ["دبي", "أبوظبي", "الشارقة", "عجمان", "غير ذلك"],
    "قطر": ["الدوحة", "الريان", "الوكرة", "غير ذلك"],
    "الكويت": ["مدينة الكويت", "حولي", "الفروانية", "الجهراء", "غير ذلك"],
    "البحرين": ["المنامة", "المحرق", "سترة", "غير ذلك"],
    "عُمان": ["مسقط", "صلالة", "نزوى", "صحار", "غير ذلك"],
    "العراق": ["بغداد", "البصرة", "أربيل", "الموصل", "غير ذلك"],
    "اليمن": ["صنعاء", "عدن", "تعز", "الحديدة", "غير ذلك"],
    "السودان": ["الخرطوم", "أم درمان", "بحري", "بور سودان", "غير ذلك"],
    "تونس": ["تونس", "صفاقس", "سوسة", "بنزرت", "غير ذلك"],
    "المغرب": ["الرباط", "الدار البيضاء", "فاس", "مراكش", "غير ذلك"],
    "الجزائر": ["الجزائر", "وهران", "قسنطينة", "عنابة", "غير ذلك"],
}

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

# ================ كيبورد الكوماند الأساسية ================
def main_reply_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [
            KeyboardButton("مواقيت اليوم 🕌"),
            KeyboardButton("تغيير المدينة 🧭"),
        ],
        [
            KeyboardButton("إرسال موقعي 📍", request_location=True),
            KeyboardButton("تنبيهات الأذان 🔔"),
        ],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


# ================ كيبورد الدول / المدن (Inline) ================
def build_countries_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    row = []
    for i, country in enumerate(ARAB_COUNTRIES, start=1):
        row.append(InlineKeyboardButton(country, callback_data=f"country|{country}"))
        if i % 2 == 0:
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
                callback_data=f"city|{country}|{city}",
            )
        )
        if i % 2 == 0:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(buttons)


# ================ استدعاء API ================
def get_prayer_times(country_ar: str, city_ar: str) -> Optional[Dict]:
    """عن طريق الدولة / المدينة."""
    country_en = COUNTRY_API_NAMES.get(country_ar, country_ar)
    city_en = CITY_API_NAMES.get((country_ar, city_ar), city_ar)

    try:
        url = "http://api.aladhan.com/v1/timingsByCity"
        params = {
            "city": city_en,
            "country": country_en,
            "method": 2,
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
        timezone = data["data"]["meta"]["timezone"]

        return {
            "Fajr": timings.get("Fajr"),
            "Dhuhr": timings.get("Dhuhr"),
            "Asr": timings.get("Asr"),
            "Maghrib": timings.get("Maghrib"),
            "Isha": timings.get("Isha"),
            "gregorian": gregorian,
            "hijri": hijri,
            "timezone": timezone,
            "country_ar": country_ar,
            "city_ar": city_ar,
        }
    except Exception as e:
        logger.exception(f"Error fetching prayer times by city: {e}")
        return None


def get_prayer_times_by_coords(lat: float, lon: float) -> Optional[Dict]:
    """عن طريق الإحداثيات (GPS)."""
    try:
        url = "http://api.aladhan.com/v1/timings"
        params = {
            "latitude": lat,
            "longitude": lon,
            "method": 2,
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
        timezone = data["data"]["meta"]["timezone"]

        # لا نعرف المدينة بالضبط، فنكتب وصف عام
        country_ar = "حسب موقعك"
        city_ar = "موقعك الحالي"

        return {
            "Fajr": timings.get("Fajr"),
            "Dhuhr": timings.get("Dhuhr"),
            "Asr": timings.get("Asr"),
            "Maghrib": timings.get("Maghrib"),
            "Isha": timings.get("Isha"),
            "gregorian": gregorian,
            "hijri": hijri,
            "timezone": timezone,
            "country_ar": country_ar,
            "city_ar": city_ar,
        }
    except Exception as e:
        logger.exception(f"Error fetching prayer times by coords: {e}")
        return None


# ================ تنسيق الرسالة ================
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


# ================ تنبيهات الأذان (JobQueue) ================
def cancel_alert_jobs(context: CallbackContext, chat_id: int):
    for job in context.job_queue.jobs():
        if str(job.name).startswith(f"alert-{chat_id}-"):
            job.schedule_removal()


def send_adhan_alert(context: CallbackContext):
    job = context.job
    data = job.context or {}
    chat_id = data.get("chat_id")
    prayer_name = data.get("prayer_name_ar", "أحد الأوقات")
    if not chat_id:
        return
    context.bot.send_message(
        chat_id=chat_id,
        text=f"🕌 حان الآن وقت صلاة *{prayer_name}*.\n\nتقبّل الله طاعتكم 🤍",
        parse_mode="Markdown",
    )


def schedule_prayer_alerts(context: CallbackContext, chat_id: int, user_data: Dict) -> bool:
    """تفعيل التنبيهات لباقي أوقات اليوم فقط."""
    # نحدد المصدر: إحداثيات أو مدينة
    times = None
    if user_data.get("saved_lat") is not None and user_data.get("saved_lon") is not None:
        times = get_prayer_times_by_coords(user_data["saved_lat"], user_data["saved_lon"])
    elif user_data.get("saved_country") and user_data.get("saved_city"):
        times = get_prayer_times(user_data["saved_country"], user_data["saved_city"])

    if not times:
        return False

    tz = pytz.timezone(times["timezone"])
    now_local = datetime.now(tz)
    today = now_local.date()

    # حذف أي تنبيهات قديمة
    cancel_alert_jobs(context, chat_id)

    prayers = [
        ("الفجر", "Fajr"),
        ("الظهر", "Dhuhr"),
        ("العصر", "Asr"),
        ("المغرب", "Maghrib"),
        ("العشاء", "Isha"),
    ]

    scheduled_any = False

    for label_ar, key in prayers:
        t_str = times.get(key)
        if not t_str:
            continue
        try:
            hour, minute = map(int, t_str.split(":")[:2])
        except Exception:
            continue

        prayer_dt_local = tz.localize(datetime(today.year, today.month, today.day, hour, minute))
        if prayer_dt_local <= now_local:
            # هذا الوقت مرّ
            continue

        run_time_utc = prayer_dt_local.astimezone(pytz.UTC)

        context.job_queue.run_once(
            send_adhan_alert,
            when=run_time_utc,
            context={
                "chat_id": chat_id,
                "prayer_name_ar": label_ar,
            },
            name=f"alert-{chat_id}-{key}",
        )

        scheduled_any = True

    return scheduled_any


# ================ Handlers ================
def send_country_menu(update: Update, context: CallbackContext):
    text = (
        "اختَر الدولة أولًا من القائمة التالية، ثم اختر مدينتك للحصول على مواقيت الصلاة.\n\n"
        "بعد اختيار المدينة سيتم تثبيتها تلقائيًا لك."
    )

    if update.message:
        update.message.reply_text(
            text,
            reply_markup=build_countries_keyboard(),
        )
    else:
        query = update.callback_query
        query.answer()
        query.edit_message_text(
            text,
            reply_markup=build_countries_keyboard(),
        )


def start_command(update: Update, context: CallbackContext):
    welcome = (
        "👋 أهلًا بك.\n\n"
        "اكتب *السلام عليكم* أو استخدم الأزرار بالأسفل:\n"
        "• مواقيت اليوم 🕌\n"
        "• تغيير المدينة 🧭\n"
        "• إرسال موقعي 📍\n"
        "• تنبيهات الأذان 🔔"
    )
    update.message.reply_text(
        welcome,
        reply_markup=main_reply_keyboard(),
        parse_mode="Markdown",
    )


def text_handler(update: Update, context: CallbackContext):
    text = (update.message.text or "").strip()

    # تحية = نفس /start
    lowered = text.lower()
    if (
        "السلام" in lowered
        or "سلام" in lowered
        or "/start" in lowered
        or lowered in ("hi", "hello")
    ):
        start_command(update, context)
        return

    user_data = context.user_data
    chat_id = update.message.chat_id

    # لو كان ينتظر اسم مدينة غير موجودة في القائمة
    if user_data.get("awaiting_city_name"):
        country_ar = user_data["awaiting_city_name"]["country"]
        city_ar = text.strip()

        times = get_prayer_times(country_ar, city_ar)
        if not times:
            update.message.reply_text(
                "❌ لم أستطع العثور على مواقيت الصلاة لهذه المدينة.\n"
                "حاول كتابة الاسم بطريقة أخرى أو اختر مدينة من القائمة."
            )
            return

        user_data["saved_country"] = country_ar
        user_data["saved_city"] = city_ar
        user_data["saved_lat"] = None
        user_data["saved_lon"] = None
        user_data["awaiting_city_name"] = None

        msg = format_prayer_message(country_ar, city_ar, times)
        keyboard = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("🔁 مواقيت اليوم من جديد", callback_data="repeat_last")],
                [InlineKeyboardButton("🌍 تغيير الدولة", callback_data="change_country")],
            ]
        )
        update.message.reply_markdown(msg, reply_markup=keyboard)
        return

    # زر مواقيت اليوم
    if "مواقيت" in text:
        # عنده موقع محفوظ؟
        times = None
        if user_data.get("saved_lat") is not None and user_data.get("saved_lon") is not None:
            times = get_prayer_times_by_coords(user_data["saved_lat"], user_data["saved_lon"])
        elif user_data.get("saved_country") and user_data.get("saved_city"):
            times = get_prayer_times(user_data["saved_country"], user_data["saved_city"])

        if not times:
            # لم يتم تعيين مدينة بعد
            send_country_menu(update, context)
            return

        msg = format_prayer_message(times["country_ar"], times["city_ar"], times)
        keyboard = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("🔁 مواقيت اليوم من جديد", callback_data="repeat_last")],
                [InlineKeyboardButton("🌍 تغيير الدولة", callback_data="change_country")],
            ]
        )
        update.message.reply_markdown(msg, reply_markup=keyboard)
        return

    # زر تغيير المدينة
    if "تغيير المدينة" in text:
        # مسح المكان المحفوظ
        user_data.pop("saved_country", None)
        user_data.pop("saved_city", None)
        user_data.pop("saved_lat", None)
        user_data.pop("saved_lon", None)
        send_country_menu(update, context)
        return

    # زر تنبيهات الأذان
    if "تنبيهات" in text:
        if not (
            user_data.get("saved_lat") is not None and user_data.get("saved_lon") is not None
        ) and not (user_data.get("saved_country") and user_data.get("saved_city")):
            update.message.reply_text(
                "⚠️ من فضلك حدِّد مدينتك أو أرسل موقعك أولًا، ثم فعِّل تنبيهات الأذان."
            )
            return

        alerts_on = user_data.get("alerts_on", False)
        if alerts_on:
            user_data["alerts_on"] = False
            cancel_alert_jobs(context, chat_id)
            update.message.reply_text("🔕 تم إيقاف تنبيهات الأذان لليوم.")
        else:
            ok = schedule_prayer_alerts(context, chat_id, user_data)
            if ok:
                user_data["alerts_on"] = True
                update.message.reply_text(
                    "🔔 تم تفعيل تنبيهات الأذان لباقي أوقات *اليوم الحالي*.\n"
                    "غدًا يمكنك الضغط على الزر مرة أخرى لتجديد التنبيهات.",
                    parse_mode="Markdown",
                )
            else:
                update.message.reply_text(
                    "❌ لم أستطع جدولة التنبيهات. حاول لاحقًا أو غيّر المدينة."
                )
        return

    # أي نص آخر
    update.message.reply_text(
        "👋 استخدم الأزرار بالأسفل للحصول على مواقيت الصلاة أو تغيير المدينة.",
        reply_markup=main_reply_keyboard(),
    )


def location_handler(update: Update, context: CallbackContext):
    """عند إرسال الموقع من زر (إرسال موقعي 📍)."""
    loc = update.message.location
    lat, lon = loc.latitude, loc.longitude

    user_data = context.user_data
    user_data["saved_lat"] = lat
    user_data["saved_lon"] = lon
    user_data["saved_country"] = None
    user_data["saved_city"] = None

    times = get_prayer_times_by_coords(lat, lon)
    if not times:
        update.message.reply_text(
            "❌ حدث خطأ أثناء جلب مواقيت الصلاة حسب موقعك.\nحاول مرة أخرى لاحقًا."
        )
        return

    msg = format_prayer_message(times["country_ar"], times["city_ar"], times)
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🔁 مواقيت اليوم من جديد", callback_data="repeat_last")],
            [InlineKeyboardButton("🌍 اختيار دولة/مدينة يدويًا", callback_data="change_country")],
        ]
    )
    update.message.reply_markdown(msg, reply_markup=keyboard)


def callback_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data
    chat_id = query.message.chat.id
    user_data = context.user_data

    # اختيار دولة
    if data.startswith("country|"):
        _, country_ar = data.split("|", 1)
        user_data["selected_country"] = country_ar

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
            user_data["awaiting_city_name"] = {"country": country_ar}
            query.answer()
            query.edit_message_text(
                f"✏️ اكتب الآن اسم المدينة داخل *{country_ar}*:",
                parse_mode="Markdown",
            )
            return

        times = get_prayer_times(country_ar, city_ar)
        if not times:
            query.answer()
            context.bot.send_message(
                chat_id=chat_id,
                text="❌ لم أستطع العثور على مواقيت الصلاة لهذه المدينة.\n"
                     "اختر (غير ذلك) وادخل الاسم يدويًا."
            )
            return

        # حفظ المدينة
        user_data["saved_country"] = country_ar
        user_data["saved_city"] = city_ar
        user_data["saved_lat"] = None
        user_data["saved_lon"] = None

        msg = format_prayer_message(country_ar, city_ar, times)
        keyboard = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("🔁 مواقيت اليوم من جديد", callback_data="repeat_last")],
                [InlineKeyboardButton("🌍 تغيير الدولة", callback_data="change_country")],
            ]
        )
        query.answer()
        context.bot.send_message(
            chat_id=chat_id,
            text=msg,
            parse_mode="Markdown",
            reply_markup=keyboard,
        )
        return

    # إعادة آخر مدينة/موقع
    if data == "repeat_last":
        times = None
        if user_data.get("saved_lat") is not None and user_data.get("saved_lon") is not None:
            times = get_prayer_times_by_coords(user_data["saved_lat"], user_data["saved_lon"])
        elif user_data.get("saved_country") and user_data.get("saved_city"):
            times = get_prayer_times(user_data["saved_country"], user_data["saved_city"])

        if not times:
            query.answer()
            context.bot.send_message(
                chat_id=chat_id,
                text="⚠️ لا توجد مدينة أو موقع محفوظ.\n"
                     "استخدم زر (مواقيت اليوم 🕌) لتحديد المدينة أولًا."
            )
            return

        msg = format_prayer_message(times["country_ar"], times["city_ar"], times)
        keyboard = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("🔁 مواقيت اليوم من جديد", callback_data="repeat_last")],
                [InlineKeyboardButton("🌍 تغيير الدولة", callback_data="change_country")],
            ]
        )
        query.answer()
        context.bot.send_message(
            chat_id=chat_id,
            text=msg,
            parse_mode="Markdown",
            reply_markup=keyboard,
        )
        return

    # تغيير الدولة من جديد
    if data == "change_country":
        user_data.pop("saved_country", None)
        user_data.pop("saved_city", None)
        user_data.pop("saved_lat", None)
        user_data.pop("saved_lon", None)
        user_data.pop("selected_country", None)

        query.answer()
        query.edit_message_text(
            "اختر الدولة من جديد 🌍:",
            reply_markup=build_countries_keyboard(),
        )
        return


# ================ Main =================
def main():
    logger.info("Starting bot with webhook mode...")

    updater = Updater(TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start_command))
    dp.add_handler(CallbackQueryHandler(callback_handler))
    dp.add_handler(MessageHandler(Filters.location, location_handler))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, text_handler))

    logger.info(f"Using BASE_URL={BASE_URL}, PORT={PORT}")
    logger.info(f"Setting webhook to {WEBHOOK_URL}")

    updater.start_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=WEBHOOK_PATH,
        webhook_url=WEBHOOK_URL,
    )

    updater.idle()


if __name__ == "__main__":
    main()
