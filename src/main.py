if __name__ == "__main__":
    from DataBase import DataBase

import sqlite3
import time
from telebot import TeleBot, types
import logging
import json
import re
from vars import *
import datetime
import base64
import hashlib
from cryptography.fernet import Fernet
logger = logging.getLogger('TeleBot').setLevel(logging.INFO)

bot = TeleBot(API_TOKEN)
me = bot.get_me()

# دکمه‌های بخش‌ها
help_keyboard = types.InlineKeyboardMarkup(row_width=1)
help_keyboard.add(
    types.InlineKeyboardButton("👮 مدیریت اعضا", callback_data="help_admins"),
    types.InlineKeyboardButton("🏷️ فیلترها و پاسخ خودکار", callback_data="help_tags"),
    types.InlineKeyboardButton("⚙️ تنظیمات گروه", callback_data="help_settings"),
    types.InlineKeyboardButton("🔗 لینک دعوت", callback_data="help_invite"),
)
start_keyboard = types.InlineKeyboardMarkup(row_width=1)
start_keyboard.add(
    types.InlineKeyboardButton("اضافه کردن ربات به گروه", url=f"https://t.me/{me.username}?startgroup")
)

class KomakYaar():
    def __init__(self):
        self.db = DataBase()
        self.setup_events()
    
    def setup_events(self):
        @bot.message_handler(func=lambda m: m.text == "فعال شو")
        def cmd_startgroup(message):
            if self.db.is_group_blocked(message.chat.id):
                return
            if self.db.is_group_active(message.chat.id):
                bot.reply_to(message, "گروه از قبل فعال شده بود" if int(self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "گروه که از قبل فعال بود کصخل")
                return
            self.db.ensure_group(message.chat.id)
            if not self.db.is_admin(message.chat.id, message.from_user.id):
                bot.reply_to(message, "دوست عزیز، شما دسترسی ادمین ندارید" if int(self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "اخه تو ادمینی؟")
                return
            self.db.set_group_active(message.chat.id)
            bot.reply_to(message, "✅ گروه فعال شد و بات آماده مدیریت است!")

        @bot.message_handler(func=lambda m: m.text == "سیکتیر کن")
        def leaver(message):
            if self.db.is_group_blocked(message.chat.id):
                return
            if not self.db.is_admin(message.chat.id, message.from_user.id):
                bot.reply_to(message, "دوست عزیز، شما دسترسی ادمین ندارید" if int(self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "خفه شو تا سیکتو نزدم")
                return
            bot.reply_to(message, "ناراحت شدم، میرم سیکتیر کنم")
            bot.leave_chat(message.chat.id)


        @bot.message_handler(func=lambda m: m.text == "راهنما")
        def send_help(message):
            if self.db.is_group_blocked(message.chat.id):
                return
            try:
                bot.send_message(message.from_user.id, HELP_TEXT, reply_markup=help_keyboard)
                if message.chat.type != "private":
                    bot.reply_to(message, "📬 پنل راهنما به پیوی شما ارسال شد!")
            except:
                bot.reply_to(message, "⚠️ نمی‌تونم پیوی شما پیام بفرستم، لطفا دایرکت ربات رو باز کنید.")


        @bot.message_handler(func=lambda m: m.text == "ریست")
        def reset_bot_in_group(message):
            if self.db.is_group_blocked(message.chat.id):
                return
            if not self.db.is_group_active(message.chat.id):
                bot.reply_to(message, "دوست عزیز، گروه شما فعال نیست که بخواد ریست بشه" if int(self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "گروهت فعال نیست که بخوای ریست کنی")
                return
            if not self.db.is_admin(message.chat.id, message.from_user.id):
                bot.reply_to(message, "دوست عزیز، شما دسترسی ادمین ندارید" if int(self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "خفه شو")
                return
            msg = bot.reply_to(message, "حله، الان کل رکورد گروه (بجز فیلتر ها) رو پاک و بازنویسی از صفر میکنم، انگار که هیچ اتفاقی نیوفتاده")
            self.db.reset_group(message.chat.id)
            bot.edit_message_text("خب، تموم شد، همه چی ریست شد", message.chat.id, msg.id)

        @bot.message_handler(func=lambda m: m.text.startswith("تنظیم حداکثر دعوت"))
        def change_maximum(message:types.Message):
            if self.db.is_group_blocked(message.chat.id):
                return
            if not self.db.is_admin(message.chat.id, message.from_user.id):
                bot.reply_to(message, "دوست عزیز، شما دسترسی ادمین ندارید" if int(self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "حداقل حداکثرتو یکی میکنما!")
                return
            if message.text[len("تنظیم حداکثر دعوت"):].strip().isdigit():
                maximum = int(message.text[len("تنظیم حداکثر دعوت"):].strip())
                self.db.set_group_setting(message.chat.id, "invite_maximum", maximum)
                if bool(int(self.db.get_group_setting(message.chat.id, "creates_request", 0))):
                    self.db.delete_group_setting(message.chat.id, "creates_request")
                bot.reply_to(message, f"حداکثر تعداد دعوت به {maximum} دعوت تغییر پیدا کرد")
            else:
                bot.reply_to(message, "کصخل اشتباه نوشتی")

        @bot.message_handler(func=lambda m: m.text == "قفل فحش")
        def active_swear_strict(message:types.Message):
            if self.db.is_group_blocked(message.chat.id):
                return
            if not self.db.is_group_active(message.chat.id):
                bot.reply_to(message, "دوست عزیز، گروه شما فعال نیست" if int(self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "گروهت فعال نیست که بخوای قفل فحش کنی")
                return
            if not self.db.is_admin(message.chat.id, message.from_user.id):
                bot.reply_to(message, "دوست عزیز، شما دسترسی ادمین ندارید" if int(self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else ":\\ گمشو از جلو چشام دور شو")
                return
            if int(self.db.get_group_setting(message.chat.id, "SWEAR_LOCK", 0)) in [-1, 1]:
                self.db.set_group_setting(message.chat.id, "SWEAR_LOCK", 1)
                bot.reply_to(message, "ضدفحش در حال حاضر نیز فعال است" if int(self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "همینطوریشم فعال هست ستونم")
            else:
                self.db.set_group_setting(message.chat.id, "SWEAR_LOCK", 1)
                bot.reply_to(message, "قفل فعال شد")

        @bot.message_handler(func=lambda m: m.text == "بازکردن فحش")
        def active_swear_strict(message:types.Message):
            if self.db.is_group_blocked(message.chat.id):
                return
            if not self.db.is_group_active(message.chat.id):
                bot.reply_to(message, "دوست عزیز، گروه شما فعال نیست" if int(self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "گروهت فعال نیست که")
                return
            if not self.db.is_admin(message.chat.id, message.from_user.id):
                bot.reply_to(message, "دوست عزیز، شما دسترسی ادمین ندارید" if int(self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else ":\\ گمشو از جلو چشام دور شو")
                return
            if int(self.db.get_group_setting(message.chat.id, "SWEAR_LOCK", 0)) in [-1, 0]:
                self.db.set_group_setting(message.chat.id, "SWEAR_LOCK", 0)
                bot.reply_to(message, "ضدفحش در حال حاضر نیز غیرفعال است" if int(self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "همینطوریشم غیرفعال هست ستونم")
            else:
                self.db.set_group_setting(message.chat.id, "SWEAR_LOCK", 0)
                bot.reply_to(message, "قفل غیرفعال شد")

        @bot.message_handler(func=lambda m: m.text == "قفل گروه")
        def lock_group(message: types.Message):
            if self.db.is_group_blocked(message.chat.id):
                return
            if not self.db.is_admin(message.chat.id, message.from_user.id):
                bot.reply_to(message, "دوست عزیز، شما دسترسی ادمین ندارید" if int(self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "لطفا تا ادمین نشدی گوه نخور")
                return
            if int(self.db.get_group_setting(message.chat.id, "GROUP_LOCK", 0)) == 0:
                self.db.set_group_setting(message.chat.id, "GROUP_LOCK", 1)
                bot.reply_to(message, "گروه با موفقیت قفل شد" if int(self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "کسی خایه داره پیام بده")
                bot.set_chat_permissions(message.chat.id, types.ChatPermissions(can_send_animations=not bool(int(self.db.get_group_setting(message.chat.id, "GIF_LOCK", 0))), can_send_messages=False))
            else:
                bot.reply_to(message, "گروه از قبل نیز قفل بود" if int(self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "گروه که از قبل قفل بود کصخل")

        @bot.message_handler(func=lambda m: m.text == "بازکردن گروه")
        def unlock_group(message: types.Message):
            if self.db.is_group_blocked(message.chat.id):
                return
            if not self.db.is_admin(message.chat.id, message.from_user.id):
                bot.reply_to(message, "دوست عزیز، شما دسترسی ادمین ندارید" if int(self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "لطفا تا ادمین نشدی گوه نخور")
                return
            if int(self.db.get_group_setting(message.chat.id, "GROUP_LOCK", 0)) == 0:
                bot.reply_to(message, "گروه از قبل نیز باز بود" if int(self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "گروه که از قبل باز بود کصخل")
            else:
                self.db.set_group_setting(message.chat.id, "GROUP_LOCK", 0)
                bot.reply_to(message, "گروه با موفقیت باز شد" if int(self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "راحت گوه بخورید")
                bot.set_chat_permissions(message.chat.id, types.ChatPermissions(can_send_animations=not bool(int(self.db.get_group_setting(message.chat.id, "GIF_LOCK", 0))), can_send_messages=True))

        @bot.message_handler(func=lambda m: m.text == "بی ادب شو")
        def turn_rude(message: types.Message):
            if self.db.is_group_blocked(message.chat.id):
                return
            if not self.db.is_admin(message.chat.id, message.from_user.id):
                bot.reply_to(message, "دوست عزیز، شما ادمین نیستید")
                return
            if int(self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1:
                self.db.set_group_setting(message.chat.id, "POLITE_MODE", 0)
                bot.reply_to(message, "وقتشه کیری حرف بزنم")
            else:
                bot.reply_to(message, "کصمغز منکه از قبلشم بی ادب بودم")

        @bot.message_handler(func=lambda m: m.text == "باادب شو")
        def turn_polite(message: types.Message):
            if self.db.is_group_blocked(message.chat.id):
                return
            if not self.db.is_admin(message.chat.id, message.from_user.id):
                bot.reply_to(message, "دوست عزیز، شما دسترسی ادمین ندارید")
                return
            if int(self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1:
                bot.reply_to(message, "بنده از قبل باادب بوده‌ام")
            else:
                self.db.set_group_setting(message.chat.id, "POLITE_MODE", 1)
                bot.reply_to(message, "ادب کیری مهمه، من باادب میشم")

        @bot.message_handler(func=lambda m: m.text == "قفل لینک")
        def link_blocker(message: types.Message):
            if self.db.is_group_blocked(message.chat.id):
                return
            if not self.db.is_admin(message.chat.id, message.from_user.id):
                bot.reply_to(message, "دوست عزیز، شما دسترسی ادمین ندارید" if int(self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "نذار دولمو به کصت لینک کنم")
                return
            if int(self.db.get_group_setting(message.chat.id, "LINK_LOCK", 0)) == 1:
                bot.reply_to(message, "ضدلینک در حال حاضر نیز فعال است" if int(self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "خیالت راحت باشه نمیگفتی هم لینکارو پاک میکردم")
            else:
                self.db.set_group_setting(message.chat.id, "LINK_LOCK", 1)
                bot.reply_to(message, "ضدلینک فعال شد" if int(self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "ردیفه ستون اوکیش کردم")

        @bot.message_handler(func= lambda m: m.text == "بازکردن لینک")
        def link_unblocking(message: types.Message):
            if self.db.is_group_blocked(message.chat.id):
                return
            if not self.db.is_admin(message.chat.id, message.from_user.id):
                bot.reply_to(message, "دوست عزیز، شما دسترسی ادمین ندارید" if int(self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "خیلی دوست داری بازت کنم نه؟")
                return
            if int(self.db.get_group_setting(message.chat.id, "LINK_LOCK", 0)) == 0:
                bot.reply_to(message, "ضدلینک از قبل نیز غیرفعال بود" if int(self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "باع، قفل که قبلشم باز بود")
            else:
                self.db.set_group_setting(message.chat.id, "LINK_LOCK", 0)
                bot.reply_to(message, "ضدلینک غیرفعال شد" if int(self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "انقدر لینکو باز کردم تا جر خورد (اوکی)")

        @bot.message_handler(func=lambda m: m.text == "قفل فوروارد")
        def forward_blocker(message: types.Message):
            if self.db.is_group_blocked(message.chat.id):
                return
            if not self.db.is_admin(message.chat.id, message.from_user.id):
                bot.reply_to(message, "دوست عزیز، شما دسترسی ادمین ندارید" if int(self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "نذار دولمو به کصت فوروارد کنم")
                return
            if int(self.db.get_group_setting(message.chat.id, "FORWARD_LOCK", 0)) == 1:
                bot.reply_to(message, "ضدفوروارد در حال حاضر نیز فعال است" if int(self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "خیالت راحت باشه نمیگفتی هم فورواردارو پاک میکردم")
            else:
                self.db.set_group_setting(message.chat.id, "FORWARD_LOCK", 1)
                bot.reply_to(message, "ضدفوروارد فعال شد" if int(self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "ردیفه ستون اوکیش کردم")

        @bot.message_handler(func=lambda m: m.text == "بازکردن فوروارد")
        def forward_unblocking(message: types.Message):
            if self.db.is_group_blocked(message.chat.id):
                return
            if not self.db.is_admin(message.chat.id, message.from_user.id):
                bot.reply_to(message, "دوست عزیز، شما دسترسی ادمین ندارید" if int(self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "خیلی دوست داری بازت کنم نه؟")
                return
            if int(self.db.get_group_setting(message.chat.id, "FORWARD_LOCK", 0)) == 0:
                bot.reply_to(message, "ضدفوروارد از قبل نیز غیرفعال بود" if int(self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "باع، قفل که قبلشم باز بود")
            else:
                self.db.set_group_setting(message.chat.id, "FORWARD_LOCK", 0)
                bot.reply_to(message, "ضدفوروارد غیرفعال شد" if int(self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "انقدر فورواردارو باز کردم تا جر خورد (اوکی)")

        @bot.message_handler(func=lambda m: m.text == "قفل گیف")
        def gif_lock(message: types.Message):
            if self.db.is_group_blocked(message.chat.id):
                return
            if not self.db.is_admin(message.chat.id, message.from_user.id):
                bot.reply_to(message, "دوست عزیز، شما دسترسی ادمین ندارید" if int(self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "نذار دولمو به کصت گیف کنم")
                return
            if int(self.db.get_group_setting(message.chat.id, "GIF_LOCK", 0)) == 1:
                bot.reply_to(message, "ضدگیف در حال حاضر نیز فعال است" if int(self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "خیالت راحت باشه نمیگفتی هم گیفارو پاک میکردم")
            else:
                self.db.set_group_setting(message.chat.id, "GIF_LOCK", 1)
                bot.reply_to(message, "ضدگیف فعال شد" if int(self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "ردیفه ستون اوکیش کردم")

        @bot.message_handler(func=lambda m: m.text == "بازکردن گیف")
        def gif_unlock(message: types.Message):
            if self.db.is_group_blocked(message.chat.id):
                return
            if not self.db.is_admin(message.chat.id, message.from_user.id):
                bot.reply_to(message, "دوست عزیز، شما دسترسی ادمین ندارید" if int(self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "خیلی دوست داری بازت کنم نه؟")
                return
            if int(self.db.get_group_setting(message.chat.id, "GIF_LOCK", 0)) == 0:
                bot.reply_to(message, "ضدگیف از قبل نیز غیرفعال بود" if int(self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "باع، قفل که قبلشم باز بود")
            else:
                self.db.set_group_setting(message.chat.id, "GIF_LOCK", 0)
                bot.reply_to(message, "ضدگیف غیرفعال شد" if int(self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "انقدر گیفارو باز کردم تا جر خورد (اوکی)")

        @bot.message_handler(func=lambda m: m.text == "پنل قفل")
        def lock_panel(message: types.Message):
            if self.db.is_group_blocked(message.chat.id):
                return
            if not self.db.is_admin(message.chat.id, message.from_user.id):
                bot.reply_to(message, "دوست عزیز، شما دسترسی ادمین ندارید" if int(self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "توکی باشی که اینارو برا من تنظیم کنی")
                return
            lock_keyboard = types.InlineKeyboardMarkup(row_width=1)
            lock_keyboard.add(
                types.InlineKeyboardButton("قفل لینک ✅" if int(self.db.get_group_setting(message.chat.id, "LINK_LOCK", 0)) == 1 else "قفل لینک ❌", callback_data="lock_link:"+ ("off" if int(self.db.get_group_setting(message.chat.id, "LINK_LOCK", 0)) == 1 else "on")),
                types.InlineKeyboardButton("قفل فوروارد ✅" if int(self.db.get_group_setting(message.chat.id, "FORWARD_LOCK", 0)) == 1 else "قفل فوروارد ❌", callback_data="lock_forward:"+ ("off" if int(self.db.get_group_setting(message.chat.id, "FORWARD_LOCK", 0)) == 1 else "on")),
                types.InlineKeyboardButton("قفل فحش ✅" if int(self.db.get_group_setting(message.chat.id, "SWEAR_LOCK", 0)) == 1 else "قفل فحش ❌", callback_data="lock_swear:"+ ("off" if int(self.db.get_group_setting(message.chat.id, "SWEAR_LOCK", 0)) == 1 else "on")),
                types.InlineKeyboardButton("قفل گروه ✅" if int(self.db.get_group_setting(message.chat.id, "GROUP_LOCK", 0)) == 1 else "قفل گروه ❌", callback_data="lock_group:"+ ("off" if int(self.db.get_group_setting(message.chat.id, "GROUP_LOCK", 0)) == 1 else "on")),
                types.InlineKeyboardButton("قفل گیف ✅" if int(self.db.get_group_setting(message.chat.id, "GIF_LOCK", 0)) == 1 else "قفل گیف ❌", callback_data="lock_gif:"+ ("off" if int(self.db.get_group_setting(message.chat.id, "GIF_LOCK", 0)) == 1 else "on")),
                types.InlineKeyboardButton("بستن پنل قفل", callback_data="close_lock_panel")
            )
            bot.reply_to(message, "از دکمه‌های زیر برای قفل و باز کردن ویژگی‌های مختلف گروه استفاده کنید:", reply_markup=lock_keyboard)

        @bot.message_handler(func=lambda m: m.text.startswith("دستورات عمومی"))
        def public_commands(message:types.Message):
            if self.db.is_group_blocked(message.chat.id):
                return
            if not self.db.is_admin(message.chat.id, message.from_user.id):
                bot.reply_to(message, "دوست عزیز، شما دسترسی ادمین ندارید" if int(self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "توکی باشی که اینارو برا من تنظیم کنی")
                return
            toggle = message.text.replace("دستورات عمومی", "").strip()
            if toggle == "روشن":
                if self.db.get_group_setting(message.chat.id, "PUBLIC_COMMANDS", 1) == 1:
                    bot.reply_to(message, "دستورات عمومی از قبل نیز برای همه قابل استفاده بود" if int(self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "همینطوریشم روشنه ستونم")
                    return
                else:
                    self.db.set_group_setting(message.chat.id, "PUBLIC_COMMANDS", 1)
                    bot.reply_to(message, "دستورات عمومی روشن شد")
            elif toggle == "خاموش":
                if self.db.get_group_setting(message.chat.id, "PUBLIC_COMMANDS", 1) == 0:
                    bot.reply_to(message, "دستورات عمومی از قبل نیز غیرفعال بود" if int(self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "همینطوریشم خاموشه ستونم")
                    return
                else:
                    self.db.set_group_setting(message.chat.id, "PUBLIC_COMMANDS", 0)
                    bot.reply_to(message, "دستورات عمومی خاموش شد")

        @bot.message_handler(func=lambda m: m.text.startswith("مسدود کلمه "))
        def block_word(message: types.Message):
            if self.db.is_group_blocked(message.chat.id):
                return
            if not self.db.is_admin(message.chat.id, message.from_user.id):
                bot.reply_to("دوست عزیز، شما دسترسی ادمین ندارید" if int(self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "برو گمشو بابا")
                return
            word = message.text.replace("مسدود کلمه ", "")
            self.db.block_word(message.chat.id, word)
            bot.reply_to(message, f"کلمه ی \"{word}\" با موفقیت مسدود شد")

        @bot.message_handler(func=lambda m: m.text.startswith("بازکردن کلمه "))
        def unblock_word(message: types.Message):
            if self.db.is_group_blocked(message.chat.id):
                return
            if not self.db.is_admin(message.chat.id, message.from_user.id):
                bot.reply_to(message, "دوست عزیز، شما دسترسی ادمین ندارید" if int(self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "دیگه اینورا نبینمت ناادمین بی ادب")
                return
            word = message.text.replace("بازکردن کلمه ", "")
            self.db.unblock_word(message.chat.id, word)
            bot.reply_to(message, f"کلمه ی \"{word}\" با موفقیت از مسدودی خارج شد و کاربران میتوانند آنرا در گروه ارسال کنند")

        @bot.message_handler(func=lambda m: m.text.startswith("بلاک بات "))
        def block_bot_handler(message:types.Message):
            if self.db.is_group_blocked(message.chat.id):
                return
            if not self.db.is_admin(message.chat.id, message.from_user.id):
                bot.reply_to(message, "دوست عزیز، شما دسترسی ادمین ندارید" if int(self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "کصخلییییییییییی؟")
                return
            bot_username = message.text.replace("بلاک بات ", "").strip().replace("@", "")
            self.db.block_bot(message.chat.id, bot_username)
            bot.reply_to(message, f"بات {bot_username} بلاک شد")

        @bot.message_handler(func=lambda m: m.text.startswith("آن‌بلاک بات "))
        def unblock_bot_handler(message: types.Message):
            if self.db.is_group_blocked(message.chat.id):
                return
            if not self.db.is_admin(message.chat.id, message.from_user.id):
                bot.reply_to(message, "دوست عزیز، شما دسترسی ادمین ندارید" if int(self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "اره حاجی راستی بهت گفتم کسایی که ادمین نیستن کیر منم نیستن؟")
                return
            bot_username = message.text.replace("آن‌بلاک بات ", "").strip().replace("@", "")
            self.db.unblock_bot(message.chat.id, bot_username)
            bot.reply_to(message, f"بات {bot_username} آن‌بلاک شد")

        @bot.message_handler(func=lambda m: m.text == "درخواست کمک")
        def request_help_group(message: types.Message):
            if not self.db.is_admin(message.chat.id, message.from_user.id):
                bot.reply_to("دوست عزیز، لطفا برای کمک از ادمین گروه درخواست کنید تا این دستور را ارسال کند" if int(self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "سیشتیر بابا")
                return
            confirm_keyboard = types.InlineKeyboardMarkup()
            ok_button = types.InlineKeyboardButton("تایید ✅", callback_data="ok_btn")
            cancel_button = types.InlineKeyboardButton("لغو ❌", callback_data="cancel_req")
            confirm_keyboard.add(ok_button, cancel_button)
            bot.reply_to(message, "این دستور، درخواستی حاوی لینک گروه به اونر برای ورود و حل مشکل شما ارسال میکند، درصورتی که مشکل شما فوری و بدون جواب داخل راهنماها باشد کمک یار به دستور اونر در گروه از کار خواهد افتاد", reply_markup=confirm_keyboard)

        @bot.message_handler(func=lambda m: m.text == "بات های بلاک شده")
        def blocked_bots(message: types.Message):
            if not self.db.is_admin(message.chat.id, message.from_user.id):
                bot.reply_to(message, "دوست عزیز، شما دسترسی ادمین ندارید" if int(self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "خفه شو بابا")
                return
            blocked_bots = self.db.get_botBlocks(message.chat.id)
            if not blocked_bots:
                bot.reply_to(message, "هیچ باتی بلاک نشده")
                return
            string = "بات های بلاک شده :\n"
            for bot_username in blocked_bots:
                string += f" - @{bot_username}\n"
            bot.reply_to(message, string)

        @bot.message_handler(func=lambda m: m.text == "درخواست برای ورود")
        def toggle_request(message:types.Message):
            if self.db.is_group_blocked(message.chat.id):
                return
            if not self.db.is_admin(message.chat.id, message.from_user.id):
                bot.reply_to(message, "دوست عزیز، شما دسترسی ادمین ندارید" if int(self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "توکی باشی که اینارو برا من تنظیم کنی")
                return
            bot.set_message_reaction(message.chat.id, message.message_id, [types.ReactionTypeEmoji('👍')])
            toggle = bool(int(self.db.get_group_setting(message.chat.id, "creates_request", 0)))
            markup = types.InlineKeyboardMarkup()
            if toggle:
                button_off = types.InlineKeyboardButton("خاموش کردن", callback_data="request:off")
                markup.add(button_off)
            else:
                button_on = types.InlineKeyboardButton("روشن کردن", callback_data="request:on")
                markup.add(button_on)
            bot.reply_to(message, f"از دکمه ی زیر برای تغییر وضعیت درخواست دعوت استفاده کنید \n وضعیت فعلی : {"روشن" if toggle else "خاموش"}", reply_markup=markup)

        @bot.message_handler(func=lambda m: m.text == "لینک")
        def create_invite_link(message):
            if self.db.is_group_blocked(message.chat.id):
                return
            toggle = self.db.get_group_setting(message.chat.id, "PUBLIC_COMMANDS", 1)
            if not self.db.is_admin(message.chat.id, message.from_user.id) and int(toggle) == 0:
                return
            lnk = bot.create_chat_invite_link(
                chat_id=message.chat.id,
                name=f"Link by {message.from_user.first_name}",
                member_limit=int(self.db.get_group_setting(message.chat.id, "invite_maximum", 0)),
                creates_join_request=bool(int(self.db.get_group_setting(message.chat.id, "creates_request", 0)))
            )
            bot.reply_to(
                message,
                f"🔗 لینک دعوت مخصوص شما:\n{lnk.invite_link}\n📌 ساخته شده توسط کمک‌یـــار"
            )

        @bot.message_handler(func=lambda m: m.text == "فیلترها")
        def all_filters(message:types.Message):
            if self.db.is_group_blocked(message.chat.id):
                return
            toggle = self.db.get_group_setting(message.chat.id, "PUBLIC_COMMANDS", 1)
            if not self.db.is_admin(message.chat.id, message.from_user.id) and int(toggle) == 0:
                return
            filters = self.db.get_tags(message.chat.id)
            string = "تمامی فیلترها :\n"
            for filter, response in filters.items():
                string += f"{filter} : {response}\n"
            bot.reply_to(message, string)


        @bot.message_handler(func=lambda m: m.text.startswith("اکو "))
        def echo_word(message:types.Message):
            if self.db.is_group_blocked(message.chat.id):
                return
            toggle = self.db.get_group_setting(message.chat.id, "PUBLIC_COMMANDS", 1)
            if not self.db.is_admin(message.chat.id, message.from_user.id) and int(toggle) == 0:
                return
            echo = message.text[len("اکو"):].strip()
            if message.reply_to_message:
                bot.reply_to(message.reply_to_message, f"{message.from_user.first_name}: \n {echo}")
            else:
                bot.send_message(message.chat.id, f"{message.from_user.first_name}: \n {echo}")
            bot.delete_message(message.chat.id, message.message_id)


        @bot.message_handler(func=lambda m: m.text == "قوانین")
        def show_group_rules(message):
            bot.reply_to(message, f"قوانین گروه :\n {self.db.get_group_rules(message.chat.id)}")



        @bot.message_handler(content_types=["new_chat_members"])
        def greet(message):
            if not self.db.is_group_active(message.chat.id) or self.db.is_group_blocked(message.chat.id):
                return

            if message.new_chat_members[0].id == me.id:
                bot.send_message(message.chat.id, """سلام رفقا
من کمک‌یـــارم، یه دستیار مدیریت گروه و یه رفیق باحال برای شما
از طریق من میتونین به راحتی کاربرا، مدیرا، محتوا و... گروهتون رو مدیریت کنید
فقط کافیه برای شروع یه ادمین بگه `فعال شو` تا کارمونو شروع کنیم
برای دیدن طرز کار با من کلمه ی `راهنما` رو ارسال کنید

همچنین، من یه ربات متن‌بازم پس میتونید کد منو ببینید و تغییر بدید و استفاده کنید در صورت نام بردن از کمک یار
لینک پروژه :
https://github.com/Code-Wizaard/KomakYaar
                """, parse_mode="Markdown", disable_web_page_preview=True)
                return

            template = self.db.member_template(message.chat.id)

            for user in message.new_chat_members:
                text = template
                text = text.replace("{name}", user.first_name)
                text = text.replace("{username}", f"@{user.username}" if user.username else user.first_name)
                text = text.replace("{id}", str(user.id))
                text = text.replace("{chat}", message.chat.title)
                # تعداد اعضای گروه
                try:
                    member_count = bot.get_chat_member_count(message.chat.id)
                except:
                    member_count = "نامشخص"
                text = text.replace("{members}", str(member_count))

                bot.send_message(message.chat.id, text)


        @bot.inline_handler(func=lambda q: True)
        def send_whisper(inline_query: types.InlineQuery):
            query = inline_query.query.strip()
            results = []

            if not query:
                help_result = types.InlineQueryResultArticle(
                    id="help",
                    title="راهنمای ارسال نجوا با کمک یار",
                    description=f"پیام خود را به صورت زیر بنویسید تا پیام خصوصی شما به فرد مورد نظر ارسال شود:\n\n@{me.username} <متن پیام> @username",
                    input_message_content=types.InputTextMessageContent(
                        message_text=f"راهنمای ارسال نجوا با کمک یار\n\nبرای ارسال پیام خصوصی به فردی خاص، می‌توانید از فرمت زیر استفاده کنید:\n\n@{me.username} <متن پیام> @username\n\nدر این فرمت، @{me.username} نام کاربری ربات است، <متن پیام> محتوای پیامی است که می‌خواهید ارسال کنید، و @username نام کاربری فردی است که می‌خواهید پیام را برای او ارسال کنید."
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
                            bot.answer_inline_query(inline_query.id, [], cache_time=0, switch_pm_text="نمیتوانید در پیوی نجوا ارسال کنید", switch_pm_parameter="invalid_context")
                            return

                        elif target_username == inline_query.from_user.username:
                            bot.answer_inline_query(inline_query.id, [], cache_time=0, switch_pm_text="شما نمی‌توانید به خودتان پیام دهید", switch_pm_parameter="invalid_target")
                            return
                        elif target_username == me.username:
                            bot.answer_inline_query(inline_query.id, [], cache_time=0, switch_pm_text="شما نمی‌توانید به خود ربات پیام دهید", switch_pm_parameter="invalid_target")
                            return

                        target = "@" + target_username
                        target_chat = None

                        try:
                            target_chat = bot.get_chat(target)
                        except:
                            pass


                        timestamp = int(time.time())
                        token = f"wh#{inline_query.from_user.id}:{target_username}:{timestamp}"

                        

                        result_send = types.InlineQueryResultArticle(
                            id=f"send:{token}",
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
            bot.answer_inline_query(inline_query.id, results, cache_time=0)
        
        @bot.chosen_inline_handler(func=lambda ch: True)
        def chosen_inline(inline_result: types.ChosenInlineResult):
            query = inline_result.query
            result_id = inline_result.result_id

            if result_id != "help":
            
                token = result_id.split(":", 1)[1]
                infos = token.split("#")[1]
                sender_id = infos.split(":")[0]
                receiver_username = infos.split(":")[1]
                target_chat = None
                try:
                    target_chat = bot.get_chat("@" + receiver_username)
                except:
                    pass
                parts = query.rsplit("@", 1)
                message_text = parts[0].strip()
                timestamp = infos.split(":")[2]

                key = base64.urlsafe_b64encode(hashlib.sha256(token.encode('utf-8')).digest())
                f = Fernet(key)
                encrypted_text = f.encrypt(message_text.encode('utf-8'))
                encrypted_str = base64.b64encode(encrypted_text).decode('utf-8')

                self.db.store_whisper(
                    token=token,
                    sender_id=sender_id,
                    receiver_username=receiver_username.lower(),
                    receiver_id=target_chat.id if target_chat else None,
                    whisper=encrypted_str,
                    timestamp=timestamp
                )

        @bot.callback_query_handler(func=lambda call: True)
        def callback_handler(call: types.CallbackQuery):
            try:
                data = call.data
                if data.startswith("showmsg:"):
                    token = data.removeprefix("showmsg:")
                    datab = self.db.get_whisper(token)
                    if not datab:
                        bot.answer_callback_query(call.id, "این پیام منقضی شده یا وجود ندارد", show_alert=True)
                        return
                    
                    if (call.from_user.id == datab["sender_id"]) or (call.from_user.username.lower() == datab["receiver_username"]) or (call.from_user.id == datab["receiver_id"]):
                        encrypted_str = datab["whisper"]
                        encrypted = base64.b64decode(encrypted_str)
                        key = base64.urlsafe_b64encode(hashlib.sha256(token.encode('utf-8')).digest())
                        f = Fernet(key)
                        message_text = f.decrypt(encrypted).decode('utf-8')
                        text = f"{message_text}"
                        bot.answer_callback_query(call.id, text, show_alert=True)
                    else:
                        bot.answer_callback_query(call.id, "شما اجازه دیدن این پیام را ندارید", show_alert=True)
                        return
                    


                elif data.startswith("lock_"):
                    if not self.db.is_admin(call.message.chat.id, call.from_user.id):
                        bot.answer_callback_query(call.id, "دوست عزیز، شما دسترسی ادمین ندارید" if int(self.db.get_group_setting(call.message.chat.id, "POLITE_MODE", 1)) == 1 else "انگشت نکن بیشرف", show_alert=True)
                        return
                    setting = data.split(":")[0].split("_")[1]
                    toggle = data.split(":")[1]
                    current_value = self.db.get_group_setting(call.message.chat.id, setting.upper() + "_LOCK", 0)
                    if (current_value == 1 and toggle == "on") or (current_value == 0 and toggle == "off"):
                        bot.answer_callback_query(call.id, "این ویژگی از قبل نیز در همین وضعیت بود" if int(self.db.get_group_setting(call.message.chat.id, "POLITE_MODE", 1)) == 1 else "همینطوریشم همینه ستونم")
                        return
                    self.db.set_group_setting(call.message.chat.id, setting.upper() + "_LOCK", 1 if toggle == "on" else 0)
                    bot.set_chat_permissions(call.message.chat.id, types.ChatPermissions(can_send_messages=not bool(int(self.db.get_group_setting(call.message.chat.id, "GROUP_LOCK", 0)))))
                    locks = {
                        "swear": "فحش",
                        "link": "لینک",
                        "forward": "فوروارد",
                        "group": "گروه",
                        "gif": "گیف"
                    }
                    bot.answer_callback_query(call.id, f"{locks[setting]} با موفقیت {'قفل' if toggle == 'on' else 'باز'} شد" if int(self.db.get_group_setting(call.message.chat.id, "POLITE_MODE", 1)) == 1 else f"ردیفه ستون {setting} رو {'قفل' if toggle == 'on' else 'باز'} کردم", show_alert=True)
                    lock_keyboard = types.InlineKeyboardMarkup(row_width=1)
                    lock_keyboard.add(
                        types.InlineKeyboardButton("قفل لینک ✅" if int(self.db.get_group_setting(call.message.chat.id, "LINK_LOCK", 0)) == 1 else "قفل لینک ❌", callback_data="lock_link:"+ ("off" if int(self.db.get_group_setting(call.message.chat.id, "LINK_LOCK", 0)) == 1 else "on")),
                        types.InlineKeyboardButton("قفل فوروارد ✅" if int(self.db.get_group_setting(call.message.chat.id, "FORWARD_LOCK", 0)) == 1 else "قفل فوروارد ❌", callback_data="lock_forward:"+ ("off" if int(self.db.get_group_setting(call.message.chat.id, "FORWARD_LOCK", 0)) == 1 else "on")),
                        types.InlineKeyboardButton("قفل فحش ✅" if int(self.db.get_group_setting(call.message.chat.id, "SWEAR_LOCK", 0)) == 1 else "قفل فحش ❌", callback_data="lock_swear:"+ ("off" if int(self.db.get_group_setting(call.message.chat.id, "SWEAR_LOCK", 0)) == 1 else "on")),
                        types.InlineKeyboardButton("قفل گروه ✅" if int(self.db.get_group_setting(call.message.chat.id, "GROUP_LOCK", 0)) == 1 else "قفل گروه ❌", callback_data="lock_group:"+ ("off" if int(self.db.get_group_setting(call.message.chat.id, "GROUP_LOCK", 0)) == 1 else "on")),
                        types.InlineKeyboardButton("قفل گیف ✅" if int(self.db.get_group_setting(call.message.chat.id, "GIF_LOCK", 0)) == 1 else "قفل گیف ❌", callback_data="lock_gif:"+ ("off" if int(self.db.get_group_setting(call.message.chat.id, "GIF_LOCK", 0)) == 1 else "on")),
                        types.InlineKeyboardButton("بستن پنل قفل", callback_data="close_lock_panel")
                    )
                    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=lock_keyboard)

                elif data == "close_lock_panel":
                    bot.set_message_reaction(call.message.chat.id, call.message.message_id, [types.ReactionTypeEmoji('👍')])
                    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)

                elif data == "ok_btn":
                    link = bot.create_chat_invite_link(call.message.chat.id, "CREATED FOR OWNER HELP REQUEST", member_limit=1)
                    markup = types.InlineKeyboardMarkup()
                    goGroup_btn = types.InlineKeyboardButton("رفتن به گروه", link.invite_link)
                    markup.add(goGroup_btn)
                    bot.send_message(OWNER_ID, "درخواست کمک از گروهی ارسال شده\n"
                                     f"نام گروه : {call.message.chat.title}\n"
                                     f"آیدی گروه : {call.message.chat.id}",
                                     reply_markup=markup)
                    bot.edit_message_text("درخواست به اونر ارسال شد! در صورت تایید به گروه عضو خواهد شد", call.message.chat.id, call.message.message_id)

                elif data == "cancel_req":
                    bot.edit_message_text("این درخواست لغو شده است!", call.message.chat.id, call.message.message_id)

                elif data.startswith("request:"):
                    toggle = data.split(":")[1]
                    if toggle == "on":
                        self.db.delete_group_setting(call.message.chat.id, "invite_maximum")
                    self.db.set_group_setting(call.message.chat.id, "creates_request", "1" if toggle == "on" else "0")
                    bot.answer_callback_query(call.id, "درخواست برای دعوت با موفقیت خاموش شد" if toggle == "off" else "درخواست برای دعوت با موفقیت روشن شد")
                    bot.delete_message(call.message.chat.id, call.message.message_id)

                elif data.startswith("swear:"):
                    array = data.split(":")[1]
                    bot.answer_callback_query(call.id, f"لیست فحش های :\n {" - ".join(eval(array))}")

                elif data.startswith("check:"):
                    rep_id = data.split(":")[1]
                    self.db.check_report(rep_id)
                    bot.answer_callback_query(call.id, "گزارش با موفقیت توسط شما بررسی شد")
                    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)

                elif data.startswith("help_"):
                    text_map = {
                        "help_admins": (
                            "👮 مدیریت اعضا:\n"
                            "- `خفه/سکوت <مدت>` : سکوت دادن کاربر (بر حسب دقیقه)\n"
                            "- `آن‌میوت` : آزاد کردن کاربر از سکوت\n"
                            "- `سیک/ریم/کیک` : کیک کردن کاربر\n"
                            "- `بن / سیکتیر` : بن کردن کاربر\n"
                            "- `آن‌بن` : آزاد کردن کاربر از بن\n"
                            "- `سیک مخفی/بن+` : کاربر بدون سر و صدا بن میشه و پیام هم پاک میشه\n"
                            "- `اخطار` : کاربر اخطار داده میشه، میتونید با دستور `سقف اخطار` تعداد اخطارو تغییر بدید که پیش فرض روی ۳ هست و در صورت رسیدن به این تعداد کاربر از گروه کیک میشه\n"
                            "- `حذف اخطارها`: حذف تمامی اخطارهای کاربر و تنظیم اون روی صفر\n"
                            "- `گزارش` : ریپلای روی پیام کاربر برای گزارش دادن به ادمین‌ها\n"
                            "- `مسدود کلمه <کلمه مورد نظر>`: مسدود کردن کلمه از استفاده شدن در گروه\n"
                            "- `بازکردن کلمه <کلمه مورد نظر>`: بازکردن کلمه ی مسدود شده برای استفاده در گروه\n"
                        ),
                        "help_tags": (
                            "🏷️ فیلترها و پاسخ خودکار:\n"
                            "- ریپلای روی پیام + `فیلتر <پاسخ>` : اضافه کردن پاسخ خودکار\n"
                            "- ریپلای روی پیام + `حذف فیلتر` : حذف پاسخ خودکار\n"
                            "- `فیلترها` : نمایش لیست همه فیلترهای گروه\n"
                        ),
                        "help_settings": (
                            "⚙️ تنظیمات گروه:\n"
                            "- ریپلای روی پیام + `تنظیم خوشامد` : تغییر متن خوشامدگویی\n"
                            "- جای گذاری ها در پیام خوشامد :\n"
                            "1. `{name}` : نام کاربر جدید\n"
                            "2. `{username}` : یوزرنیم کاربر جدید\n"
                            "3. `{id}` : آیدی کاربر جدید\n"
                            "4. `{chat}` : نام گروه\n"
                            "5. `{members}` : تعداد اعضای گروه\n"
                            "- ریپلای روی پیام + `تنظیم قوانین` : تغییر قوانین گروه\n"
                            "- `قوانین` : نمایش قوانین ثبت‌شده گروه\n"
                            "- `ریست` : بازنشانی تنظیمات گروه (غیر از فیلترها)\n"
                            "- `سقف اخطار + عدد` : تنظیم سقف اخطار ها به عدد موردنظر\n"
                            "- `بلاک بات @username` : بلاک کردن یک بات از گروه\n"
                            "- `آن‌بلاک بات @username` : آن‌بلاک کردن یک بات از گروه\n"
                            "- `بات های بلاک شده` : نمایش لیست بات‌های بلاک شده در گروه\n"
                            "- `باادب شو\بی ادب شو` : تنظیم مدل رفتار و صحبت کردن ربات\n"
                            "- `ریپلای روی پیام + تنظیم متن کامنت` : تنظیم متنی که ربات زیر پست های کانال کامنت میکند\n"
                            "- `درخواست کمک`: ارسال لینک دعوت گروه به اونر ربات برای کمک گرفتن در صورت بروز مشکل اورژانسی"
                        ),
                        "help_invite": (
                            "🔗 لینک دعوت:\n"
                            "- `تنظیم حداکثر دعوت <عدد>` : محدود کردن تعداد اعضای هر لینک\n"
                            "- `درخواست برای ورود` : روشن/خاموش کردن نیاز به تایید برای عضویت\n"
                            "- `لینک` : ساخت لینک دعوت شخصی\n"
                        )
                    }

                    if data in text_map:
                        bot.edit_message_text(
                            chat_id=call.message.chat.id,
                            message_id=call.message.message_id,
                            text=text_map[data],
                            parse_mode="Markdown",
                            reply_markup=help_keyboard
                        )
                    bot.answer_callback_query(call.id)
            except Exception as e:
                print(f"Callback error: {e}")

        @bot.message_handler(commands=['bangroup'])
        def ban_group(message: types.Message):
            if message.from_user.id != OWNER_ID:
                bot.reply_to(message, "تو اونر بات نیستی")
                return
            if not message.text.startswith("/bangroup "):
                bot.reply_to(message, "فرمت پیامت اشتباهه")
                return
            group_id = message.text.replace("/bangroup ", "")
            if not self.db.is_group_blocked(group_id):
                self.db.ban_group(group_id)
                bot.reply_to(message, "گروه دریافتی با موفقیت بن شد و قادر به کار با ربات نیست")
                bot.send_message(group_id, "درود، متاسفانه، این گروه از کمک‌یــار بن شده و اعضا و ادمین های آن دیگر قادر به کار با ربات نیستند")
            else:
                bot.reply_to(message, "گروه از قبل هم بن شده بود")

        @bot.message_handler(commands=['unbangroup'])
        def unban_group(message: types.Message):
            if message.from_user.id != OWNER_ID:
                bot.reply_to(message, "فقط به حرف اونر گوش میدم")
                return
            if not message.text.startswith("/unbangroup "):
                bot.reply_to(message, "فرمت پیام اشتباه است")
                return
            group_id = message.text.replace("/unbangroup ", "")
            if self.db.is_group_blocked(group_id):
                self.db.unban_group(group_id)
                bot.reply_to(message, "گروه دریافتی با موفقیت از حالت مسدودی درآمد")
                bot.send_message(group_id, "خبر خوب، گروه شما از حالت مسدودی خارج شده و همگی دوباره قادر به استفاده از ربات هستند")
            else:
                bot.reply_to(message, "گروه که اصلا بن نشده بود بخوای آن‌بن کنی")

        @bot.message_handler(commands=['update'])
        def handle_update_command(message):
            if message.from_user.id != OWNER_ID:
                bot.reply_to(message, "فقط اونر می‌تونه آپدیت پخش کنه!")
                return

            text = message.text.strip()
            lines = text.splitlines()

            if len(lines) < 1:
                return

            first_line = lines[0].strip()

            version_match = re.search(r'/update\s+([vV]?\d+\.\d+(\.\d+)?)', first_line, re.IGNORECASE)

            if not version_match:
                bot.reply_to(message, 
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
                bot.reply_to(message, "❌ هیچ آپدیتی نوشته نشده!")
                return

            preview = f"*نسخه جدید ربات کمک‌یار (***{display_version}***) منتشر شد!*\n\n"
            for upd in updates:
                preview += f"{upd}\n"

            bot.reply_to(message, 
                        f"✅ در حال پخش آپدیت {display_version} به همه گروه‌ها...\n\n"
                        f"پیش‌نمایش:\n{preview}", 
                        parse_mode="Markdown")

            try:
                success, err = self.db.update_message(updates, full_version.lstrip('vV'))
                
                bot.reply_to(message, 
                            f"✅ پخش آپدیت تموم شد!\n\n"
                            f"ارسال موفق: {success} گروه\n"
                            f"خطا یا بلاک شده: {err} گروه")
            except Exception as e:
                bot.reply_to(message, f"❌ خطا در پخش آپدیت: {str(e)}")
                

        @bot.message_handler(func=lambda m: m.chat.type == "private")
        def pv_chats(message:types.Message):
            if message.text == "/start":
                bot.send_message(
                    message.chat.id,
                    """سلام 👋

به **ربات کمک‌یار** خوش اومدی 🤖
این ربات بهت کمک می‌کنه گروهت رو راحت‌تر مدیریت کنی.

📌 کاری که لازمه بکنی:
    1. ربات رو به گروه اضافه کن.
    2. دستور `فعال شو` رو بزن.
    3. از این به بعد ربات همه چیز رو هندل می‌کنه.

❓ برای دیدن همه دستورات، کافیه `/help` رو بزنی.

همچنین، من یه ربات متن‌بازم پس میتونید کد منو ببینید و تغییر بدید و استفاده کنید در صورت نام بردن از کمک یار
لینک پروژه :
https://github.com/Code-Wizaard/KomakYaar
            """,
                    parse_mode="Markdown",
                    disable_web_page_preview=True,
                    reply_markup=start_keyboard
            )
            elif message.text == "/help":
                bot.send_message(message.from_user.id, HELP_TEXT, parse_mode="Markdown", reply_markup=help_keyboard)

        @bot.message_handler(func= lambda m: m.from_user.id == OWNER_ID and m.text.startswith("db:"))
        def execute_to_db(message):
            try:
                query = message.text.split(":")[1]
                con = sqlite3.connect(DB_PATH)
                cur = con.cursor()
                cur.execute(query)
                rows = cur.fetchall()
                if rows:
                    bot.reply_to(message, f"Hello Master, These are the responses : \n {json.dumps(rows, ensure_ascii=False)}")
                else:
                    con.commit()
            except Exception as e:
                bot.reply_to(message, f"ریدی ارور گرفتم \n {e}")
            finally:
                con.close()

        @bot.message_handler(func= lambda m: m.from_user.id == OWNER_ID and m.text == ";id;")
        def id_informations_owner(message: types.Message):
            if message.reply_to_message:
                bot.reply_to(message, f"اطلاعات فرد مشخص شده : \n"
                f"آیدی فرد : {message.reply_to_message.from_user.id}\n"
                f"آیدی پیام : {message.reply_to_message.id}\n")
            else:
                bot.reply_to(message, f"آیدی گروه : {message.chat.id}\n")

        @bot.message_handler(func= lambda m: m.from_user.id == OWNER_ID and m.text.startswith("(tag): "))
        def make_id_into_tag(message: types.Message):
            user_id = message.text.replace("(tag): ", "").strip()
            bot.reply_to(message, f"[HereYouGo](tg://user?id={user_id})", parse_mode="Markdown")


        @bot.message_handler(func=lambda m: True, content_types=['text', 'photo', 'video', 'document', 'audio', 'voice', 'sticker', 'animation', 'video_note'])
        def handle_messages(message:types.Message):
            chat_id = message.chat.id
            user_id = message.from_user.id
            text = (message.text or message.caption) or ""
            message.text = text
            is_comment = message.reply_to_message.is_automatic_forward if message.reply_to_message else None
            comment_channel = message.reply_to_message
            file = open(SWEARS_PATH, "r")
            swears = []

            if self.db.is_group_blocked(chat_id):
                return

            if int(self.db.get_group_setting(chat_id, "GROUP_LOCK", 0)) == 1:
                if not self.db.is_admin(chat_id, user_id):
                    bot.delete_message(chat_id, message.message_id)

            if int(self.db.get_group_setting(chat_id, "GIF_LOCK", 0)) == 1:
                if message.content_type == "animation":
                    if not self.db.is_admin(chat_id, user_id):
                        bot.delete_message(chat_id, message.message_id)

            if message.via_bot:
                bot_username = message.via_bot.username
                blocked_bots = self.db.get_botBlocks(message.chat.id)
                if bot_username in blocked_bots:
                    bot.delete_message(message.chat.id, message.message_id)
                    return
                
            if message.is_automatic_forward:
                msg = self.db.get_comment_message(chat_id)
                bot.reply_to(message, msg)
                
            if self.db.get_group_setting(chat_id, "LINK_LOCK", 0):
                if re.search(r"(http|ftp|https):\/\/([\w_-]+(?:(?:\.[\w_-]+)+))([\w.,@?^=%&:\/~+#-]*[\w@?^=%&\/~+#-])", text):
                    bot.delete_message(chat_id, message.message_id)
                    return

            toggle = self.db.get_group_setting(message.chat.id, "PUBLIC_COMMANDS", 1)
            if not self.db.is_admin(message.chat.id, message.from_user.id) and int(toggle) == 0:
                return

            for word in text.split(" "):
                word = word.strip("‌")
                blocked_word = self.db.blocked_words(chat_id)
                if word in blocked_word:
                    swears.append(word)

            if int(self.db.get_group_setting(chat_id, "SWEAR_LOCK", 0)) == 1:
                with open(SWEARS_PATH) as f:
                    banned_words = {line.strip() for line in f}

                for word in text.split(" "):
                    word = word.strip("‌")
                    word = word.replace("‌", "")
                    if word in banned_words:
                        swears.append(word)

            if not len(swears) == 0:

                for swear in swears:
                    pattern = re.compile(re.escape(swear), re.IGNORECASE)
                    text = pattern.sub(r"\*" * len(swear), text)

                if self.db.is_admin(chat_id, message.from_user.id):
                    return
                markup = types.InlineKeyboardMarkup()
                check_button = types.InlineKeyboardButton("نمایش کلمه", callback_data=f"swear:{repr(swears)}")
                markup.add(check_button)
                bot.reply_to(comment_channel if is_comment else message, f"[{message.from_user.first_name}](tg://user?id={user_id}) عزیزم قرار شد دیگه فحش ندیم بیاید باهم دوست باشیم \n\n متن سانسور شده :\n >> {text}", parse_mode="Markdown", reply_markup=markup)
                bot.delete_message(chat_id, message.message_id)

            if text.startswith("db:"):
                bot.reply_to(message, "دوست عزیز، شما اونر نیستید" if int(self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "گوه نخور بابا این گوزا به تو نیومده")

            if text == "کمک یار" or text == "کمک‌یار":
                bot.reply_to(message, f"{message.from_user.first_name}")

            if not self.db.is_group_active(chat_id):
                return

            tags = self.db.get_tags(chat_id)
            for k, r in tags.items():
                if text == k:
                    bot.reply_to(message, r)
                    break

            if text.startswith("سقف اخطار") and self.db.is_admin(chat_id, user_id):
                words = text.split(" ")
                words.remove("سقف")
                words.remove("اخطار")
                self.db.set_warn_maximum(chat_id, words[0])
                bot.reply_to(message, "سقف اخطارها با موفقیت تنظیم شد")

            if text.startswith("حذف فیلتر") and self.db.is_admin(chat_id, user_id):
                # اگر ریپلای شده روی پیام کلیدواژه
                if message.reply_to_message:
                    keyword = message.reply_to_message.text.strip()
                else:
                    # جدا کردن کلیدواژه از متن: حذف فیلتر <کلیدواژه>
                    keyword = text[len("حذف فیلتر"):].strip()

                if keyword:
                    self.db.del_tag(chat_id, keyword)
                    bot.reply_to(message, f"❌ فیلتر '{keyword}' حذف شد")
                else:
                    bot.reply_to(message, "⚠️ فرمت درست: حذف فیلتر روی ریپلای یا با نوشتن کلیدواژه")
                return

            if (message.text.startswith("حذف") and text != "حذف اخطارها") and self.db.is_admin(chat_id, user_id):
                try:
                    n = int(message.text.replace("حذف", "").strip())
                except:
                    n = 1

                chat_id = message.chat.id
                start_id = message.message_id   # id دستور "حذف ۵"
                err = 0
                for i in range(n+1):  # +1 یعنی خود دستور هم پاک بشه
                    try:
                        bot.delete_message(chat_id, start_id - i)
                    except:
                        err += 1
                msg = bot.send_message(chat_id, f"{n-err} با موفقیت حذف شد 🗑️")
                time.sleep(4)
                bot.delete_message(msg.chat.id, msg.message_id)

            if message.reply_to_message:
                target_id = message.reply_to_message.from_user.id

                # ADD TAG (فیلتر)
                if text.startswith("فیلتر") and self.db.is_admin(chat_id, user_id):
                    keyword = message.reply_to_message.text.strip()
                    response = text[len("فیلتر"):].strip()
                    if keyword and response:
                        self.db.add_tag(chat_id, keyword, response)
                        bot.reply_to(message, f"✅ فیلتر اضافه شد!\nکلیدواژه: {keyword}\nپاسخ: {response}")
                    else:
                        bot.reply_to(message, "⚠️ فرمت درست: ریپلای روی پیام و نوشتن: فیلتر پاسخ")
                    return

                if text == "حذف":
                    bot.delete_message(chat_id, message.reply_to_message.message_id)
                    msg = bot.reply_to(message, "پیام پاک شد 🗑️")
                    time.sleep(4)
                    bot.delete_message(msg.chat.id, msg.message_id)

                if text == "گزارش":
                    admins = bot.get_chat_administrators(chat_id)
                    msg = bot.reply_to(message, "گزارش با موفقیت ثبت و به ادمین ها اطلاع رسانی شد، به زودی گزارش بررسی میشود")
                    id = self.db.file_report(chat_id, user_id, target_id, msg.message_id)
                    target = bot.get_chat(target_id)
                    markup = types.InlineKeyboardMarkup()
                    check_button = types.InlineKeyboardButton("بررسی شد", callback_data=f"check:{id}")
                    message_btn = types.InlineKeyboardButton("رفتن به پیام", url=f"https://t.me/c/{str(chat_id)[4:]}/{message.reply_to_message.message_id}")

                    markup.add(check_button)
                    markup.add(message_btn)
                    for admin in admins:
                        if not admin.user.is_bot and admin.user.id != bot.get_me().id:
                            try:
                                bot.send_message(admin.user.id, f"گزارش دریافتی از کاربر [{message.from_user.first_name}](tg://user?id={user_id}) در گروه با ایدی {chat_id}\n فرد گزارش شده : [{target.first_name}](tg://user?id={target_id})\n متن پیام ارسالی :\n > {message.reply_to_message.text}", reply_markup=markup, parse_mode="Markdown")
                            except:
                                pass

                if text.startswith("ثبت لقب") and (self.db.is_admin(chat_id, user_id) or target_id == user_id):
                    alias = text[len("ثبت لقب"):].strip()
                    self.db.set_alias(chat_id, target_id, alias)
                    bot.reply_to(message, f"لقب {alias} با موفقیت برای این کاربر ثبت شد")

                if text == "لقب":
                    alias = self.db.get_alias(chat_id, target_id).strip()
                    bot.reply_to(message, f"لقب ثبت شده برای این کاربر :\n {alias}")

                if text.startswith("ثبت اصل") and (self.db.is_admin(chat_id, user_id) or target_id == user_id):
                    asl = text[len("ثبت اصل"):].strip()
                    self.db.set_asl(chat_id, target_id, asl)
                    bot.reply_to(message, f"اصل {asl} با موفقیت برای این کاربر ثبت شد")

                if text == "اصل":
                    asl = self.db.get_asl(chat_id, target_id).strip()
                    bot.reply_to(message, f"اصل ثبت شده برای این کاربر :\n {asl}")

                if text == "تنظیم خوشامد" and self.db.is_admin(chat_id, user_id):
                    self.db.set_group_welcome(chat_id, message.reply_to_message.text)
                    bot.reply_to(message, "متن خوشامد گویی ربات با موفقیت تنظیم شد")

                if text == "تنظیم قوانین" and self.db.is_admin(chat_id, user_id):
                    self.db.set_group_rules(chat_id, message.reply_to_message.text)
                    bot.reply_to(message, "قوانین گروه با موفقیت تنظیم شد")

                if text == "تنظیم متن کامنت" and self.db.is_admin(chat_id, user_id):
                    self.db.set_comment_message(chat_id, message.reply_to_message.text)
                    bot.reply_to(message, "متن کامنت زیر پست ها تغییر پیدا کرد")

                if text == "اطلاعات":
                    try:
                        # گرفتن اطلاعات پایه کاربر
                        user = bot.get_chat_member(chat_id, target_id).user
                        user_id = user.id
                        first_name = user.first_name or ""
                        last_name = user.last_name or ""
                        username = f"@{user.username}" if user.username else "❌ ندارد"
                        is_bot = "🤖 بله" if user.is_bot else "👤 خیر"

                        # وضعیت کاربر توی گروه
                        member = bot.get_chat_member(chat_id, target_id)
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
                        photos = bot.get_user_profile_photos(user_id, limit=1)
                        if photos.total_count > 0:
                            file_id = photos.photos[0][0].file_id
                            bot.send_photo(chat_id, file_id, caption, parse_mode="HTML")
                        else:
                            bot.send_message(chat_id, caption, parse_mode="HTML")

                    except Exception as e:
                        bot.send_message(chat_id, f"❌ خطا در گرفتن اطلاعات کاربر:\n<code>{e}</code>", parse_mode="HTML")

                # MUTE
                if (text.startswith("خفه") or text.startswith("سکوت")) and self.db.is_admin(chat_id, user_id):
                    if self.db.is_admin(chat_id, target_id):
                        bot.reply_to(message, "دوست عزیز، فرد انتخاب شده ادمین است" if int(self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "من مثل بعضیا خیانتکار نیستم")
                        return
                    parts = text.split()
                    if len(parts) >= 2 and parts[1].isdigit():
                        mins = int(parts[1])
                        if mins == "شو":
                            bot.restrict_chat_member(chat_id, target_id, can_send_messages=False)
                            self.db.add_punishment(chat_id, target_id, "mute", "0")
                            bot.reply_to(message, f"🔇 کاربر سکوت داده شد.")
                        else:
                            bot.restrict_chat_member(chat_id, target_id,
                                                until_date=int(time.time()+mins*60),
                                                can_send_messages=False)
                            self.db.add_punishment(chat_id, target_id, "mute", int(time.time()+mins*60))
                            bot.reply_to(message, f"🔇 کاربر سکوت داده شد برای {mins} دقیقه.")

                elif (text.startswith("اخطار")) and self.db.is_admin(chat_id, user_id):
                    if self.db.is_admin(chat_id, target_id):
                        bot.reply_to(message, "دوست عزیز، فرد انتخاب شده ادمین است" if int(self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "اخه کصمغز چرا باید ادمینو اخطار بدم")
                        return
                    self.db.warn_user(chat_id, target_id)
                    warns = self.db.get_user_warnings(chat_id, target_id)
                    warn_max = self.db.get_group_setting(chat_id, "WARN_MAXIMUM", 3)
                    bot.reply_to(message, f"کاربر با موفقیت اخطار داده شد! ⚠️\n اخطار های کاربر : {warns}/{warn_max}")
                    if warns >= warn_max:
                        punish = self.db.get_group_setting(chat_id, "WARN_PUNISHMENT", "kick")
                        if punish == "kick":
                            bot.ban_chat_member(chat_id, target_id)
                            bot.unban_chat_member(chat_id, target_id)
                            self.db.add_punishment(chat_id, target_id, "kick")
                            bot.reply_to(message, "👢 کاربر کیک شد!")
                        elif punish == "ban":
                            bot.ban_chat_member(chat_id, target_id)
                            self.db.add_punishment(chat_id, target_id, "ban")
                            bot.reply_to(message, "⛔ کاربر بن شد!")
                        elif punish == "mute":
                            bot.restrict_chat_member(chat_id, target_id, can_send_messages=False)
                            bot.reply_to("کاربر میوت شد! 🤐")
                        self.db.remove_all_warns(chat_id, target_id)

                elif (text == "حذف اخطارها") and self.db.is_admin(chat_id, user_id):
                    if self.db.is_admin(chat_id, target_id):
                        bot.reply_to("فرد انتخاب شده ادمین است" if int(self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "چیزی میزنی؟ اصلا مگه میتونم اخطار بدم که الان میگی حذف اخطار")
                        return
                    self.db.remove_all_warns(chat_id, target_id)
                    bot.reply_to(message, "شتر دیدی ندیدی! ✅")



                # KICK
                elif (text == "ریم" or text == "کیک" or text == "سیک") and self.db.is_admin(chat_id, user_id):
                    if self.db.is_admin(chat_id, target_id):
                        bot.reply_to(message, "دوست عزیز، فرد انتخاب شده ادمین است" if int(self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "باشه داداش دوبار الان برات ادمینو کیک میکنم")
                        return
                    bot.ban_chat_member(chat_id, target_id)
                    bot.unban_chat_member(chat_id, target_id)
                    self.db.add_punishment(chat_id, target_id, "kick")
                    bot.reply_to(message, "👢 کاربر کیک شد!")

                # BAN
                elif (text == "بن" or text =="سیکتیر") and self.db.is_admin(chat_id, user_id):
                    if self.db.is_admin(chat_id, target_id):
                        bot.reply_to(message, "دوست عزیز، فرد انتخاب شده ادمین است" if int(self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "پاول دوروفم نمیتونه ادمین بن کنه تو دیگه چه انتظاری داری")
                        return
                    bot.ban_chat_member(chat_id, target_id)
                    self.db.add_punishment(chat_id, target_id, "ban")
                    bot.reply_to(message, "⛔ کاربر بن شد!")

                elif (text == "مخفی کاری" or text == "بن+" or text.startswith("سیک مخفی")) and self.db.is_admin(chat_id, user_id):
                    if self.db.is_admin(chat_id, target_id):
                        bot.reply_to(message, "دوست عزیز، نمیتوانم ادمین هارا بن یا کیک کنم" if int(self.db.get_group_setting(message.chat.id, "POLITE_MODE", 1)) == 1 else "سیشتیر بابا همتون همینو میگید")
                        return
                    bot.delete_message(chat_id, message.message_id)
                    bot.ban_chat_member(chat_id, target_id)

                # UNBAN
                elif (text == "آن‌بن" or text == "آن بن" or text == "ان بن") and self.db.is_admin(chat_id, user_id):
                    bot.unban_chat_member(chat_id, target_id)
                    self.db.remove_punishment(chat_id, target_id, "ban")
                    bot.reply_to(message, "✅ کاربر آن‌بن شد!")

                # UNMUTE
                elif (text == "آن‌میوت" or text == "آن میوت" or text == "ان میوت") and self.db.is_admin(chat_id, user_id):
                    bot.restrict_chat_member(chat_id, target_id,
                                            can_send_messages=True)
                    self.db.remove_punishment(chat_id, target_id, "mute")
                    bot.reply_to(message, "✅ کاربر آن‌میوت شد!")


            if text == "@admins":
                admins = bot.get_chat_administrators(chat_id)
                mentions = [f"[{a.user.first_name}](tg://user?id={a.user.id})" for a in admins]
                bot.send_message(chat_id, " ".join(mentions), parse_mode="Markdown")
            
            file.close()

    def run(self):
        print(f"{me.username} Group Helper running...")
        bot.polling(non_stop=True, skip_pending=True)
    
    def stop(self):
        print(f"Shutting down {me.username}...")
        bot.stop_polling()

if __name__ == "__main__":
    komak = KomakYaar()
    komak.run()