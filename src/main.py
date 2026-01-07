import sqlite3
import time
from telebot import TeleBot, types
import logging
import json
import re
import os
from dotenv import load_dotenv
logger = logging.getLogger('TeleBot').setLevel(logging.INFO)

load_dotenv()
API_TOKEN = os.getenv("TOKEN")
bot = TeleBot(API_TOKEN)
me = bot.get_me()

DB_PATH = os.getenv("DB_PATH", "groups.db")
SWEARS_PATH = os.getenv("SWEARS_PATH", "swears.txt")
OWNER_ID = int(os.getenv("OWNER_ID"))

HELP_TEXT = (
    "📖 راهنمای استفاده از ربات کمک‌یار\n\n"
    "این ربات برای مدیریت ساده و سریع گروه طراحی شده. از منوی زیر می‌تونید بخش‌های مختلف رو ببینید.\n"
    "هر بخش شامل دستورها و توضیحات مرتبطه.\n\n"
    "👇 روی دکمه‌های زیر کلیک کنید:"
)

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



# ---------------- DATABASE ----------------
def db():
    return sqlite3.connect(DB_PATH)

def init_db():
    con = db()
    cur = con.cursor()
    # جدول گروه‌ها
    cur.execute("""
    CREATE TABLE IF NOT EXISTS groups (
        group_id INTEGER PRIMARY KEY,
        welcome_text TEXT DEFAULT '{name} عزیز خوش امدید',
        rules TEXT DEFAULT NULL,
        active INTEGER DEFAULT 0
    )
    """)
    # جدول تگ‌ها
    cur.execute("""
    CREATE TABLE IF NOT EXISTS tags (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        group_id INTEGER,
        keyword TEXT,
        response TEXT
    )
    """)
    # جدول مجازات‌ها
    cur.execute("""
    CREATE TABLE IF NOT EXISTS punishments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        group_id INTEGER,
        user_id INTEGER,
        type TEXT,
        until INTEGER
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS group_settings (
        group_id INTEGER,
        setting_key TEXT,
        setting_value TEXT,
        PRIMARY KEY (group_id, setting_key)
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        group_id INTEGER,
        user_id INTEGER,
        target_id INTEGER,
        msg_id INTEGER,
        status TEXT DEFAULT 'Pending...'
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS aliases (
        group_id INTEGER,
        user_id INTEGER,
        ailas TEXT
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS warnings (
        group_id INTEGER,
        user_id INTEGER,
        warnings INTEGER
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS botBlocks (
            group_id INTEGER,
            bot_username TEXT
        )
    """)


    con.commit()
    con.close()

init_db()


def ensure_group(group_id):
    con = db()
    cur = con.cursor()
    cur.execute("SELECT group_id FROM groups WHERE group_id=?", (group_id,))
    if not cur.fetchone():
        cur.execute("INSERT INTO groups (group_id) VALUES (?)", (group_id,))
    con.commit()
    con.close()

def reset_group(group_id):
    con = db()
    cur = con.cursor()
    cur.execute("DELETE FROM groups WHERE group_id=?", (group_id,))
    cur.execute("INSERT INTO groups (group_id) VALUES (?)", (group_id,))
    con.commit()
    con.close()

def set_group_active(group_id):
    con = db()
    cur = con.cursor()
    cur.execute("UPDATE groups SET active=1 WHERE group_id=?", (group_id,))
    con.commit()
    con.close()

def is_group_active(group_id):
    con = db()
    cur = con.cursor()
    cur.execute("SELECT active FROM groups WHERE group_id=?", (group_id,))
    row = cur.fetchone()
    con.close()
    return bool(row[0]) if row else False


def set_group_setting(group_id, key, value):
    """
    ثبت یا بروزرسانی یک تنظیم برای گروه
    """
    con = db()
    cur = con.cursor()
    cur.execute("""
        INSERT INTO group_settings (group_id, setting_key, setting_value)
        VALUES (?, ?, ?)
        ON CONFLICT(group_id, setting_key) DO UPDATE SET setting_value=excluded.setting_value
    """, (group_id, key, str(value)))
    con.commit()
    con.close()

