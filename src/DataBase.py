import aiosqlite
from utils import DB_PATH


class DataBase():

    def __init__(self, bot):
        self.bot = bot

    def _db(self) -> aiosqlite.Connection:
        return aiosqlite.connect(DB_PATH)

    async def init_db(self):
        async with self._db() as con:
            
            # جدول گروه‌ها
            await con.execute("""
            CREATE TABLE IF NOT EXISTS groups (
                group_id INTEGER PRIMARY KEY,
                welcome_text TEXT DEFAULT '{name} عزیز خوش امدید',
                comment_text TEXT DEFAULT 'ریاکشن یادت نره. ❤️😁',
                rules TEXT DEFAULT NULL,
                active INTEGER DEFAULT 0
            )
            """)
            # جدول تگ‌ها
            await con.execute("""
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER,
                keyword TEXT,
                response TEXT
            )
            """)
            # جدول مجازات‌ها
            await con.execute("""
            CREATE TABLE IF NOT EXISTS punishments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER,
                user_id INTEGER,
                type TEXT,
                until INTEGER
            )
            """)
            await con.execute("""
            CREATE TABLE IF NOT EXISTS group_settings (
                group_id INTEGER,
                setting_key TEXT,
                setting_value TEXT,
                PRIMARY KEY (group_id, setting_key)
            )
            """)
            await con.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER,
                user_id INTEGER,
                target_id INTEGER,
                msg_id INTEGER,
                status TEXT DEFAULT 'Pending...'
            )
            """)
            await con.execute("""
            CREATE TABLE IF NOT EXISTS aliases (
                group_id INTEGER,
                user_id INTEGER,
                alias TEXT
            )
            """)
            await con.execute("""
            CREATE TABLE IF NOT EXISTS ASLs (
                group_id INTEGER,
                user_id INTEGER,
                asl TEXT
            )
            """)
            await con.execute("""
            CREATE TABLE IF NOT EXISTS warnings (
                group_id INTEGER,
                user_id INTEGER,
                warnings INTEGER
            )
            """)
            await con.execute("""
            CREATE TABLE IF NOT EXISTS botBlocks (
                    group_id INTEGER,
                    bot_username TEXT
                )
            """)
            await con.execute("""
            CREATE TABLE IF NOT EXISTS blocked_words (
                    group_id INTEGER,
                    word TEXT
                )
            """)
            await con.execute("""
            CREATE TABLE IF NOT EXISTS blocked_groups (
                    group_id INTEGER PRIMARY KEY
                )
            """)
            await con.execute("""
            CREATE TABLE IF NOT EXISTS whispers (
                    token TEXT PRIMARY KEY,
                    sender_id INTEGER,
                    receiver_id INTEGER,
                    receiver_username TEXT,
                    whisper TEXT,
                    timestamp INTEGER)
                """)
            await con.execute("""
            CREATE TABLE IF NOT EXISTS locked_posts (
                    group_id INTEGER,
                    post_id INTEGER
                )
            """)
            await con.execute("""CREATE TABLE IF NOT EXISTS bridge_channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_channel_id INTEGER NOT NULL,
                bale_channel_id TEXT NOT NULL,
                enabled INTEGER DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now')),
                UNIQUE(telegram_channel_id));
            """)


            await con.commit()
            



    async def ensure_group(self,group_id):
        async with self._db() as con:
            
            cur = await con.execute("SELECT group_id FROM groups WHERE group_id=?", (group_id,))
            if not await cur.fetchone():
                await con.execute("INSERT INTO groups (group_id) VALUES (?)", (group_id,))
            await con.commit()
            

    async def reset_group(self, group_id):
        async with self._db() as con:
            
            await con.execute("DELETE FROM groups WHERE group_id=?", (group_id,))
            await con.execute("INSERT INTO groups (group_id) VALUES (?)", (group_id,))
            await con.commit()
            

    async def set_group_active(self, group_id):
        async with self._db() as con:
            
            await con.execute("UPDATE groups SET active=1 WHERE group_id=?", (group_id,))
            await con.commit()
            

    async def is_group_active(self, group_id):
        async with self._db() as con:
            
            cur = await con.execute("SELECT active FROM groups WHERE group_id=?", (group_id,))
            row = await cur.fetchone()
            
            return bool(row[0]) if row else False


    async def set_group_setting(self, group_id, key, value):
        """
        ثبت یا بروزرسانی یک تنظیم برای گروه
        """
        async with self._db() as con:
            
            await con.execute("""
            INSERT INTO group_settings (group_id, setting_key, setting_value)
            VALUES (?, ?, ?)
            ON CONFLICT(group_id, setting_key) DO UPDATE SET setting_value=excluded.setting_value
            """, (group_id, key, str(value)))
            await con.commit()
            

    async def get_group_setting(self, group_id, key, default=None):
        """
        گرفتن یک تنظیم مشخص
        """
        async with self._db() as con:
            
            cur = await con.execute("""
            SELECT setting_value FROM group_settings
            WHERE group_id=? AND setting_key=?
            """, (group_id, key))
            row = await cur.fetchone()
            
            if row is None:
                return default
            return row[0]

    async def get_group_settings(self, group_id):
        """
        گرفتن همه تنظیمات گروه به صورت دیکشنری
        """
        async with self._db() as con:
            
            cur = await con.execute("SELECT setting_key, setting_value FROM group_settings WHERE group_id=?", (group_id,))
            rows = await cur.fetchall()
            
            return {k: v for k, v in rows}

    async def delete_group_setting(self, group_id, key):
        """
        حذف یک تنظیم مشخص از گروه
        """
        async with self._db() as con:
            
            await con.execute("DELETE FROM group_settings WHERE group_id=? AND setting_key=?", (group_id, key))
            await con.commit()
            

    async def set_group_welcome(self, group_id, text):
        async with self._db() as con:
            
            await con.execute("UPDATE groups SET welcome_text=? WHERE group_id=?", (text, group_id,))
            await con.commit()
            

    async def set_group_rules(self, group_id, text):
        async with self._db() as con:
            
            await con.execute("UPDATE groups SET rules=? WHERE group_id=?", (text, group_id,))
            await con.commit()
            

    async def get_group_rules(self, group_id):
        async with self._db() as con:
            
            cur = await con.execute("SELECT rules FROM groups WHERE group_id=?", (group_id,))
            rows = await cur.fetchone()
            
            return rows[0]

    async def set_alias(self, group, user, alias):
        async with self._db() as con:
            
            cur = await con.execute("SELECT alias FROM aliases WHERE group_id=? AND user_id=?", (group, user))
            if not await cur.fetchone():
                await con.execute("INSERT INTO aliases (group_id, user_id, alias) VALUES (?, ?, ?)", (group, user, alias))
            else:
                await con.execute("UPDATE aliases SET alias=? WHERE group_id=? AND user_id=?", (alias, group, user))
            await con.commit()
            


    async def get_alias(self, group, user):
        async with self._db() as con:
            
            cur = await con.execute("SELECT alias FROM aliases WHERE group_id=? AND user_id=?", (group, user))
            rows = await cur.fetchone()
            if rows:
                return rows[0]
            else:
                return "هیچ لقبی برای این کاربر در این گروه ثبت نشده :("
        
    async def set_asl(self, group_id, user_id, asl):
        async with self._db() as con:
            
            curr_asl = await self.get_asl(group_id, user_id)
            if curr_asl == "هیچ اصلی برای این کاربر در این گروه ثبت نشده :(":
                await con.execute("INSERT INTO ASLs (group_id, user_id, asl) VALUES (?, ?, ?)", (group_id, user_id, asl))
            else:
                await con.execute("UPDATE ASLs SET asl=? WHERE group_id=? AND user_id=?", (asl, group_id, user_id))
            await con.commit()
            

    async def get_asl(self, group_id, user_id):
        async with self._db() as con:
            
            cur = await con.execute("SELECT asl FROM ASLs WHERE group_id=? AND user_id=?", (group_id, user_id))
            rows = await cur.fetchone()
            if rows:
                return rows[0]
            else:
                return "هیچ اصلی برای این کاربر در این گروه ثبت نشده :("

    async def is_admin(self, group_id, user_id, sender_chat_id=None):
        """
        بررسی ادمین بودن کاربر.
        اگر پیام توسط یک ادمین ناشناس (anonymous) ارسال شده باشد، sender_chat_id
        ارسال می‌شود تا هویت واقعی (چنل/گروه) به‌عنوان ادمین بررسی شود.
        """
        try:
            admins = await self.bot.get_chat_administrators(group_id)
            if user_id and any(a.user.id == user_id for a in admins):
                return True
            if sender_chat_id and any(a.user.id == sender_chat_id for a in admins):
                return True
        except:
            pass
        if sender_chat_id:
            # Anonymous admin posting as the group itself
            if sender_chat_id == group_id:
                return True
            try:
                member = await self.bot.get_chat_member(group_id, sender_chat_id)
                if member.status in ["administrator", "creator"]:
                    return True
            except:
                pass
            # Anonymous posts from the group's linked channel are always admin
            try:
                chat = await self.bot.get_chat(group_id)
                if sender_chat_id == getattr(chat, 'linked_chat_id', None):
                    return True
            except:
                pass
        return False


    async def get_tags(self, group_id):
        async with self._db() as con:
            
            cur = await con.execute("SELECT keyword, response FROM tags WHERE group_id=?", (group_id,))
            rows = await cur.fetchall()
            
            return {k:r for k,r in rows}

    async def add_tag(self, group_id, keyword, response):
        async with self._db() as con:
            
            await con.execute("INSERT INTO tags (group_id, keyword, response) VALUES (?, ?, ?)", (group_id, keyword, response))
            await con.commit()
            

    async def del_tag(self, group_id, keyword):
        async with self._db() as con:
            
            await con.execute("DELETE FROM tags WHERE group_id=? AND keyword=?", (group_id, keyword))
            await con.commit()
            

    async def member_template(self, group_id):
        async with self._db() as con:
            
            cur = await con.execute("SELECT welcome_text FROM groups WHERE group_id=?", (group_id,))
            row = await cur.fetchone()
            return row[0] if row else "خوش آمدید {name} به گروه {chat}! الان {members} نفر هستیم."
    

    async def file_report(self, group_id, user_id, target_id, msg_id):
        async with self._db() as con:
            
            await con.execute("INSERT INTO reports (group_id, user_id, target_id, msg_id) VALUES (?, ?, ?, ?)", (group_id, user_id, target_id, msg_id))
            await con.commit()
            cur = await con.execute("SELECT id FROM reports WHERE group_id=? AND target_id=? AND msg_id=?", (group_id, target_id, msg_id))
            rows = await cur.fetchone()
            
            return rows[0]

    async def check_report(self, rep_id):
        async with self._db() as con:
            
            cur = await con.execute("SELECT msg_id, group_id FROM reports WHERE id=?", (rep_id,))
            rows = await cur.fetchone()
            msg_id = rows[0]
            group_id = rows[1]
            await self.bot.edit_message_text("گزارش با موفقیت توسط ادمین بررسی شد!", group_id, msg_id)
            await con.execute("UPDATE reports SET status=? WHERE id=?", ("Checked", rep_id,))
            await con.commit()
            


    async def add_punishment(self, group_id, user_id, p_type, until=None):
        async with self._db() as con:
            
            await con.execute("INSERT INTO punishments (group_id, user_id, type, until) VALUES (?, ?, ?, ?)",
                        (group_id, user_id, p_type, until))
            await con.commit()
            

    async def remove_punishment(self, group_id, user_id, p_type):
        async with self._db() as con:
            await con.execute("DELETE FROM punishments WHERE group_id=? AND user_id=? AND type=?", (group_id, user_id, p_type))
            await con.commit()
            

    async def set_warn_maximum(self, group_id, max):
        async with self._db() as con:
            
            await self.set_group_setting(group_id, "WARN_MAXIMUM", max)
            await con.commit()
            

    async def set_warn_punishment(self, group_id, punishment):
        async with self._db() as con:
            
            await self.set_group_setting(group_id, "WARN_PUNISHMENT", punishment)
            await con.commit()
            

    async def get_user_warnings(self, group_id, user_id):
        async with self._db() as con:
            
            cur = await con.execute("SELECT warnings FROM warnings WHERE group_id=? AND user_id=?", (group_id, user_id))
            row = await cur.fetchone()
            return row[0] if row else 3
        
    async def get_comment_message(self, group_id):
        async with self._db() as con:
            
            cur = await con.execute("SELECT comment_text FROM groups WHERE group_id=?", (group_id,))
            row = await cur.fetchone()
            return row[0] if row else "Err fetching comment msg"
        
    async def set_comment_message(self, group_id, message):
        async with self._db() as con:
            
            await con.execute("UPDATE groups SET comment_text = ? WHERE group_id=?", (message, group_id))
            await con.commit()


    async def warn_user(self, group_id, user_id):
        async with self._db() as con:
            
            cur = await con.execute("SELECT * FROM warnings WHERE group_id=? AND user_id=?", (group_id, user_id))
            if await cur.fetchone():
                await con.execute("UPDATE warnings SET warnings = warnings + 1 WHERE group_id=? AND user_id=?", (group_id, user_id))
            else:
                await con.execute("INSERT INTO warnings (group_id, user_id, warnings) VALUES (?, ?, 1)", (group_id, user_id))
            await con.commit()
            

    async def remove_all_warns(self, group_id, user_id):
        async with self._db() as con:
            
            await con.execute("UPDATE warnings SET warnings = 0 WHERE group_id=? AND user_id=?", (group_id, user_id))
            await con.commit()
            

    async def block_bot(self, group_id, bot_username):
        async with self._db() as con:
            
            await con.execute("INSERT INTO botBlocks (group_id, bot_username) VALUES (?, ?)", (group_id, bot_username))
            await con.commit()
            

    async def unblock_bot(self, group_id, bot_username):
        async with self._db() as con:
              
            await con.execute("DELETE FROM botBlocks WHERE group_id=? AND bot_username=?", (group_id, bot_username))
            await con.commit()
            

    async def get_botBlocks(self, group_id):
        async with self._db() as con:
            
            cur = await con.execute("SELECT bot_username FROM botBlocks WHERE group_id=?", (group_id,))
            rows = await cur.fetchall()
            
            return [row[0] for row in rows]

    async def block_word(self, group_id, word):
        async with self._db() as con:
            
            await con.execute("INSERT INTO blocked_words (group_id, word) VALUES (?, ?)", (group_id, word))
            await con.commit()
            

    async def unblock_word(self, group_id, word):
        async with self._db() as con:
            
            await con.execute("DELETE FROM blocked_words WHERE group_id=? AND word=?", (group_id, word))
            await con.commit()

    async def ban_group(self, group_id):
        async with self._db() as con:
            
            await con.execute("INSERT INTO blocked_groups (group_id) VALUES (?)", (group_id,))
            await con.commit()
    
    async def unban_group(self, group_id):
        async with self._db() as con:
            
            await con.execute("DELETE FROM blocked_groups WHERE group_id=?", (group_id,))
            await con.commit()

    async def is_group_blocked(self, group_id):
        async with self._db() as con:
            
            cur = await con.execute("SELECT group_id FROM blocked_groups WHERE group_id=?", (group_id,))
            row = await cur.fetchone()
            return True if row != None else False
            

    async def blocked_words(self, group_id):
        async with self._db() as con:
            
            cur = await con.execute("SELECT word FROM blocked_words WHERE group_id=?", (group_id,))
            rows = await cur.fetchall()
            
            return [row[0] for row in rows]
        
    async def store_whisper(self, token, sender_id, receiver_id, receiver_username, whisper, timestamp):
        async with self._db() as con:
            
            await con.execute("INSERT INTO whispers (token, sender_id, receiver_id, receiver_username, whisper, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                        (token, sender_id, receiver_id, receiver_username, whisper, timestamp))
            await con.commit()

    async def get_whisper(self, token):
        async with self._db() as con:
            
            cur = await con.execute("SELECT sender_id, receiver_id, receiver_username, whisper, timestamp FROM whispers WHERE token=?", (token,))
            row = await cur.fetchone()
            if row:
                return {
                    "sender_id": row[0],
                    "receiver_id": row[1],
                    "receiver_username": row[2],
                    "whisper": row[3],
                    "timestamp": row[4]
                }
            else:
                return None
            
    async def post_lock_status(self, group_id: int, post_id: int) -> bool:
        async with self._db() as con:
            
            cur = await con.execute("SELECT * FROM locked_posts WHERE group_id=? AND post_id=?", (group_id, post_id))
            row = await cur.fetchone()
            return True if row else False

    async def lock_post(self, group_id: int, post_id: int):
        async with self._db() as con:
            
            if not await self.post_lock_status(group_id, post_id):
                await con.execute("INSERT INTO locked_posts (group_id, post_id) VALUES (?, ?)", (group_id, post_id))
                await con.commit()
            
    async def unlock_post(self, group_id: int, post_id: int):
        async with self._db() as con:            
            if await self.post_lock_status(group_id, post_id):
                await con.execute("DELETE FROM locked_posts WHERE group_id=? AND post_id=?", (group_id, post_id))
                await con.commit()

    async def set_bridge(self, telegram_channel_id: int, bale_channel_id: str):
        """تنظیم یا بروزرسانی بریج"""
        async with self._db() as con:
            await con.execute("""
                INSERT INTO bridge_channels 
                (telegram_channel_id, bale_channel_id, enabled)
                VALUES (?, ?, 1)
                ON CONFLICT(telegram_channel_id) 
                DO UPDATE SET bale_channel_id = ?, enabled = 1
            """, (telegram_channel_id, bale_channel_id, bale_channel_id))
            await con.commit()


    async def get_bale_bridge_channel(self, telegram_channel_id: int):
        """دریافت آیدی کانال بله برای یک کانال تلگرام"""
        async with self._db() as con:
            cur = await con.execute("SELECT bale_channel_id FROM bridge_channels WHERE telegram_channel_id = ? AND enabled = 1", (telegram_channel_id,))
            row = await cur.fetchone()
        return row[0] if row else None
    
    async def get_telegram_bridge_channel(self, bale_channel_id: str):
        """دریافت آیدی کانال تلگرام برای یک کانال بله"""
        async with self._db() as con:
            cur = await con.execute("SELECT telegram_channel_id FROM bridge_channels WHERE bale_channel_id = ? AND enabled = 1", (bale_channel_id,))
            row = await cur.fetchone()
        return row[0] if row else None


    async def remove_bridge(self, telegram_channel_id: int):
        """غیرفعال کردن بریج"""
        async with self._db() as con:
            await con.execute("UPDATE bridge_channels SET enabled = 0 WHERE telegram_channel_id = ?", (telegram_channel_id,))
            await con.commit()


    async def get_all_active_bridges(self):
        """دریافت همه بریج‌های فعال"""
        async with self._db() as con:
            rows = await con.execute("SELECT telegram_channel_id, bale_channel_id FROM bridge_channels WHERE enabled = 1").fetchall()
        return dict(rows)

    async def update_message(self, updates:list, version:str):
        message = f"*نسخه جدید ربات کمک‌یار (***{version}***) منتشر شد!*\n\n"
        for update in updates:
            message += f"{update}\n"
        async with self._db() as con:
            
            cur = await con.execute("SELECT group_id FROM groups WHERE active=1")
            rows = await cur.fetchall()
            
        success = 0
        err = 0
        for row in rows:
            try:
                await self.bot.send_message(row[0], message, parse_mode="Markdown")
                success += 1                
            except:
                err += 1
                continue
        return success, err
