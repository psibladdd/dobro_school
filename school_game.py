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
def init_db():
    """Инициализация БД + leaderboard_cache"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Таблица tasks (если нет)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY,
                ''' + ', '.join([f'{col} INTEGER DEFAULT 0' for col in columns]) + ''',
                last_updated INTEGER DEFAULT 0
            )
        ''')
        
        # 🔥 ТАБЛИЦА КЭША РЕЙТИНГОВ!
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS leaderboard_cache (
                id INTEGER PRIMARY KEY,
                rating INTEGER DEFAULT 0,
                rank INTEGER DEFAULT 0,
                last_updated INTEGER DEFAULT 0,
                username TEXT DEFAULT ''
            )
        ''')
        
        # При старте пересчитываем КЭШ один раз!
        recalculate_leaderboard_cache(conn, cursor)
        
        conn.commit()
        print("✅ DB + КЭШ рейтингов готов!")
        conn.close()
    except Exception as e:
        print(f"❌ INIT DB ERROR: {e}")
        raise

def recalculate_leaderboard_cache(conn, cursor):
    """Пересчитывает кэш рейтингов для ВСЕХ игроков"""
    print("🔄 Пересчет кэша рейтингов...")
    
    # 1. Берем всех из tasks
    cursor.execute('SELECT id FROM tasks WHERE id IS NOT NULL')
    user_ids = [row[0] for row in cursor.fetchall()]
    
    players = []
    for uid in user_ids:
        cursor.execute('SELECT * FROM tasks WHERE id = ?', (uid,))
        row = cursor.fetchone()
        done_count = sum(1 for i in range(1, len(columns)+1) if row and row[i] == 1)
        players.append({"id": uid, "rating": done_count})
    
    # 2. Сортируем
    players.sort(key=lambda x: x["rating"], reverse=True)
    
    # 3. Записываем места в КЭШ!
    for i, player in enumerate(players):
        cursor.execute('''
            INSERT OR REPLACE INTO leaderboard_cache (id, rating, rank, last_updated)
            VALUES (?, ?, ?, ?)
        ''', (player["id"], player["rating"], i+1, int(time.time())))
    
    print(f"✅ Кэш обновлен: {len(players)} игроков")

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
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # 🔥 Берем ИЗ КЭША (быстро!)
        cursor.execute('''
            SELECT id, rating, rank, username 
            FROM leaderboard_cache 
            ORDER BY rank ASC
            LIMIT 10
        ''')
        top_players = []
        for row in cursor.fetchall():
            top_players.append({
                "id": row[0], "rating": row[1], "rank": row[2], 
                "username": row[3] or f"Игрок {row[0]}"
            })
        
        # Мое место
        my_rank = None
        if user_id:
            cursor.execute('SELECT rank FROM leaderboard_cache WHERE id = ?', (user_id,))
            result = cursor.fetchone()
            my_rank = result[0] if result else len(top_players) + 1
        
        return {
            "top_players": top_players,
            "my_rank": my_rank,
            "total_players": cursor.execute('SELECT COUNT(*) FROM leaderboard_cache').fetchone()[0],
            "players_ahead": (my_rank - 1) if my_rank else 0
        }
    finally:
        if conn: conn.close()




from fastapi import FastAPI, Request, Form
from fastapi.responses import JSONResponse
@app_api.post("/api/tasks/complete")
async def complete_task(user_id: int = Form(...), task_id: str = Form(...)):
    conn = None
    try:
        import time
        current_time = int(time.time())
        
        conn = get_db()
        cursor = conn.cursor()
        
        # 1. Обновляем задачу
        col_name = f't{task_id.zfill(2)}'
        if col_name not in columns:
            return {"status": "error", "message": f"Задача {task_id} не найдена"}
        
        cursor.execute('INSERT OR IGNORE INTO tasks (id) VALUES (?)', (user_id,))
        cursor.execute(f'''
            UPDATE tasks SET {col_name} = 1, last_updated = ? WHERE id = ?
        ''', (current_time, user_id))
        
        # 2. Пересчитываем НОВЫЙ рейтинг этого игрока
        cursor.execute('SELECT * FROM tasks WHERE id = ?', (user_id,))
        row = cursor.fetchone()
        new_rating = sum(1 for i in range(1, len(columns)+1) if row and row[i] == 1)
        
        # 3. ДВИГАЕМ ТАБЛИЦУ РЕЙТИНГОВ!
        update_leaderboard_positions(conn, cursor, user_id, new_rating)
        
        conn.commit()
        print(f"✅ Рейтинг {user_id}: {new_rating}, место обновлено!")
        
        return {
            "status": "success", 
            "message": f"Задача {task_id} выполнена! Рейтинг: {new_rating}"
        }
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        if conn: conn.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        if conn: conn.close()

def update_leaderboard_positions(conn, cursor, changed_user_id, new_rating):
    """Пересчитывает места ВСЕХ игроков после изменения"""
    
    # 1. Берем всех из кэша
    cursor.execute('SELECT id, rating FROM leaderboard_cache')
    players = [{"id": row[0], "rating": row[1]} for row in cursor.fetchall()]
    
    # 2. Обновляем измененного игрока
    for player in players:
        if player["id"] == changed_user_id:
            player["rating"] = new_rating
            break
    
    # 3. Сортируем заново
    players.sort(key=lambda x: x["rating"], reverse=True)
    
    # 4. Перезаписываем места
    for i, player in enumerate(players):
        cursor.execute('''
            UPDATE leaderboard_cache 
            SET rank = ?, rating = ? 
            WHERE id = ?
        ''', (i+1, player["rating"], player["id"]))


if __name__ == "__main__":
    uvicorn.run("school_game:app_api", host="0.0.0.0", port=8000, reload=True)