def get_group_setting(group_id, key, default=None):
    """
    گرفتن یک تنظیم مشخص
    """
    con = db()
    cur = con.cursor()
    cur.execute("""
        SELECT setting_value FROM group_settings
        WHERE group_id=? AND setting_key=?
    """, (group_id, key))
    row = cur.fetchone()
    con.close()
    if row is None:
        return default
    return row[0]

def get_group_settings(group_id):
    """
    گرفتن همه تنظیمات گروه به صورت دیکشنری
    """
    con = db()
    cur = con.cursor()
    cur.execute("SELECT setting_key, setting_value FROM group_settings WHERE group_id=?", (group_id,))
    rows = cur.fetchall()
    con.close()
    return {k: v for k, v in rows}

def delete_group_setting(group_id, key):
    """
    حذف یک تنظیم مشخص از گروه
    """
    con = db()
    cur = con.cursor()
    cur.execute("DELETE FROM group_settings WHERE group_id=? AND setting_key=?", (group_id, key))
    con.commit()
    con.close()

def set_group_welcome(group_id, text):
    con = db()
    cur = con.cursor()
    cur.execute("UPDATE groups SET welcome_text=? WHERE group_id=?", (text, group_id,))
    con.commit()
    con.close()

def set_group_rules(group_id, text):
    con = db()
    cur = con.cursor()
    cur.execute("UPDATE groups SET rules=? WHERE group_id=?", (text, group_id,))
    con.commit()
    con.close()

def get_group_rules(group_id):
    con = db()
    cur = con.cursor()
    cur.execute("SELECT rules FROM groups WHERE group_id=?", (group_id,))
    rows = cur.fetchone()
    con.close()
    return rows[0]

def set_alias(group, user, alias):
    con = db()
    cur = con.cursor()
    cur.execute("SELECT alias FROM aliases WHERE group_id=? AND user_id=?", (group, user))
    if not cur.fetchone():
        cur.execute("INSERT INTO aliases (group_id, user_id, alias) VALUES (?, ?, ?)", (group, user, alias))
    else:
        cur.execute("UPDATE aliases SET alias=? WHERE group_id=? AND user_id=?", (alias, group, user))
    con.commit()
    con.close()


def get_alias(group, user):
    con = db()
    cur = con.cursor()
    cur.execute("SELECT alias FROM aliases WHERE group_id=? AND user_id=?", (group, user))
    rows = cur.fetchone()
    if rows:
        return rows[0]
    else:
        return "هیچ لقبی برای این کاربر در این گروه ثبت نشده :("

def is_admin(group_id, user_id):
    try:
        admins = bot.get_chat_administrators(group_id)
        return any(a.user.id == user_id for a in admins)
    except:
        return False


def get_tags(group_id):
    con = db()
    cur = con.cursor()
    cur.execute("SELECT keyword, response FROM tags WHERE group_id=?", (group_id,))
    rows = cur.fetchall()
    con.close()
    return {k:r for k,r in rows}

def add_tag(group_id, keyword, response):
    con = db()
    cur = con.cursor()
    cur.execute("INSERT INTO tags (group_id, keyword, response) VALUES (?, ?, ?)", (group_id, keyword, response))
    con.commit()
    con.close()

def del_tag(group_id, keyword):
    con = db()
    cur = con.cursor()
    cur.execute("DELETE FROM tags WHERE group_id=? AND keyword=?", (group_id, keyword))
    con.commit()
    con.close()



def file_report(group_id, user_id, target_id, msg_id):
    con = db()
    cur = con.cursor()
    cur.execute("INSERT INTO reports (group_id, user_id, target_id, msg_id) VALUES (?, ?, ?, ?)", (group_id, user_id, target_id, msg_id))
    con.commit()
    cur.execute("SELECT id FROM reports WHERE group_id=? AND target_id=? AND msg_id=?", (group_id, target_id, msg_id))
    rows = cur.fetchone()
    con.close()
    return rows[0]

