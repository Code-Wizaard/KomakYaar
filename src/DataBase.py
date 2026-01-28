import sqlite3
from main import bot
from vars import DB_PATH


class DataBase():

    def __init__(self):
        self.init_db()

    def _db(self) -> sqlite3.Connection:
        return sqlite3.connect(DB_PATH)

    def init_db(self):
        with self._db() as con:
            cur = con.cursor()
            # جدول گروه‌ها
            cur.execute("""
            CREATE TABLE IF NOT EXISTS groups (
                group_id INTEGER PRIMARY KEY,
                welcome_text TEXT DEFAULT '{name} عزیز خوش امدید',
                comment_text TEXT DEFAULT 'ریاکشن یادت نره. ❤️😁',
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
            CREATE TABLE IF NOT EXISTS ASLs (
                group_id INTEGER,
                user_id INTEGER,
                asl TEXT
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
            cur.execute("""
            CREATE TABLE IF NOT EXISTS blocked_words (
                    group_id INTEGER,
                    word TEXT
                )
            """)
            cur.execute("""
            CREATE TABLE IF NOT EXISTS blocked_groups (
                    group_id INTEGER PRIMARY KEY
                )
            """)


            con.commit()
            



    def ensure_group(self,group_id):
        with self._db() as con:
            cur = con.cursor()
            cur.execute("SELECT group_id FROM groups WHERE group_id=?", (group_id,))
            if not cur.fetchone():
                cur.execute("INSERT INTO groups (group_id) VALUES (?)", (group_id,))
            con.commit()
            

    def reset_group(self, group_id):
        with self._db() as con:
            cur = con.cursor()
            cur.execute("DELETE FROM groups WHERE group_id=?", (group_id,))
            cur.execute("INSERT INTO groups (group_id) VALUES (?)", (group_id,))
            con.commit()
            

    def set_group_active(self, group_id):
        with self._db() as con:
            cur = con.cursor()
            cur.execute("UPDATE groups SET active=1 WHERE group_id=?", (group_id,))
            con.commit()
            

    def is_group_active(self, group_id):
        with self._db() as con:
            cur = con.cursor()
            cur.execute("SELECT active FROM groups WHERE group_id=?", (group_id,))
            row = cur.fetchone()
            
            return bool(row[0]) if row else False


    def set_group_setting(self, group_id, key, value):
        """
        ثبت یا بروزرسانی یک تنظیم برای گروه
        """
        with self._db() as con:
            cur = con.cursor()
            cur.execute("""
            INSERT INTO group_settings (group_id, setting_key, setting_value)
            VALUES (?, ?, ?)
            ON CONFLICT(group_id, setting_key) DO UPDATE SET setting_value=excluded.setting_value
            """, (group_id, key, str(value)))
            con.commit()
            

    def get_group_setting(self, group_id, key, default=None):
        """
        گرفتن یک تنظیم مشخص
        """
        with self._db() as con:
            cur = con.cursor()
            cur.execute("""
            SELECT setting_value FROM group_settings
            WHERE group_id=? AND setting_key=?
            """, (group_id, key))
            row = cur.fetchone()
            
            if row is None:
                return default
            return row[0]

    def get_group_settings(self, group_id):
        """
        گرفتن همه تنظیمات گروه به صورت دیکشنری
        """
        with self._db() as con:
            cur = con.cursor()
            cur.execute("SELECT setting_key, setting_value FROM group_settings WHERE group_id=?", (group_id,))
            rows = cur.fetchall()
            
            return {k: v for k, v in rows}

    def delete_group_setting(self, group_id, key):
        """
        حذف یک تنظیم مشخص از گروه
        """
        with self._db() as con:
            cur = con.cursor()
            cur.execute("DELETE FROM group_settings WHERE group_id=? AND setting_key=?", (group_id, key))
            con.commit()
            

    def set_group_welcome(self, group_id, text):
        with self._db() as con:
            cur = con.cursor()
            cur.execute("UPDATE groups SET welcome_text=? WHERE group_id=?", (text, group_id,))
            con.commit()
            

    def set_group_rules(self, group_id, text):
        with self._db() as con:
            cur = con.cursor()
            cur.execute("UPDATE groups SET rules=? WHERE group_id=?", (text, group_id,))
            con.commit()
            

    def get_group_rules(self, group_id):
        with self._db() as con:
            cur = con.cursor()
            cur.execute("SELECT rules FROM groups WHERE group_id=?", (group_id,))
            rows = cur.fetchone()
            
            return rows[0]

    def set_alias(self, group, user, alias):
        with self._db() as con:
            cur = con.cursor()
            cur.execute("SELECT alias FROM aliases WHERE group_id=? AND user_id=?", (group, user))
            if not cur.fetchone():
                cur.execute("INSERT INTO aliases (group_id, user_id, alias) VALUES (?, ?, ?)", (group, user, alias))
            else:
                cur.execute("UPDATE aliases SET alias=? WHERE group_id=? AND user_id=?", (alias, group, user))
            con.commit()
            


    def get_alias(self, group, user):
        with self._db() as con:
            cur = con.cursor()
            cur.execute("SELECT alias FROM aliases WHERE group_id=? AND user_id=?", (group, user))
            rows = cur.fetchone()
            if rows:
                return rows[0]
            else:
                return "هیچ لقبی برای این کاربر در این گروه ثبت نشده :("
        
    def set_asl(self, group_id, user_id, asl):
        with self._db() as con:
            cur = con.cursor()
            curr_asl = self.get_asl(group_id, user_id)
            if curr_asl == "هیچ اصلی برای این کاربر در این گروه ثبت نشده :(":
                cur.execute("INSERT INTO ASLs (group_id, user_id, asl) VALUES (?, ?, ?)", (group_id, user_id, asl))
            else:
                cur.execute("UPDATE ASLs SET asl=? WHERE group_id=? AND user_id=?", (asl, group_id, user_id))
            con.commit()
            

    def get_asl(self, group_id, user_id):
        with self._db() as con:
            cur = con.cursor()
            cur.execute("SELECT asl FROM ASLs WHERE group_id=? AND user_id=?", (group_id, user_id))
            rows = cur.fetchone()
            if rows:
                return rows[0]
            else:
                return "هیچ اصلی برای این کاربر در این گروه ثبت نشده :("

    def is_admin(self, group_id, user_id):
        try:
            admins = bot.get_chat_administrators(group_id)
            return any(a.user.id == user_id for a in admins)
        except:
            return False


    def get_tags(self, group_id):
        with self._db() as con:
            cur = con.cursor()
            cur.execute("SELECT keyword, response FROM tags WHERE group_id=?", (group_id,))
            rows = cur.fetchall()
            
            return {k:r for k,r in rows}

    def add_tag(self, group_id, keyword, response):
        with self._db() as con:
            cur = con.cursor()
            cur.execute("INSERT INTO tags (group_id, keyword, response) VALUES (?, ?, ?)", (group_id, keyword, response))
            con.commit()
            

    def del_tag(self, group_id, keyword):
        with self._db() as con:
            cur = con.cursor()
            cur.execute("DELETE FROM tags WHERE group_id=? AND keyword=?", (group_id, keyword))
            con.commit()
            

    def member_template(self, group_id):
        with self._db() as con:
            cur = con.cursor()
            cur.execute("SELECT welcome_text FROM groups WHERE group_id=?", (group_id,))
            row = cur.fetchone()
            return row[0] if row else "خوش آمدید {name} به گروه {chat}! الان {members} نفر هستیم."
    

    def file_report(self, group_id, user_id, target_id, msg_id):
        with self._db() as con:
            cur = con.cursor()
            cur.execute("INSERT INTO reports (group_id, user_id, target_id, msg_id) VALUES (?, ?, ?, ?)", (group_id, user_id, target_id, msg_id))
            con.commit()
            cur.execute("SELECT id FROM reports WHERE group_id=? AND target_id=? AND msg_id=?", (group_id, target_id, msg_id))
            rows = cur.fetchone()
            
            return rows[0]

    def check_report(self, rep_id):
        with self._db() as con:
            cur = con.cursor()
            cur.execute("SELECT msg_id, group_id FROM reports WHERE id=?", (rep_id,))
            rows = cur.fetchone()
            msg_id = rows[0]
            group_id = rows[1]
            bot.edit_message_text("گزارش با موفقیت توسط ادمین بررسی شد!", group_id, msg_id)
            cur.execute("UPDATE reports SET status=? WHERE id=?", ("Checked", rep_id,))
            con.commit()
            


    def add_punishment(self, group_id, user_id, p_type, until=None):
        with self._db() as con:
            cur = con.cursor()
            cur.execute("INSERT INTO punishments (group_id, user_id, type, until) VALUES (?, ?, ?, ?)",
                        (group_id, user_id, p_type, until))
            con.commit()
            

    def remove_punishment(self, group_id, user_id, p_type):
        with self._db() as con:
            cur = con.cursor()
            cur.execute("DELETE FROM punishments WHERE group_id=? AND user_id=? AND type=?", (group_id, user_id, p_type))
            con.commit()
            

    def set_warn_maximum(self, group_id, max):
        with self._db() as con:
            cur = con.cursor()
            self.set_group_setting(group_id, "WARN_MAXIMUM", max)
            con.commit()
            

    def set_warn_punishment(self, group_id, punishment):
        with self._db() as con:
            cur = con.cursor()
            self.set_group_setting(group_id, "WARN_PUNISHMENT", punishment)
            con.commit()
            

    def get_user_warnings(self, group_id, user_id):
        with self._db() as con:
            cur = con.cursor()
            cur.execute("SELECT warnings FROM warnings WHERE group_id=? AND user_id=?", (group_id, user_id))
            row = cur.fetchone()
            return row[0] if row else 3
        
    def get_comment_message(self, group_id):
        with self._db() as con:
            cur = con.cursor()
            cur.execute("SELECT comment_text FROM groups WHERE group_id=?", (group_id,))
            row = cur.fetchone()
            return row[0] if row else "Err fetching comment msg"
        
    def set_comment_message(self, group_id, message):
        with self._db() as con:
            cur = con.cursor()
            cur.execute("UPDATE groups SET comment_text = ? WHERE group_id=?", (message, group_id))
            con.commit()


    def warn_user(self, group_id, user_id):
        with self._db() as con:
            cur = con.cursor()
            cur.execute("SELECT * FROM warnings WHERE group_id=? AND user_id=?", (group_id, user_id))
            if cur.fetchone():
                cur.execute("UPDATE warnings SET warnings = warnings + 1 WHERE group_id=? AND user_id=?", (group_id, user_id))
            else:
                cur.execute("INSERT INTO warnings (group_id, user_id, warnings) VALUES (?, ?, 1)", (group_id, user_id))
            con.commit()
            

    def remove_all_warns(self, group_id, user_id):
        with self._db() as con:
            cur = con.cursor()
            cur.execute("UPDATE warnings SET warnings = 0 WHERE group_id=? AND user_id=?", (group_id, user_id))
            con.commit()
            

    def block_bot(self, group_id, bot_username):
        with self._db() as con:
            cur = con.cursor()
            cur.execute("INSERT INTO botBlocks (group_id, bot_username) VALUES (?, ?)", (group_id, bot_username))
            con.commit()
            

    def unblock_bot(self, group_id, bot_username):
        with self._db() as con:
            cur = con.cursor()  
            cur.execute("DELETE FROM botBlocks WHERE group_id=? AND bot_username=?", (group_id, bot_username))
            con.commit()
            

    def get_botBlocks(self, group_id):
        with self._db() as con:
            cur = con.cursor()
            cur.execute("SELECT bot_username FROM botBlocks WHERE group_id=?", (group_id,))
            rows = cur.fetchall()
            
            return [row[0] for row in rows]

    def block_word(self, group_id, word):
        with self._db() as con:
            cur = con.cursor()
            cur.execute("INSERT INTO blocked_words (group_id, word) VALUES (?, ?)", (group_id, word))
            con.commit()
            

    def unblock_word(self, group_id, word):
        with self._db() as con:
            cur = con.cursor()
            cur.execute("DELETE FROM blocked_words WHERE group_id=? AND word=?", (group_id, word))
            con.commit()

    def ban_group(self, group_id):
        with self._db() as con:
            cur = con.cursor()
            cur.execute("INSERT INTO blocked_groups (group_id) VALUES (?)", (group_id,))
            con.commit()
    
    def unban_group(self, group_id):
        with self._db() as con:
            cur = con.cursor()
            cur.execute("DELETE FROM blocked_groups WHERE group_id=?", (group_id,))
            con.commit()

    def is_group_blocked(self, group_id):
        with self._db() as con:
            cur = con.cursor()
            cur.execute("SELECT group_id FROM blocked_groups WHERE group_id=?", (group_id,))
            row = cur.fetchone()
            return True if row[0] else False
            

    def blocked_words(self, group_id):
        with self._db() as con:
            cur = con.cursor()
            cur.execute("SELECT word FROM blocked_words WHERE group_id=?", (group_id,))
            rows = cur.fetchall()
            
            return [row[0] for row in rows]

    def update_message(self, updates:list, version:str):
        message = f"*نسخه جدید ربات کمک‌یار (***{version}***) منتشر شد!*\n\n"
        for update in updates:
            message += f"{update}\n"
        with self._db() as con:
            cur = con.cursor()
            cur.execute("SELECT group_id FROM groups WHERE active=1")
            rows = cur.fetchall()
            
        success = 0
        err = 0
        for row in rows:
            try:
                bot.send_message(row[0], message, parse_mode="Markdown")
                success += 1                
            except:
                err += 1
                continue
        return success, err
