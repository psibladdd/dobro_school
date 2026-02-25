from fastapi import FastAPI, Request, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import sqlite3
import uvicorn
import traceback
import os

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
def get_db():
    """Безопасное подключение к БД"""
    try:
        os.makedirs(os.path.dirname(DB_PATH) if DB_PATH else '.', exist_ok=True)
        conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30.0)
        
        # 🔥 ОДИН PRAGMA за раз!
        conn.execute('PRAGMA journal_mode = WAL')
        conn.execute('PRAGMA busy_timeout = 30000')
        conn.execute('PRAGMA synchronous = NORMAL')
        conn.execute('PRAGMA temp_store = MEMORY')
        
        return conn
    except Exception as e:
        print(f"❌ DB ERROR: {e}")
        raise
import time  # ← ДОБАВЬ импорт time в начало файла!

def init_db():
    """Только tasks таблица"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Проверяем last_updated
        cursor.execute("PRAGMA table_info(tasks)")
        if 'last_updated' not in [row[1] for row in cursor.fetchall()]:
            cursor.execute('ALTER TABLE tasks ADD COLUMN last_updated INTEGER DEFAULT 0')
            print("✅ last_updated добавлена")
        
        # Основная таблица
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY,
                ''' + ', '.join([f'{col} INTEGER DEFAULT 0' for col in columns]) + ''',
                last_updated INTEGER DEFAULT 0
            )
        ''')
        
        cursor.execute('INSERT OR IGNORE INTO tasks (id) VALUES (123456)')
        conn.commit()
        print("✅ DB готова!")
        conn.close()
    except Exception as e:
        print(f"❌ INIT ERROR: {e}")


def recalculate_leaderboard_cache(conn, cursor):
    """Пересчитывает кэш для всех игроков"""
    try:
        print("🔄 Пересчет кэша...")
        
        # Берем всех игроков
        cursor.execute('SELECT id FROM tasks WHERE id IS NOT NULL')
        user_ids = [row[0] for row in cursor.fetchall()]
        
        players = []
        for uid in user_ids:
            cursor.execute('SELECT * FROM tasks WHERE id = ?', (uid,))
            row = cursor.fetchone()
            done_count = sum(1 for i in range(1, len(columns)+1) if row and row[i] == 1)
            players.append({"id": uid, "rating": done_count})
        
        # Сортируем и записываем места
        players.sort(key=lambda x: x["rating"], reverse=True)
        for i, player in enumerate(players):
            cursor.execute('''
                INSERT OR REPLACE INTO leaderboard_cache (id, rating, rank, last_updated)
                VALUES (?, ?, ?, ?)
            ''', (player["id"], player["rating"], i+1, int(time.time())))
        
        print(f"✅ Кэш: {len(players)} игроков")
    except Exception as e:
        print(f"❌ Кэш ошибка: {e}")


# 🔥 ГЛОБАЛЬНАЯ обработка ошибок 500
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
    return {"status": "OK", "timestamp": "2026-02-24"}

@app_api.get("/api/tasks")
async def get_tasks(user_id: int = 123456):
    try:
        print(f"🚀 GET /api/tasks?user_id={user_id}")
        
        conn = None
        try:
            conn = get_db()
            cursor = conn.cursor()
            
            # Создаем пользователя
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
            else:
                # Пустая БД = все задания false
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
        print(f"TRACEBACK: {traceback.format_exc()}")
        # Возвращаем демо-данные при ошибке!
        return {
            "user_id": user_id,
            "all_tasks": [{"id": f"{i:02d}", "done": False} for i in range(11,56)],
            "done_tasks": [],
            "pending_count": 25,
            "error": "demo_mode"
        }
@app_api.get("/api/leaderboard")
async def get_leaderboard(user_id: int = None):
    """ТОП игроков - просто и без кэша"""
    conn = None
    try:
        print("🚀 GET /api/leaderboard")
        conn = get_db()
        cursor = conn.cursor()
        
        # 🔥 Берем ВСЕХ игроков
        cursor.execute('SELECT id FROM tasks WHERE id IS NOT NULL')
        user_ids = [row[0] for row in cursor.fetchall()]
        print(f"📊 Найдено игроков: {len(user_ids)}")
        
        players = []
        
        # 🔥 Считаем задания для каждого (как в get_tasks)
        for uid in user_ids:
            cursor.execute('SELECT * FROM tasks WHERE id = ?', (uid,))
            row = cursor.fetchone()
            
            done_count = 0
            if row:
                for i, col in enumerate(columns):
                    if row[i + 1] == 1:  # id=0, колонки с 1
                        done_count += 1
            
            players.append({
                "id": uid,
                "rating": done_count,
                "username": f"Игрок {uid}"
            })
        
        # 🔥 Сортируем
        players.sort(key=lambda x: x["rating"], reverse=True)
        
        # 🔥 Находим ТЕБЯ
        my_rank = None
        if user_id:
            for i, player in enumerate(players):
                if player["id"] == user_id:
                    my_rank = i + 1
                    break
            if not my_rank:
                my_rank = len(players) + 1
        
        print(f"🎯 Топ: {players[0]['rating'] if players else 0}, Ты: #{my_rank}")
        
        return {
            "top_players": players[:10],
            "my_rank": my_rank,
            "total_players": len(players),
            "players_ahead": (my_rank - 1) if my_rank else len(players)
        }
        
    except Exception as e:
        print(f"❌ LEADERBOARD ERROR: {e}")
        return {"error": "Серверная ошибка", "fallback": True}
    finally:
        if conn:
            conn.close()


from fastapi import FastAPI, Request, Form
from fastapi.responses import JSONResponse
@app_api.post("/api/tasks/complete")
async def complete_task(user_id: int = Form(...), task_id: str = Form(...)):
    conn = None
    try:
        import time
        current_time = int(time.time())
        
        print(f"🎯 COMPLETE: {user_id}, {task_id}")
        conn = get_db()
        cursor = conn.cursor()
        
        col_name = f't{task_id.zfill(2)}'
        if col_name not in columns:
            return {"status": "error", "message": f"Задача {task_id} не найдена"}
        
        # Обновляем задачу
        cursor.execute('INSERT OR IGNORE INTO tasks (id) VALUES (?)', (user_id,))
        cursor.execute(f'UPDATE tasks SET {col_name} = 1, last_updated = ? WHERE id = ?', 
                      (current_time, user_id))
        conn.commit()
        
        print(f"✅ {col_name} выполнена!")
        return {"status": "success", "message": f"Задача {task_id} выполнена!"}
        
    except Exception as e:
        print(f"❌ COMPLETE ERROR: {e}")
        if conn:
            conn.rollback()
        return {"status": "error", "message": str(e)[:100]}
    finally:
        if conn:
            conn.close()



def update_leaderboard_positions(conn, cursor, changed_user_id, new_rating):
    """Обновляет места всех игроков"""
    cursor.execute('SELECT id, rating FROM leaderboard_cache')
    players = [{"id": r[0], "rating": r[1]} for r in cursor.fetchall()]
    
    # Обновляем измененного
    for p in players:
        if p["id"] == changed_user_id:
            p["rating"] = new_rating
            break
    
    # Сортируем
    players.sort(key=lambda x: x["rating"], reverse=True)
    
    # Перезаписываем места
    for i, p in enumerate(players):
        cursor.execute('UPDATE leaderboard_cache SET rank = ?, rating = ? WHERE id = ?', 
                      (i+1, p["rating"], p["id"]))



if __name__ == "__main__":
    uvicorn.run("school_game:app_api", host="0.0.0.0", port=8000, reload=True)




