def check_report(rep_id):
    con = db()
    cur = con.cursor()
    cur.execute("SELECT msg_id, group_id FROM reports WHERE id=?", (rep_id,))
    rows = cur.fetchone()
    msg_id = rows[0]
    group_id = rows[1]
    bot.edit_message_text("گزارش با موفقیت توسط ادمین بررسی شد!", group_id, msg_id)
    cur.execute("UPDATE reports SET status=? WHERE id=?", ("Checked", rep_id,))
    con.commit()
    con.close()


def add_punishment(group_id, user_id, p_type, until=None):
    con = db()
    cur = con.cursor()
    cur.execute("INSERT INTO punishments (group_id, user_id, type, until) VALUES (?, ?, ?, ?)",
                (group_id, user_id, p_type, until))
    con.commit()
    con.close()

def remove_punishment(group_id, user_id, p_type):
    con = db()
    cur = con.cursor()
    cur.execute("DELETE FROM punishments WHERE group_id=? AND user_id=? AND type=?", (group_id, user_id, p_type))
    con.commit()
    con.close()

def set_warn_maximum(group_id, max):
    con = db()
    cur = con.cursor()
    set_group_setting(group_id, "WARN_MAXIMUM", max)
    con.commit()
    con.close()

def set_warn_punishment(group_id, punishment):
    con = db()
    cur = con.cursor()
    set_group_setting(group_id, "WARN_PUNISHMENT", punishment)
    con.commit()
    con.close()

def get_user_warnings(group_id, user_id):
    con = db()
    cur = con.cursor()
    cur.execute("SELECT warnings FROM warnings WHERE group_id=? AND user_id=?", (group_id, user_id))
    row = cur.fetchone()
    return row[0] if row else 3


def warn_user(group_id, user_id):
    con = db()
    cur = con.cursor()
    cur.execute("SELECT * FROM warnings WHERE group_id=? AND user_id=?", (group_id, user_id))
    if cur.fetchone():
        cur.execute("UPDATE warnings SET warnings = warnings + 1 WHERE group_id=? AND user_id=?", (group_id, user_id))
    else:
        cur.execute("INSERT INTO warnings (group_id, user_id, warnings) VALUES (?, ?, 1)", (group_id, user_id))
    con.commit()
    con.close()

def remove_all_warns(group_id, user_id):
    con = db()
    cur = con.cursor()
    cur.execute("UPDATE warnings SET warnings = 0 WHERE group_id=? AND user_id=?", (group_id, user_id))
    con.commit()
    con.close()

def block_bot(group_id, bot_username):
    con = db()
    cur = con.cursor()
    cur.execute("INSERT INTO botBlocks (group_id, bot_username) VALUES (?, ?)", (group_id, bot_username))
    con.commit()
    con.close()

def unblock_bot(group_id, bot_username):
    con = db()
    cur = con.cursor()
    cur.execute("DELETE FROM botBlocks WHERE group_id=? AND bot_username=?", (group_id, bot_username))
    con.commit()
    con.close()

def get_botBlocks(group_id):
    con = db()
    cur = con.cursor()
    cur.execute("SELECT bot_username FROM botBlocks WHERE group_id=?", (group_id,))
    rows = cur.fetchall()
    con.close()
    return [row[0] for row in rows]

# ---------------- HANDLERS ----------------
@bot.message_handler(func=lambda m: m.text == "فعال شو")
def cmd_startgroup(message):
    ensure_group(message.chat.id)
    if not is_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, "اخه تو ادمینی؟")
        return
    set_group_active(message.chat.id)
    bot.reply_to(message, "✅ گروه فعال شد و بات آماده مدیریت است!")

