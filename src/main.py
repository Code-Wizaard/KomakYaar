if __name__ == "__main__":
    from DataBase import DataBase

import aiosqlite
import asyncio
import time
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
import aiohttp
from io import BytesIO
logger = logging.getLogger('TeleBot').setLevel(logging.INFO)

class KomakYaar():
    def __init__(self):
        self.bot = AsyncTeleBot(API_TOKEN)
        self.me = asyncio.run(self.bot.get_me())
        self.bale_bot = Client(BALE_TOKEN)
        self.bale_bot_me: User = self.bale_bot.get_me()
        # Main help keyboard - categorized
        self.help_keyboard = types.InlineKeyboardMarkup(row_width=2)
        self.help_keyboard.add(
            types.InlineKeyboardButton("👥 مدیریت اعضا", callback_data="help_members"),
            types.InlineKeyboardButton("🔒 قفل‌ها و محدودیت‌ها", callback_data="help_locks"),
            types.InlineKeyboardButton("🎯 فیلترها و پاسخ خودکار", callback_data="help_filters"),
            types.InlineKeyboardButton("💬 دستورات عمومی", callback_data="help_public"),
            types.InlineKeyboardButton("🔗 لینک و دعوت", callback_data="help_invite"),
            types.InlineKeyboardButton("⚙️ تنظیمات گروه", callback_data="help_settings"),
            types.InlineKeyboardButton("📝 گزارش و اخطار", callback_data="help_warnings"),
            types.InlineKeyboardButton("🎭 لقب و اصل", callback_data="help_profile"),
            types.InlineKeyboardButton("🕵️ نجوا (پیام خصوصی)", callback_data="help_whisper"),
            types.InlineKeyboardButton("بریج بله ↔ تلگرام 🌉", callback_data="help_bridge"),
            types.InlineKeyboardButton("❓ سوالات متداول", callback_data="help_faq")
        )

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
        self.profanity_detector = ProfanityDetector()
        self.setup_events()
    
    async def apply_group_permissions(self, chat_id):
        """Apply comprehensive permissions based on all locks"""
        try:
            group_locked = bool(int(await self.db.get_group_setting(chat_id, "GROUP_LOCK", 0)))
            gif_locked = bool(int(await self.db.get_group_setting(chat_id, "GIF_LOCK", 0)))
                
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
            )
            await self.bot.set_chat_permissions(chat_id, permissions)
        except Exception as e:
            print(f"Permission apply error: {e}")
       
    def setup_events(self):
        check = lambda require_admin=False: handler_check(self.bot, self.db, self.anti_spam, require_admin)
        @self.bot.message_handler(func=lambda m: m.text == "فعال شو")
        async def cmd_startgroup(message):
            if await self.db.is_group_blocked(message.chat.id):
                return
            if await self.db.is_group_active(message.chat.id):
                await self.bot.reply_to(message, "گروه از قبل فعال شده بود" if int(await self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "گروه که از قبل فعال بود کصخل")
                return
            if not await self.db.is_admin(message.chat.id, message.from_user.id):
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

        @self.bot.message_handler(func=lambda m: m.text == "پنل قفل")
        @check(require_admin=True)
        async def lock_panel(message: types.Message):
            reply_to = message.reply_to_message
            is_comment = False
            lock_keyboard = types.InlineKeyboardMarkup(row_width=2)
            lock_keyboard.add(
                types.InlineKeyboardButton("قفل لینک ✅" if int(await self.db.get_group_setting(message.chat.id, "LINK_LOCK", 0)) == 1 else "قفل لینک ❌", callback_data="lock_link:"+ ("off" if int(await self.db.get_group_setting(message.chat.id, "LINK_LOCK", 0)) == 1 else "on")),
                types.InlineKeyboardButton("قفل فوروارد ✅" if int(await self.db.get_group_setting(message.chat.id, "FORWARD_LOCK", 0)) == 1 else "قفل فوروارد ❌", callback_data="lock_forward:"+ ("off" if int(await self.db.get_group_setting(message.chat.id, "FORWARD_LOCK", 0)) == 1 else "on")),
                types.InlineKeyboardButton("قفل فحش ✅" if int(await self.db.get_group_setting(message.chat.id, "SWEAR_LOCK", 0)) == 1 else "قفل فحش ❌", callback_data="lock_swear:"+ ("off" if int(await self.db.get_group_setting(message.chat.id, "SWEAR_LOCK", 0)) == 1 else "on")),
                types.InlineKeyboardButton("قفل گروه ✅" if int(await self.db.get_group_setting(message.chat.id, "GROUP_LOCK", 0)) == 1 else "قفل گروه ❌", callback_data="lock_group:"+ ("off" if int(await self.db.get_group_setting(message.chat.id, "GROUP_LOCK", 0)) == 1 else "on")),
                types.InlineKeyboardButton("قفل گیف ✅" if int(await self.db.get_group_setting(message.chat.id, "GIF_LOCK", 0)) == 1 else "قفل گیف ❌", callback_data="lock_gif:"+ ("off" if int(await self.db.get_group_setting(message.chat.id, "GIF_LOCK", 0)) == 1 else "on")),
                types.InlineKeyboardButton("قفل اسپم ✅" if int(await self.db.get_group_setting(message.chat.id, "SPAM_LOCK", 0)) == 1 else "قفل اسپم ❌", callback_data="lock_spam:"+ ("off" if int(await self.db.get_group_setting(message.chat.id, "SPAM_LOCK", 0)) == 1 else "on")),
                types.InlineKeyboardButton("قفل فلاد ✅" if int(await self.db.get_group_setting(message.chat.id, "FLOOD_LOCK", 0)) == 1 else "قفل فلاد ❌", callback_data="lock_flood:"+ ("off" if int(await self.db.get_group_setting(message.chat.id, "FLOOD_LOCK", 0)) == 1 else "on")),
                types.InlineKeyboardButton("قفل اینلاین ✅" if int(await self.db.get_group_setting(message.chat.id, "INLINE_LOCK", 0)) == 1 else "قفل اینلاین ❌", callback_data="lock_inline:"+ ("off" if int(await self.db.get_group_setting(message.chat.id, "INLINE_LOCK", 0)) == 1 else "on"))
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
            if is_comment:
                post_lock = await self.db.post_lock_status(reply_to.chat.id, reply_to.message_id)
                lock_keyboard.add(
                    types.InlineKeyboardButton("قفل پست ✅" if post_lock else "قفل پست ❌", callback_data="post_" + "lock" if not post_lock else "unlock")
                )
            lock_keyboard.add(
                types.InlineKeyboardButton("بستن پنل قفل", callback_data="close_lock_panel")
            )
            await self.bot.reply_to(message, "از دکمه‌های زیر برای قفل و باز کردن ویژگی‌های مختلف گروه استفاده کنید:", reply_markup=lock_keyboard)

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
            word = message.text.replace("مسدود کلمه ", "")
            await self.db.block_word(message.chat.id, word)
            await self.bot.reply_to(message, f"کلمه ی \"{word}\" با موفقیت مسدود شد")

        @self.bot.message_handler(func=lambda m: m.text.startswith("بازکردن کلمه "))
        @check(require_admin=True)
        async def unblock_word(message: types.Message):
            word = message.text.replace("بازکردن کلمه ", "")
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
            await self.bot.reply_to(message, f"از دکمه ی زیر برای تغییر وضعیت درخواست دعوت استفاده کنید \n وضعیت فعلی : {"روشن" if toggle else "خاموش"}", reply_markup=markup)

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
                types.InlineKeyboardButton(f"کیک {"✅" if warn_punish == "kick" else "❌"}", callback_data="warn_punish:kick"),
                types.InlineKeyboardButton(f"بن {"✅" if warn_punish == "ban" else "❌"}", callback_data="warn_punish:ban"),
                types.InlineKeyboardButton(f"میوت {"✅" if warn_punish == "mute" else "❌"}", callback_data="warn_punish:mute")
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
            await self.bot.reply_to(message, f"{await self.db.get_group_rules(message.chat.id) or "قانونی برای این گروه ثبت نشده!"}")



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

            template = await self.db.member_template(message.chat.id)

            for user in message.new_chat_members:
                text = template
                text = text.replace("{name}", user.first_name)
                text = text.replace("{username}", f"@{user.username}" if user.username else user.first_name)
                text = text.replace("{id}", str(user.id))
                text = text.replace("{chat}", message.chat.title)
                # تعداد اعضای گروه
                try:
                    member_count = await self.bot.get_chat_member_count(message.chat.id)
                except:
                    member_count = "نامشخص"
                text = text.replace("{members}", str(member_count))

                await self.bot.send_message(message.chat.id, text)


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
                    current_value = await self.db.get_group_setting(call.message.chat.id, setting.upper() + "_LOCK", 0)
                    if (current_value == 1 and toggle == "on") or (current_value == 0 and toggle == "off"):
                        await self.bot.answer_callback_query(call.id, "این ویژگی از قبل نیز در همین وضعیت بود" if int(await self.db.get_group_setting(call.message.chat.id, "POLITE_MODE", 1)) == 1 else "همینطوریشم همینه ستونم")
                        return
                    await self.apply_group_permissions(call.message.chat.id)
                    locks = {
                        "swear": "فحش",
                        "link": "لینک",
                        "forward": "فوروارد",
                        "group": "گروه",
                        "gif": "گیف",
                        "spam": "اسپم",
                        "flood": "فلاد",
                        "inline": "اینلاین"
                    }
                    await self.bot.answer_callback_query(call.id, f"{locks.get(setting, setting)} با موفقیت {'قفل' if toggle == 'on' else 'باز'} شد" if int(await self.db.get_group_setting(call.message.chat.id, "POLITE_MODE", 1)) == 1 else f"ردیفه ستون {locks.get(setting, setting)} رو {'قفل' if toggle == 'on' else 'باز'} کردم", show_alert=True)
                    lock_keyboard = types.InlineKeyboardMarkup(row_width=2)
                    lock_keyboard.add(
                        types.InlineKeyboardButton("قفل لینک ✅" if int(await self.db.get_group_setting(call.message.chat.id, "LINK_LOCK", 0)) == 1 else "قفل لینک ❌", callback_data="lock_link:"+ ("off" if int(await self.db.get_group_setting(call.message.chat.id, "LINK_LOCK", 0)) == 1 else "on")),
                        types.InlineKeyboardButton("قفل فوروارد ✅" if int(await self.db.get_group_setting(call.message.chat.id, "FORWARD_LOCK", 0)) == 1 else "قفل فوروارد ❌", callback_data="lock_forward:"+ ("off" if int(await self.db.get_group_setting(call.message.chat.id, "FORWARD_LOCK", 0)) == 1 else "on")),
                        types.InlineKeyboardButton("قفل فحش ✅" if int(await self.db.get_group_setting(call.message.chat.id, "SWEAR_LOCK", 0)) == 1 else "قفل فحش ❌", callback_data="lock_swear:"+ ("off" if int(await self.db.get_group_setting(call.message.chat.id, "SWEAR_LOCK", 0)) == 1 else "on")),
                        types.InlineKeyboardButton("قفل گروه ✅" if int(await self.db.get_group_setting(call.message.chat.id, "GROUP_LOCK", 0)) == 1 else "قفل گروه ❌", callback_data="lock_group:"+ ("off" if int(await self.db.get_group_setting(call.message.chat.id, "GROUP_LOCK", 0)) == 1 else "on")),
                        types.InlineKeyboardButton("قفل گیف ✅" if int(await self.db.get_group_setting(call.message.chat.id, "GIF_LOCK", 0)) == 1 else "قفل گیف ❌", callback_data="lock_gif:"+ ("off" if int(await self.db.get_group_setting(call.message.chat.id, "GIF_LOCK", 0)) == 1 else "on")),
                        types.InlineKeyboardButton("قفل اسپم ✅" if int(await self.db.get_group_setting(call.message.chat.id, "SPAM_LOCK", 0)) == 1 else "قفل اسپم ❌", callback_data="lock_spam:"+ ("off" if int(await self.db.get_group_setting(call.message.chat.id, "SPAM_LOCK", 0)) == 1 else "on")),
                        types.InlineKeyboardButton("قفل فلاد ✅" if int(await self.db.get_group_setting(call.message.chat.id, "FLOOD_LOCK", 0)) == 1 else "قفل فلاد ❌", callback_data="lock_flood:"+ ("off" if int(await self.db.get_group_setting(call.message.chat.id, "FLOOD_LOCK", 0)) == 1 else "on")),
                        types.InlineKeyboardButton("قفل اینلاین ✅" if int(await self.db.get_group_setting(call.message.chat.id, "INLINE_LOCK", 0)) == 1 else "قفل اینلاین ❌", callback_data="lock_inline:"+ ("off" if int(await self.db.get_group_setting(call.message.chat.id, "INLINE_LOCK", 0)) == 1 else "on"))
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
                    if is_comment:
                        post_lock = await self.db.post_lock_status(call.message.chat.id, reply_to.message_id)
                        lock_keyboard.add(
                            types.InlineKeyboardButton("قفل پست ✅" if post_lock else "قفل پست ❌", callback_data="post_" + "lock" if not post_lock else "unlock")
                        )
                    lock_keyboard.add(
                        types.InlineKeyboardButton("بستن پنل قفل", callback_data="close_lock_panel")
                    )
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
                    await self.bot.answer_callback_query(call.id, f"قفل پست با موفقیت {"فعال" if status == "lock" else "غیرفعال"} شد ✅", show_alert=True)
                    lock_keyboard = types.InlineKeyboardMarkup(row_width=2)
                    lock_keyboard.add(
                        types.InlineKeyboardButton("قفل لینک ✅" if int(await self.db.get_group_setting(call.message.chat.id, "LINK_LOCK", 0)) == 1 else "قفل لینک ❌", callback_data="lock_link:"+ ("off" if int(await self.db.get_group_setting(call.message.chat.id, "LINK_LOCK", 0)) == 1 else "on")),
                        types.InlineKeyboardButton("قفل فوروارد ✅" if int(await self.db.get_group_setting(call.message.chat.id, "FORWARD_LOCK", 0)) == 1 else "قفل فوروارد ❌", callback_data="lock_forward:"+ ("off" if int(await self.db.get_group_setting(call.message.chat.id, "FORWARD_LOCK", 0)) == 1 else "on")),
                        types.InlineKeyboardButton("قفل فحش ✅" if int(await self.db.get_group_setting(call.message.chat.id, "SWEAR_LOCK", 0)) == 1 else "قفل فحش ❌", callback_data="lock_swear:"+ ("off" if int(await self.db.get_group_setting(call.message.chat.id, "SWEAR_LOCK", 0)) == 1 else "on")),
                        types.InlineKeyboardButton("قفل گروه ✅" if int(await self.db.get_group_setting(call.message.chat.id, "GROUP_LOCK", 0)) == 1 else "قفل گروه ❌", callback_data="lock_group:"+ ("off" if int(await self.db.get_group_setting(call.message.chat.id, "GROUP_LOCK", 0)) == 1 else "on")),
                        types.InlineKeyboardButton("قفل گیف ✅" if int(await self.db.get_group_setting(call.message.chat.id, "GIF_LOCK", 0)) == 1 else "قفل گیف ❌", callback_data="lock_gif:"+ ("off" if int(await self.db.get_group_setting(call.message.chat.id, "GIF_LOCK", 0)) == 1 else "on")),
                        types.InlineKeyboardButton("قفل اسپم ✅" if int(await self.db.get_group_setting(call.message.chat.id, "SPAM_LOCK", 0)) == 1 else "قفل اسپم ❌", callback_data="lock_spam:"+ ("off" if int(await self.db.get_group_setting(call.message.chat.id, "SPAM_LOCK", 0)) == 1 else "on")),
                        types.InlineKeyboardButton("قفل فلاد ✅" if int(await self.db.get_group_setting(call.message.chat.id, "FLOOD_LOCK", 0)) == 1 else "قفل فلاد ❌", callback_data="lock_flood:"+ ("off" if int(await self.db.get_group_setting(call.message.chat.id, "FLOOD_LOCK", 0)) == 1 else "on")),
                        types.InlineKeyboardButton("قفل اینلاین ✅" if int(await self.db.get_group_setting(call.message.chat.id, "INLINE_LOCK", 0)) == 1 else "قفل اینلاین ❌", callback_data="lock_inline:"+ ("off" if int(await self.db.get_group_setting(call.message.chat.id, "INLINE_LOCK", 0)) == 1 else "on"))
                    )
                    
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
                    admin = await self.db.is_admin(call.message.chat.id, call.message.from_user.id)
                    if admin:
                        await self.bot.edit_message_text("پنل به دستور مدیر بسته شد!", call.message.chat.id, call.message.message_id)
                        await self.bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)
                    else:
                        await self.bot.answer_callback_query(call.id, "ادمین نیستی!")

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
                    await self.bot.answer_callback_query(call.id, f"لیست فحش های :\n {" - ".join(eval(array))}")

                elif data.startswith("check:"):
                    rep_id = data.split(":")[1]
                    await self.db.check_report(rep_id)
                    await self.bot.answer_callback_query(call.id, "گزارش با موفقیت توسط شما بررسی شد")
                    await self.bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)

                elif data.startswith("help_"):
                    help_contents = {
                        "help_main": HELP_TEXT,
                        
                        "help_members": (
                            "👥 **مدیریت اعضا**\n\n"
                            "**دستورات پایه:**\n"
                            "• `اخطار` (ریپلای) - اخطار به کاربر\n"
                            "• `حذف اخطارها` (ریپلای) - پاک کردن اخطارها\n"
                            "• `سقف اخطار <عدد>` - تنظیم حداکثر اخطار (پیش‌فرض: 3)\n\n"
                            "**مجازات‌ها:**\n"
                            "• `خفه <دقیقه>` یا `سکوت` - میوت موقت\n"
                            "• `آن‌میوت` - برداشتن میوت\n"
                            "• `کیک` یا `سیک` یا `ریم` - اخراج از گروه\n"
                            "• `بن` یا `سیکتیر` - بن دائم\n"
                            "• `بن+` یا `سیک مخفی` - بن + حذف پیام فرمان\n"
                            "• `آن‌بن` - برداشتن بن\n\n"
                            "**تنظیم مجازات اخطار:**\n"
                            "• `تعیین مجازات اخطار` - انتخاب نوع مجازات (کیک/بن/میوت)"
                        ),
                        
                        "help_locks": (
                            "🔒 **قفل‌ها و محدودیت‌ها**\n\n"
                            "**قفل‌های قابل تنظیم:**\n"
                            "• `قفل فحش` / `بازکردن فحش` - مسدودسازی فحش\n"
                            "• `قفل لینک` / `بازکردن لینک` - مسدودسازی لینک\n"
                            "• `قفل فوروارد` / `بازکردن فوروارد` - مسدودسازی فوروارد\n"
                            "• `قفل گیف` / `بازکردن گیف` - مسدودسازی گیف\n"
                            "• `قفل گروه` / `بازکردن گروه` - قفل کامل گروه\n\n"
                            "**مدیریت کلمات:**\n"
                            "• `مسدود کلمه <متن>` - مسدود کردن کلمه خاص\n"
                            "• `بازکردن کلمه <متن>` - آزاد کردن کلمه\n\n"
                            "**قفل پست‌ها:**\n"
                            "• `قفل پست` (ریپلای روی پست کانال) - غیرفعال کردن کامنت\n"
                            "• `باز کردن پست` (ریپلای) - فعال کردن کامنت\n\n"
                            "**قفل اسپم و فلاد:**\n"
                            "• `قفل اسپم` / `بازکردن اسپم` - جلوگیری از پیام‌های تکراری و سریع\n"
                            "• `قفل فلاد` / `بازکردن فلاد` - جلوگیری از ارسال پیام خیلی سریع پشت سر هم\n\n"
                            "💡 **پنل مدیریت قفل:**\n"
                            "• `پنل قفل` - نمایش پنل گرافیکی برای مدیریت قفل‌ها"
                        ),
                        
                        "help_filters": (
                            "🎯 **فیلترها و پاسخ خودکار**\n\n"
                            "**اضافه کردن فیلتر جدید:**\n"
                            "1. روی پیامی که می‌خواید پاسخ بده **ریپلای** کنید\n"
                            "2. بنویسید: `فیلتر <پاسخ مورد نظر>`\n"
                            "3. مثال: ریپلای روی پیام `سلام` و نوشتن `فیلتر علیک سلام`\n\n"
                            "**حذف فیلتر:**\n"
                            "• ریپلای روی پیام فیلتر شده + `حذف فیلتر`\n"
                            "• یا: `حذف فیلتر <کلمه کلیدی>`\n\n"
                            "**مشاهده فیلترها:**\n"
                            "• `فیلترها` - نمایش لیست تمام فیلترهای گروه\n\n"
                            "💡 فیلترها دقیقاً برابر با کلمه کلیدی عمل می‌کنند (حساس به حروف بزرگ و کوچک نیست)"
                        ),
                        
                        "help_public": (
                            "💬 **دستورات عمومی (قابل استفاده برای همه اعضا)**\n\n"
                            "**فعال/غیرفعال کردن دستورات عمومی:**\n"
                            "• `دستورات عمومی روشن` - فعال کردن\n"
                            "• `دستورات عمومی خاموش` - غیرفعال کردن\n\n"
                            "**دستورات قابل استفاده برای همه:**\n"
                            "• `لینک` - دریافت لینک دعوت اختصاصی\n"
                            "• `قوانین` - مشاهده قوانین گروه\n"
                            "• `فیلترها` - مشاهده فیلترهای فعال\n"
                            "• `اکو <متن>` - تکرار متن (ریپلای اختیاری)\n"
                            "• `کمک یار` - منو و راهنما\n"
                            "• `@admins` - منشن کردن همه ادمین‌ها\n"
                            "• `گزارش` (ریپلای) - گزارش پیام به ادمین‌ها\n"
                            "• `اطلاعات` (ریپلای) - مشاهده اطلاعات کاربر\n"
                            "• `لقب` (ریپلای) - مشاهده لقب کاربر\n"
                            "• `اصل` (ریپلای) - مشاهده اصل و نسب کاربر"
                        ),
                        
                        "help_invite": (
                            "🔗 **لینک دعوت**\n\n"
                            "**دستورات لینک:**\n"
                            "• `لینک` - ساخت لینک دعوت جدید\n\n"
                            "**تنظیمات پیشرفته لینک:**\n"
                            "• `تنظیم حداکثر دعوت <عدد>` - محدودیت تعداد استفاده از لینک\n"
                            "• `درخواست برای ورود` - فعال/غیرفعال کردن نیاز به تایید ادمین\n\n"
                            "💡 **نکات:**\n"
                            "- هر کاربر می‌تونه لینک اختصاصی خودش رو بسازه\n"
                            "- لینک‌ها با نام کاربر سازنده ذخیره می‌شن\n"
                            "- در حالت `درخواست برای ورود`،افرادی که بر روی لینک کلیک میکنند باید توسط ادمین تایید بشن"
                        ),
                        
                        "help_settings": (
                            "⚙️ **تنظیمات گروه**\n\n"
                            "**تنظیم متون:**\n"
                            "• `تنظیم خوشامد` (ریپلای) - متن خوشامدگویی به اعضای جدید\n"
                            "• `تنظیم قوانین` (ریپلای) - قوانین گروه\n"
                            "• `تنظیم متن کامنت` (ریپلای) - متن زیر پست‌های کانال\n\n"
                            "**متغیرهای قابل استفاده در متن خوشامد:**\n"
                            "• `{name}` - نام کاربر جدید\n"
                            "• `{username}` - یوزرنیم کاربر\n"
                            "• `{id}` - آیدی عددی کاربر\n"
                            "• `{chat}` - نام گروه\n"
                            "• `{members}` - تعداد اعضای گروه\n\n"
                            "**مدیریت بات‌ها:**\n"
                            "• `بلاک بات @username` - مسدود کردن یک بات\n"
                            "• `آن‌بلاک بات @username` - آزاد کردن بات\n"
                            "• `بات های بلاک شده` - لیست بات‌های مسدود\n\n"
                            "**سایر تنظیمات:**\n"
                            "• `ریست` - بازنشانی تنظیمات (فیلترها باقی می‌مانند)\n"
                            "• `باادب شو` / `بی ادب شو` - تغییر لحن پاسخ‌های بات\n"
                            "• `درخواست کمک` - درخواست ورود اونر بات به گروه (مشکلات فوری)"
                        ),
                        
                        "help_warnings": (
                            "📝 **سیستم اخطار و گزارش**\n\n"
                            "**اخطار:**\n"
                            "• `اخطار` (ریپلای) - ثبت اخطار برای کاربر\n"
                            "• `حذف اخطارها` (ریپلای) - پاک کردن تمام اخطارهای کاربر\n"
                            "• `سقف اخطار <عدد>` - تعیین حداکثر اخطار (پیش‌فرض: 3)\n"
                            "• `تعیین مجازات اخطار` - انتخاب مجازات پس از رسیدن به سقف\n\n"
                            "**گزارش به ادمین:**\n"
                            "• `گزارش` (ریپلای) - گزارش یک پیام به همه ادمین‌ها\n"
                            "- ادمین‌ها می‌توانند گزارش را در پیوی خود بررسی کنند\n"
                            "- گزارش‌ها شامل لینک مستقیم به پیام هستند\n\n"
                            "💡 مجازات‌های اخطار شامل: کیک، بن، یا میوت می‌شود"
                        ),
                        
                        "help_profile": (
                            "🎭 **لقب و اصل (پروفایل کاربری)**\n\n"
                            "**ثبت اطلاعات:**\n"
                            "• `ثبت لقب <متن>` (ریپلای روی خود یا دیگران) - ثبت لقب\n"
                            "• `ثبت اصل <متن>` (ریپلای) - ثبت اصل و نسب\n\n"
                            "**مشاهده اطلاعات:**\n"
                            "• `لقب` (ریپلای) - مشاهده لقب کاربر\n"
                            "• `اصل` (ریپلای) - مشاهده اصل کاربر\n"
                            "• `اطلاعات` (ریپلای) - اطلاعات کامل (آیدی، وضعیت، عکس)\n\n"
                            "💡 کاربران می‌توانند لقب و اصل خود را ثبت کنند، ادمین‌ها می‌توانند برای دیگران ثبت کنند"
                        ),
                        
                        "help_whisper": (
                            "🕵️ **نجوا (ارسال پیام خصوصی)**\n\n"
                            "**چگونه کار می‌کند:**\n"
                            "از طریق **Inline Mode** می‌توانید به کاربران دیگر پیام خصوصی بفرستید بدون اینکه دیگران ببینند.\n\n"
                            "**طریقه استفاده:**\n"
                            "1. در باکس پیام، `@username_ربات` را تایپ کنید\n"
                            "2. بنویسید: `<متن پیام> @username_مقصد`\n"
                            "3. مثال: `@KomakYaarBot سلام چطوری؟ @Ali`\n"
                            "4. روی نتیجه کلیک کنید و ارسال کنید\n\n"
                            "**نکات مهم:**\n"
                            "- فقط فرستنده و گیرنده می‌توانند پیام را بخوانند\n"
                            "- پیام‌ها در دیتابیس رمزنگاری می‌شوند\n"
                            "- نمی‌توانید به خودتان یا به ربات پیام بفرستید\n"
                            "- در پیوی شخصی نمی‌توانید استفاده کنید"
                        ),

                        "help_bridge": (
                            "🌉 **پل ارتباطی (Telegram ↔ Bale)**\n\n"
                            "**قابلیت:**\n"
                            "ارسال خودکار تمام پیام‌ها، عکس‌ها، ویدیوها و فایل‌ها از یک کانال تلگرام به کانال بله (و بالعکس).\n\n"
                            
                            "**تنظیم پل از تلگرام به بله:**\n"
                            "1. ربات را به عنوان ادمین در **کانال تلگرام** و **کانال بله** اضافه کنید.\n"
                            f"آیدی ربات در بله : [@{self.bale_bot_me.username}](https://ble.ir/{self.bale_bot_me.username})\n"
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
                            "• متن‌های طولانی به صورت هوشمند تمیز می‌شوند تا خطای Markdown رخ ندهد.\n"
                            "• بریج دو طرفه است، این به این معناس که محتوای ارسال شده در بله و محتوای ارسال شده در بله به تلگرام منتقل میشوند.\n"
                            "• پیام‌های ارسال شده در تلگرام ممکن است باری دیگر توسط ربات دوباره به کانال ارسال شوند.\n\n"
                            
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
                            "• https://github.com/Code-Wizaard/KomakYaar\n\n"
                            "**۶. چطور باگ‌ها را گزارش کنم؟**\n"
                            "• به گروه پشتیبانی بات بپیوندید:\n"
                            "• لینک گروه در پیوی بات موجود است"
                        )
                    }
                    
                    if data in help_contents:
                        await self.bot.edit_message_text(
                            chat_id=call.message.chat.id,
                            message_id=call.message.message_id,
                            text=help_contents[data],
                            parse_mode="Markdown",
                            reply_markup=self.back_keyboard if data != "help_main" else self.help_keyboard
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
                        await self.bot.send_message(
                            chat_id,
                            f"[{message.from_user.first_name}](tg://user?id={user_id}) {"اسپم" if violation == "spam" else "فلاد"} نکن! ۵ دقیقه سکوت داده شدی 🔇",
                            parse_mode="Markdown"
                        )
                        return

                
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
                    if not await self.db.is_admin(chat_id, user_id):
                        await self.bot.delete_message(chat_id, message.message_id)

                if int(await self.db.get_group_setting(chat_id, "GIF_LOCK", 0)) == 1:
                    if message.content_type == "animation":
                        if not await self.db.is_admin(chat_id, user_id):
                            await self.bot.delete_message(chat_id, message.message_id)

                if message.via_bot:
                    lock = await self.db.get_group_setting(chat_id, "INLINE_LOCK", 0)
                    if int(lock) == 1 and not await self.db.is_admin(chat_id, user_id):
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

                toggle = await self.db.get_group_setting(message.chat.id, "PUBLIC_COMMANDS", 1)
                if not await self.db.is_admin(message.chat.id, message.from_user.id) and int(toggle) == 0:
                    return

                for word in text.split(" "):
                    word = word.strip("‌")
                    blocked_word = await self.db.blocked_words(chat_id)
                    if word in blocked_word:
                        swears.append(word)

                if int(await self.db.get_group_setting(chat_id, "SWEAR_LOCK", 0)) == 1:
                    with open(SWEARS_PATH) as f:
                        banned_words = {line.strip() for line in f}

                    for word in text.split(" "):
                        word = word.strip("‌")
                        word = word.replace("‌", "")
                        if word in banned_words:
                            swears.append(word)
                    is_swear_flag, accuracy = self.profanity_detector.is_swear(text)

                    if is_swear_flag and accuracy >= 0.75:
                        is_swear = True
                        swears.append("swear detected by model")


                if (not len(swears) == 0) or is_swear:

                    # for swear in swears:
                    #     pattern = re.compile(re.escape(swear), re.IGNORECASE)
                    #     text = pattern.sub(r"\*" * len(swear), text)

                    # if await self.db.is_admin(chat_id, message.from_user.id):
                    #     return
                    # markup = types.InlineKeyboardMarkup()
                    # check_button = types.InlineKeyboardButton("نمایش کلمه", callback_data=f"swear:{repr(swears)}")
                    # markup.add(check_button)
                    #  \n\n متن سانسور شده :\n >> {text}
                    # , reply_markup=markup
                    await self.bot.reply_to(comment_channel if is_comment else message, f"[{message.from_user.first_name}](tg://user?id={user_id}) عزیزم قرار شد دیگه فحش ندیم بیاید باهم دوست باشیم", parse_mode="Markdown")
                    await self.bot.delete_message(chat_id, message.message_id)

                if text.startswith("db:"):
                    await self.bot.reply_to(message, "دوست عزیز، شما اونر نیستید" if int(await self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "گوه نخور بابا این گوزا به تو نیومده")

                if text == "کمک یار" or text == "کمک‌یار":
                    await self.bot.reply_to(message, f"{message.from_user.first_name}")

                if not await self.db.is_group_active(chat_id):
                    return

                tags = await self.db.get_tags(chat_id)
                for k, r in tags.items():
                    if text == k:
                        await self.bot.reply_to(message, r)
                        break

                if text.startswith("سقف اخطار"):
                    if not await self.db.is_admin(chat_id, user_id):
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
                    if not await self.db.is_admin(chat_id, user_id):
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
                    if not await self.db.is_admin(chat_id, user_id):
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
                    if text.startswith("فیلتر") and await self.db.is_admin(chat_id, user_id):
                        keyword = message.reply_to_message.text.strip()
                        response = text[len("فیلتر"):].strip()
                        if keyword and response:
                            await self.db.add_tag(chat_id, keyword, response)
                            await self.bot.reply_to(message, f"✅ فیلتر اضافه شد!\nکلیدواژه: {keyword}\nپاسخ: {response}")
                        else:
                            await self.bot.reply_to(message, "⚠️ فرمت درست: ریپلای روی پیام و نوشتن: فیلتر پاسخ")
                        return

                    if text == "حذف" and await self.db.is_admin(chat_id, user_id):
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
                        if not (await self.db.is_admin(chat_id, user_id) or target_id == user_id):
                            await self.bot.reply_to(message, "دوست عزیز، شما دسترسی ادمین ندارید" if int(await self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "بدو بینم")
                            return
                        alias = text[len("ثبت لقب"):].strip()
                        await self.db.set_alias(chat_id, target_id, alias)
                        await self.bot.reply_to(message, f"لقب {alias} با موفقیت برای این کاربر ثبت شد")

                    if text == "لقب":
                        alias = await self.db.get_alias(chat_id, target_id).strip()
                        await self.bot.reply_to(message, f"لقب ثبت شده برای این کاربر :\n {alias}")

                    if text.startswith("ثبت اصل"):
                        if not (await self.db.is_admin(chat_id, user_id) or target_id == user_id):
                            await self.bot.reply_to(message, "دوست عزیز، شما دسترسی ادمین ندارید" if int(await self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "کیرم تو اصلت")
                            return
                        asl = text[len("ثبت اصل"):].strip()
                        await self.db.set_asl(chat_id, target_id, asl)
                        await self.bot.reply_to(message, f"اصل {asl} با موفقیت برای این کاربر ثبت شد")

                    if text == "اصل":
                        asl = await self.db.get_asl(chat_id, target_id).strip()
                        await self.bot.reply_to(message, f"اصل ثبت شده برای این کاربر :\n {asl}")

                    if text == "تنظیم خوشامد" and await self.db.is_admin(chat_id, user_id):
                        await self.db.set_group_welcome(chat_id, message.reply_to_message.text)
                        await self.bot.reply_to(message, "متن خوشامد گویی ربات با موفقیت تنظیم شد")

                    if text == "تنظیم قوانین" and await self.db.is_admin(chat_id, user_id):
                        await self.db.set_group_rules(chat_id, message.reply_to_message.text)
                        await self.bot.reply_to(message, "قوانین گروه با موفقیت تنظیم شد")

                    if text == "تنظیم متن کامنت" and await self.db.is_admin(chat_id, user_id):
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
                        if not await self.db.is_admin(chat_id, user_id):
                            await self.bot.reply_to(message, "دوست عزیز، شما دسترسی ادمین ندارید" if int(await self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "اخه چی بگم من به تو")
                            return
                        if await self.db.is_admin(chat_id, target_id):
                            await self.bot.reply_to(message, "دوست عزیز، فرد انتخاب شده ادمین است" if int(await self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "حاجی بی شوخی خیلی کصخلی طرف ادمینه من اینو چیکارش کنم")
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
                        if not await self.db.is_admin(chat_id, user_id):
                            await self.bot.reply_to(message, "دوست عزیز، شما دسترسی ادمین ندارید" if int(await self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "برنامه نویس : خداوکیلی مغزم گوزید دیگه نمیدونم چی بنویسم")
                            return
                        if await self.db.is_admin(chat_id, target_id):
                            await self.bot.reply_to(message, "دوست عزیز، فرد انتخاب شده ادمین است" if int(await self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "اخه کصمغز چرا باید ادمینو اخطار بدم")
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

                    elif (text == "حذف اخطارها") and await self.db.is_admin(chat_id, user_id):
                        if await self.db.is_admin(chat_id, target_id):
                            await self.bot.reply_to("فرد انتخاب شده ادمین است" if int(await self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "چیزی میزنی؟ اصلا مگه میتونم اخطار بدم که الان میگی حذف اخطار")
                            return
                        await self.db.remove_all_warns(chat_id, target_id)
                        await self.bot.reply_to(message, "شتر دیدی ندیدی! ✅")



                    # KICK
                    elif (text == "ریم" or text == "کیک" or text == "سیک"):
                        if not await self.db.is_admin(chat_id, user_id):
                            await self.bot.reply_to(message, "دوست عزیز، شما دسترسی ادمین ندارید" if int(await self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "برو تا سیکتو نزدم")
                            return
                        if await self.db.is_admin(chat_id, target_id):
                            await self.bot.reply_to(message, "دوست عزیز، فرد انتخاب شده ادمین است" if int(await self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "باشه داداش دوبار الان برات ادمینو کیک میکنم")
                            return
                        await self.bot.ban_chat_member(chat_id, target_id)
                        await self.bot.unban_chat_member(chat_id, target_id)
                        await self.db.add_punishment(chat_id, target_id, "kick")
                        await self.bot.reply_to(message, "👢 کاربر کیک شد!")

                    # BAN
                    elif (text == "بن" or text =="سیکتیر"):
                        if not await self.db.is_admin(chat_id, user_id):
                            await self.bot.reply_to(message, "دوست عزیز، شما دسترسی ادمین ندارید" if int(await self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "کیر شدی بدبخت ادمین نیستی")
                            return
                        if await self.db.is_admin(chat_id, target_id):
                            await self.bot.reply_to(message, "دوست عزیز، فرد انتخاب شده ادمین است" if int(await self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "پاول دوروفم نمیتونه ادمین بن کنه تو دیگه چه انتظاری داری")
                            return
                        await self.bot.ban_chat_member(chat_id, target_id)
                        await self.db.add_punishment(chat_id, target_id, "ban")
                        await self.bot.reply_to(message, "⛔ کاربر بن شد!")

                    elif (text == "مخفی کاری" or text == "بن+" or text.startswith("سیک مخفی")):
                        if not await self.db.is_admin(chat_id, user_id):
                            await self.bot.reply_to(message, "دوست عزیز، شما دسترسی ادمین ندارید" if int(await self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "ببین بچه جون تا نبردمت زیرزمین خونمون برو گمشو")
                            return
                        if await self.db.is_admin(chat_id, target_id):
                            await self.bot.reply_to(message, "دوست عزیز، نمیتوانم ادمین هارا بن یا کیک کنم" if int(await self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "سیشتیر بابا همتون همینو میگید")
                            return
                        await self.bot.delete_message(chat_id, message.message_id)
                        await self.bot.ban_chat_member(chat_id, target_id)

                    # UNBAN
                    elif (text == "آن‌بن" or text == "آن بن" or text == "ان بن") and await self.db.is_admin(chat_id, user_id):
                        await self.bot.unban_chat_member(chat_id, target_id)
                        await self.db.remove_punishment(chat_id, target_id, "ban")
                        await self.bot.reply_to(message, "✅ کاربر آن‌بن شد!")

                    # UNMUTE
                    elif (text == "آن‌میوت" or text == "آن میوت" or text == "ان میوت") and await self.db.is_admin(chat_id, user_id):
                        await self.bot.restrict_chat_member(chat_id, target_id,
                                                can_send_messages=True, can_send_media_messages=True)
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