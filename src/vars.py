import os
from dotenv import load_dotenv

load_dotenv()
API_TOKEN = os.getenv("TOKEN")
DB_PATH = os.getenv("DB_PATH", "groups.db")
SWEARS_PATH = os.getenv("SWEARS_PATH", "swears.txt")
OWNER_ID = int(os.getenv("OWNER_ID"))

HELP_TEXT = (
    "📖 راهنمای استفاده از ربات کمک‌یار\n\n"
    "این ربات برای مدیریت ساده و سریع گروه طراحی شده. از منوی زیر می‌تونید بخش‌های مختلف رو ببینید.\n"
    "هر بخش شامل دستورها و توضیحات مرتبطه.\n\n"
    "👇 روی دکمه‌های زیر کلیک کنید:"
)

if __name__ == "__main__":
    print(f"API Token = {API_TOKEN if API_TOKEN else "no token"}")
    print(f"DB Path = {DB_PATH}")
    print(f"Swears file path = {SWEARS_PATH}")
    print(f"Owner ID = {OWNER_ID if OWNER_ID else "no id"}")