@bot.message_handler(func=lambda m: m.text == "سیکتیر کن")
def leaver(message):
    if not is_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, "خفه شو تا سیکتو نزدم")
        return
    bot.reply_to(message, "ناراحت شدم، میرم سیکتیر کنم")
    bot.leave_chat(message.chat.id)


@bot.message_handler(func=lambda m: m.text == "راهنما")
def send_help(message):
    try:
        bot.send_message(message.from_user.id, HELP_TEXT, reply_markup=help_keyboard)
        if message.chat.type != "private":
            bot.reply_to(message, "📬 پنل راهنما به پیوی شما ارسال شد!")
    except:
        bot.reply_to(message, "⚠️ نمی‌تونم پیوی شما پیام بفرستم، لطفا دایرکت ربات رو باز کنید.")


@bot.message_handler(func=lambda m: m.text == "ریست")
def reset_bot_in_group(message):
    if not is_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, "خفه شو")
        return
    msg = bot.reply_to(message, "حله، الان کل رکورد گروه (بجز فیلتر ها) رو پاک و بازنویسی از صفر میکنم، انگار که هیچ اتفاقی نیوفتاده")
    reset_group(message.chat.id)
    bot.edit_message_text("خب، تموم شد، همه چی ریست شد", message.chat.id, msg.id)

@bot.message_handler(func=lambda m: m.text.startswith("تنظیم حداکثر دعوت"))
def change_maximum(message:types.Message):
    if not is_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, "حداقل حداکثرتو یکی میکنما!")
        return
    if message.text[len("تنظیم حداکثر دعوت"):].strip().isdigit():
        maximum = int(message.text[len("تنظیم حداکثر دعوت"):].strip())
        set_group_setting(message.chat.id, "invite_maximum", maximum)
        if bool(int(get_group_setting(message.chat.id, "creates_request", 0))):
            delete_group_setting(message.chat.id, "creates_request")
        bot.reply_to(message, f"حداکثر تعداد دعوت به {maximum} دعوت تغییر پیدا کرد")
    else:
        bot.reply_to(message, "کصخل اشتباه نوشتی")

@bot.message_handler(func=lambda m: m.text == "قفل فحش")
def active_swear_strict(message:types.Message):
    if not is_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, ":\\ گمشو از جلو چشام دور شو")
        return
    if int(get_group_setting(message.chat.id, "SWEAR_LOCK", 0)) in [-1, 1]:
        set_group_setting(message.chat.id, "SWEAR_LOCK", 1)
        bot.reply_to(message, "همینطوریشم فعال هست ستونم")
    else:
        set_group_setting(message.chat.id, "SWEAR_LOCK", 1)
        bot.reply_to(message, "قفل فعال شد")

@bot.message_handler(func=lambda m: m.text == "بازکردن فحش")
def active_swear_strict(message:types.Message):
    if not is_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, ":\\ گمشو از جلو چشام دور شو")
        return
    if int(get_group_setting(message.chat.id, "SWEAR_LOCK", 0)) in [-1, 0]:
        set_group_setting(message.chat.id, "SWEAR_LOCK", 0)
        bot.reply_to(message, "همینطوریشم غیرفعال هست ستونم")
    else:
        set_group_setting(message.chat.id, "SWEAR_LOCK", 0)
        bot.reply_to(message, "قفل غیرفعال شد")


@bot.message_handler(func=lambda m: m.text.startswith("دستورات عمومی"))
def public_commands(message:types.Message):
    if not is_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, "توکی باشی که اینارو برا من تنظیم کنی")
        return
    toggle = message.text.replace("دستورات عمومی", "").strip()
    if toggle == "روشن":
        if get_group_setting(message.chat.id, "PUBLIC_COMMANDS", 1) == 1:
            bot.reply_to(message, "همینطوریشم روشنه ستونم")
            return
        else:
            set_group_setting(message.chat.id, "PUBLIC_COMMANDS", 1)
            bot.reply_to(message, "دستورات عمومی روشن شد")
    elif toggle == "خاموش":
        if get_group_setting(message.chat.id, "PUBLIC_COMMANDS", 1) == 0:
            bot.reply_to(message, "همینطوریشم خاموشه ستونم")
            return
        else:
            set_group_setting(message.chat.id, "PUBLIC_COMMANDS", 0)
            bot.reply_to(message, "دستورات عمومی خاموش شد")

