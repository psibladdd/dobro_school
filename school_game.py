from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import uvicorn

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
    # Тестовый пользователь
    cursor.execute('INSERT OR IGNORE INTO tasks (id) VALUES (123456)')
    conn.commit()
    conn.close()

@app_api.on_event("startup")
async def startup():
    init_db()

@app_api.get("/")
async def root():
    return {"status": "Dobro School API — только чтение! 🚀"}

@app_api.get("/api/tasks")
async def get_tasks(user_id: int = 123456):
    print(f"🚀 GET /api/tasks?user_id={user_id}")
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Создаем пользователя если нет
    cursor.execute('INSERT OR IGNORE INTO tasks (id) VALUES (?)', (user_id,))
    conn.commit()
    
    # Читаем статусы
    cursor.execute('SELECT * FROM tasks WHERE id = ?', (user_id,))
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
        "user_id": user_id,
        "all_tasks": all_tasks,        # Все 25 заданий
        "done_tasks": done_tasks,      # Только выполненные
        "pending_count": len(all_tasks) - len(done_tasks)
    }

# Заглушка для фронта (куратор через бота)
@app_api.post("/api/complete_task")
async def complete_task(request: Request):
    return {"success": False, "message": "Используй /done в боте @mary_vii!"}

if __name__ == "__main__":
    uvicorn.run("school_game:app_api", host="0.0.0.0", port=8000, reload=True)
