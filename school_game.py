from fastapi import FastAPI, Request, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import sqlite3
import uvicorn
import traceback
import os
import time

app_api = FastAPI(title="Dobro School Game", debug=True)

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
TIME_COLUMN = 'time'

def get_db():
    """Безопасное подключение к БД"""
    try:
        os.makedirs(os.path.dirname(DB_PATH) if os.path.dirname(DB_PATH) else '.', exist_ok=True)
        conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30.0)
        
        conn.execute('PRAGMA journal_mode = WAL')
        conn.execute('PRAGMA busy_timeout = 30000')
        conn.execute('PRAGMA synchronous = NORMAL')
        conn.execute('PRAGMA temp_store = MEMORY')
        
        return conn
    except Exception as e:
        print(f"❌ DB ERROR: {e}")
        raise

def init_db():
    """Инициализация БД с полем time"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Создаем таблицу с time
        create_sql = f'''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY,
                {', '.join([f'{col} INTEGER DEFAULT 0' for col in columns])},
                {TIME_COLUMN} INTEGER DEFAULT 0
            )
        '''
        cursor.execute(create_sql)
        
        # Миграция: добавляем time если нет
        try:
            cursor.execute(f'ALTER TABLE tasks ADD COLUMN {TIME_COLUMN} INTEGER DEFAULT 0')
            print("✅ Добавлено поле time")
        except sqlite3.OperationalError:
            print("ℹ️ Поле time уже существует")
        
        # Тестовый пользователь
        cursor.execute('INSERT OR IGNORE INTO tasks (id) VALUES (123456)')
        conn.commit()
        print("✅ DB инициализирована с time")
        conn.close()
    except Exception as e:
        print(f"❌ INIT DB ERROR: {e}")
        raise

@app_api.exception_handler(500)
async def internal_exception_handler(request: Request, exc: Exception):
    print(f"💥 500 ERROR: {str(exc)}")
    print(f"TRACEBACK: {traceback.format_exc()}")
    return JSONResponse(
        status_code=500,
        content={"error": "Server error", "message": str(exc)[:100]}
    )

@app_api.on_event("startup")
async def startup():
    try:
        init_db()
    except Exception as e:
        print(f"STARTUP ERROR: {e}")

@app_api.get("/")
async def root():
    return {"status": "Dobro School API — работает! 🚀"}

@app_api.get("/health")
async def health():
    return {"status": "OK", "timestamp": "2026-02-25"}

@app_api.get("/api/tasks")
async def get_tasks(user_id: int = 123456):
    try:
        print(f"🚀 GET /api/tasks?user_id={user_id}")
        
        conn = None
        try:
            conn = get_db()
            cursor = conn.cursor()
            
            cursor.execute('INSERT OR IGNORE INTO tasks (id) VALUES (?)', (user_id,))
            conn.commit()
            
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
            else:
                for col in columns:
                    task_id = col.replace('t', '')
                    task = {"id": task_id, "done": False}
                    all_tasks.append(task)
            
            result = {
                "user_id": user_id,
                "all_tasks": all_tasks,
                "done_tasks": done_tasks,
                "pending_count": len(all_tasks) - len(done_tasks)
            }
            
            print(f"✅ Ответ: {len(done_tasks)}/25 выполнено")
            return result
            
        finally:
            if conn:
                conn.close()
                
    except Exception as e:
        print(f"❌ API TASKS ERROR: {e}")
        return {
            "user_id": user_id,
            "all_tasks": [{"id": f"{i:02d}", "done": False} for i in range(11,56)],
            "done_tasks": [],
            "pending_count": 25,
            "error": "demo_mode"
        }

@app_api.get("/api/leaderboard")
async def get_leaderboard(user_id: int = None):
    """ТОП с сортировкой: done_count DESC, time ASC"""
    conn = None
    try:
        print("🚀 GET /api/leaderboard")
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('SELECT id FROM tasks WHERE id IS NOT NULL')
        user_ids = [row[0] for row in cursor.fetchall()]
        print(f"📊 Найдено игроков: {len(user_ids)}")
        
        players = []
        
        for uid in user_ids:
            cursor.execute('SELECT * FROM tasks WHERE id = ?', (uid,))
            row = cursor.fetchone()
            
            done_count = 0
            last_time = 0
            
            if row:
                # Считаем выполненные
                for i, col in enumerate(columns):
                    if bool(row[i + 1]):
                        done_count += 1
                last_time = row[-1]  # time - последнее поле
            
            players.append({
                "id": uid, 
                "done_count": done_count,
                "last_time": last_time,
                "username": f"Игрок {uid}"
            })
        
        # 🔥 СОРТИРОВКА: больше заданий, раньше время
        players.sort(key=lambda x: (-x["done_count"], x["last_time"]))
        
        my_rank = None
        if user_id:
            for i, player in enumerate(players):
                if player["id"] == user_id:
                    my_rank = i + 1
                    break
            if not my_rank:
                my_rank = len(players) + 1
        
        print(f"🎯 Топ: {players[0]['done_count']} (time:{players[0]['last_time']}), Ты: #{my_rank}")
        
        return {
            "top_players": [
                {
                    "id": p["id"],
                    "done_count": p["done_count"],
                    "username": p["username"],
                    "rank": i+1,
                    "last_time": p["last_time"]
                } for i, p in enumerate(players[:10])
            ],
            "my_rank": my_rank,
            "total_players": len(players),
            "players_ahead": (my_rank - 1) if my_rank else len(players)
        }
        
    except Exception as e:
        print(f"❌ LEADERBOARD ERROR: {e}")
        return {"error": str(e)}
    finally:
        if conn:
            conn.close()

@app_api.post("/api/tasks/complete")
async def complete_task(user_id: int = Form(...), task_id: str = Form(...)):
    conn = None
    try:
        print(f"🎯 COMPLETE: user_id={user_id}, task_id={task_id}")
        
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('INSERT OR IGNORE INTO tasks (id) VALUES (?)', (user_id,))
        
        col_name = f't{task_id.zfill(2)}'
        current_time = int(time.time() * 1000)  # ms
        
        if col_name in columns:
            cursor.execute(
                f'UPDATE tasks SET {col_name} = 1, {TIME_COLUMN} = ? WHERE id = ?', 
                (current_time, user_id)
            )
            affected = cursor.rowcount
            conn.commit()
            
            print(f"✅ {col_name}=1, time={current_time} для user {user_id}")
            return {"status": "success", "message": f"Задача {task_id} выполнена!", "affected_rows": affected}
        else:
            return {"status": "error", "message": f"Задача {task_id} не найдена"}
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        if conn:
            conn.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    uvicorn.run("school_game:app_api", host="0.0.0.0", port=8000, reload=True)