@bot.message_handler(func=lambda m: m.text.startswith("بلاک بات "))
def block_bot_handler(message:types.Message):
    if not is_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, "کصخلییییییییییی؟")
        return
    bot_username = message.text.replace("بلاک بات ", "").strip().replace("@", "")
    block_bot(message.chat.id, bot_username)
    bot.reply_to(message, f"بات {bot_username} بلاک شد")

@bot.message_handler(func=lambda m: m.text.startswith("آن‌بلاک بات "))
def unblock_bot_handler(message:types.Message):
    if not is_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, "اره حاجی راستی بهت گفتم کسایی که ادمین نیستن کیر منم نیستن؟")
        return
    bot_username = message.text.replace("آن‌بلاک بات ", "").strip().replace("@", "")
    unblock_bot(message.chat.id, bot_username)
    bot.reply_to(message, f"بات {bot_username} آن‌بلاک شد")

@bot.message_handler(func=lambda m: m.text == "بات های بلاک شده")
def blocked_bots(message: types.Message):
    if not is_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, "خفه شو بابا")
        return
    blocked_bots = get_botBlocks(message.chat.id)
    if not blocked_bots:
        bot.reply_to(message, "هیچ باتی بلاک نشده")
        return
    string = "بات های بلاک شده :\n"
    for bot_username in blocked_bots:
        string += f" - @{bot_username}\n"
    bot.reply_to(message, string)

@bot.message_handler(func=lambda m: m.text == "درخواست برای ورود")
def toggle_request(message:types.Message):
    if not is_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, "توکی باشی که اینارو برا من تنظیم کنی")
        return
    bot.set_message_reaction(message.chat.id, message.message_id, [types.ReactionTypeEmoji('👍')])
    toggle = bool(int(get_group_setting(message.chat.id, "creates_request", 0)))
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
    toggle = get_group_setting(message.chat.id, "PUBLIC_COMMANDS", 1)
    if not is_admin(message.chat.id, message.from_user.id) and int(toggle) == 0:
        return
    lnk = bot.create_chat_invite_link(
        chat_id=message.chat.id,
        name=f"Link by {message.from_user.first_name}",
        member_limit=int(get_group_setting(message.chat.id, "invite_maximum", 0)),
        creates_join_request=bool(int(get_group_setting(message.chat.id, "creates_request", 0)))
    )
    bot.reply_to(
        message,
        f"🔗 لینک دعوت مخصوص شما:\n{lnk.invite_link}\n📌 ساخته شده توسط کمک‌یـــار"
    )

@bot.message_handler(func=lambda m: m.text == "فیلترها")
def all_filters(message:types.Message):
    toggle = get_group_setting(message.chat.id, "PUBLIC_COMMANDS", 1)
    if not is_admin(message.chat.id, message.from_user.id) and int(toggle) == 0:
        return
    filters = get_tags(message.chat.id)
    string = "تمامی فیلترها :\n"
    for filter, response in filters.items():
        string += f"{filter} : {response}\n"
    bot.reply_to(message, string)


@bot.message_handler(func=lambda m: m.text.startswith("اکو "))
def echo_word(message:types.Message):
    toggle = get_group_setting(message.chat.id, "PUBLIC_COMMANDS", 1)
    if not is_admin(message.chat.id, message.from_user.id) and int(toggle) == 0:
        return
    echo = message.text[len("اکو"):].strip()
    if message.reply_to_message:
        bot.reply_to(message.reply_to_message, f"{message.from_user.first_name}: \n {echo}")
    else:
        bot.send_message(message.chat.id, f"{message.from_user.first_name}: \n {echo}")
    bot.delete_message(message.chat.id, message.message_id)


