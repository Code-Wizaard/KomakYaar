if __name__ == "__main__":
    from DataBase import DataBase

import aiosqlite
import asyncio
import time
import random
import secrets
from telebot import types
from telebot.async_telebot import AsyncTeleBot
from pyrobale import Client
from pyrobale.objects import Message, InputFile, User
from pyrobale.objects.enums import ChatType
import logging
import json
import re
from utils import *
import datetime
import base64
import hashlib
from cryptography.fernet import Fernet
from anti_spam import AntiSpam
from profanity_checker import ProfanityDetector
from anti_virus import AntiVirus
import aiohttp
from io import BytesIO
logger = logging.getLogger('TeleBot').setLevel(logging.INFO)

class KomakYaar():
    def __init__(self):
        self.bot = AsyncTeleBot(API_TOKEN)
        self.me = asyncio.run(self.bot.get_me())
        self.bale_bot = Client(BALE_TOKEN)
        self.bale_bot_me: User = self.bale_bot.get_me()
        # ============ راهنمای گام‌به‌گام ============
        # ساختار: دسته → زیردسته → راهنمای دقیق همان دستور
        self.guide_categories = {
            "help_members": {
                "title": "👥 مدیریت اعضا",
                "subs": [
                    ("help_members_warn", "⚠️ اخطار و سقف اخطار"),
                    ("help_members_punish", "🔨 مجازات‌ها (میوت / کیک / بن)"),
                    ("help_members_info", "ℹ️ اطلاعات کاربر"),
                ],
            },
            "help_locks": {
                "title": "🔒 قفل‌ها و محدودیت‌ها",
                "subs": [
                    ("help_locks_content", "📝 قفل محتوا (فحش / لینک / فوروارد / گیف / گروه)"),
                    ("help_locks_words", "🔤 مدیریت کلمات مسدود"),
                    ("help_locks_post", "📌 قفل پست‌های کانال"),
                    ("help_locks_antiabuse", "🛑 اسپم / فلاد / حمله"),
                    ("help_locks_captcha", "🤖 کپچای ورود اعضا"),
                    ("help_locks_panel", "💡 پنل مدیریت قفل"),
                ],
            },
            "help_filters": {
                "title": "🎯 فیلترها و پاسخ خودکار",
                "subs": [
                    ("help_filters_add", "➕ افزودن فیلتر"),
                    ("help_filters_remove", "➖ حذف فیلتر"),
                    ("help_filters_list", "📋 مشاهده فیلترها"),
                ],
            },
            "help_public": {
                "title": "💬 دستورات عمومی",
                "subs": [
                    ("help_public_toggle", "⚙️ فعال / غیرفعال کردن"),
                    ("help_public_cmds", "💬 لیست دستورات عمومی"),
                ],
            },
            "help_invite": {
                "title": "🔗 لینک و دعوت",
                "subs": [
                    ("help_invite_make", "🔗 ساخت لینک دعوت"),
                    ("help_invite_limits", "🔢 تنظیم حداکثر دعوت"),
                    ("help_invite_request", "✅ درخواست برای ورود"),
                ],
            },
            "help_settings": {
                "title": "⚙️ تنظیمات گروه",
                "subs": [
                    ("help_settings_texts", "📝 تنظیم متون (خوشامد / قوانین / کامنت)"),
                    ("help_settings_vars", "🔤 متغیرهای متن خوشامد"),
                    ("help_settings_bots", "🤖 مدیریت بات‌ها"),
                    ("help_settings_misc", "🛠️ سایر تنظیمات"),
                ],
            },
            "help_warnings": {
                "title": "📝 سیستم اخطار و گزارش",
                "subs": [
                    ("help_warnings_warn", "⚠️ اخطار و مجازات"),
                    ("help_warnings_report", "📢 گزارش به ادمین"),
                ],
            },
            "help_profile": {
                "title": "🎭 لقب و اصل",
                "subs": [
                    ("help_profile_set", "✏️ ثبت لقب و اصل"),
                    ("help_profile_view", "👀 مشاهده اطلاعات"),
                ],
            },
            "help_antivirus": {
                "title": "🛡️ ضدویروس فایل",
                "direct": True,
            },
            "help_whisper": {
                "title": "🕵️ نجوا (پیام خصوصی)",
                "direct": True,
            },
            "help_bridge": {
                "title": "🌉 بریج بله ↔ تلگرام",
                "direct": True,
            },
            "help_faq": {
                "title": "❓ سوالات متداول",
                "direct": True,
            },
        }

        _size_mb = MAX_ANTIVIRUS_FILE_SIZE / (1024 * 1024)

        self.guide_texts = {
            "help_members_warn": (
                "⚠️ **اخطار و سقف اخطار**\n\n"
                "**ثبت اخطار:**\n"
                "• `اخطار` (ریپلای روی پیام کاربر) - یک اخطار اضافه می‌کند\n"
                "• `حذف اخطارها` (ریپلای) - تمام اخطارهای کاربر را پاک می‌کند\n"
                "• `سقف اخطار <عدد>` - حداکثر اخطار قبل از مجازات (پیش‌فرض: 3)\n\n"
                "**تنظیم مجازات اخطار:**\n"
                "• `تعیین مجازات اخطار` - انتخاب مجازات (کیک/بن/میوت) هنگام رسیدن به سقف\n\n"
                "**مثال:**\n"
                "• `سقف اخطار 5` - بعد از ۵ اخطار کاربر مجازات می‌شود"
            ),
            "help_members_punish": (
                "🔨 **مجازات‌ها**\n\n"
                "**میوت (سکوت):**\n"
                "• `خفه <دقیقه>` - میوت موقت کاربر\n"
                "• `سکوت` (ریپلای) - میوت کاربر\n"
                "• `آن‌میوت` (ریپلای) - برداشتن میوت\n\n"
                "**اخراج و بن:**\n"
                "• `کیک` / `سیک` / `ریم` (ریپلای) - اخراج از گروه\n"
                "• `بن` / `سیکتیر` (ریپلای) - بن دائم\n"
                "• `بن+` / `سیک مخفی` (ریپلای) - بن + حذف پیام فرمان\n"
                "• `آن‌بن` (ریپلای) - برداشتن بن\n\n"
                "**تنظیم مجازات اخطار:**\n"
                "• `تعیین مجازات اخطار` - انتخاب نوع مجازاتی که با رسیدن به سقف اخطار اجرا شود"
            ),
            "help_members_info": (
                "ℹ️ **اطلاعات کاربر**\n\n"
                "• `اطلاعات` (ریپلای روی کاربر) - اطلاعات کامل (آیدی، وضعیت، عکس)\n"
                "• `لقب` (ریپلای) - نمایش لقب کاربر\n"
                "• `اصل` (ریپلای) - نمایش اصل و نسب کاربر"
            ),

            "help_locks_content": (
                "📝 **قفل محتوا**\n\n"
                "• `قفل فحش` / `بازکردن فحش` - مسدود کردن فحش\n"
                "• `قفل لینک` / `بازکردن لینک` - مسدود کردن لینک\n"
                "• `قفل فوروارد` / `بازکردن فوروارد` - مسدود کردن فوروارد\n"
                "• `قفل گیف` / `بازکردن گیف` - مسدود کردن گیف\n"
                "• `قفل گروه` / `بازکردن گروه` - قفل کامل گروه (حذف پیام همه)\n\n"
                "💡 راه ساده‌تر: دستور `پنل` را بفرستید و قفل‌ها را با دکمه روشن/خاموش کنید."
            ),
            "help_locks_words": (
                "🔤 **مدیریت کلمات مسدود**\n\n"
                "• `مسدود کلمه <متن>` - مسدود کردن یک کلمه خاص\n"
                "• `بازکردن کلمه <متن>` - آزاد کردن کلمه مسدود\n\n"
                "**مثال:**\n"
                "• `مسدود کلمه بی‌ادبی` - هر پیامی که شامل «بی‌ادبی» باشد حذف می‌شود\n\n"
                "💡 اگر کلمه چندکلمه‌ای باشد در هر جای متن حذف می‌شود؛ اگر تک‌کلمه‌ای باشد دقیقاً همان کلمه."
            ),
            "help_locks_post": (
                "📌 **قفل پست‌های کانال**\n\n"
                "• `قفل پست` (ریپلای روی پست کانال) - غیرفعال کردن کامنت روی پست\n"
                "• `باز کردن پست` (ریپلای) - فعال کردن دوباره کامنت\n\n"
                "💡 وقتی پست قفل باشد، کامنت‌های ارسال‌شده روی آن حذف می‌شوند."
            ),
            "help_locks_antiabuse": (
                "🛑 **ضد اسپم، فلاد و حمله**\n\n"
                "**اسپم:**\n"
                "• `قفل اسپم` / `بازکردن اسپم` - جلوگیری از پیام‌های تکراری و سریع\n\n"
                "**فلاد:**\n"
                "• `قفل فلاد` / `بازکردن فلاد` - جلوگیری از ارسال پشت‌سرهم خیلی سریع\n\n"
                "**ضد حمله (Anti-Raid):**\n"
                "• `قفل حمله` / `بازکردن حمله` - جلوگیری از ورود انبوه اعضا\n"
                "• `تنظیم سقف حمله <عدد>` - حداکثر ورود عضو در بازه (پیش‌فرض: ۵)\n"
                "• `تنظیم بازه حمله <ثانیه>` - بازه زمانی تشخیص حمله (پیش‌فرض: ۳۰)\n\n"
                "**مثال:**\n"
                "• `تنظیم سقف حمله 10`\n"
                "• `تنظیم بازه حمله 60`"
            ),
            "help_locks_captcha": (
                "🤖 **کپچای ورود اعضا**\n\n"
                "• `قفل کپچا` - فعال کردن کپچا برای اعضای جدید\n"
                "• `بازکردن کپچا` - غیرفعال کردن کپچا\n\n"
                "💡 با فعال بودن کپچا، اعضای جدید باید یک معما را حل کنند؛ این کار از ورود ربات‌ها و اکانت‌های جعلی جلوگیری می‌کند."
            ),
            "help_locks_panel": (
                "💡 **پنل مدیریت قفل**\n\n"
                "• `پنل قفل` - نمایش پنل گرافیکی قفل‌ها با دکمه روشن/خاموش\n"
                "• `پنل` - نمایش پنل جامع (همه قفل‌ها + تنظیمات + دسترسی به راهنما)\n\n"
                "💡 با دکمه‌های پنل می‌توانید قفل‌ها را بدون تایپ کردن روشن/خاموش کنید."
            ),

            "help_filters_add": (
                "➕ **افزودن فیلتر (پاسخ خودکار)**\n\n"
                "روی پیامی که می‌خواهید پاسخ داده شود **ریپلای** کنید و بنویسید:\n"
                "`فیلتر <پاسخ مورد نظر>`\n\n"
                "**مثال:**\n"
                "1. روی پیام «سلام» ریپلای کنید\n"
                "2. بنویسید: `فیلتر علیک سلام`\n"
                "3. از این به بعد هرکس «سلام» بنویسد، جواب «علیک سلام» می‌گیرد\n\n"
                "💡 فیلترها به حروف بزرگ و کوچک حساس نیستند."
            ),
            "help_filters_remove": (
                "➖ **حذف فیلتر**\n\n"
                "**روش اول:**\n"
                "روی پیام فیلتر شده ریپلای کنید و بنویسید:\n"
                "`حذف فیلتر`\n\n"
                "**روش دوم:**\n"
                "`حذف فیلتر <کلمه کلیدی>`\n\n"
                "**مثال:**\n"
                "• `حذف فیلتر سلام` - فیلتر «سلام» را حذف می‌کند"
            ),
            "help_filters_list": (
                "📋 **مشاهده فیلترها**\n\n"
                "• `فیلترها` - نمایش لیست تمام فیلترهای گروه\n\n"
                "💡 این دستور برای همه اعضا (در صورت روشن بودن دستورات عمومی) قابل استفاده است."
            ),

            "help_public_toggle": (
                "⚙️ **فعال / غیرفعال کردن دستورات عمومی**\n\n"
                "• `دستورات عمومی روشن` - همه اعضا می‌توانند از دستورات عمومی استفاده کنند\n"
                "• `دستورات عمومی خاموش` - فقط ادمین‌ها می‌توانند از دستورات استفاده کنند\n\n"
                "💡 پیش‌فرض: روشن"
            ),
            "help_public_cmds": (
                "💬 **لیست دستورات عمومی (برای همه اعضا)**\n\n"
                "• `لینک` - دریافت لینک دعوت اختصاصی\n"
                "• `قوانین` - مشاهده قوانین گروه\n"
                "• `فیلترها` - مشاهده فیلترهای فعال\n"
                "• `اکو <متن>` - تکرار متن\n"
                "• `کمک یار` - منو و راهنما\n"
                "• `@admins` - منشن کردن همه ادمین‌ها\n"
                "• `گزارش` (ریپلای) - گزارش پیام به ادمین‌ها\n"
                "• `اطلاعات` (ریپلای) - اطلاعات کاربر\n"
                "• `لقب` (ریپلای) - لقب کاربر\n"
                "• `اصل` (ریپلای) - اصل و نسب کاربر"
            ),

            "help_invite_make": (
                "🔗 **ساخت لینک دعوت**\n\n"
                "• `لینک` - ساخت لینک دعوت اختصاصی شما\n\n"
                "💡 هر کاربر می‌تواند لینک اختصاصی خودش را بسازد و لینک‌ها با نام سازنده ذخیره می‌شوند."
            ),
            "help_invite_limits": (
                "🔢 **تنظیم حداکثر دعوت**\n\n"
                "• `تنظیم حداکثر دعوت <عدد>` - محدودیت تعداد استفاده از لینک\n\n"
                "**مثال:**\n"
                "• `تنظیم حداکثر دعوت 50` - هر لینک فقط ۵۰ بار قابل استفاده است\n\n"
                "💡 اگر حداکثری تعیین نشده باشد، لینک نامحدود است."
            ),
            "help_invite_request": (
                "✅ **درخواست برای ورود**\n\n"
                "• `درخواست برای ورود` - روشن/خاموش کردن نیاز به تایید ادمین برای ورود\n\n"
                "💡 وقتی روشن باشد، افرادی که با لینک وارد می‌شوند باید توسط ادمین تایید شوند."
            ),

            "help_settings_texts": (
                "📝 **تنظیم متون**\n\n"
                "• `تنظیم خوشامد` (ریپلای روی پیام حاوی متن جدید) - تغییر متن خوشامدگویی\n"
                "• `تنظیم قوانین` (ریپلای) - تغییر قوانین گروه\n"
                "• `تنظیم متن کامنت` (ریپلای) - تغییر متن زیر پست‌های کانال\n\n"
                "**مثال:**\n"
                "1. پیامی بنویسید: `به {name} خوش آمدید!`\n"
                "2. روی همان پیام ریپلای کنید و بنویسید `تنظیم خوشامد`"
            ),
            "help_settings_vars": (
                "🔤 **متغیرهای متن خوشامد**\n\n"
                "• `{name}` - نام کاربر جدید\n"
                "• `{username}` - یوزرنیم کاربر\n"
                "• `{id}` - آیدی عددی کاربر\n"
                "• `{chat}` - نام گروه\n"
                "• `{members}` - تعداد اعضای گروه\n\n"
                "**نمونه متن خوشامد:**\n"
                "`{name} عزیز خوش اومدی به {chat}! الان {members} نفر هستیم 🎉`"
            ),
            "help_settings_bots": (
                "🤖 **مدیریت بات‌ها**\n\n"
                "• `بلاک بات @username` - مسدود کردن یک بات در گروه\n"
                "• `آن‌بلاک بات @username` - آزاد کردن بات\n"
                "• `بات های بلاک شده` - لیست بات‌های مسدود\n\n"
                "**مثال:**\n"
                "• `بلاک بات @somebot`"
            ),
            "help_settings_misc": (
                "🛠️ **سایر تنظیمات**\n\n"
                "• `باادب شو` / `بی ادب شو` - تغییر لحن پاسخ‌های بات\n"
                "• `دستورات عمومی روشن / خاموش` - کنترل دسترسی همه به دستورات عمومی\n"
                "• `ریست` - بازنشانی تنظیمات گروه (فیلترها باقی می‌مانند)\n"
                "• `درخواست کمک` - درخواست ورود اونر بات به گروه برای مشکلات فوری\n"
                "• `پنل` - نمایش پنل جامع مدیریت"
            ),

            "help_warnings_warn": (
                "⚠️ **اخطار و مجازات**\n\n"
                "• `اخطار` (ریپلای) - ثبت اخطار برای کاربر\n"
                "• `حذف اخطارها` (ریپلای) - پاک کردن تمام اخطارهای کاربر\n"
                "• `سقف اخطار <عدد>` - تعیین حداکثر اخطار (پیش‌فرض: 3)\n"
                "• `تعیین مجازات اخطار` - انتخاب مجازات (کیک/بن/میوت) هنگام رسیدن به سقف\n\n"
                "**مثال:**\n"
                "• `سقف اخطار 5` - بعد از ۵ اخطار مجازات اجرا می‌شود"
            ),
            "help_warnings_report": (
                "📢 **گزارش به ادمین**\n\n"
                "• `گزارش` (ریپلای روی پیام) - گزارش یک پیام به همه ادمین‌ها\n\n"
                "💡 ادمین‌ها می‌توانند گزارش را در پیوی خود بررسی کنند. گزارش‌ها شامل لینک مستقیم به پیام هستند."
            ),

            "help_profile_set": (
                "✏️ **ثبت لقب و اصل**\n\n"
                "• `ثبت لقب <متن>` (ریپلای روی خود یا دیگران) - ثبت لقب برای کاربر\n"
                "• `ثبت اصل <متن>` (ریپلای) - ثبت اصل و نسب\n\n"
                "**مثال:**\n"
                "1. روی پیام کاربر ریپلای کنید\n"
                "2. بنویسید: `ثبت لقب دانشمند بزرگ`\n\n"
                "💡 ادمین‌ها می‌توانند برای دیگران ثبت کنند، بقیه فقط برای خودشان."
            ),
            "help_profile_view": (
                "👀 **مشاهده اطلاعات**\n\n"
                "• `لقب` (ریپلای) - مشاهده لقب کاربر\n"
                "• `اصل` (ریپلای) - مشاهده اصل کاربر\n"
                "• `اطلاعات` (ریپلای) - اطلاعات کامل (آیدی، وضعیت، عکس)"
            ),

            "help_antivirus": (
                "🛡️ **ضدویروس فایل**\n\n"
                "**نحوه عملکرد:**\n"
                "با ارسال فایل‌های متنی (مثل `txt`, `py`, `js` و...) در گروه، ربات به صورت خودکار محتوای فایل را بررسی می‌کند و در صورت تشخیص بدافزار هشدار می‌دهد.\n\n"
                "**معنای واکنش‌های ربات روی فایل:**\n"
                "• `🤔` - در حال بررسی فایل\n"
                "• `👍` - فایل سالم است\n"
                "• `💀` - بدافزار تشخیص داده شد!\n"
                "• `❓` - محتوای فایل قابل خواندن نبود\n"
                "• `🥴` - نوع فایل پشتیبانی نمی‌شود یا فایل بزرگ‌تر از سقف مجاز است (بررسی نمی‌شود)\n\n"
                "**فایل‌های قابل بررسی:**\n"
                "`txt`, `py`, `js`, `html`, `css`, `json`, `xml`, `md`, `csv`, `log`, `sh`, `bat`, `ps1`, `php`, `java`, `cs`, `cpp`, `c`, `h`, `hpp`, `rb`, `pl`, `go`, `rs`\n\n"
                f"💡 فایل‌های بزرگ‌تر از حدود `{_size_mb:.1f}MB` بدون دانلود رد می‌شوند تا پهنای باند ربات مصرف نشود."
            ),

            "help_whisper": (
                "🕵️ **نجوا (ارسال پیام خصوصی)**\n\n"
                "از طریق **Inline Mode** می‌توانید به کاربران دیگر پیام خصوصی بفرستید بدون اینکه دیگران ببینند.\n\n"
                "**طریقه استفاده:**\n"
                "1. در باکس پیام، `@username_ربات` را تایپ کنید\n"
                "2. بنویسید: `<متن پیام> @username_مقصد`\n"
                "3. مثال: `@KomakYaarBot سلام چطوری؟ @Ali`\n"
                "4. روی نتیجه کلیک کنید و ارسال کنید\n\n"
                "**نکات مهم:**\n"
                "• فقط فرستنده و گیرنده می‌توانند پیام را بخوانند\n"
                "• پیام‌ها در دیتابیس رمزنگاری می‌شوند\n"
                "• نمی‌توانید به خودتان یا به ربات پیام بفرستید\n"
                "• در پیوی شخصی نمی‌توانید استفاده کنید"
            ),

            "help_bridge": (
                "🌉 **پل ارتباطی (Telegram ↔ Bale)**\n\n"
                "**قابلیت:**\n"
                "ارسال خودکار تمام پیام‌ها، عکس‌ها، ویدیوها و فایل‌ها از یک کانال تلگرام به کانال بله (و بالعکس).\n\n"
                "**تنظیم پل از تلگرام به بله:**\n"
                "1. ربات را به عنوان ادمین در **کانال تلگرام** و **کانال بله** اضافه کنید.\n"
                f"آیدی ربات در بله: [@{self.bale_bot_me.username}](https://ble.ir/{self.bale_bot_me.username})\n"
                "2. در کانال بله دستور `/getid` را ارسال کنید تا آیدی کانال بله را بگیرید.\n"
                "3. در **کانال تلگرام** دستور زیر را ارسال کنید:\n"
                "`/setbridge آیدی_کانال_بله`\n\n"
                "**حذف پل:**\n"
                "در کانال تلگرام:\n"
                "`/removebridge آیدی_کانال_بله`\n\n"
                "**نکات مهم:**\n"
                "• پل فقط روی **کانال‌ها** کار می‌کند (نه گروه).\n"
                "• ربات باید ادمین هر دو کانال باشد.\n"
                "• فورواردها، عکس، ویدیو، گیف، استیکر، صدا و فایل پشتیبانی می‌شوند.\n"
                "• بریج دوطرفه است؛ محتوای تلگرام به بله و بالعکس منتقل می‌شود.\n\n"
                "💡 **مثال:**\n"
                "`/setbridge -1001234567890`"
            ),

            "help_faq": (
                "❓ **سوالات متداول**\n\n"
                "**۱. چرا بات پاسخ نمی‌دهد؟**\n"
                "• مطمئن شوید دستور `فعال شو` را فرستاده باشید\n"
                "• بررسی کنید بات ادمین گروه باشد\n"
                "• گروه ممکن است بن شده باشد\n\n"
                "**۲. چگونه تنظیمات را ریست کنم؟**\n"
                "• از دستور `ریست` استفاده کنید\n"
                "• فیلترها حذف نمی‌شوند، فقط تنظیمات ریست می‌شوند\n\n"
                "**۳. چرا لینک دعوت کار نمی‌کند؟**\n"
                "• بررسی کنید `تنظیم حداکثر دعوت` را تنظیم کرده‌اید\n"
                "• اگر `درخواست برای ورود` فعال است، افراد باید تایید شوند\n\n"
                "**۴. چگونه از شر پیام‌های اسپم خلاص شوم؟**\n"
                "• از قفل‌های لینک، فحش و فوروارد استفاده کنید\n"
                "• کلمات نامناسب را با `مسدود کلمه` اضافه کنید\n\n"
                "**۵. آیا بات اوپن سورس است؟**\n"
                "• بله! کد بات در گیت‌هاب موجود است:\n"
                "• https://github.com/Code-Wizaard/KomakYaar"
            ),
        }

        self.guide_sub_parent = {}
        for parent, cat in self.guide_categories.items():
            for sub_cb, _ in cat.get("subs", []):
                self.guide_sub_parent[sub_cb] = parent

        # Main help keyboard - built from categories
        self.help_keyboard = types.InlineKeyboardMarkup(row_width=2)
        for cb, cat in self.guide_categories.items():
            self.help_keyboard.add(types.InlineKeyboardButton(cat["title"], callback_data=cb))

        # Start keyboard for private chat
        self.start_keyboard = types.InlineKeyboardMarkup(row_width=2)
        self.start_keyboard.add(
            types.InlineKeyboardButton("➕ اضافه کردن به گروه", url=f"https://t.me/{self.me.username}?startgroup"),
            types.InlineKeyboardButton("📖 راهنمای سریع", callback_data="help_main"),
            types.InlineKeyboardButton("💻 گیت‌هاب پروژه", url="https://github.com/Code-Wizaard/KomakYaar")
        )

        # Back button keyboard
        self.back_keyboard = types.InlineKeyboardMarkup(row_width=1)
        self.back_keyboard.add(
            types.InlineKeyboardButton("🔙 برگشت به منوی اصلی", callback_data="help_main")
        )
        self.db = DataBase(self.bot)
        self.anti_spam = AntiSpam(self.db)
        self.anti_virus = AntiVirus()
        self.profanity_detector = ProfanityDetector()
        self.join_tracker = {}
        self.raid_active = {}
        self.captchas = {}
        self.setup_events()
    
    async def apply_group_permissions(self, chat_id):
        """Apply full permissions to the group based on its settings"""
        try:
            group_locked = bool(int(await self.db.get_group_setting(chat_id, "GROUP_LOCK", 0)))
            gif_locked = bool(int(await self.db.get_group_setting(chat_id, "GIF_LOCK", 0)))
            inline_locked = bool(int(await self.db.get_group_setting(chat_id, "INLINE_LOCK", 0)))
            
            permissions = types.ChatPermissions(
                can_send_messages=not group_locked,
                can_send_photos=not group_locked,
                can_send_videos=not group_locked,
                can_send_documents=not group_locked,
                can_send_stickers=not group_locked,
                can_send_animations=not (group_locked or gif_locked),
                can_send_audios=not group_locked,
                can_send_voices=not group_locked,
                can_send_video_notes=not group_locked,
                can_send_polls=not group_locked,
                can_send_other_messages=not (group_locked or inline_locked),
            )
            await self.bot.set_chat_permissions(chat_id, permissions)
        except Exception as e:
            print(f"Permission apply error: {e}")

    @staticmethod
    def sender_chat_id(message):
        sender_chat = getattr(message, 'sender_chat', None)
        return sender_chat.id if sender_chat else None

    async def send_welcome(self, message, user):
        template = await self.db.member_template(message.chat.id)
        text = template
        text = text.replace("{name}", user.first_name)
        text = text.replace("{username}", f"@{user.username}" if user.username else user.first_name)
        text = text.replace("{id}", str(user.id))
        text = text.replace("{chat}", message.chat.title)
        try:
            member_count = await self.bot.get_chat_member_count(message.chat.id)
        except:
            member_count = "نامشخص"
        text = text.replace("{members}", str(member_count))
        await self.bot.send_message(message.chat.id, text)

    async def check_raid(self, chat_id):
        now = time.time()
        window = int(await self.db.get_group_setting(chat_id, "RAID_WINDOW", 30))
        threshold = int(await self.db.get_group_setting(chat_id, "RAID_THRESHOLD", 5))
        stamps = self.join_tracker.setdefault(chat_id, [])
        stamps.append(now)
        self.join_tracker[chat_id] = [s for s in stamps if now - s <= window]
        if len(self.join_tracker[chat_id]) >= threshold:
            self.raid_active[chat_id] = now
            return True
        return False

    async def is_raid_active(self, chat_id):
        until = self.raid_active.get(chat_id, 0)
        return time.time() - until < 60

    async def start_captcha(self, message, user):
        chat_id = message.chat.id
        key = (chat_id, user.id)
        timeout = int(await self.db.get_group_setting(chat_id, "CAPTCHA_TIMEOUT", 300))
        try:
            await self.bot.restrict_chat_member(
                chat_id, user.id,
                until_date=int(time.time()) + timeout + 60,
                can_send_messages=False
            )
        except Exception:
            pass
        a = random.randint(1, 9)
        b = random.randint(1, 9)
        answer = a + b
        options = [answer]
        while len(options) < 4:
            o = answer + random.randint(-3, 3)
            if o > 0 and o != answer and o not in options:
                options.append(o)
        random.shuffle(options)
        token = secrets.token_hex(4)
        kb = types.InlineKeyboardMarkup(row_width=2)
        for o in options:
            kb.add(types.InlineKeyboardButton(str(o), callback_data=f"captcha:{chat_id}:{token}:{o}"))
        msg = await self.bot.send_message(
            chat_id,
            f"[{user.first_name}](tg://user?id={user.id}) برای اثبات انسان بودن، حاصل جمع را انتخاب کن:\n\n{a} + {b} = ؟",
            parse_mode="Markdown",
            reply_markup=kb
        )
        task = asyncio.create_task(self.captcha_timeout(chat_id, user.id, token, timeout))
        self.captchas[key] = {"answer": answer, "attempts": 0, "msg_id": msg.message_id, "token": token, "task": task}

    async def captcha_timeout(self, chat_id, user_id, token, timeout):
        await asyncio.sleep(timeout)
        key = (chat_id, user_id)
        entry = self.captchas.get(key)
        if entry and entry.get("token") == token:
            try:
                await self.bot.delete_message(chat_id, entry["msg_id"])
            except Exception:
                pass
            try:
                await self.bot.ban_chat_member(chat_id, user_id)
                await self.bot.unban_chat_member(chat_id, user_id)
            except Exception:
                pass
            self.captchas.pop(key, None)

    async def captcha_success(self, chat_id, user_id, user_name):
        try:
            await self.bot.restrict_chat_member(
                chat_id, user_id,
                can_send_messages=True,
                can_send_media_messages=True,
                can_add_web_page_previews=True,
                can_send_polls=True,
                can_send_other_messages=True
            )
        except Exception:
            pass
        await self.bot.send_message(chat_id, f"[{user_name}](tg://user?id={user_id}) تایید شد! خوش اومدی", parse_mode="Markdown")

    async def build_lock_panel(self, chat_id):
        kb = types.InlineKeyboardMarkup(row_width=2)
        locks = {
            "link": "لینک", "forward": "فوروارد", "swear": "فحش", "group": "گروه",
            "gif": "گیف", "spam": "اسپم", "flood": "فلاد", "inline": "اینلاین",
            "raid": "حمله", "captcha": "کپچا",
        }
        for latin, persian in locks.items():
            on = int(await self.db.get_group_setting(chat_id, latin.upper() + "_LOCK", 0)) == 1
            kb.add(types.InlineKeyboardButton(
                f"قفل {persian} {'✅' if on else '❌'}",
                callback_data=f"lock_{latin}:" + ("off" if on else "on")
            ))
        return kb

    async def build_global_panel(self, chat_id):
        locks = {
            "link": "لینک", "forward": "فوروارد", "swear": "فحش", "group": "گروه",
            "gif": "گیف", "spam": "اسپم", "flood": "فلاد", "inline": "اینلاین",
            "raid": "حمله", "captcha": "کپچا",
        }
        punishment_map = {"kick": "کیک", "ban": "بن", "mute": "میوت"}

        lines = ["📊 **پنل جامع مدیریت گروه**\n"]
        lines.append("🔒 **قفل‌ها:**")
        lock_states = {}
        for latin, persian in locks.items():
            on = int(await self.db.get_group_setting(chat_id, latin.upper() + "_LOCK", 0)) == 1
            lock_states[latin] = on
            lines.append(f"• قفل {persian}: {'✅ فعال' if on else '❌ غیرفعال'}")
        lines.append("")
        lines.append("⚙️ **تنظیمات:**")
        polite = int(await self.db.get_group_setting(chat_id, "POLITE_MODE", 1)) == 1
        public = int(await self.db.get_group_setting(chat_id, "PUBLIC_COMMANDS", 1)) == 1
        raid_threshold = await self.db.get_group_setting(chat_id, "RAID_THRESHOLD", 5)
        raid_window = await self.db.get_group_setting(chat_id, "RAID_WINDOW", 30)
        warn_max = await self.db.get_group_setting(chat_id, "WARN_MAXIMUM", 3)
        warn_punishment = punishment_map.get(await self.db.get_group_setting(chat_id, "WARN_PUNISHMENT", "kick"), "کیک")
        invite_max = await self.db.get_group_setting(chat_id, "invite_maximum", "نامحدود")
        lines.append(f"• لحن بات: {'باادب 🎩' if polite else 'بی‌ادب 😈'}")
        lines.append(f"• دستورات عمومی: {'روشن ✅' if public else 'خاموش ❌'}")
        lines.append(f"• سقف حمله: {raid_threshold} | بازه حمله: {raid_window} ثانیه")
        lines.append(f"• سقف اخطار: {warn_max} | مجازات اخطار: {warn_punishment}")
        lines.append(f"• حداکثر دعوت: {invite_max}")
        text = "\n".join(lines)

        kb = types.InlineKeyboardMarkup(row_width=2)
        for latin, persian in locks.items():
            on = lock_states[latin]
            kb.add(types.InlineKeyboardButton(
                f"قفل {persian} {'✅' if on else '❌'}",
                callback_data=f"lock_{latin}:" + ("off" if on else "on")
            ))
        kb.add(
            types.InlineKeyboardButton(f"لحن باادب {'✅' if polite else '❌'}", callback_data="panel_polite"),
            types.InlineKeyboardButton(f"دستورات عمومی {'✅' if public else '❌'}", callback_data="panel_public")
        )
        kb.add(
            types.InlineKeyboardButton("📖 راهنمای گام به گام", callback_data="help_main"),
            types.InlineKeyboardButton("بستن پنل", callback_data="close_panel")
        )
        return text, kb

    def setup_events(self):
        check = lambda require_admin=False: handler_check(self.bot, self.db, self.anti_spam, require_admin)
        @self.bot.message_handler(func=lambda m: m.text == "فعال شو")
        async def cmd_startgroup(message):
            if await self.db.is_group_blocked(message.chat.id):
                return
            if await self.db.is_group_active(message.chat.id):
                await self.bot.reply_to(message, "گروه از قبل فعال شده بود" if int(await self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "گروه که از قبل فعال بود کصخل")
                return
            if not await self.db.is_admin(message.chat.id, message.from_user.id, self.sender_chat_id(message)):
                await self.bot.reply_to(message, "دوست عزیز، شما دسترسی ادمین ندارید" if int(await self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "اخه تو ادمینی؟")
                return
            await self.db.ensure_group(message.chat.id)
            await self.db.set_group_active(message.chat.id)
            await self.bot.reply_to(message, "✅ گروه فعال شد و بات آماده مدیریت است!")

        @self.bot.message_handler(func=lambda m: m.text == "سیکتیر کن")
        @check(require_admin=True)
        async def leaver(message):
            await self.bot.reply_to(message, "ناراحت شدم، میرم سیکتیر کنم")
            await self.bot.leave_chat(message.chat.id)


        @self.bot.message_handler(func=lambda m: m.text == "راهنما")
        @check()
        async def send_help(message):
            try:
                await self.bot.send_message(message.from_user.id, HELP_TEXT, parse_mode="Markdown", reply_markup=self.help_keyboard)
                if message.chat.type != "private":
                    await self.bot.reply_to(message, "📬 پنل راهنما به پیوی شما ارسال شد!")
            except:
                await self.bot.reply_to(message, "⚠️ نمی‌تونم پیوی شما پیام بفرستم، لطفا دایرکت ربات رو باز کنید.")


        @self.bot.message_handler(func=lambda m: m.text == "ریست")
        @check(require_admin=True)
        async def reset_bot_in_group(message):
            msg = await self.bot.reply_to(message, "حله، الان کل رکورد گروه (بجز فیلتر ها) رو پاک و بازنویسی از صفر میکنم، انگار که هیچ اتفاقی نیوفتاده")
            await self.db.reset_group(message.chat.id)
            await self.bot.edit_message_text("خب، تموم شد، همه چی ریست شد", message.chat.id, msg.id)

        @self.bot.message_handler(func=lambda m: m.text.startswith("تنظیم حداکثر دعوت"))
        @check(require_admin=True)
        async def change_maximum(message:types.Message):
            if message.text[len("تنظیم حداکثر دعوت"):].strip().isdigit():
                maximum = int(message.text[len("تنظیم حداکثر دعوت"):].strip())
                await self.db.set_group_setting(message.chat.id, "invite_maximum", maximum)
                if bool(int(await self.db.get_group_setting(message.chat.id, "creates_request", 0))):
                    await self.db.delete_group_setting(message.chat.id, "creates_request")
                await self.bot.reply_to(message, f"حداکثر تعداد دعوت به {maximum} دعوت تغییر پیدا کرد")
            else:
                await self.bot.reply_to(message, "کصخل اشتباه نوشتی")

        @self.bot.message_handler(func=lambda m: m.text == "قفل فحش")
        @check(require_admin=True)
        async def active_swear_strict(message:types.Message):
            if int(await self.db.get_group_setting(message.chat.id, "SWEAR_LOCK", 0)) in [-1, 1]:
                await self.db.set_group_setting(message.chat.id, "SWEAR_LOCK", 1)
                await self.bot.reply_to(message, "ضدفحش در حال حاضر نیز فعال است" if int(await self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "همینطوریشم فعال هست ستونم")
            else:
                await self.db.set_group_setting(message.chat.id, "SWEAR_LOCK", 1)
                await self.bot.reply_to(message, "قفل فعال شد")

        @self.bot.message_handler(func=lambda m: m.text == "بازکردن فحش")
        @check(require_admin=True)
        async def active_swear_strict(message:types.Message):
            if int(await self.db.get_group_setting(message.chat.id, "SWEAR_LOCK", 0)) in [-1, 0]:
                await self.db.set_group_setting(message.chat.id, "SWEAR_LOCK", 0)
                await self.bot.reply_to(message, "ضدفحش در حال حاضر نیز غیرفعال است" if int(await self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "همینطوریشم غیرفعال هست ستونم")
            else:
                await self.db.set_group_setting(message.chat.id, "SWEAR_LOCK", 0)
                await self.bot.reply_to(message, "قفل غیرفعال شد")

        @self.bot.message_handler(func=lambda m: m.text == "قفل گروه")
        @check(require_admin=True)
        async def lock_group(message: types.Message):
            if int(await self.db.get_group_setting(message.chat.id, "GROUP_LOCK", 0)) == 0:
                await self.db.set_group_setting(message.chat.id, "GROUP_LOCK", 1)
                await self.bot.reply_to(message, "گروه با موفقیت قفل شد" if int(await self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "کسی خایه داره پیام بده")
                await self.apply_group_permissions(message.chat.id)
            else:
                await self.bot.reply_to(message, "گروه از قبل نیز قفل بود" if int(await self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "گروه که از قبل قفل بود کصخل")

        @self.bot.message_handler(func=lambda m: m.text == "بازکردن گروه")
        @check(require_admin=True)
        async def unlock_group(message: types.Message):
            if int(await self.db.get_group_setting(message.chat.id, "GROUP_LOCK", 0)) == 0:
                await self.bot.reply_to(message, "گروه از قبل نیز باز بود" if int(await self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "گروه که از قبل باز بود کصخل")
            else:
                await self.db.set_group_setting(message.chat.id, "GROUP_LOCK", 0)
                await self.bot.reply_to(message, "گروه با موفقیت باز شد" if int(await self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "راحت گوه بخورید")
                await self.apply_group_permissions(message.chat.id)

        @self.bot.message_handler(func=lambda m: m.text == "بی ادب شو")
        @check(require_admin=True)
        async def turn_rude(message: types.Message):
            if int(await self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1:
                await self.db.set_group_setting(message.chat.id, "POLITE_MODE", 0)
                await self.bot.reply_to(message, "وقتشه کیری حرف بزنم")
            else:
                await self.bot.reply_to(message, "کصمغز منکه از قبلشم بی ادب بودم")

        @self.bot.message_handler(func=lambda m: m.text in ["باادب شو", "با ادب شو"])
        @check(require_admin=True)
        async def turn_polite(message: types.Message):
            if int(await self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1:
                await self.bot.reply_to(message, "بنده از قبل باادب بوده‌ام")
            else:
                await self.db.set_group_setting(message.chat.id, "POLITE_MODE", 1)
                await self.bot.reply_to(message, "ادب کیری مهمه، من باادب میشم")

        @self.bot.message_handler(func=lambda m: m.text == "قفل لینک")
        @check(require_admin=True)
        async def link_blocker(message: types.Message):
            if int(await self.db.get_group_setting(message.chat.id, "LINK_LOCK", 0)) == 1:
                await self.bot.reply_to(message, "ضدلینک در حال حاضر نیز فعال است" if int(await self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "خیالت راحت باشه نمیگفتی هم لینکارو پاک میکردم")
            else:
                await self.db.set_group_setting(message.chat.id, "LINK_LOCK", 1)
                await self.bot.reply_to(message, "ضدلینک فعال شد" if int(await self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "ردیفه ستون اوکیش کردم")

        @self.bot.message_handler(func= lambda m: m.text == "بازکردن لینک")
        @check(require_admin=True)
        async def link_unblocking(message: types.Message):
            if int(await self.db.get_group_setting(message.chat.id, "LINK_LOCK", 0)) == 0:
                await self.bot.reply_to(message, "ضدلینک از قبل نیز غیرفعال بود" if int(await self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "باع، قفل که قبلشم باز بود")
            else:
                await self.db.set_group_setting(message.chat.id, "LINK_LOCK", 0)
                await self.bot.reply_to(message, "ضدلینک غیرفعال شد" if int(await self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "انقدر لینکو باز کردم تا جر خورد (اوکی)")

        @self.bot.message_handler(func=lambda m: m.text == "قفل فوروارد")
        @check(require_admin=True)
        async def forward_blocker(message: types.Message):
            if int(await self.db.get_group_setting(message.chat.id, "FORWARD_LOCK", 0)) == 1:
                await self.bot.reply_to(message, "ضدفوروارد در حال حاضر نیز فعال است" if int(await self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "خیالت راحت باشه نمیگفتی هم فورواردارو پاک میکردم")
            else:
                await self.db.set_group_setting(message.chat.id, "FORWARD_LOCK", 1)
                await self.bot.reply_to(message, "ضدفوروارد فعال شد" if int(await self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "ردیفه ستون اوکیش کردم")

        @self.bot.message_handler(func=lambda m: m.text == "بازکردن فوروارد")
        @check(require_admin=True)
        async def forward_unblocking(message: types.Message):
            if int(await self.db.get_group_setting(message.chat.id, "FORWARD_LOCK", 0)) == 0:
                await self.bot.reply_to(message, "ضدفوروارد از قبل نیز غیرفعال بود" if int(await self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "باع، قفل که قبلشم باز بود")
            else:
                await self.db.set_group_setting(message.chat.id, "FORWARD_LOCK", 0)
                await self.bot.reply_to(message, "ضدفوروارد غیرفعال شد" if int(await self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "انقدر فورواردارو باز کردم تا جر خورد (اوکی)")

        @self.bot.message_handler(func=lambda m: m.text == "قفل گیف")
        @check(require_admin=True)
        async def gif_lock(message: types.Message):
            if int(await self.db.get_group_setting(message.chat.id, "GIF_LOCK", 0)) == 1:
                await self.bot.reply_to(message, "ضدگیف در حال حاضر نیز فعال است" if int(await self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "خیالت راحت باشه نمیگفتی هم گیفارو پاک میکردم")
            else:
                await self.db.set_group_setting(message.chat.id, "GIF_LOCK", 1)
                await self.bot.reply_to(message, "ضدگیف فعال شد" if int(await self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "ردیفه ستون اوکیش کردم")

        @self.bot.message_handler(func=lambda m: m.text == "بازکردن گیف")
        @check(require_admin=True)
        async def gif_unlock(message: types.Message):
            if int(await self.db.get_group_setting(message.chat.id, "GIF_LOCK", 0)) == 0:
                await self.bot.reply_to(message, "ضدگیف از قبل نیز غیرفعال بود" if int(await self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "باع، قفل که قبلشم باز بود")
            else:
                await self.db.set_group_setting(message.chat.id, "GIF_LOCK", 0)
                await self.bot.reply_to(message, "ضدگیف غیرفعال شد" if int(await self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "انقدر گیفارو باز کردم تا جر خورد (اوکی)")

        @self.bot.message_handler(func=lambda m: m.text == "قفل حمله")
        @check(require_admin=True)
        async def raid_lock(message: types.Message):
            if int(await self.db.get_group_setting(message.chat.id, "RAID_LOCK", 0)) == 1:
                await self.bot.reply_to(message, "ضد حمله در حال حاضر نیز فعال است" if int(await self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "حله دیگه، همونطوریشم فعاله")
            else:
                await self.db.set_group_setting(message.chat.id, "RAID_LOCK", 1)
                await self.bot.reply_to(message, "ضد حمله فعال شد، ورود انبوه اعضا کنترل می‌شود")

        @self.bot.message_handler(func=lambda m: m.text == "بازکردن حمله")
        @check(require_admin=True)
        async def raid_unlock(message: types.Message):
            if int(await self.db.get_group_setting(message.chat.id, "RAID_LOCK", 0)) == 0:
                await self.bot.reply_to(message, "ضد حمله از قبل نیز غیرفعال بود" if int(await self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "باع، که قبلشم باز بود")
            else:
                await self.db.set_group_setting(message.chat.id, "RAID_LOCK", 0)
                await self.bot.reply_to(message, "ضد حمله غیرفعال شد")

        @self.bot.message_handler(func=lambda m: m.text.startswith("تنظیم سقف حمله "))
        @check(require_admin=True)
        async def raid_threshold(message: types.Message):
            val = message.text[len("تنظیم سقف حمله "):].strip()
            if val.isdigit():
                await self.db.set_group_setting(message.chat.id, "RAID_THRESHOLD", int(val))
                await self.bot.reply_to(message, f"سقف ورود انبوه به {val} عضو تنظیم شد")
            else:
                await self.bot.reply_to(message, "عدد معتبر وارد کن")

        @self.bot.message_handler(func=lambda m: m.text.startswith("تنظیم بازه حمله "))
        @check(require_admin=True)
        async def raid_window(message: types.Message):
            val = message.text[len("تنظیم بازه حمله "):].strip()
            if val.isdigit():
                await self.db.set_group_setting(message.chat.id, "RAID_WINDOW", int(val))
                await self.bot.reply_to(message, f"بازه تشخیص حمله به {val} ثانیه تنظیم شد")
            else:
                await self.bot.reply_to(message, "عدد معتبر وارد کن")

        @self.bot.message_handler(func=lambda m: m.text == "قفل کپچا")
        @check(require_admin=True)
        async def captcha_lock(message: types.Message):
            if int(await self.db.get_group_setting(message.chat.id, "CAPTCHA_LOCK", 0)) == 1:
                await self.bot.reply_to(message, "کپچا در حال حاضر نیز فعال است" if int(await self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "همینطوریشم فعاله کصخل")
            else:
                await self.db.set_group_setting(message.chat.id, "CAPTCHA_LOCK", 1)
                await self.bot.reply_to(message, "کپچا فعال شد؛ اعضای جدید باید برای ورود کپچا حل کنند")

        @self.bot.message_handler(func=lambda m: m.text == "بازکردن کپچا")
        @check(require_admin=True)
        async def captcha_unlock(message: types.Message):
            if int(await self.db.get_group_setting(message.chat.id, "CAPTCHA_LOCK", 0)) == 0:
                await self.bot.reply_to(message, "کپچا از قبل نیز غیرفعال بود" if int(await self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "باع، که قبلشم باز بود")
            else:
                await self.db.set_group_setting(message.chat.id, "CAPTCHA_LOCK", 0)
                await self.bot.reply_to(message, "کپچا غیرفعال شد")

        @self.bot.message_handler(func=lambda m: m.text == "پنل قفل")
        @check(require_admin=True)
        async def lock_panel(message: types.Message):
            reply_to = message.reply_to_message
            is_comment = False
            lock_keyboard = await self.build_lock_panel(message.chat.id)
            while reply_to:
                if reply_to.is_automatic_forward:
                    is_comment = True
                    break
                else:
                    if reply_to.reply_to_message:
                        reply_to = reply_to.reply_to_message
                    else:
                        reply_to = None
                        break
            if is_comment:
                post_lock = await self.db.post_lock_status(reply_to.chat.id, reply_to.message_id)
                lock_keyboard.add(
                    types.InlineKeyboardButton("قفل پست ✅" if post_lock else "قفل پست ❌", callback_data="post_" + "lock" if not post_lock else "unlock")
                )
            lock_keyboard.add(
                types.InlineKeyboardButton("بستن پنل قفل", callback_data="close_lock_panel")
            )
            await self.bot.reply_to(message, "از دکمه‌های زیر برای قفل و باز کردن ویژگی‌های مختلف گروه استفاده کنید:", reply_markup=lock_keyboard)

        @self.bot.message_handler(func=lambda m: m.text == "پنل")
        @check(require_admin=True)
        async def global_panel(message: types.Message):
            text, kb = await self.build_global_panel(message.chat.id)
            await self.bot.reply_to(message, text, parse_mode="Markdown", reply_markup=kb)

        @self.bot.message_handler(func=lambda m: m.text.startswith("دستورات عمومی"))
        @check(require_admin=True)
        async def public_commands(message:types.Message):
            toggle = message.text.replace("دستورات عمومی", "").strip()
            if toggle == "روشن":
                if await self.db.get_group_setting(message.chat.id, "PUBLIC_COMMANDS", 1) == 1:
                    await self.bot.reply_to(message, "دستورات عمومی از قبل نیز برای همه قابل استفاده بود" if int(await self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "همینطوریشم روشنه ستونم")
                    return
                else:
                    await self.db.set_group_setting(message.chat.id, "PUBLIC_COMMANDS", 1)
                    await self.bot.reply_to(message, "دستورات عمومی روشن شد")
            elif toggle == "خاموش":
                if await self.db.get_group_setting(message.chat.id, "PUBLIC_COMMANDS", 1) == 0:
                    await self.bot.reply_to(message, "دستورات عمومی از قبل نیز غیرفعال بود" if int(await self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "همینطوریشم خاموشه ستونم")
                    return
                else:
                    await self.db.set_group_setting(message.chat.id, "PUBLIC_COMMANDS", 0)
                    await self.bot.reply_to(message, "دستورات عمومی خاموش شد")

        @self.bot.message_handler(func=lambda m: m.text.startswith("مسدود کلمه "))
        @check(require_admin=True)
        async def block_word(message: types.Message):
            word = message.text.replace("مسدود کلمه", "").strip()
            await self.db.block_word(message.chat.id, word)
            await self.bot.reply_to(message, f"کلمه ی \"{word}\" با موفقیت مسدود شد")

        @self.bot.message_handler(func=lambda m: m.text.startswith("بازکردن کلمه "))
        @check(require_admin=True)
        async def unblock_word(message: types.Message):
            word = message.text.replace("بازکردن کلمه", "").strip()
            await self.db.unblock_word(message.chat.id, word)
            await self.bot.reply_to(message, f"کلمه ی \"{word}\" با موفقیت از مسدودی خارج شد و کاربران میتوانند آنرا در گروه ارسال کنند")

        @self.bot.message_handler(func=lambda m: m.text.startswith("بلاک بات "))
        @check(require_admin=True)
        async def block_bot_handler(message:types.Message):
            bot_username = message.text.replace("بلاک بات ", "").strip().replace("@", "")
            await self.db.block_bot(message.chat.id, bot_username)
            await self.bot.reply_to(message, f"بات {bot_username} بلاک شد")

        @self.bot.message_handler(func=lambda m: m.text.startswith("آن‌بلاک بات "))
        @check(require_admin=True)
        async def unblock_bot_handler(message: types.Message):
            bot_username = message.text.replace("آن‌بلاک بات ", "").strip().replace("@", "")
            await self.db.unblock_bot(message.chat.id, bot_username)
            await self.bot.reply_to(message, f"بات {bot_username} آن‌بلاک شد")
        
        @self.bot.message_handler(func=lambda m: m.text == "قفل پست")
        @check(require_admin=True)
        async def lock_comment_post(message: types.Message):
            reply_to = message.reply_to_message
            is_comment = False
            while reply_to:
                if reply_to.is_automatic_forward:
                    is_comment = True
                    break
                else:
                    if reply_to.reply_to_message:
                        reply_to = reply_to.reply_to_message
                    else:
                        reply_to = None
                        break
            if is_comment:
                await self.db.lock_post(message.reply_to.chat.id, message.reply_to.id)
                await self.bot.reply_to(message, "این پست قفل شده است 🔒\n دیگر اعضای عادی دسترسی ارسال کامنت زیر این پست را ندارد" if int(await self.db.get_group_setting(message.chat.id, "POLITE_MODE",1)) == 1 else "کیر کردم تو این پست حالا خایه داری کامنت بذار این زیر")
            else:
                await self.bot.reply_to(message, "پیام شما به هیچ پستی اشاره نمیکند، لطفا زیر پستی که میخواهید قفل شود این دستور را کامنت کنید")

        @self.bot.message_handler(func=lambda m: m.text == "باز کردن پست")
        @check(require_admin=True)
        async def unlock_comment_post(message: types.Message):
            reply_to = message.reply_to_message
            is_comment = False
            while reply_to:
                if reply_to.is_automatic_forward:
                    is_comment = True
                    break
                else:
                    if reply_to.reply_to_message:
                        reply_to = reply_to.reply_to_message
                    else:
                        reply_to = None
                        break
            if is_comment:
                await self.db.unlock_post(message.reply_to_message.chat.id, message.reply_to_message.id)
                await self.bot.reply_to(message, "پست باز شد 🔓\n دیگر تمامی اعضا قادر به ارسال کامنت زیر این پست خواهند بود" if int(await self.db.get_group_setting(message.chat.id, "POLITE_MODE",1)) == 1 else "تا کی تبعیض، قفل رو جر دادم برید کامنتارو بگایید")
            else:
                await self.bot.reply_to(message, "پیام شما به هیچ پستی اشاره نمیکند، لطفا زیر پستی که میخواهید قفل شود این دستور را کامنت کنید")

        @self.bot.message_handler(func=lambda m: m.text == "قفل اسپم")
        @check(require_admin=True)
        async def spam_lock_on(message: types.Message):
            if int(await self.db.get_group_setting(message.chat.id, "SPAM_LOCK", 0)) == 1:
                await self.bot.reply_to(message, 
                    "ضد اسپم از قبل فعال است" if int(await self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 
                    else "قفل اسپم که قبلاً روشنه کصخل")
            else:
                await self.db.set_group_setting(message.chat.id, "SPAM_LOCK", 1)
                await self.bot.reply_to(message, 
                    "✅ قفل اسپم فعال شد" if int(await self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 
                    else "قفل اسپم روشن شد")


        @self.bot.message_handler(func=lambda m: m.text == "بازکردن اسپم")
        @check(require_admin=True)
        async def spam_lock_off(message: types.Message):
            if int(await self.db.get_group_setting(message.chat.id, "SPAM_LOCK", 0)) == 0:
                await self.bot.reply_to(message, 
                    "ضد اسپم از قبل غیرفعال است" if int(await self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 
                    else "قفل اسپم که قبلاً باز بود")
            else:
                await self.db.set_group_setting(message.chat.id, "SPAM_LOCK", 0)
                await self.bot.reply_to(message, 
                    "✅ قفل اسپم غیرفعال شد" if int(await self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 
                    else "قفل اسپم خاموش شد")
                
        @self.bot.message_handler(func=lambda m: m.text == "قفل فلاد")
        @check(require_admin=True)
        async def flood_lock_on(message: types.Message):
            if int(await self.db.get_group_setting(message.chat.id, "FLOOD_LOCK", 0)) == 1:
                await self.bot.reply_to(message, 
                    "ضد فلود از قبل فعال است" if int(await self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 
                    else "قفل فلود که قبلاً روشنه کصخل")
            else:
                await self.db.set_group_setting(message.chat.id, "FLOOD_LOCK", 1)
                await self.bot.reply_to(message, 
                    "✅ قفل فلود فعال شد" if int(await self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 
                    else "قفل فلود روشن شد")
                
        @self.bot.message_handler(func=lambda m: m.text == "بازکردن فلاد")
        @check(require_admin=True)
        async def flood_lock_off(message: types.Message):
            if int(await self.db.get_group_setting(message.chat.id, "FLOOD_LOCK", 0)) == 0:
                await self.bot.reply_to(message, 
                    "ضد فلود از قبل غیرفعال است" if int(await self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 
                    else "قفل فلود که قبلاً باز بود")
            else:
                await self.db.set_group_setting(message.chat.id, "FLOOD_LOCK", 0)
                await self.bot.reply_to(message, 
                    "✅ قفل فلود غیرفعال شد" if int(await self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 
                    else "قفل فلود خاموش شد")
                
        @self.bot.message_handler(func=lambda m: m.text == "قفل اینلاین")
        @check(require_admin=True)
        async def inline_lock_on(message: types.Message):
            if int(await self.db.get_group_setting(message.chat.id, "INLINE_LOCK", 0)) == 1:
                await self.bot.reply_to(message,
                    "قفل اینلاین از قبل فعال بوده" if int(await self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "قفل اینلاین رو که قبلا روشن کرده بودی کصخل الزایمری"
                )
            else:
                await self.db.set_group_setting(message.chat.id, "INLINE_LOCK", 1)
                await self.bot.reply_to(message, "قفل اینلاین فعال شد ✅")
        
        @self.bot.message_handler(func=lambda m: m.text == "بازکردن اینلاین")
        @check(require_admin=True)
        async def inline_lock_off(message: types.Message):
            if int(await self.db.get_group_setting(message.chat.id, "INLINE_LOCK", 0)) == 0:
                await self.bot.reply_to(message,
                    "قفل اینلاین از قبل غیرفعال بوده" if int(await self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "اقا من بعنوان برنامه نویس ناموسا خسته شدم دیگه مغزم نمیکشه چی بنویسم کصخل نباشید دیگه غیرفعال بوده از قبل")
            else:
                await self.db.set_group_setting(message.chat.id, "INLINE_LOCK", 0)
                await self.bot.reply_to(message,
                    "قفل اینلاین غیرفعال شد ✅")
                

        @self.bot.message_handler(func=lambda m: m.text == "درخواست کمک")
        @check(require_admin=True)
        async def request_help_group(message: types.Message):
            confirm_keyboard = types.InlineKeyboardMarkup()
            ok_button = types.InlineKeyboardButton("تایید ✅", callback_data="ok_btn")
            cancel_button = types.InlineKeyboardButton("لغو ❌", callback_data="cancel_req")
            confirm_keyboard.add(ok_button, cancel_button)
            await self.bot.reply_to(message, "این دستور، درخواستی حاوی لینک گروه به اونر برای ورود و حل مشکل شما ارسال میکند، درصورتی که مشکل شما فوری و بدون جواب داخل راهنماها باشد کمک یار به دستور اونر در گروه از کار خواهد افتاد", reply_markup=confirm_keyboard)

        @self.bot.message_handler(func=lambda m: m.text == "بات های بلاک شده")
        @check(require_admin=True)
        async def blocked_bots(message: types.Message):
            blocked_bots = await self.db.get_botBlocks(message.chat.id)
            if not blocked_bots:
                await self.bot.reply_to(message, "هیچ باتی بلاک نشده")
                return
            string = "بات های بلاک شده :\n"
            for bot_username in blocked_bots:
                string += f" - @{bot_username}\n"
            await self.bot.reply_to(message, string)

        @self.bot.message_handler(func=lambda m: m.text == "درخواست برای ورود")
        @check(require_admin=True)
        async def toggle_request(message:types.Message):
            await self.bot.set_message_reaction(message.chat.id, message.message_id, [types.ReactionTypeEmoji('👍')])
            toggle = bool(int(await self.db.get_group_setting(message.chat.id, "creates_request", 0)))
            markup = types.InlineKeyboardMarkup()
            if toggle:
                button_off = types.InlineKeyboardButton("خاموش کردن", callback_data="request:off")
                markup.add(button_off)
            else:
                button_on = types.InlineKeyboardButton("روشن کردن", callback_data="request:on")
                markup.add(button_on)
            await self.bot.reply_to(message, f'از دکمه ی زیر برای تغییر وضعیت درخواست دعوت استفاده کنید \n وضعیت فعلی : {"روشن" if toggle else "خاموش"}', reply_markup=markup)

        @self.bot.message_handler(func=lambda m: m.text == "لینک")
        @check(require_admin=False)
        async def create_invite_link(message):
            try:
                lnk = await self.bot.create_chat_invite_link(
                    chat_id=message.chat.id,
                    name=f"Link by {message.from_user.first_name}",
                    member_limit=int(await self.db.get_group_setting(message.chat.id, "invite_maximum", 0)),
                    creates_join_request=bool(int(await self.db.get_group_setting(message.chat.id, "creates_request", 0)))
                )
                await self.bot.reply_to(
                    message,
                    f"🔗 لینک دعوت مخصوص شما:\n{lnk.invite_link}\n📌 ساخته شده توسط کمک‌یـــار"
                )
            except:
                await self.bot.reply_to(
                    message,
                    "ربات دسترسی ساخت لینک ندارد"
                )

            

        @self.bot.message_handler(func=lambda m: m.text == "فیلترها")
        @check(require_admin=False)
        async def all_filters(message:types.Message):
            filters = await self.db.get_tags(message.chat.id)
            string = "تمامی فیلترها :\n"
            for filter, response in filters.items():
                string += f"{filter} : {response}\n"
            await self.bot.reply_to(message, string)

        @self.bot.message_handler(func=lambda m: m.text == "تعیین مجازات اخطار")
        @check(require_admin=True)
        async def set_warn_punish(message: types.Message):
            warn_punish = await self.db.get_group_setting(message.chat.id, "WARN_PUNISHMENT", "kick")
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(
                types.InlineKeyboardButton(f'کیک {"✅" if warn_punish == "kick" else "❌"}', callback_data="warn_punish:kick"),
                types.InlineKeyboardButton(f'بن {"✅" if warn_punish == "ban" else "❌"}', callback_data="warn_punish:ban"),
                types.InlineKeyboardButton(f'میوت {"✅" if warn_punish == "mute" else "❌"}', callback_data="warn_punish:mute")
            )
            await self.bot.reply_to(message, "از دکمه‌های زیر برای انتخاب نوع مجازات استفاده کنید", reply_markup=keyboard)


        @self.bot.message_handler(func=lambda m: m.text.startswith("اکو "))
        @check(require_admin=False)
        async def echo_word(message:types.Message):
            echo = message.text[len("اکو"):].strip()
            if message.reply_to_message:
                await self.bot.reply_to(message.reply_to_message, f"{message.from_user.first_name}: \n {echo}")
            else:
                await self.bot.send_message(message.chat.id, f"{message.from_user.first_name}: \n {echo}")
            await self.bot.delete_message(message.chat.id, message.message_id)


        @self.bot.message_handler(func=lambda m: m.text == "قوانین")
        async def show_group_rules(message):
            rules = await self.db.get_group_rules(message.chat.id) or "قانونی برای این گروه ثبت نشده!"
            try:
                await self.bot.reply_to(message, rules, parse_mode="HTML")
            except ApiTelegramException:
                await self.bot.reply_to(message, rules)



        @self.bot.message_handler(content_types=["new_chat_members"])
        async def greet(message):
            if not await self.db.is_group_active(message.chat.id) or await self.db.is_group_blocked(message.chat.id):
                return

            if message.new_chat_members[0].id == self.me.id:
                await self.bot.send_message(message.chat.id, f"""سلام رفقا
من کمک‌یـــارم، یه دستیار مدیریت گروه و یه رفیق باحال برای شما
از طریق من میتونین به راحتی کاربرا، مدیرا، محتوا و... گروهتون رو مدیریت کنید
فقط کافیه برای شروع بهم دسترسی های کامل بدید و یه ادمین بگه `فعال شو` تا کارمونو شروع کنیم
برای دیدن طرز کار با من کلمه ی `راهنما` رو ارسال کنید

پیشنهاد میکنیم برای باخبر شدن از قابلیت های جدید ربات و همچنین گزارش باگ و پیشنهادات، در کانال و گروه کمک یار هم عضو شید :
کانال : {BOT_CHANNEL}
گروه : {BOT_GROUP}
همچنین، من یه ربات متن‌بازم پس میتونید کد منو ببینید و تغییر بدید و استفاده کنید در صورت نام بردن از کمک یار
لینک پروژه :
https://github.com/Code-Wizaard/KomakYaar
                """, parse_mode="Markdown", disable_web_page_preview=True)
                return

            for user in message.new_chat_members:
                if user.id == self.me.id:
                    continue

                if int(await self.db.get_group_setting(message.chat.id, "RAID_LOCK", 0)) == 1:
                    triggered = await self.check_raid(message.chat.id)
                    if triggered or await self.is_raid_active(message.chat.id):
                        mute_minutes = int(await self.db.get_group_setting(message.chat.id, "RAID_MUTE_MINUTES", 60))
                        try:
                            await self.bot.restrict_chat_member(
                                message.chat.id, user.id,
                                until_date=int(time.time()) + mute_minutes * 60,
                                can_send_messages=False
                            )
                        except Exception:
                            pass
                        if triggered:
                            await self.bot.send_message(
                                message.chat.id,
                                "🚨 ورود انبوه اعضا (حمله) تشخیص داده شد!\n"
                                f"اعضای جدید به مدت {mute_minutes} دقیقه سکوت می‌شوند."
                            )
                        continue

                if int(await self.db.get_group_setting(message.chat.id, "CAPTCHA_LOCK", 0)) == 1:
                    if not await self.db.is_admin(message.chat.id, user.id):
                        key = (message.chat.id, user.id)
                        if key not in self.captchas:
                            await self.start_captcha(message, user)
                        continue

                await self.send_welcome(message, user)


        @self.bot.inline_handler(func=lambda q: True)
        async def send_whisper(inline_query: types.InlineQuery):
            query = inline_query.query.strip()
            results = []

            if not query:
                help_result = types.InlineQueryResultArticle(
                    id="help",
                    title="راهنمای ارسال نجوا با کمک یار",
                    description=f"پیام خود را به صورت زیر بنویسید تا پیام خصوصی شما به فرد مورد نظر ارسال شود:\n\n@{self.me.username} <متن پیام> @username",
                    input_message_content=types.InputTextMessageContent(
                        message_text=f"راهنمای ارسال نجوا با کمک یار\n\nبرای ارسال پیام خصوصی به فردی خاص، می‌توانید از فرمت زیر استفاده کنید:\n\n@{self.me.username} <متن پیام> @username\n\nدر این فرمت، @{self.me.username} نام کاربری ربات است، <متن پیام> محتوای پیامی است که می‌خواهید ارسال کنید، و @username نام کاربری فردی است که می‌خواهید پیام را برای او ارسال کنید."
                    )
                )
                results.append(help_result)
            else:
                parts = query.rsplit("@", 1)

                if len(parts) == 2:
                    message_text = parts[0].strip()
                    target_username = parts[1].strip()


                    
                    if message_text and target_username:

                        if inline_query.chat_type == "private":
                            await self.bot.answer_inline_query(inline_query.id, [], cache_time=0, switch_pm_text="نمیتوانید در پیوی نجوا ارسال کنید", switch_pm_parameter="invalid_context")
                            return

                        elif target_username == inline_query.from_user.username:
                            await self.bot.answer_inline_query(inline_query.id, [], cache_time=0, switch_pm_text="شما نمی‌توانید به خودتان پیام دهید", switch_pm_parameter="invalid_target")
                            return
                        elif target_username == self.me.username:
                            await self.bot.answer_inline_query(inline_query.id, [], cache_time=0, switch_pm_text="شما نمی‌توانید به خود ربات پیام دهید", switch_pm_parameter="invalid_target")
                            return
                        elif len(message_text) > 200:
                            await self.bot.answer_inline_query(inline_query.id, [], cache_time=0, switch_pm_text="پیام بسیار طولانی است! محدودیت کاراکتر ارسال نجوا ۲۰۰ کاراکتر")

                        target = "@" + target_username
                        target_chat = None

                        try:
                            target_chat = await self.bot.get_chat(target)
                        except:
                            pass


                        timestamp = int(time.time())
                        token = f"wh#{inline_query.from_user.id}:{target_username}:{timestamp}"

                        

                        result_send = types.InlineQueryResultArticle(
                            id=f"wh:{token}",
                            title=f"ارسال پیام به {target}",
                            description=f"پیام شما:\n{message_text[:40] if len(message_text) > 40 else message_text}\n\nبرای ارسال این پیام به {target}، روی این پیام کلیک کنید.",
                            input_message_content=types.InputTextMessageContent(
                                message_text=f"💬 نجوا ارسال شده توسط @{inline_query.from_user.username}\n🗣️ برای {target}"
                            ),
                            reply_markup=types.InlineKeyboardMarkup().add(
                                types.InlineKeyboardButton("نمایش پیام", callback_data=f"showmsg:{token}")
                            )
                        )
                        results.append(result_send)
            await self.bot.answer_inline_query(inline_query.id, results, cache_time=0)
        
        @self.bot.chosen_inline_handler(func=lambda ch: True)
        async def chosen_inline(inline_result: types.ChosenInlineResult):
            query = inline_result.query
            result_id = inline_result.result_id

            if result_id.startswith("wh:"):
            
                token = result_id.split(":", 1)[1]
                infos = token.split("#")[1]
                sender_id = infos.split(":")[0]
                receiver_username = infos.split(":")[1]
                target_chat = None
                try:
                    target_chat = await self.bot.get_chat("@" + receiver_username)
                except:
                    pass
                parts = query.rsplit("@", 1)
                message_text = parts[0].strip()
                timestamp = infos.split(":")[2]

                key = base64.urlsafe_b64encode(hashlib.sha256(token.encode('utf-8')).digest())
                f = Fernet(key)
                encrypted_text = f.encrypt(message_text.encode('utf-8'))
                encrypted_str = base64.b64encode(encrypted_text).decode('utf-8')

                await self.db.store_whisper(
                    token=token,
                    sender_id=sender_id,
                    receiver_username=receiver_username.lower(),
                    receiver_id=target_chat.id if target_chat else None,
                    whisper=encrypted_str,
                    timestamp=timestamp
                )

        @self.bot.callback_query_handler(func=lambda call: True)
        async def callback_handler(call: types.CallbackQuery):
            try:
                data = call.data
                if data.startswith("captcha:"):
                    parts = data.split(":")
                    if len(parts) == 4:
                        _, chat_id_s, token, chosen_s = parts
                        chat_id = int(chat_id_s)
                        chosen = int(chosen_s)
                        user_id = call.from_user.id
                        key = (chat_id, user_id)
                        entry = self.captchas.get(key)
                        if not entry or entry.get("token") != token:
                            await self.bot.answer_callback_query(call.id, "کپچا منقضی شده است", show_alert=True)
                            return
                        if chosen == entry["answer"]:
                            if entry.get("task"):
                                entry["task"].cancel()
                            try:
                                await self.bot.delete_message(chat_id, entry["msg_id"])
                            except Exception:
                                pass
                            self.captchas.pop(key, None)
                            await self.captcha_success(chat_id, user_id, call.from_user.first_name)
                            await self.bot.answer_callback_query(call.id, "✅ پاسخ درست بود، خوش اومدی!")
                        else:
                            entry["attempts"] += 1
                            if entry["attempts"] >= 3:
                                if entry.get("task"):
                                    entry["task"].cancel()
                                try:
                                    await self.bot.delete_message(chat_id, entry["msg_id"])
                                except Exception:
                                    pass
                                self.captchas.pop(key, None)
                                try:
                                    await self.bot.ban_chat_member(chat_id, user_id)
                                    await self.bot.unban_chat_member(chat_id, user_id)
                                except Exception:
                                    pass
                                await self.bot.answer_callback_query(call.id, "پاسخ غلط بود؛ شما از گروه حذف شدید", show_alert=True)
                            else:
                                await self.bot.answer_callback_query(call.id, f"پاسخ غلط بود! {3 - entry['attempts']} تلاش دیگر باقی مانده", show_alert=True)
                    return

                if data.startswith("showmsg:"):
                    token = data.removeprefix("showmsg:")
                    datab = await self.db.get_whisper(token)
                    if not datab:
                        await self.bot.answer_callback_query(call.id, "این پیام منقضی شده یا وجود ندارد", show_alert=True)
                        return
                    
                    if (call.from_user.id == datab["sender_id"]) or (call.from_user.username.lower() == datab["receiver_username"]) or (call.from_user.id == datab["receiver_id"]):
                        encrypted_str = datab["whisper"]
                        encrypted = base64.b64decode(encrypted_str)
                        key = base64.urlsafe_b64encode(hashlib.sha256(token.encode('utf-8')).digest())
                        f = Fernet(key)
                        message_text = f.decrypt(encrypted).decode('utf-8')
                        text = f"{message_text}"
                        await self.bot.answer_callback_query(call.id, text, show_alert=True)
                    else:
                        await self.bot.answer_callback_query(call.id, "شما اجازه دیدن این پیام را ندارید", show_alert=True)
                        return
                    


                elif data.startswith("lock_"):
                    if not await self.db.is_admin(call.message.chat.id, call.from_user.id):
                        await self.bot.answer_callback_query(call.id, "دوست عزیز، شما دسترسی ادمین ندارید" if int(await self.db.get_group_setting(call.message.chat.id, "POLITE_MODE", 1)) == 1 else "انگشت نکن بیشرف", show_alert=True)
                        return
                    
                    reply_to = call.message.reply_to_message
                    is_comment = False
                    setting = data.split(":")[0].split("_")[1]
                    toggle = data.split(":")[1]
                    
                    current_value = int(await self.db.get_group_setting(call.message.chat.id, setting.upper() + "_LOCK", 0))
                    if (current_value == 1 and toggle == "on") or (current_value == 0 and toggle == "off"):
                        await self.bot.answer_callback_query(call.id, "این ویژگی از قبل نیز در همین وضعیت بود" if int(await self.db.get_group_setting(call.message.chat.id, "POLITE_MODE", 1)) == 1 else "همینطوریشم همینه ستونم")
                        return
                    
                    await self.db.set_group_setting(call.message.chat.id, setting.upper() + "_LOCK", 1 if toggle == "on" else 0)
                    await self.apply_group_permissions(call.message.chat.id)
                    
                    
                    locks = {
                        "swear": "فحش", "link": "لینک", "forward": "فوروارد", "group": "گروه",
                        "gif": "گیف", "spam": "اسپم", "flood": "فلاد", "inline": "اینلاین",
                        "raid": "حمله", "captcha": "کپچا"
                    }
                    status_text = f"{locks.get(setting, setting)} با موفقیت {'قفل' if toggle == 'on' else 'باز'} شد"
                    await self.bot.answer_callback_query(call.id, status_text if int(await self.db.get_group_setting(call.message.chat.id, "POLITE_MODE", 1)) == 1 else f"ردیفه ستون {locks.get(setting, setting)} رو {'قفل' if toggle == 'on' else 'باز'} کردم")
                    
                    
                    if "پنل جامع مدیریت گروه" in (call.message.text or ""):
                        text, kb = await self.build_global_panel(call.message.chat.id)
                        await self.bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=kb)
                        return

                    lock_keyboard = await self.build_lock_panel(call.message.chat.id)
                    

                    while reply_to:
                        if reply_to.is_automatic_forward:
                            is_comment = True
                            break
                        else:
                            if reply_to.reply_to_message:
                                reply_to = reply_to.reply_to_message
                            else:
                                reply_to = None
                                break
                    if is_comment:
                        post_lock = await self.db.post_lock_status(call.message.chat.id, reply_to.message_id)
                        lock_keyboard.add(
                            types.InlineKeyboardButton("قفل پست ✅" if post_lock else "قفل پست ❌", callback_data="post_" + ("lock" if not post_lock else "unlock"))
                        )
                    
                    lock_keyboard.add(types.InlineKeyboardButton("بستن پنل قفل", callback_data="close_lock_panel"))
                    
                    await self.bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=lock_keyboard)

                elif data.startswith("post_"):
                    if not await self.db.is_admin(call.message.chat.id, call.from_user.id):
                        await self.bot.answer_callback_query(call.id, "دوست عزیز، شما دسترسی ادمین ندارید", show_alert=True)
                    reply_to = call.message.reply_to_message
                    is_comment = False
                    while reply_to:
                        if reply_to.is_automatic_forward:
                            is_comment = True
                            break
                        else:
                            if reply_to.reply_to_message:
                                reply_to = reply_to.reply_to_message
                            else:
                                reply_to = None
                                break
                    data = call.data
                    status = data.split("_")[1]
                    chat_id = reply_to.chat.id
                    post_id = reply_to.message_id
                    if status == "lock":
                        await self.db.lock_post(chat_id, post_id)
                    else:
                        await self.db.unlock_post(chat_id, post_id)
                    await self.bot.answer_callback_query(call.id, f'قفل پست با موفقیت {"فعال" if status == "lock" else "غیرفعال"} شد ✅')
                    lock_keyboard = await self.build_lock_panel(call.message.chat.id)

                    if is_comment:
                        post_lock = await self.db.post_lock_status(chat_id, post_id)
                        lock_keyboard.add(
                            types.InlineKeyboardButton("قفل پست ✅" if post_lock else "قفل پست ❌", callback_data="post_" + "lock" if not post_lock else "unlock")
                        )
                    lock_keyboard.add(
                        types.InlineKeyboardButton("بستن پنل قفل", callback_data="close_lock_panel")
                    )
                    await self.bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=lock_keyboard)


                elif data == "close_lock_panel":
                    if not await self.db.is_admin(call.message.chat.id, call.from_user.id):
                        await self.bot.answer_callback_query(call.id, "دوست عزیز، شما دسترسی ادمین ندارید" if int(await self.db.get_group_setting(call.message.chat.id, "POLITE_MODE", 1)) == 1 else "انگشت نکن بیشرف", show_alert=True)
                        return
                    await self.bot.edit_message_text("پنل به دستور مدیر بسته شد!", call.message.chat.id, call.message.message_id)
                    await self.bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)

                elif data.startswith("panel_"):
                    if not await self.db.is_admin(call.message.chat.id, call.from_user.id):
                        await self.bot.answer_callback_query(call.id, "دوست عزیز، شما دسترسی ادمین ندارید" if int(await self.db.get_group_setting(call.message.chat.id, "POLITE_MODE", 1)) == 1 else "انگشت نکن بیشرف", show_alert=True)
                        return
                    setting = data.split("_")[1]
                    key = "POLITE_MODE" if setting == "polite" else "PUBLIC_COMMANDS"
                    current = int(await self.db.get_group_setting(call.message.chat.id, key, 1))
                    await self.db.set_group_setting(call.message.chat.id, key, 0 if current == 1 else 1)
                    text, kb = await self.build_global_panel(call.message.chat.id)
                    await self.bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=kb)
                    await self.bot.answer_callback_query(call.id, "تنظیمات به‌روزرسانی شد ✅")

                elif data == "close_panel":
                    if not await self.db.is_admin(call.message.chat.id, call.from_user.id):
                        await self.bot.answer_callback_query(call.id, "دوست عزیز، شما دسترسی ادمین ندارید" if int(await self.db.get_group_setting(call.message.chat.id, "POLITE_MODE", 1)) == 1 else "انگشت نکن بیشرف", show_alert=True)
                        return
                    await self.bot.edit_message_text("پنل به دستور مدیر بسته شد!", call.message.chat.id, call.message.message_id)
                    await self.bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)

                elif data.startswith("warn_punish:"):
                    punish_type = data.split(":")[1]
                    if not await self.db.is_admin(call.message.chat.id, call.from_user.id):
                        await self.bot.answer_callback_query(call.id, "دوست عزیز، شما دسترسی ادمین ندارید" if int(await self.db.get_group_setting(call.message.chat.id, "POLITE_MODE", 1)) == 1 else "برو باو بگو بزرگ‌ترت بیاد", show_alert=True)
                        return
                    await self.db.set_group_setting(call.message.chat.id, "WARN_PUNISHMENT", punish_type)
                    punish_map = {
                        "kick": "کیک",
                        "ban": "بن",
                        "mute": "میوت"
                    }
                    await self.bot.answer_callback_query(call.id, f"نوع مجازات اخطار با موفقیت به {punish_map.get(punish_type, punish_type)} تغییر کرد" if int(await self.db.get_group_setting(call.message.chat.id, "POLITE_MODE", 1)) == 1 else f"ردیفه اخطار رو گذاشتم رو {punish_map.get(punish_type, punish_type)}", show_alert=True)
                    keyboard = types.InlineKeyboardMarkup()
                    keyboard.add(
                        types.InlineKeyboardButton(f"کیک {'✅' if punish_type == 'kick' else '❌'}", callback_data="warn_punish:kick"),
                        types.InlineKeyboardButton(f"بن {'✅' if punish_type == 'ban' else '❌'}", callback_data="warn_punish:ban"),
                        types.InlineKeyboardButton(f"میوت {'✅' if punish_type == 'mute' else '❌'}", callback_data="warn_punish:mute")
                    )
                    await self.bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=keyboard)

                elif data == "ok_btn":
                    link = await self.bot.create_chat_invite_link(call.message.chat.id, "CREATED FOR OWNER HELP REQUEST", member_limit=1)
                    markup = types.InlineKeyboardMarkup()
                    goGroup_btn = types.InlineKeyboardButton("رفتن به گروه", link.invite_link)
                    markup.add(goGroup_btn)
                    await self.bot.send_message(OWNER_ID, "درخواست کمک از گروهی ارسال شده\n"
                                     f"نام گروه : {call.message.chat.title}\n"
                                     f"آیدی گروه : {call.message.chat.id}",
                                     reply_markup=markup)
                    await self.bot.edit_message_text("درخواست به اونر ارسال شد! در صورت تایید به گروه عضو خواهد شد", call.message.chat.id, call.message.message_id)

                elif data == "cancel_req":
                    await self.bot.edit_message_text("این درخواست لغو شده است!", call.message.chat.id, call.message.message_id)

                elif data.startswith("request:"):
                    toggle = data.split(":")[1]
                    if toggle == "on":
                        await self.db.delete_group_setting(call.message.chat.id, "invite_maximum")
                    await self.db.set_group_setting(call.message.chat.id, "creates_request", "1" if toggle == "on" else "0")
                    await self.bot.answer_callback_query(call.id, "درخواست برای دعوت با موفقیت خاموش شد" if toggle == "off" else "درخواست برای دعوت با موفقیت روشن شد")
                    await self.bot.delete_message(call.message.chat.id, call.message.message_id)

                elif data.startswith("swear:"):
                    array = data.split(":")[1]
                    await self.bot.answer_callback_query(call.id, f'لیست فحش های :\n {" - ".join(eval(array))}')

                elif data.startswith("check:"):
                    rep_id = data.split(":")[1]
                    await self.db.check_report(rep_id)
                    await self.bot.answer_callback_query(call.id, "گزارش با موفقیت توسط شما بررسی شد")
                    await self.bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)

                elif data.startswith("help_"):
                    if data == "help_main":
                        await self.bot.edit_message_text(
                            chat_id=call.message.chat.id,
                            message_id=call.message.message_id,
                            text=HELP_TEXT,
                            parse_mode="Markdown",
                            reply_markup=self.help_keyboard
                        )
                    elif data in self.guide_categories:
                        cat = self.guide_categories[data]
                        if cat.get("direct"):
                            await self.bot.edit_message_text(
                                chat_id=call.message.chat.id,
                                message_id=call.message.message_id,
                                text=self.guide_texts[data],
                                parse_mode="Markdown",
                                reply_markup=self.back_keyboard
                            )
                        else:
                            kb = types.InlineKeyboardMarkup(row_width=2)
                            for sub_cb, sub_title in cat["subs"]:
                                kb.add(types.InlineKeyboardButton(sub_title, callback_data=sub_cb))
                            kb.add(types.InlineKeyboardButton("🔙 برگشت به منوی اصلی", callback_data="help_main"))
                            await self.bot.edit_message_text(
                                chat_id=call.message.chat.id,
                                message_id=call.message.message_id,
                                text=f"📂 **{cat['title']}**\n\nیک موضوع را انتخاب کنید تا راهنمای دقیق همان دستور را ببینید:",
                                parse_mode="Markdown",
                                reply_markup=kb
                            )
                    elif data in self.guide_texts:
                        parent = self.guide_sub_parent.get(data, "help_main")
                        kb = types.InlineKeyboardMarkup(row_width=1)
                        kb.add(types.InlineKeyboardButton("🔙 برگشت به دسته", callback_data=parent))
                        kb.add(types.InlineKeyboardButton("🔙 برگشت به منوی اصلی", callback_data="help_main"))
                        await self.bot.edit_message_text(
                            chat_id=call.message.chat.id,
                            message_id=call.message.message_id,
                            text=self.guide_texts[data],
                            parse_mode="Markdown",
                            reply_markup=kb
                        )
                    await self.bot.answer_callback_query(call.id)
            except Exception as e:
                error_text = f"callback_handler: {str(e)}\n{traceback.format_exc()}"
                await send_error_to_owner(error_text, OWNER_ID, self.bot, "CALLBACK_ERROR")

        @self.bot.message_handler(commands=['bangroup'])
        async def ban_group(message: types.Message):
            if message.from_user.id != OWNER_ID:
                await self.bot.reply_to(message, "تو اونر بات نیستی")
                return
            if not message.text.startswith("/bangroup "):
                await self.bot.reply_to(message, "فرمت پیامت اشتباهه")
                return
            group_id = message.text.replace("/bangroup ", "")
            if not await self.db.is_group_blocked(group_id):
                await self.db.ban_group(group_id)
                await self.bot.reply_to(message, "گروه دریافتی با موفقیت بن شد و قادر به کار با ربات نیست")
                await self.bot.send_message(group_id, "درود، متاسفانه، این گروه از کمک‌یــار بن شده و اعضا و ادمین های آن دیگر قادر به کار با ربات نیستند")
            else:
                await self.bot.reply_to(message, "گروه از قبل هم بن شده بود")

        @self.bot.message_handler(commands=['unbangroup'])
        async def unban_group(message: types.Message):
            if message.from_user.id != OWNER_ID:
                await self.bot.reply_to(message, "فقط به حرف اونر گوش میدم")
                return
            if not message.text.startswith("/unbangroup "):
                await self.bot.reply_to(message, "فرمت پیام اشتباه است")
                return
            group_id = message.text.replace("/unbangroup ", "")
            if await self.db.is_group_blocked(group_id):
                await self.db.unban_group(group_id)
                await self.bot.reply_to(message, "گروه دریافتی با موفقیت از حالت مسدودی درآمد")
                await self.bot.send_message(group_id, "خبر خوب، گروه شما از حالت مسدودی خارج شده و همگی دوباره قادر به استفاده از ربات هستند")
            else:
                await self.bot.reply_to(message, "گروه که اصلا بن نشده بود بخوای آن‌بن کنی")

        @self.bot.message_handler(commands=['update'])
        async def handle_update_command(message):
            if message.from_user.id != OWNER_ID:
                await self.bot.reply_to(message, "فقط اونر می‌تونه آپدیت پخش کنه!")
                return

            text = message.text.strip()
            lines = text.splitlines()

            if len(lines) < 1:
                return

            first_line = lines[0].strip()

            version_match = re.search(r'/update\s+([vV]?\d+\.\d+(\.\d+)?)', first_line, re.IGNORECASE)

            if not version_match:
                await self.bot.reply_to(message, 
                    "❌ فرمت اشتباه!\n\n"
                    "مثال:\n"
                    "/update v1.2.5\n"
                    "یا\n"
                    "/update 1.2.5\n"
                    "سپس تغییرات رو در خطوط بعدی بنویس")
                return

            full_version = version_match.group(1)       
            display_version = full_version if full_version.lower().startswith('v') else f"v{full_version}"


            updates = []
            for line in lines[1:]:
                stripped = line.strip()
                if stripped and not stripped.startswith('/'):
                    if not stripped.startswith('•'):
                        stripped = '• ' + stripped
                    updates.append(stripped)

            if not updates:
                await self.bot.reply_to(message, "❌ هیچ آپدیتی نوشته نشده!")
                return

            preview = f"*نسخه جدید ربات کمک‌یار (***{display_version}***) منتشر شد!*\n\n"
            for upd in updates:
                preview += f"{upd}\n"

            await self.bot.reply_to(message, 
                        f"✅ در حال پخش آپدیت {display_version} به همه گروه‌ها...\n\n"
                        f"پیش‌نمایش:\n{preview}", 
                        parse_mode="Markdown")

            try:
                success, err = await self.db.update_message(updates, full_version.lstrip('vV'))
                
                await self.bot.reply_to(message, 
                            f"✅ پخش آپدیت تموم شد!\n\n"
                            f"ارسال موفق: {success} گروه\n"
                            f"خطا یا بلاک شده: {err} گروه")
            except Exception as e:
                await self.bot.reply_to(message, f"❌ خطا در پخش آپدیت: {str(e)}")
                

        @self.bot.message_handler(func=lambda m: m.chat.type == "private")
        async def pv_chats(message:types.Message):
            if message.text == "/start":
                await self.bot.send_message(
                    message.chat.id,
                    f"""🌟 به **ربات کمک‌یار** خوش اومدی!

من یه دستیار قدرتمند برای مدیریت گروه‌های تلگرامی هستم.

🚀 **برای شروع کافیه:** 
1. منو به گروهت اضافه کن
2. بهم دسترسی ادمین بده
3. تو گروه دستور `فعال شو` رو بفرست

📊 **قابلیت‌های من:**
• مدیریت کامل اعضا (اخطار، بن، میوت، کیک)
• فیلترهای هوشمند و پاسخ خودکار
• قفل‌های متنوع (لینک، فحش، فوروارد، گیف)
• سیستم نجوا برای پیام‌های خصوصی
• گزارش‌دهی و لاگ‌گیری
• و ده‌ها قابلیت دیگر...

🔗 **لینک‌های مفید:**
• کد منبع: [گیت‌هاب](https://github.com/Code-Wizaard/KomakYaar)
• کانال آپدیت: {BOT_CHANNEL}
• گروه پشتیبانی: {BOT_GROUP}

📖 برای مشاهده راهنما، دکمه `/help` رو بزن.

🎉 نسخه {VERSION}

Made with ❤️ by Code-Wizaard""",
                    parse_mode="Markdown",
                    disable_web_page_preview=True,
                    reply_markup=self.start_keyboard
                )
            elif message.text == "/help":
                await self.bot.send_message(
                    message.from_user.id, 
                    HELP_TEXT, 
                    parse_mode="Markdown", 
                    reply_markup=self.help_keyboard
                )

        @self.bot.message_handler(commands=['start'], func=lambda m: m.chat.type in ["group", "supergroup"])
        async def group_starts(message: types.Message):
            await self.bot.reply_to(message, f"""درود و مهر ❤️👋
من کمک یارم، یه ربات خودمونی همه کاره برای مدیریت انواع گروه ها، از گروه های دوستانه و رفاقتی تا گروه های رسمی و پرجمعیت و همچنین گروه های کامنت
خیلی خوشحالم که اینجام، اگر دسترسی های ادمین رو بهم دادی، با فرستادن دستور فعال شو من میتونم کارمو شروع کنم
اگرم تا الان من فعال هستم که چه بهتر، گوش به زنگم
پیشنهاد میکنم برای باخبر شدن از قابلیت های جدید ربات و همچنین گزارش باگ و پیشنهادات، در کانال و گروه کمک یار هم عضو شید :
کانال : {BOT_CHANNEL}
گروه : {BOT_GROUP}
همچنین اگر دلتون میخواد که یه کمک‌یــــــــار برای خودتون داشته باشید یا روی امنیت چیزایی که استفاده میکنید حساسید، بهتره که بگم کمک‌یـــــار یه ربات کاملا اوپن سورسه و میتونید کدش رو ببینید و اگر تونستید و ایده ای داشتید روش مشارکت کنید
لینک سورس :
https://github.com/Code-Wizaard/KomakYaar
""", disable_web_page_preview=True)

        @self.bot.message_handler(func= lambda m: m.from_user.id == OWNER_ID and m.text.startswith("db:"))
        async def execute_to_db(message):
            try:
                query = message.text.split(":")[1]
                async with aiosqlite.connect(DB_PATH) as con:
                    cur = await con.execute(query)
                    rows = await cur.fetchall()
                    if rows:
                        await self.bot.reply_to(message, f"Hello Master, These are the responses : \n {json.dumps(rows, ensure_ascii=False)}")
                    else:
                        await con.commit()
            except Exception as e:
                await self.bot.reply_to(message, f"ریدی ارور گرفتم \n {e}")
            finally:
                await con.close()

        @self.bot.message_handler(func= lambda m: m.from_user.id == OWNER_ID and m.text == ";id;")
        async def id_informations_owner(message: types.Message):
            if message.reply_to_message:
                await self.bot.reply_to(message, f"اطلاعات فرد مشخص شده : \n"
                f"آیدی فرد : {message.reply_to_message.from_user.id}\n"
                f"آیدی پیام : {message.reply_to_message.id}\n")
            else:
                await self.bot.reply_to(message, f"آیدی گروه : {message.chat.id}\n")

        @self.bot.message_handler(func= lambda m: m.from_user.id == OWNER_ID and m.text.startswith("(tag): "))
        async def make_id_into_tag(message: types.Message):
            user_id = message.text.replace("(tag): ", "").strip()
            await self.bot.reply_to(message, f"[HereYouGo](tg://user?id={user_id})", parse_mode="Markdown")

        @self.bot.channel_post_handler(func=lambda m: m.text.startswith("/setbridge "))
        async def set_bridge(message: types.Message):
            if not message.text.startswith("/setbridge "):
                await self.bot.reply_to(message, "فرمت دستور اشتباه است")
                return
            target_chat_id = message.text.replace("/setbridge ", "").strip()
            if not target_chat_id:
                await self.bot.reply_to(message, "لطفا آیدی گروه مقصد را وارد کنید\n برای انجام این کار میتوانید در کانال مقصد خود که کمک‌یـــــار را عضو ان کرده اید و بعنوان ادمین انتخاب کرده اید از دستور /getid استفاده کنید و آیدی گروه را دریافت کنید")
                return
            try:
                chat = await self.bale_bot.get_chat(target_chat_id)
            except Exception as e:
                await self.bot.reply_to(message, "چنین کانالی ای وجود ندارد یا من به آن دسترسی ندارم")
                await send_error_to_owner(f"Error in set_bridge: {str(e)}\n{traceback.format_exc()}", OWNER_ID, self.bot, "SET_BRIDGE_ERROR")
                return
            await self.db.set_bridge(message.chat.id, target_chat_id)
            await self.bot.reply_to(message, f"پل ارتباطی با کانال {chat.title} با موفقیت تنظیم شد")

        @self.bot.channel_post_handler(func=lambda m: m.text.startswith("/removebridge "))
        async def remove_bridge(message: types.Message):
            if not message.text.startswith("/removebridge "):
                await self.bot.reply_to(message, "فرمت دستور اشتباه است")
                return
            target_chat_id = message.text.replace("/removebridge ", "").strip()
            if not target_chat_id:
                await self.bot.reply_to(message, "لطفا آیدی کانال مقصد را وارد کنید\n برای انجام این کار میتوانید در کانال مقصد خود که کمک‌یـــــار را عضو ان کرده اید و بعنوان ادمین انتخاب کرده اید از دستور /getid استفاده کنید و آیدی کانال را دریافت کنید")
                return
            await self.db.remove_bridge(message.chat.id)
            await self.bot.reply_to(message, f"پل ارتباطی با کانال {target_chat_id} با موفقیت حذف شد")

        @self.bot.channel_post_handler(content_types=['text', 'photo', 'video', 'document', 'audio', 'voice', 'sticker', 'animation', 'video_note'])
        async def handle_telegram_bridge(message: types.Message):
            if (message.from_user and message.from_user.id == self.me.id) or \
                (message.sender_chat and message.sender_chat.id == self.me.id):
                return
            
            bale_chat_id = await self.db.get_bale_bridge_channel(message.chat.id)
            if not bale_chat_id:
                return

            try:
                text = ""
                if message.forward_origin:
                    text = f"فوروارد شده از [{message.forward_origin.chat.title}](https://t.me/{message.forward_origin.chat.username})\n\n"
                text = text + ((message.text or message.caption) or "")

                if message.text:
                    await self.bale_bot.send_message(bale_chat_id, text)

                elif message.photo:
                    photo = message.photo[-1]
                    file_info = await self.bot.get_file(photo.file_id)
                    downloaded = await self.bot.download_file(file_info.file_path)
                    
                    input_file = InputFile(downloaded, file_name="photo.jpg")
                    await self.bale_bot.send_photo(bale_chat_id, input_file, caption=text)

                elif message.video:
                    file_info = await self.bot.get_file(message.video.file_id)
                    downloaded = await self.bot.download_file(file_info.file_path)
                    input_file = InputFile(downloaded, file_name="video.mp4")
                    await self.bale_bot.send_video(bale_chat_id, input_file, caption=text)

                elif message.document:
                    file_info = await self.bot.get_file(message.document.file_id)
                    downloaded = await self.bot.download_file(file_info.file_path)
                    file_name = message.document.file_name or "document"
                    input_file = InputFile(downloaded, file_name=file_name)
                    await self.bale_bot.send_document(bale_chat_id, input_file, caption=text)

                elif message.animation:
                    file_info = await self.bot.get_file(message.animation.file_id)
                    downloaded = await self.bot.download_file(file_info.file_path)
                    input_file = InputFile(downloaded, file_name="animation.gif")
                    await self.bale_bot.send_animation(bale_chat_id, input_file, caption=text)

                elif message.sticker:
                    file_info = await self.bot.get_file(message.sticker.file_id)
                    downloaded = await self.bot.download_file(file_info.file_path)
                    input_file = InputFile(downloaded, file_name="sticker.webp")
                    await self.bale_bot.send_sticker(bale_chat_id, input_file)

                elif message.voice:
                    file_info = await self.bot.get_file(message.voice.file_id)
                    downloaded = await self.bot.download_file(file_info.file_path)
                    input_file = InputFile(downloaded, file_name="voice.ogg")
                    await self.bale_bot.send_voice(bale_chat_id, input_file)

            except Exception as e:
                error_text = f"Telegram → Bale Bridge Error:\n{traceback.format_exc()}"
                print(error_text)
                await send_error_to_owner(error_text, OWNER_ID, self.bot, "BRIDGE_TG_TO_BALE")

        @self.bale_bot.on_message()
        async def get_id(message: Message):
            if message.text and message.text == "/getid" and message.chat.type == ChatType.CHANNEL:
                await self.bale_bot.send_message(message.chat.id, f"آیدی کانال : {message.chat.id}")

        @self.bale_bot.on_message()
        async def handle_bale_bridge(message: Message):
            if message.chat.type == ChatType.CHANNEL:
                if (message.sender_chat and message.sender_chat.id == self.me.id):
                    return
                bridge = await self.db.get_telegram_bridge_channel(message.chat.id)
                if not bridge:
                    return
                telegram_chat_id = bridge
                try:
                    text = ""
                    if message.forward_from_chat:
                        text = f"فوروارد شده از [{message.forward_from_chat['title']}](https://ble.ir/{message.forward_from_chat['username']})\n\n"
                    text = text + ((message.text or message.caption) or "")
                    text = parse_strip(text)

                    if message.text:
                        await self.bot.send_message(telegram_chat_id, text, parse_mode="Markdown")

                    elif message.photo:
                        photo = message.photo[-1]
                        async with aiohttp.ClientSession() as session:
                            async with session.get(f"https://tapi.bale.ai/file/bot{BALE_TOKEN}/{photo['file_id']}") as resp:
                                data = await resp.read()
                        photo_file = BytesIO(data)
                        photo_file.name = "photo.jpg"
                        await self.bot.send_photo(telegram_chat_id, photo_file, caption=text, parse_mode="Markdown")

                    elif message.video:
                        async with aiohttp.ClientSession() as session:
                            async with session.get(f"https://tapi.bale.ai/file/bot{BALE_TOKEN}/{message.video['file_id']}") as resp:
                                data = await resp.read()
                        video_file = BytesIO(data)
                        video_file.name = message.video.get("file_name", "video.mp4")
                        await self.bot.send_video(telegram_chat_id, video_file, caption=text, parse_mode="Markdown")

                    elif message.animation:
                        async with aiohttp.ClientSession() as session:
                            async with session.get(f"https://tapi.bale.ai/file/bot{BALE_TOKEN}/{message.animation.file_id}") as resp:
                                data = await resp.read()
                        animation_file = BytesIO(data)
                        animation_file.name = message.animation.file_name or "animation.gif"
                        await self.bot.send_animation(telegram_chat_id, animation_file, caption=text, parse_mode="Markdown")

                    elif message.sticker:
                        async with aiohttp.ClientSession() as session:
                            async with session.get(f"https://tapi.bale.ai/file/bot{BALE_TOKEN}/{message.sticker.file_id}") as resp:
                                data = await resp.read()
                        sticker_file = BytesIO(data)
                        sticker_file.name = "sticker.webp"
                        await self.bot.send_sticker(telegram_chat_id, sticker_file, parse_mode="Markdown")

                    elif message.voice:
                        async with aiohttp.ClientSession() as session:
                            async with session.get(f"https://tapi.bale.ai/file/bot{BALE_TOKEN}/{message.voice.file_id}") as resp:
                                data = await resp.read()
                        voice_file = BytesIO(data)
                        voice_file.name = "voice.ogg"
                        await self.bot.send_voice(telegram_chat_id, voice_file, caption=text, parse_mode="Markdown")

                    elif message.document:
                        async with aiohttp.ClientSession() as session:
                            async with session.get(f"https://tapi.bale.ai/file/bot{BALE_TOKEN}/{message.document.file_id}") as resp:
                                data = await resp.read()
                        document_file = BytesIO(data)
                        document_file.name = message.document.file_name or"document.pdf"
                        await self.bot.send_document(telegram_chat_id, document_file, caption=text, parse_mode="Markdown")

                    else:
                        await self.bot.send_message(telegram_chat_id, f"نوع محتوا ناشناخته")
                except Exception as e:
                    error_text = f"Error in Bale Bridge: {str(e)}\n{traceback.format_exc()}"
                    await send_error_to_owner(error_text, OWNER_ID, self.bot, "BALE_BRIDGE_ERROR")


        @self.bot.message_handler(func=lambda m: True, content_types=['text', 'photo', 'video', 'document', 'audio', 'voice', 'sticker', 'animation', 'video_note'])
        async def handle_messages(message:types.Message):
            try:
                chat_id = message.chat.id
                user_id = message.from_user.id
                sender_chat_id = self.sender_chat_id(message)
                text = (message.text or message.caption) or ""
                message.text = text
                is_comment = False
                reply_to = message.reply_to_message
                comment_channel = message.reply_to_message
                file = open(SWEARS_PATH, "r")
                swears = []
                is_swear = False

                
                if await self.db.is_group_blocked(chat_id):
                    return

                if not await self.db.is_group_active(chat_id):
                    return
                
                if (int(await self.db.get_group_setting(chat_id, "SPAM_LOCK", 0)) == 1 or
                    int(await self.db.get_group_setting(chat_id, "FLOOD_LOCK", 0)) == 1):
                    
                    if not text:
                        if message.sticker:
                            text = f"sticker:{message.sticker.file_unique_id}"
                        elif message.animation:
                            text = f"animation:{message.animation.file_unique_id}"
                        elif message.document:
                            text = f"document:{message.document.file_unique_id}"
                        else:
                            text = f"{message.content_type}:{message.message_id}"
                    spam_result = await self.anti_spam.check(chat_id, user_id, text)
                    if spam_result[0] is not None:
                        violation, count = spam_result
                        try:
                            await self.bot.delete_message(chat_id, message.message_id)
                        except ApiTelegramException:
                            pass
                        try:
                            await self.bot.restrict_chat_member(
                                chat_id, 
                                user_id, 
                                until_date=int(time.time()) + 300,
                                can_send_messages=False
                            )
                        except ApiTelegramException:
                            pass
                        self.anti_spam.reset_user(chat_id, user_id)
                        if not await self.db.is_admin(chat_id, user_id, sender_chat_id):
                            await self.bot.send_message(
                                chat_id,
                                f'[{message.from_user.first_name}](tg://user?id={user_id}) {"اسپم" if violation == "spam" else "فلاد"} نکن! ۵ دقیقه سکوت داده شدی 🔇',
                                parse_mode="Markdown"
                            )
                            return
                        else:
                            await self.bot.send_message(
                                chat_id,
                                f'[{message.from_user.first_name}](tg://user?id={user_id}) {"اسپم" if violation == "spam" else "فلاد"} کردی، حیف که ادمینی وگرنه میوتت میکردم',
                                parse_mode="Markdown"
                            )

                if message.document:
                    file_name = message.document.file_name or ""
                    ext = file_name.split('.')[-1].lower() if '.' in file_name else ""
                    file_size = message.document.file_size or 0

                    supported_exts = {
                        'txt', 'py', 'js', 'html', 'css', 'json', 'xml', 
                        'md', 'csv', 'log', 'sh', 'bat', 'ps1', 'php', 'java',
                        'cs', 'cpp', 'c', 'h', 'hpp', 'rb', 'pl', 'go', 'rs',
                    }

                    if ext not in supported_exts:
                        await self.bot.set_message_reaction(
                            chat_id, 
                            message.message_id, 
                            [types.ReactionTypeEmoji('🥴')]  # Unsupported type
                        )
                    elif file_size > MAX_ANTIVIRUS_FILE_SIZE:
                        await self.bot.set_message_reaction(
                            chat_id, 
                            message.message_id, 
                            [types.ReactionTypeEmoji('🥴')]  # Too large to download & scan
                        )
                    else:
                        await self.bot.set_message_reaction(
                            chat_id, 
                            message.message_id, 
                            [types.ReactionTypeEmoji('🤔')]  # Scanning
                        )
                        try:
                            # Download file
                            file_info = await self.bot.get_file(message.document.file_id)
                            downloaded = await self.bot.download_file(file_info.file_path)
                            
                            # Try to read as text (fallback to empty if binary)
                            try:
                                content = downloaded.decode('utf-8', errors='ignore')
                            except:
                                content = str(downloaded)[:10000]  # fallback

                            if content.strip():
                                is_malware, prob = self.anti_virus.is_malware(content)
                                
                                if is_malware:
                                    await self.bot.set_message_reaction(
                                        chat_id, 
                                        message.message_id, 
                                        [types.ReactionTypeEmoji('💀')]  # Malware detected
                                    )
                                else:
                                    await self.bot.set_message_reaction(
                                        chat_id, 
                                        message.message_id, 
                                        [types.ReactionTypeEmoji('👍')]  # Clean
                                    )
                            else:
                                await self.bot.set_message_reaction(
                                    chat_id, 
                                    message.message_id, 
                                    [types.ReactionTypeEmoji('❓')] # Not Sure
                                )
                        except Exception as e:
                            error_text = f"handle_malwares: {str(e)}\n{traceback.format_exc()}"
                            await send_error_to_owner(error_text, OWNER_ID, self.bot, "MAIN_ERROR")
                            await self.bot.set_message_reaction(
                                chat_id, 
                                message.message_id, 
                                [types.ReactionTypeEmoji('🤯')] # ERR
                            )

                
                while reply_to:
                    if reply_to.is_automatic_forward:
                        is_comment = True
                        break
                    else:
                        if reply_to.reply_to_message:
                            reply_to = reply_to.reply_to_message
                        else:
                            reply_to = None
                            break

                if int(await self.db.get_group_setting(chat_id, "GROUP_LOCK", 0)) == 1:
                    if not await self.db.is_admin(chat_id, user_id, sender_chat_id):
                        await self.bot.delete_message(chat_id, message.message_id)

                if int(await self.db.get_group_setting(chat_id, "GIF_LOCK", 0)) == 1:
                    if message.content_type == "animation":
                        if not await self.db.is_admin(chat_id, user_id, sender_chat_id):
                            await self.bot.delete_message(chat_id, message.message_id)

                if message.via_bot:
                    lock = await self.db.get_group_setting(chat_id, "INLINE_LOCK", 0)
                    if int(lock) == 1 and not await self.db.is_admin(chat_id, user_id, sender_chat_id):
                        await self.bot.delete_message(chat_id, message.message_id)
                        return
                    bot_username = message.via_bot.username
                    blocked_bots = await self.db.get_botBlocks(message.chat.id)
                    if bot_username in blocked_bots:
                        await self.bot.delete_message(message.chat.id, message.message_id)
                        return
                    
                if message.is_automatic_forward:
                    msg = await self.db.get_comment_message(chat_id)
                    await self.bot.reply_to(message, msg)

                if is_comment:
                    post = await self.db.post_lock_status(message.reply_to_message.chat.id, message.reply_to_message.id)
                    if post:
                        await self.bot.delete_message(message.chat.id, message.message_id)
                    
                if await self.db.get_group_setting(chat_id, "LINK_LOCK", 0):
                    if re.search(r"(http|ftp|https):\/\/([\w_-]+(?:(?:\.[\w_-]+)+))([\w.,@?^=%&:\/~+#-]*[\w@?^=%&\/~+#-])", text):
                        await self.bot.delete_message(chat_id, message.message_id)
                        return

                text_lower = text.lower()
                tokens_lower = [t.lower() for t in text.split()]
                for blocked in await self.db.blocked_words(chat_id):
                    blocked = blocked.strip()
                    if not blocked:
                        continue
                    if len(blocked.split()) > 1:
                        if blocked.lower() in text_lower:
                            swears.append(blocked)
                    elif blocked.lower() in tokens_lower:
                        swears.append(blocked)

                if int(await self.db.get_group_setting(chat_id, "SWEAR_LOCK", 0)) == 1:
                    is_swear_flag, accuracy = self.profanity_detector.is_swear(text)

                    if is_swear_flag and accuracy >= 0.75:
                        is_swear = True
                        swears.append("swear detected by model")


                if (not len(swears) == 0) or is_swear:
                    await self.bot.reply_to(comment_channel if is_comment else message, f"[{message.from_user.first_name}](tg://user?id={user_id}) عزیزم قرار شد دیگه فحش ندیم بیاید باهم دوست باشیم", parse_mode="Markdown")
                    await self.bot.delete_message(chat_id, message.message_id)

                toggle = await self.db.get_group_setting(message.chat.id, "PUBLIC_COMMANDS", 1)
                if not await self.db.is_admin(message.chat.id, message.from_user.id, sender_chat_id) and int(toggle) == 0:
                    return

                if text.startswith("db:"):
                    await self.bot.reply_to(message, "دوست عزیز، شما اونر نیستید" if int(await self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "گوه نخور بابا این گوزا به تو نیومده")

                if text == "کمک یار" or text == "کمک‌یار":
                    await self.bot.reply_to(message, f"{message.from_user.first_name}")


                tags = await self.db.get_tags(chat_id)
                for k, r in tags.items():
                    if text == k:
                        await self.bot.reply_to(message, r)
                        break

                if text.startswith("سقف اخطار"):
                    if not await self.db.is_admin(chat_id, user_id, sender_chat_id):
                        await self.bot.reply_to(message, "دوست عزیز، شما دسترسی ادمین ندارید" if int(await self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "همون سقف تو کونت")
                        return
                    words = text.split(" ")
                    words.remove("سقف")
                    words.remove("اخطار")
                    if words[0].isdigit():
                        digit = convert_digit(words[0])
                        await self.db.set_warn_maximum(chat_id, digit)
                        await self.bot.reply_to(message, "سقف اخطارها با موفقیت تنظیم شد")
                    else:
                        await self.bot.reply_to(message, f"{words[0]} خودتی")

                if text.startswith("حذف فیلتر"):
                    if not await self.db.is_admin(chat_id, user_id, sender_chat_id):
                        await self.bot.reply_to(message, "دوست عزیز، شما دسترسی ادمین ندارید" if int(await self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "انگشت نکن بیشرف")
                        return
                    # اگر ریپلای شده روی پیام کلیدواژه
                    if message.reply_to_message:
                        keyword = message.reply_to_message.text.strip()
                    else:
                        # جدا کردن کلیدواژه از متن: حذف فیلتر <کلیدواژه>
                        keyword = text[len("حذف فیلتر"):].strip()

                    if keyword:
                        await self.db.del_tag(chat_id, keyword)
                        await self.bot.reply_to(message, f"❌ فیلتر '{keyword}' حذف شد")
                    else:
                        await self.bot.reply_to(message, "⚠️ فرمت درست: حذف فیلتر روی ریپلای یا با نوشتن کلیدواژه")
                    return

                if (message.text.startswith("حذف") and text != "حذف اخطارها"):
                    if not await self.db.is_admin(chat_id, user_id, sender_chat_id):
                        await self.bot.reply_to(message, "دوست عزیز، شما دسترسی ادمین ندارید" if int(await self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "امیدوارم از زندگی حذف شی")
                        return
                    try:
                        n = int(message.text.replace("حذف", "").strip())
                    except:
                        n = 1

                    chat_id = message.chat.id
                    start_id = message.message_id   # id دستور "حذف ۵"
                    err = 0
                    for i in range(n+1):  # +1 یعنی خود دستور هم پاک بشه
                        try:
                            await self.bot.delete_message(chat_id, start_id - i)
                        except:
                            err += 1
                    msg = await self.bot.send_message(chat_id, f"{n-err} با موفقیت حذف شد 🗑️")
                    await asyncio.sleep(4)
                    await self.bot.delete_message(msg.chat.id, msg.message_id)

                if message.reply_to_message:
                    target_id = message.reply_to_message.from_user.id

                    # ADD TAG (فیلتر)
                    if text.startswith("فیلتر") and await self.db.is_admin(chat_id, user_id, sender_chat_id):
                        keyword = message.reply_to_message.text.strip()
                        response = text[len("فیلتر"):].strip()
                        if keyword and response:
                            await self.db.add_tag(chat_id, keyword, response)
                            await self.bot.reply_to(message, f"✅ فیلتر اضافه شد!\nکلیدواژه: {keyword}\nپاسخ: {response}")
                        else:
                            await self.bot.reply_to(message, "⚠️ فرمت درست: ریپلای روی پیام و نوشتن: فیلتر پاسخ")
                        return

                    if text == "حذف" and await self.db.is_admin(chat_id, user_id, sender_chat_id):
                        self.bot.delete_message(chat_id, message.reply_to_message.message_id)
                        msg = await self.bot.reply_to(message, "پیام پاک شد 🗑️")
                        await asyncio.sleep(4)
                        await self.bot.delete_message(msg.chat.id, msg.message_id)

                    if text == "گزارش":
                        admins = await self.bot.get_chat_administrators(chat_id)
                        msg = await self.bot.reply_to(message, "گزارش با موفقیت ثبت و به ادمین ها اطلاع رسانی شد، به زودی گزارش بررسی میشود")
                        id = await self.db.file_report(chat_id, user_id, target_id, msg.message_id)
                        target = await self.bot.get_chat(target_id)
                        markup = types.InlineKeyboardMarkup()
                        check_button = types.InlineKeyboardButton("بررسی شد", callback_data=f"check:{id}")
                        message_btn = types.InlineKeyboardButton("رفتن به پیام", url=f"https://t.me/c/{str(chat_id)[4:]}/{message.reply_to_message.message_id}")

                        markup.add(check_button)
                        markup.add(message_btn)
                        for admin in admins:
                            if not admin.user.is_bot and admin.user.id != self.me.id:
                                try:
                                    await self.bot.send_message(admin.user.id, f"گزارش دریافتی از کاربر [{message.from_user.first_name}](tg://user?id={user_id}) در گروه با ایدی {chat_id}\n فرد گزارش شده : [{target.first_name}](tg://user?id={target_id})\n متن پیام ارسالی :\n > {message.reply_to_message.text}", reply_markup=markup, parse_mode="Markdown")
                                except:
                                    pass

                    if text.startswith("ثبت لقب"):
                        if not (await self.db.is_admin(chat_id, user_id, sender_chat_id) or target_id == user_id):
                            await self.bot.reply_to(message, "دوست عزیز، شما دسترسی ادمین ندارید" if int(await self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "بدو بینم")
                            return
                        alias = text[len("ثبت لقب"):].strip()
                        await self.db.set_alias(chat_id, target_id, alias)
                        await self.bot.reply_to(message, f"لقب {alias} با موفقیت برای این کاربر ثبت شد")

                    if text == "لقب":
                        alias = await self.db.get_alias(chat_id, target_id).strip()
                        await self.bot.reply_to(message, f"لقب ثبت شده برای این کاربر :\n {alias}")

                    if text.startswith("ثبت اصل"):
                        if not (await self.db.is_admin(chat_id, user_id, sender_chat_id) or target_id == user_id):
                            await self.bot.reply_to(message, "دوست عزیز، شما دسترسی ادمین ندارید" if int(await self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "کیرم تو اصلت")
                            return
                        asl = text[len("ثبت اصل"):].strip()
                        await self.db.set_asl(chat_id, target_id, asl)
                        await self.bot.reply_to(message, f"اصل {asl} با موفقیت برای این کاربر ثبت شد")

                    if text == "اصل":
                        asl = await self.db.get_asl(chat_id, target_id).strip()
                        await self.bot.reply_to(message, f"اصل ثبت شده برای این کاربر :\n {asl}")

                    if text == "تنظیم خوشامد" and await self.db.is_admin(chat_id, user_id, sender_chat_id):
                        await self.db.set_group_welcome(chat_id, message.reply_to_message.text)
                        await self.bot.reply_to(message, "متن خوشامد گویی ربات با موفقیت تنظیم شد")

                    if text == "تنظیم قوانین" and await self.db.is_admin(chat_id, user_id, sender_chat_id):
                        if message.reply_to_message:
                            rules_html = message.reply_to_message.html_text or message.reply_to_message.text
                            await self.db.set_group_rules(chat_id, rules_html)
                            await self.bot.reply_to(message, "قوانین گروه با موفقیت تنظیم شد")
                        else:
                            await self.bot.reply_to(message, "روی پیام قوانین ریپلای کنید")

                    if text == "تنظیم متن کامنت" and await self.db.is_admin(chat_id, user_id, sender_chat_id):
                        if message.reply_to_message:
                            await self.db.set_comment_message(chat_id, message.reply_to_message.text)
                            await self.bot.reply_to(message, "متن کامنت زیر پست ها تغییر پیدا کرد")
                        else:
                            await self.bot.reply_to(message, "خب دقیقا متن رو به چی تغییر باید بدم :\\")

                    if text == "اطلاعات":
                        try:
                            # گرفتن اطلاعات پایه کاربر
                            user = await self.bot.get_chat_member(chat_id, target_id).user
                            user_id = user.id
                            first_name = user.first_name or ""
                            last_name = user.last_name or ""
                            username = f"@{user.username}" if user.username else "❌ ندارد"
                            is_bot = "🤖 بله" if user.is_bot else "👤 خیر"

                            # وضعیت کاربر توی گروه
                            member = await self.bot.get_chat_member(chat_id, target_id)
                            status_map = {
                                "creator": "👑 مالک گروه",
                                "administrator": "🛡️ ادمین",
                                "member": "👤 عضو عادی",
                                "restricted": "🚫 محدودشده",
                                "left": "⬅️ ترک کرده",
                                "kicked": "⛔ بن شده"
                            }
                            status = status_map.get(member.status, member.status)

                            caption = (
                                f"🆔 آیدی عددی: <code>{user_id}</code>\n"
                                f"👤 اسم: {first_name} {last_name}\n"
                                f"🔗 یوزرنیم: {username}\n"
                                f"🤖 بات هست؟ {is_bot}\n"
                                f"📌 وضعیت در گروه: {status}\n"
                            )

                            # عکس پروفایل
                            photos = await self.bot.get_user_profile_photos(user_id, limit=1)
                            if photos.total_count > 0:
                                file_id = photos.photos[0][0].file_id
                                await self.bot.send_photo(chat_id, file_id, caption, parse_mode="HTML")
                            else:
                                await self.bot.send_message(chat_id, caption, parse_mode="HTML")

                        except Exception as e:
                            await self.bot.send_message(chat_id, f"❌ خطا در گرفتن اطلاعات کاربر:\n<code>{e}</code>", parse_mode="HTML")

                    # MUTE
                    if (text.startswith("خفه") or text.startswith("سکوت")):
                        if not await self.db.is_admin(chat_id, user_id, sender_chat_id):
                            await self.bot.reply_to(message, "دوست عزیز، شما دسترسی ادمین ندارید" if int(await self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "اخه چی بگم من به تو")
                            return
                        if await self.db.is_admin(chat_id, target_id):
                            await self.bot.reply_to(message, "دوست عزیز، فرد انتخاب شده ادمین است" if int(await self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "حاجی بی شوخی خیلی کصخلی طرف ادمینه من اینو چیکارش کنم")
                            return
                        if target_id == self.me.id:
                            await self.bot.reply_to(message, "❌ نمی‌توانم خودم را سکوت کنم!" if int(await self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "چرا انقدر همه با من بد هستند")
                            return
                        parts = text.split()
                        if len(parts) >= 2 and parts[1].isdigit():
                            mins = int(parts[1])
                            if mins == "شو":
                                await self.bot.restrict_chat_member(chat_id, target_id, can_send_messages=False)
                                await self.db.add_punishment(chat_id, target_id, "mute", "0")
                                await self.bot.reply_to(message, f"🔇 کاربر سکوت داده شد.")
                            else:
                                await self.bot.restrict_chat_member(chat_id, target_id,
                                                    until_date=int(time.time()+mins*60),
                                                    can_send_messages=False)
                                await self.db.add_punishment(chat_id, target_id, "mute", int(time.time()+mins*60))
                                await self.bot.reply_to(message, f"🔇 کاربر سکوت داده شد برای {mins} دقیقه.")

                    elif (text.startswith("اخطار")):
                        if not await self.db.is_admin(chat_id, user_id, sender_chat_id):
                            await self.bot.reply_to(message, "دوست عزیز، شما دسترسی ادمین ندارید" if int(await self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "برنامه نویس : خداوکیلی مغزم گوزید دیگه نمیدونم چی بنویسم")
                            return
                        if await self.db.is_admin(chat_id, target_id):
                            await self.bot.reply_to(message, "دوست عزیز، فرد انتخاب شده ادمین است" if int(await self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "اخه کصمغز چرا باید ادمینو اخطار بدم")
                            return
                        if target_id == self.me.id:
                            await self.bot.reply_to(message, "❌ نمی‌توانم خودم را اخطار کنم!" if int(await self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "به کدامین گناه؟")
                            return
                        await self.db.warn_user(chat_id, target_id)
                        warns = await self.db.get_user_warnings(chat_id, target_id)
                        warn_max = await self.db.get_group_setting(chat_id, "WARN_MAXIMUM", 3)
                        await self.bot.reply_to(message, f"کاربر با موفقیت اخطار داده شد! ⚠️\n اخطار های کاربر : {warns}/{warn_max}")
                        if int(warns) >= int(warn_max):
                            punish = await self.db.get_group_setting(chat_id, "WARN_PUNISHMENT", "kick")
                            if punish == "kick":
                                await self.bot.ban_chat_member(chat_id, target_id)
                                await self.bot.unban_chat_member(chat_id, target_id)
                                await self.db.add_punishment(chat_id, target_id, "kick")
                                await self.bot.reply_to(message, "👢 کاربر کیک شد!")
                            elif punish == "ban":
                                await self.bot.ban_chat_member(chat_id, target_id)
                                await self.db.add_punishment(chat_id, target_id, "ban")
                                await self.bot.reply_to(message, "⛔ کاربر بن شد!")
                            elif punish == "mute":
                                await self.bot.restrict_chat_member(chat_id, target_id, can_send_messages=False)
                                await self.bot.reply_to(message, "کاربر میوت شد! 🤐")
                            await self.db.remove_all_warns(chat_id, target_id)

                    elif (text == "حذف اخطارها") and await self.db.is_admin(chat_id, user_id, sender_chat_id):
                        if await self.db.is_admin(chat_id, target_id):
                            await self.bot.reply_to("فرد انتخاب شده ادمین است" if int(await self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "چیزی میزنی؟ اصلا مگه میتونم اخطار بدم که الان میگی حذف اخطار")
                            return
                        await self.db.remove_all_warns(chat_id, target_id)
                        await self.bot.reply_to(message, "شتر دیدی ندیدی! ✅")



                    # KICK
                    elif (text == "ریم" or text == "کیک" or text == "سیک"):
                        if not await self.db.is_admin(chat_id, user_id, sender_chat_id):
                            await self.bot.reply_to(message, "دوست عزیز، شما دسترسی ادمین ندارید" if int(await self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "برو تا سیکتو نزدم")
                            return
                        if await self.db.is_admin(chat_id, target_id):
                            await self.bot.reply_to(message, "دوست عزیز، فرد انتخاب شده ادمین است" if int(await self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "باشه داداش دوبار الان برات ادمینو کیک میکنم")
                            return
                        if target_id == self.me.id:
                            await self.bot.reply_to(message, "❌ نمی‌توانم خودم را کیک کنم!" if int(await self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "حالا باهم یه چندتا شوخی کردیم چرا میخوای منو کیک کنی")
                            return
                        await self.bot.ban_chat_member(chat_id, target_id)
                        await self.bot.unban_chat_member(chat_id, target_id)
                        await self.db.add_punishment(chat_id, target_id, "kick")
                        await self.bot.reply_to(message, "👢 کاربر کیک شد!")

                    # BAN
                    elif (text == "بن" or text =="سیکتیر"):
                        if not await self.db.is_admin(chat_id, user_id, sender_chat_id):
                            await self.bot.reply_to(message, "دوست عزیز، شما دسترسی ادمین ندارید" if int(await self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "کیر شدی بدبخت ادمین نیستی")
                            return
                        if await self.db.is_admin(chat_id, target_id):
                            await self.bot.reply_to(message, "دوست عزیز، فرد انتخاب شده ادمین است" if int(await self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "پاول دوروفم نمیتونه ادمین بن کنه تو دیگه چه انتظاری داری")
                            return
                        if target_id == self.me.id:
                            await self.bot.reply_to(message, "❌ نمی‌توانم خودم را بن کنم!" if int(await self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "عامو تفنگو بگیر اونور به من چیکار داری")
                            return
                        await self.bot.ban_chat_member(chat_id, target_id)
                        await self.db.add_punishment(chat_id, target_id, "ban")
                        await self.bot.reply_to(message, "⛔ کاربر بن شد!")

                    elif (text == "مخفی کاری" or text == "بن+" or text.startswith("سیک مخفی")):
                        if not await self.db.is_admin(chat_id, user_id, sender_chat_id):
                            await self.bot.reply_to(message, "دوست عزیز، شما دسترسی ادمین ندارید" if int(await self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "ببین بچه جون تا نبردمت زیرزمین خونمون برو گمشو")
                            return
                        if await self.db.is_admin(chat_id, target_id):
                            await self.bot.reply_to(message, "دوست عزیز، نمیتوانم ادمین هارا بن یا کیک کنم" if int(await self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "سیشتیر بابا همتون همینو میگید")
                            return
                        if target_id == self.me.id:
                            await self.bot.reply_to(message, "❌ نمی‌توانم خودم را بن کنم!" if int(await self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "اگر انقدر از من بدت میاد بگو سیکتیر کن سیکتیر کنم")
                            return
                        await self.bot.delete_message(chat_id, message.message_id)
                        await self.bot.ban_chat_member(chat_id, target_id)

                    # UNBAN
                    elif (text == "آن‌بن" or text == "آن بن" or text == "ان بن") and await self.db.is_admin(chat_id, user_id, sender_chat_id):
                        await self.bot.unban_chat_member(chat_id, target_id)
                        await self.db.remove_punishment(chat_id, target_id, "ban")
                        await self.bot.reply_to(message, "✅ کاربر آن‌بن شد!")

                    # UNMUTE
                    elif (text == "آن‌میوت" or text == "آن میوت" or text == "ان میوت") and await self.db.is_admin(chat_id, user_id, sender_chat_id):
                        if target_id == self.me.id:
                            await self.bot.reply_to(message, "❌ نمی‌توانم خودم را آن‌میوت کنم!" if int(await self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "مشتی منکه میوت نیستم بخوام ان میوت شم")
                            return
                        await self.bot.restrict_chat_member(
                            chat_id, 
                            target_id,
                            can_send_messages=True,
                            can_send_media_messages=True,
                            can_add_web_page_previews=True,
                            can_send_polls=True,
                            can_send_other_messages=True
                        )
                        await self.db.remove_punishment(chat_id, target_id, "mute")
                        await self.bot.reply_to(message, "✅ کاربر آن‌میوت شد!")


                if text == "@admins":
                    admins = await self.bot.get_chat_administrators(chat_id)
                    mentions = [f"[{a.user.first_name}](tg://user?id={a.user.id})" for a in admins]
                    await self.bot.send_message(chat_id, " ".join(mentions), parse_mode="Markdown")
                
                file.close()
            except Exception as e:
                error_text = f"handle_messages: {str(e)}\n{traceback.format_exc()}"
                await send_error_to_owner(error_text, OWNER_ID, self.bot, "MAIN_ERROR")

    async def run(self):
        print(f"{self.me.username} Group Helper running...")
        try:
            await self.db.init_db()
            print("✅ Database initialized")

                
            telegram_task = asyncio.create_task(
                self.bot.infinity_polling(skip_pending=False, timeout=40)
            )
                
            bale_task = None
            if hasattr(self, 'bale_bot') and self.bale_bot:
                print("✅ Starting Bale Bot...")
                bale_task = asyncio.create_task(self.bale_bot.start_polling(timeout=40))
                
            if bale_task:
                await asyncio.gather(telegram_task, bale_task)
            else:
                await telegram_task

        except Exception as e:
            error_text = f"Polling crashed: {str(e)}\n{traceback.format_exc()}"
            print(error_text)
            try:
                await send_error_to_owner(error_text, OWNER_ID, self.bot, "POLLING_CRASH")
            except:
                pass
    
    async def stop(self):
        print(f"Shutting down {self.me.username}...")
        await self.bot.stop_polling()

if __name__ == "__main__":
    komak = KomakYaar()
    asyncio.run(komak.run())