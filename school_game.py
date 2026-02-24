from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import uvicorn
import urllib.parse
from typing import Optional

app_api = FastAPI(title="Dobro School Game")

app_api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = './gamefication_DB.db'
columns = ['t11','t12','t13','t14','t15','t21','t22','t23','t24','t25',
           't31','t32','t33','t34','t35','t41','t42','t43','t44','t45',
           't51','t52','t53','t54','t55']

def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY,
            ''' + ', '.join([f'{col} INTEGER DEFAULT 0' for col in columns]) + '''
        )
    ''')
    conn.commit()
    conn.close()

def parse_telegram_initdata(init_data: str) -> Optional[int]:
    """Парсит Telegram initData и возвращает user_id"""
    try:
        # initDataUnsafe.user.id или парсим init_data
        parts = init_data.split('&')
        for part in parts:
            if part.startswith('user=%7B'):
                # Декодируем JSON-like строку
                decoded = urllib.parse.unquote(part[5:])
                if '"id":' in decoded:
                    start = decoded.find('"id":') + 5
                    end = decoded.find(',', start)
                    if end == -1:
                        end = decoded.find('}', start)
                    user_id = int(decoded[start:end].strip())
                    return user_id
    except:
        pass
    return None

@app_api.on_event("startup")
async def startup():
    init_db()

@app_api.get("/")
async def root():
    return {"status": "Dobro School API — авто Telegram ID! 🚀"}

@app_api.get("/api/tasks")
async def get_tasks(request: Request, user_id: Optional[int] = None):
    # 🔥 1. Пробуем взять из initData (Telegram)
    init_data = request.query_params.get('initData', '')
    telegram_user_id = parse_telegram_initdata(init_data) or user_id
    
    # 2. Если нет — используем 123456
    final_user_id = telegram_user_id or 123456
    print(f"🚀 GET /api/tasks?user_id={final_user_id} (initData: {bool(init_data)})")
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Создаем пользователя
    cursor.execute('INSERT OR IGNORE INTO tasks (id) VALUES (?)', (final_user_id,))
    conn.commit()
    
    # Читаем статусы
    cursor.execute('SELECT * FROM tasks WHERE id = ?', (final_user_id,))
    row = cursor.fetchone()
    
    all_tasks = []
    done_tasks = []
    
    if row:
        for i, col in enumerate(columns):
            task_id = col.replace('t', '')
            done = bool(row[i + 1])
            task = {"id": task_id, "done": done}
            all_tasks.append(task)
            if done:
                done_tasks.append(task)
    
    conn.close()
    
    return {
        "user_id": final_user_id,
        "all_tasks": all_tasks,
        "done_tasks": done_tasks,
        "pending_count": len(all_tasks) - len(done_tasks)
    }

if __name__ == "__main__":
    uvicorn.run("school_game:app_api", host="0.0.0.0", port=8000, reload=True)
