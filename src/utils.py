import os
import traceback
import datetime
from dotenv import load_dotenv
import functools
import random
from telebot.asyncio_helper import ApiTelegramException
from telebot import types
import time
import re

load_dotenv()
API_TOKEN = os.getenv("TOKEN")
BALE_TOKEN = os.getenv("BALE_TOKEN")
DB_PATH = os.getenv("DB_PATH", "groups.db")
SWEARS_PATH = os.getenv("SWEARS_PATH", "swears.txt")
OWNER_ID = int(os.getenv("OWNER_ID"))
VERSION = "2.6.8"
BOT_CHANNEL = "@KomakYaaar"
BOT_GROUP = "@KomakYaarGap"

RUDE_ADMIN_MESSAGES = [
    "داداش تو ادمینی؟ برو باباتو ادمین کن بعد بیا اینجا حرف بزن 😏",
    "اخه تو ادمینی؟ گمشو پی کارت، اینجا جای بزرگتراست",
    "عزیزم برو اول خودتو ادمین کن، بعد بیا دستور بده",
    "ادمین؟ تو؟ خخخخخ، شوخی نکن داداش، دلم سوخت",
    "برو بابا، ادمین نیستی، فقط داری وقت ما رو تلف می‌کنی",
    "تو ادمینی؟ آره آره، منم شاه ایرانم، گمشو لاشی",
    "داداش تو هنوز تو گروهت ادمین نیستی، اینجا چه غلطی می‌کنی؟",
    "ادمین بودن رو ول کن، برو اول سواد ادمین شدن رو یاد بگیر",
    "توکی باشی که اینارو برا من تنظیم کنی",
    "لطفا تا ادمین نشدی گوه نخور",
    "آخه تو ادمینی؟",
    "به علت حماقت این فرد نادان و انگشت کردن در دستور ادمینی همه ی اعضای گروه تبدیل به بهنام تشکر شدند، برای دفع این حمله به فرستنده دستور فحش رکیک بدهید",
    "داداش ادمین؟ تو هنوز تو گروه خانوادگی‌ت ادمین نیستی، اینجا چه جاکاری؟ 😂",
    "لطفا ادمین واقعی بیاد، این یکی فقط داره خنده‌مون می‌گیره",
    "تو ادمینی؟ آره آره، منم امشب ناسا رو هک کردم",
    "ادمین نیستی کونی",
    "برو عامو سگ محلتون بهت محل نمیده من چرا باید به حرف تو گوش کنم یه ادمین بیاد لطفا"
]

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


def parse_strip(text: str) -> str:
    """
    Stronger Markdown sanitizer for Telegram.
    """
    if not text:
        return ""


    text = re.sub(r'\[([^\]]+?)\]\s*\(\s*([^)]*?)(?=$|\s|\n)', r'\1', text)   # broken links
    text = re.sub(r'\*\*([^*]+?)(?=\*\*|$)', r'\1', text)                     # **bold
    text = re.sub(r'__([^_]+?)(?=__|$)', r'\1', text)                         # __underline
    text = re.sub(r'(?<![\*_])(\*)([^*\n]+?)(?=\*|$)', r'\2', text)           # *italic
    text = re.sub(r'`([^`\n]+?)(?=`|$)', r'\1', text)                         # `code`
    text = re.sub(r'([_*[\]`])', r'\\\1', text)
    text = re.sub(r'(?<!@[\w])_(?!\w)', r'\_', text)

    if len(text) > 4096:
        text = text[:4093] + "..."

    return text

async def send_error_to_owner(error_text, owner_id, bot, error_type="ERROR"):
    """Send error details to bot owner"""
    try:
        error_message = f"""🚨 **{error_type}**

⏰ {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

❌ خطا:
```{error_text[:3000]}```
"""
        await bot.send_message(owner_id, error_message, parse_mode="Markdown")
    except:
        print(f"Error sending to owner: {error_text}")

def handler_check(bot, db, anti_spam, require_admin: bool = False):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(message: types.Message, *args, **kwargs):
            try:
                chat_id = message.chat.id
                user_id = message.from_user.id if message.from_user else None
                text = message.text or ""

                # بلاک بودن گروه
                if await db.is_group_blocked(chat_id):
                    return

                # فعال بودن گروه
                if not await db.is_group_active(chat_id):
                    return
                
                # ==================== ضد اسپم ====================
                if anti_spam:
                    spam_text = text
                    if not spam_text:
                        if hasattr(message, 'sticker') and message.sticker:
                            spam_text = f"sticker:{message.sticker.file_unique_id}"
                        elif hasattr(message, 'animation') and message.animation:
                            spam_text = f"animation:{message.animation.file_unique_id}"
                        else:
                            spam_text = f"{message.content_type}:{message.message_id}"

                    spam_result = await anti_spam.check(chat_id, user_id, spam_text)
                    if spam_result[0] is not None:
                        violation, count = spam_result
                        try:
                            await bot.delete_message(chat_id, message.message_id)
                        except:
                            pass
                        try:
                            await bot.restrict_chat_member(chat_id, user_id, until_date=int(time.time()) + 300, can_send_messages=False)
                        except:
                            pass
                        anti_spam.reset_user(chat_id, user_id)
                        await bot.send_message(
                            chat_id,
                            f"[{message.from_user.first_name}](tg://user?id={user_id}) {"اسپم" if violation == "spam" else "فلاد"} نکن! ۵ دقیقه سکوت داده شدی 🔇",
                            parse_mode="Markdown"
                        )
                        return

                # چک ادمین
                if require_admin:
                    if not await db.is_admin(chat_id, user_id):
                        polite = int(await db.get_group_setting(chat_id, "POLITE_MODE", 1)) == 1
                        if polite:
                            await bot.reply_to(message, "❌ شما دسترسی ادمین ندارید.")
                        else:
                            rude_msg = random.choice(RUDE_ADMIN_MESSAGES)
                            await bot.reply_to(message, rude_msg)
                        return

                # چک دستورات عمومی
                else:
                    if int(await db.get_group_setting(chat_id, "PUBLIC_COMMANDS", 1)) != 1 and not await db.is_admin(chat_id, user_id):
                        return

                

                # اجرای handler اصلی
                return await func(message, *args, **kwargs)

            except Exception as e:
                error_trace = traceback.format_exc()
                print(f"❌ Error in {func.__name__}(): {e}")
                try:
                    await send_error_to_owner(error_trace, OWNER_ID, bot, f"Handler: {func.__name__}")
                except:
                    pass

        return wrapper
    return decorator

if __name__ == "__main__":
    print(f"API Token = {API_TOKEN if API_TOKEN else "no token"}")
    print(f"DB Path = {DB_PATH}")
    print(f"Swears file path = {SWEARS_PATH}")
    print(f"Owner ID = {OWNER_ID if OWNER_ID else "no id"}")
    print(f"Channel username of the bot = {BOT_CHANNEL if BOT_CHANNEL else "no channel"}")
    print(f"Group username of the bot = {BOT_GROUP if BOT_GROUP else "no group"}")
    print(f"Version = {VERSION}")