@bot.message_handler(func=lambda m: m.text == "قوانین")
def show_group_rules(message):
    bot.reply_to(message, f"قوانین گروه :\n {get_group_rules(message.chat.id)}")



@bot.message_handler(content_types=["new_chat_members"])
def greet(message):
    if not is_group_active(message.chat.id):
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

    con = db()
    cur = con.cursor()
    cur.execute("SELECT welcome_text FROM groups WHERE group_id=?", (message.chat.id,))
    row = cur.fetchone()
    con.close()

    template = row[0] if row else "خوش آمدید {name} به گروه {chat}! الان {members} نفر هستیم."

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


@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    try:
        data = call.data

        if data.startswith("request:"):
            toggle = data.split(":")[1]
            if toggle == "on":
                delete_group_setting(call.message.chat.id, "invite_maximum")
            set_group_setting(call.message.chat.id, "creates_request", "1" if toggle == "on" else "0")
            bot.answer_callback_query(call.id, "درخواست برای دعوت با موفقیت خاموش شد" if toggle == "off" else "درخواست برای دعوت با موفقیت روشن شد")
            bot.delete_message(call.message.chat.id, call.message.message_id)

        if data.startswith("swear:"):
            array = data.split(":")[1]
            bot.answer_callback_query(call.id, f"لیست فحش های :\n {array}")

        if data.startswith("check:"):
            rep_id = data.split(":")[1]
            check_report(rep_id)
            bot.answer_callback_query(call.id, "گزارش با موفقیت توسط شما بررسی شد")

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
                    "- ریپلای روی پیام + `تنظیم قوانین` : تغییر قوانین گروه\n"
                    "- `قوانین` : نمایش قوانین ثبت‌شده گروه\n"
                    "- `ریست` : بازنشانی تنظیمات گروه (غیر از فیلترها)\n"
                    "- `سقف اخطار + عدد` : تنظیم سقف اخطار ها به عدد موردنظر\n"
                    "- `بلاک بات @username` : بلاک کردن یک بات از گروه\n"
                    "- `آن‌بلاک بات @username` : آن‌بلاک کردن یک بات از گروه\n"
                    "- `بات های بلاک شده` : نمایش لیست بات‌های بلاک شده در گروه\n"
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
        con = db()
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

