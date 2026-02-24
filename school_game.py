import os
import sqlite3
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from urllib.parse import parse_qs
import uvicorn

# 🔥 ГЛАВНЫЙ FastAPI экземпляр для Render
app_api = FastAPI(title="Dobro School Game")

# CORS для Telegram + GitHub Pages
app_api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# БД путь для Render
DB_PATH = './gamefication_DB.db'

# Колонки заданий
columns = ['t11','t12','t13','t14','t15','t21','t22','t23','t24','t25',
           't31','t32','t33','t34','t35','t41','t42','t43','t44','t45',
           't51','t52','t53','t54','t55']

def get_db():
    """Безопасное подключение к БД"""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    return conn

# Инициализация БД
def init_db():
    print("🧪 Инициализация БД...")
    conn = get_db()
    cursor = conn.cursor()
    
    # Таблица пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS people (
            id INTEGER PRIMARY KEY,
            username TEXT,
            rating INTEGER DEFAULT 100
        )
    ''')
    
    # Таблица заданий (25 колонок)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY,
            t11 INTEGER DEFAULT 0, t12 INTEGER DEFAULT 0, t13 INTEGER DEFAULT 0, t14 INTEGER DEFAULT 0, t15 INTEGER DEFAULT 0,
            t21 INTEGER DEFAULT 0, t22 INTEGER DEFAULT 0, t23 INTEGER DEFAULT 0, t24 INTEGER DEFAULT 0, t25 INTEGER DEFAULT 0,
            t31 INTEGER DEFAULT 0, t32 INTEGER DEFAULT 0, t33 INTEGER DEFAULT 0, t34 INTEGER DEFAULT 0, t35 INTEGER DEFAULT 0,
            t41 INTEGER DEFAULT 0, t42 INTEGER DEFAULT 0, t43 INTEGER DEFAULT 0, t44 INTEGER DEFAULT 0, t45 INTEGER DEFAULT 0,
            t51 INTEGER DEFAULT 0, t52 INTEGER DEFAULT 0, t53 INTEGER DEFAULT 0, t54 INTEGER DEFAULT 0, t55 INTEGER DEFAULT 0
        )
    ''')
    
    # Тестовый пользователь
    cursor.execute('INSERT OR IGNORE INTO tasks (id) VALUES (123456)', (123456,))
    conn.commit()
    conn.close()
    print("✅ БД готова!")

@app_api.on_event("startup")
async def startup_event():
    init_db()

@app_api.get("/")
async def root():
    return {"status": "Dobro School Game API работает!", "deploy": "Render"}

@app_api.post("/api/tasks")
async def get_tasks(request: Request):
    print("🚀 /api/tasks вызван!")
    
    try:
        data = await request.json()
        init_data = data.get('initData', '')
        print(f"📥 initData: {init_data[:50]}...")
        
        # Парсинг user_id (пока тестовый)
        user_id = 123456
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Создаем пользователя
        cursor.execute('INSERT OR IGNORE INTO tasks (id) VALUES (?)', (user_id,))
        conn.commit()
        
        # ЧИТАЕМ статус заданий из БД
        cursor.execute('SELECT * FROM tasks WHERE id = ?', (user_id,))
        row = cursor.fetchone()
        
        tasks_list = []
        if row:
            print(f"📊 Найдена строка пользователя {user_id}")
            for i, col in enumerate(columns):
                done = bool(row[i + 1])  # id=0, t11=1, t12=2...
                task_id = col.replace('t', '')
                tasks_list.append({"id": task_id, "done": done})
                print(f"📝 {task_id}: {done}")
        else:
            print("⚠️ Пользователь не найден — все задания false")
            for col in columns:
                tasks_list.append({"id": col.replace('t',''), "done": False})
        
        conn.close()
        print(f"📤 Отправляем {len(tasks_list)} заданий")
        return {"tasks": tasks_list, "user_id": user_id}
        
    except Exception as e:
        print(f"💥 Ошибка /api/tasks: {e}")
        # Fallback
        tasks_list = [{"id": col.replace('t',''), "done": False} for col in columns]
        return {"tasks": tasks_list, "user_id": 999999}

@app_api.post("/api/complete_task")
async def complete_task(request: Request):
    print("🔥 /api/complete_task вызван!")
    
    try:
        data = await request.json()
        print(f"📥 Данные: {data}")
        
        task_id = data.get('task_id')
        init_data = data.get('initData', '')
        
        if not task_id:
            return {"success": False, "error": "Нет task_id"}
        
        # Пока фиктивно (куратор через /done)
        print(f"✅ Задание {task_id} получено от куратора!")
        return {"success": True, "message": f"Задание {task_id} засчитано!"}
        
    except Exception as e:
        print(f"💥 Ошибка: {e}")
        return {"success": False, "error": str(e)}

# Кураторские команды (будут работать через Telegram локально)
print("🚀 school_game.py готов для Render!")
print("📍 URL: https://dobro-school.onrender.com")
print("🔧 Start Command: uvicorn school_game:app_api --host 0.0.0.0 --port $PORT")
