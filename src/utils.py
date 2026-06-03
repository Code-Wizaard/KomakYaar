import os
import traceback
import datetime
from dotenv import load_dotenv

load_dotenv()
API_TOKEN = os.getenv("TOKEN")
DB_PATH = os.getenv("DB_PATH", "groups.db")
SWEARS_PATH = os.getenv("SWEARS_PATH", "swears.txt")
OWNER_ID = int(os.getenv("OWNER_ID"))
VERSION = "1.5.4"
BOT_CHANNEL = "@KomakYaaaR"
BOT_GROUP = "@KomakYaarGap"

HELP_TEXT = """🤖 **راهنمای جامع ربات کمک‌یار**

سلام! من یه ربات مدیریت گروه هستم که بهت کمک می‌کنم گروهتو راحت‌تر مدیریت کنی.

📌 **برای شروع:**
1. منو به گروه اضافه کن
2. به من دسترسی **ادمین** بده
3. دستور `فعال شو` رو بفرست
4. تمام! من آماده خدمت‌گذاری هستم 🎯

⚡ **دستورات سریع:**
• `راهنما` - نمایش همین منو
• `لینک` - ساخت لینک دعوت اختصاصی
• `قوانین` - نمایش قوانین گروه
• `فیلترها` - لیست پاسخ‌های خودکار
• `اطلاعات` (ریپلای) - اطلاعات کامل کاربر

💡 **نکات مهم:**
• برای اکثر دستورات می‌تونید روی پیام کاربر **ریپلای** کنید
• بات در حالت عادی **باادب** صحبت می‌کنه (قابل تغییر با `بی ادب شو`)

از دکمه‌های زیر برای مشاهده جزئیات هر بخش استفاده کن 👇
"""

def convert_digit(text: str) -> str:
    persian_arabic_digits = '۰۱۲۳۴۵۶۷۸۹'
    persian_arabic_digits += '٠١٢٣٤٥٦٧٨٩'
    english_digits = '0123456789' * 2
    
    translation_table = str.maketrans(persian_arabic_digits, english_digits)
    return int(text.translate(translation_table))

def send_error_to_owner(error_text, owner_id, bot, error_type="ERROR"):
    """Send error details to bot owner"""
    try:
        error_message = f"""🚨 **{error_type}**

⏰ {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

❌ خطا:
```{error_text[:3000]}```
"""
        bot.send_message(owner_id, error_message, parse_mode="Markdown")
    except:
        print(f"Error sending to owner: {error_text}")

if __name__ == "__main__":
    print(f"API Token = {API_TOKEN if API_TOKEN else "no token"}")
    print(f"DB Path = {DB_PATH}")
    print(f"Swears file path = {SWEARS_PATH}")
    print(f"Owner ID = {OWNER_ID if OWNER_ID else "no id"}")
    print(f"Channel username of the bot = {BOT_CHANNEL if BOT_CHANNEL else "no channel"}")
    print(f"Group username of the bot = {BOT_GROUP if BOT_GROUP else "no group"}")
    print(f"Version = {VERSION}")