@bot.message_handler(func=lambda m: True)
def handle_messages(message:types.Message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    text = (message.text or "")
    file = open(SWEARS_PATH, "r")
    swears = []

    if message.via_bot:
        bot_username = message.via_bot.username
        blocked_bots = get_botBlocks(message.chat.id)
        if bot_username in blocked_bots:
            bot.delete_message(message.chat.id, message.message_id)
            return

    toggle = get_group_setting(message.chat.id, "PUBLIC_COMMANDS", 1)
    if not is_admin(message.chat.id, message.from_user.id) and int(toggle) == 0:
        return

    if int(get_group_setting(chat_id, "SWEAR_LOCK", 0)) == 1:
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

        if is_admin(chat_id, message.from_user.id):
            return
        bot.delete_message(chat_id, message.message_id)
        markup = types.InlineKeyboardMarkup()
        check_button = types.InlineKeyboardButton("نمایش کلمه", callback_data=f"swear:{repr(swears)}")
        markup.add(check_button)
        bot.send_message(chat_id, f"[{message.from_user.first_name}](tg://user?id={user_id}) عزیزم قرار شد دیگه فحش ندیم بیاید باهم دوست باشیم \n\n متن سانسور شده :\n >> {text}", parse_mode="Markdown", reply_markup=markup)

    if text.startswith("db:"):
        bot.reply_to(message, "گوه نخور بابا این گوزا به تو نیومده")

    if text == "کمک یار" or text == "کمک‌یار":
        bot.reply_to(message, f"{message.from_user.first_name}")

    if not is_group_active(chat_id):
        return

    tags = get_tags(chat_id)
    for k, r in tags.items():
        if text == k:
            bot.reply_to(message, r)
            break

    if text.startswith("سقف اخطار") and is_admin(chat_id, user_id):
        words = text.split(" ")
        words.remove("سقف")
        words.remove("اخطار")
        set_warn_maximum(chat_id, words[0])
        bot.reply_to(message, "سقف اخطارها با موفقیت تنظیم شد")

    if text.startswith("حذف فیلتر") and is_admin(chat_id, user_id):
        # اگر ریپلای شده روی پیام کلیدواژه
        if message.reply_to_message:
            keyword = message.reply_to_message.text.strip()
        else:
            # جدا کردن کلیدواژه از متن: حذف فیلتر <کلیدواژه>
            keyword = text[len("حذف فیلتر"):].strip()

        if keyword:
            del_tag(chat_id, keyword)
            bot.reply_to(message, f"❌ فیلتر '{keyword}' حذف شد")
        else:
            bot.reply_to(message, "⚠️ فرمت درست: حذف فیلتر روی ریپلای یا با نوشتن کلیدواژه")
        return

    if (message.text.startswith("حذف") and text != "حذف اخطارها") and is_admin(chat_id, user_id):
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
        if text.startswith("فیلتر") and is_admin(chat_id, user_id):
            keyword = message.reply_to_message.text.strip()
            response = text[len("فیلتر"):].strip()
            if keyword and response:
                add_tag(chat_id, keyword, response)
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
            id =file_report(chat_id, user_id, target_id, msg.message_id)
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

        if text.startswith("ثبت لقب") and (is_admin(chat_id, user_id) or target_id == user_id):
            alias = text[len("ثبت لقب"):].strip()
            set_alias(chat_id, target_id, alias)
            bot.reply_to(message, f"لقب {alias} با موفقیت برای این کاربر ثبت شد")

        if text == "لقب":
            alias = get_alias(chat_id, target_id).strip()
            bot.reply_to(message, f"لقب ثبت شده برای این کاربر :\n {alias}")

        if text == "تنظیم خوشامد" and is_admin(chat_id, user_id):
            set_group_welcome(chat_id, message.reply_to_message.text)
            bot.reply_to(message, "متن خوشامد گویی ربات با موفقیت تنظیم شد")

        if text == "تنظیم قوانین" and is_admin(chat_id, user_id):
            set_group_rules(chat_id, message.reply_to_message.text)
            bot.reply_to(message, "قوانین گروه با موفقیت تنظیم شد")

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
        if (text.startswith("خفه") or text.startswith("سکوت")) and is_admin(chat_id, user_id):
            if is_admin(chat_id, target_id):
                bot.reply_to(message, "من مثل بعضیا خیانتکار نیستم")
                return
            parts = text.split()
            if len(parts) >= 2 and parts[1].isdigit():
                mins = int(parts[1])
                if mins == "شو":
                    bot.restrict_chat_member(chat_id, target_id, can_send_messages=False)
                    add_punishment(chat_id, target_id, "mute", "0")
                    bot.reply_to(message, f"🔇 کاربر سکوت داده شد.")
                else:
                    bot.restrict_chat_member(chat_id, target_id,
                                         until_date=int(time.time()+mins*60),
                                         can_send_messages=False)
                    add_punishment(chat_id, target_id, "mute", int(time.time()+mins*60))
                    bot.reply_to(message, f"🔇 کاربر سکوت داده شد برای {mins} دقیقه.")

        elif (text.startswith("اخطار")) and is_admin(chat_id, user_id):
            if is_admin(chat_id, target_id):
                bot.reply_to(message, "اخه کصمغز چرا باید ادمینو اخطار بدم")
                return
            warn_user(chat_id, target_id)
            warns = get_user_warnings(chat_id, target_id)
            warn_max = get_group_setting(chat_id, "WARN_MAXIMUM", 3)
            bot.reply_to(message, f"کاربر با موفقیت اخطار داده شد! ⚠️\n اخطار های کاربر : {warns}/{warn_max}")
            if warns >= warn_max:
                punish = get_group_setting(chat_id, "WARN_PUNISHMENT", "kick")
                if punish == "kick":
                    bot.ban_chat_member(chat_id, target_id)
                    bot.unban_chat_member(chat_id, target_id)
                    add_punishment(chat_id, target_id, "kick")
                    bot.reply_to(message, "👢 کاربر کیک شد!")
                elif punish == "ban":
                    bot.ban_chat_member(chat_id, target_id)
                    add_punishment(chat_id, target_id, "ban")
                    bot.reply_to(message, "⛔ کاربر بن شد!")
                elif punish == "mute":
                    bot.restrict_chat_member(chat_id, target_id, can_send_messages=False)
                    bot.reply_to("کاربر میوت شد! 🤐")
                remove_all_warns(chat_id, target_id)

        elif (text == "حذف اخطارها") and is_admin(chat_id, user_id):
            if is_admin(chat_id, target_id):
                bot.reply_to("چیزی میزنی؟ اصلا مگه میتونم اخطار بدم که الان میگی حذف اخطار")
                return
            remove_all_warns(chat_id, target_id)
            bot.reply_to(message, "شتر دیدی ندیدی! ✅")



        # KICK
        elif (text == "ریم" or text == "کیک" or text == "سیک") and is_admin(chat_id, user_id):
            if is_admin(chat_id, target_id):
                bot.reply_to(message, "باشه داداش دوبار الان برات ادمینو کیک میکنم")
                return
            bot.ban_chat_member(chat_id, target_id)
            bot.unban_chat_member(chat_id, target_id)
            add_punishment(chat_id, target_id, "kick")
            bot.reply_to(message, "👢 کاربر کیک شد!")

        # BAN
        elif (text == "بن" or text =="سیکتیر") and is_admin(chat_id, user_id):
            if is_admin(chat_id, target_id):
                bot.reply_to(message, "پاول دوروفم نمیتونه ادمین بن کنه تو دیگه چه انتظاری داری")
                return
            bot.ban_chat_member(chat_id, target_id)
            add_punishment(chat_id, target_id, "ban")
            bot.reply_to(message, "⛔ کاربر بن شد!")

        elif (text == "مخفی کاری" or text == "بن+" or text.startswith("سیک مخفی")) and is_admin(chat_id, user_id):
            if is_admin(chat_id, target_id):
                bot.reply_to(message, "سیشتیر بابا همتون همینو میگید")
                return
            bot.delete_message(chat_id, message.message_id)
            bot.ban_chat_member(chat_id, target_id)

        # UNBAN
        elif (text == "آن‌بن" or text == "آن بن" or text == "ان بن") and is_admin(chat_id, user_id):
            bot.unban_chat_member(chat_id, target_id)
            remove_punishment(chat_id, target_id, "ban")
            bot.reply_to(message, "✅ کاربر آن‌بن شد!")

        # UNMUTE
        elif (text == "آن‌میوت" or text == "آن میوت" or text == "ان میوت") and is_admin(chat_id, user_id):
            bot.restrict_chat_member(chat_id, target_id,
                                     can_send_messages=True)
            remove_punishment(chat_id, target_id, "mute")
            bot.reply_to(message, "✅ کاربر آن‌میوت شد!")


    if text == "@admins":
        admins = bot.get_chat_administrators(chat_id)
        mentions = [f"[{a.user.first_name}](tg://user?id={a.user.id})" for a in admins]
        bot.send_message(chat_id, " ".join(mentions), parse_mode="Markdown")


# ---------------- RUN ----------------
print(f"{me.username} Group Helper running...")
bot.polling(none_stop=True, skip_pending=True)

