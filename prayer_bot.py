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
        f"الظهر  🕛 : {dhuhr}\
