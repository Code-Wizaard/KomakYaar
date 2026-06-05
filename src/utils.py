import os
import traceback
import datetime
from dotenv import load_dotenv
import functools
import random
from telebot.asyncio_helper import ApiTelegramException

load_dotenv()
API_TOKEN = os.getenv("TOKEN")
DB_PATH = os.getenv("DB_PATH", "groups.db")
SWEARS_PATH = os.getenv("SWEARS_PATH", "swears.txt")
OWNER_ID = int(os.getenv("OWNER_ID"))
VERSION = "2.5.4"
BOT_CHANNEL = "@KomakYaaar"
BOT_GROUP = "@KomakYaarGap"

RUDE_ADMIN_MESSAGES = [
    "داداش تو ادمینی؟ برو باباتو ادمین کن بعد بیا اینجا حرف بزن 😏",
    "اخه تو ادمینی؟ گمشو پی کارت، اینجا جای بزرگتراست",
    "تو که حتی ادمین کانالت نیستی، الان ادمین گروهم شدی؟ خخخخ",
    "عزیزم برو اول خودتو ادمین کن، بعد بیا دستور بده",
    "مگه مامانت ادمینه که تو ادمینی؟ 😂 برو گمشو",
    "ادمین؟ تو؟ خخخخخ، شوخی نکن داداش، دلم سوخت",
    "برو بابا، ادمین نیستی، فقط داری وقت ما رو تلف می‌کنی",
    "تو ادمینی؟ آره آره، منم شاه ایرانم، گمشو لاشی",
    "داداش تو هنوز تو گروهت ادمین نیستی، اینجا چه غلطی می‌کنی؟",
    "ادمین بودن رو ول کن، برو اول سواد ادمین شدن رو یاد بگیر",
    "توکی باشی که اینارو برا من تنظیم کنی",
    "لطفا تا ادمین نشدی گوه نخور",
    "آخه تو ادمینی؟",
    "به علت حماقت این فرد نادان و انگشت کردن در دستور ادمینی همه ی اعضای گروه تبدیل به بهنام تشکر شدند، برای دفع این حمله به فرستنده دستور فحش رکیک بدهید"
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

def handler_check(require_admin: bool = False):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(self, message, *args, **kwargs):
            try:
                chat_id = message.chat.id
                user_id = message.from_user.id if message.from_user else None
                text = message.text or ""

                # چک بلاک بودن گروه
                if await self.db.is_group_blocked(chat_id):
                    return
                
                if not await self.db.is_group_active(chat_id):
                    return

                # چک ادمین
                if require_admin:
                    if not await self.db.is_admin(chat_id, user_id):
                        polite = int(await self.db.get_group_setting(chat_id, "POLITE_MODE", 1)) == 1
                        if polite:
                            await self.bot.reply_to(message, "❌ شما دسترسی ادمین ندارید.")
                        else:
                            rude_msg = random.choice(RUDE_ADMIN_MESSAGES)
                            await self.bot.reply_to(message, rude_msg)
                        return

                # چک دستورات عمومی
                else:
                    if (await self.db.get_group_setting(message.chat.id, "PUBLIC_COMMANDS", 1) != 1) and (not await self.db.is_admin(chat_id, user_id)):
                        return

                # چک ضد اسپم
                if hasattr(self, 'anti_spam'):
                    spam_result = await self.anti_spam.check(chat_id, user_id, text)
                    if spam_result[0] is not None:
                        try:
                            await self.bot.delete_message(chat_id, message.message_id)
                        except ApiTelegramException:
                            pass
                        warning_text = f"⚠️ اسپم نکن! ({spam_result[0]})"
                        await self.bot.reply_to(message, warning_text)
                        return

                return await func(self, message, *args, **kwargs)

            except Exception as e:
                error_trace = traceback.format_exc()
                print(f"❌ Error in {func.__name__}(): {e}")

                try:
                    await send_error_to_owner(
                        error_text=error_trace,
                        owner_id=OWNER_ID,
                        bot=self.bot,
                        error_type=f"Handler: {func.__name__}"
                    )
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