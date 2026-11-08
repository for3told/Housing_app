import os
import subprocess
from datetime import datetime

# Настройки базы данных
DB_NAME = "housing_db"
DB_USER = "postgres"
DB_PASSWORD = "root"  # root
PG_DUMP_PATH = r"C:\PostgreSQL\18\bin\pg_dump.exe" 

def create_backup():
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_dir = "backups"
    
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
        
    backup_file = os.path.join(backup_dir, f"db_backup_{timestamp}.sql")
    
    # 1. Дамп базы данных PostgreSQL
    os.environ['PGPASSWORD'] = DB_PASSWORD
    dump_cmd = f'"{PG_DUMP_PATH}" -U {DB_USER} -d {DB_NAME} -f "{backup_file}"'
    
    print(f"--> Создаем дамп базы данных в {backup_file}...")
    res = subprocess.run(dump_cmd, shell=True)
    
    if res.returncode == 0:
        print("✅ Дамп БД успешно создан!")
    else:
        print("❌ Ошибка при создании дампа БД.")
        return

    # 2. Автоматический коммит в Git
    commit_msg = f"Auto-backup: {timestamp}"
    print(f"--> Фиксируем изменения в Git: '{commit_msg}'...")
    subprocess.run("git add .", shell=True)
    subprocess.run(f'git commit -m "{commit_msg}"', shell=True)
    print("✅ Снимок проекта успешно сохранен!")

if __name__ == "__main__":
    create_backup()