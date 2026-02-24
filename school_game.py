import threading
import os
import json
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from telegram.constants import ParseMode
import sqlite3
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from urllib.parse import parse_qs
import uvicorn

load_dotenv()

# 🔥 БАЗА ДАННЫХ — ТЕКУЩАЯ ПАПКА
DB_PATH = './gamefication_DB.db'
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()
def get_db_connection():
    """🔥 НОВАЯ ФУНКЦИЯ — безопасное подключение"""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    return conn
# Создание таблиц
cursor.execute('''
               CREATE TABLE IF NOT EXISTS people
               (
                   id
                   INTEGER
                   PRIMARY
                   KEY,
                   username
                   TEXT,
                   rating
                   INTEGER
                   DEFAULT
                   100
               )
               ''')

cursor.execute('''
               CREATE TABLE IF NOT EXISTS tasks
               (
                   id
                   INTEGER
                   PRIMARY
                   KEY,
                   t11
                   INTEGER
                   DEFAULT
                   0,
                   t12
                   INTEGER
                   DEFAULT
                   0,
                   t13
                   INTEGER
                   DEFAULT
                   0,
                   t14
                   INTEGER
                   DEFAULT
                   0,
                   t15
                   INTEGER
                   DEFAULT
                   0,
                   t21
                   INTEGER
                   DEFAULT
                   0,
                   t22
                   INTEGER
                   DEFAULT
                   0,
                   t23
                   INTEGER
                   DEFAULT
                   0,
                   t24
                   INTEGER
                   DEFAULT
                   0,
                   t25
                   INTEGER
                   DEFAULT
                   0,
                   t31
                   INTEGER
                   DEFAULT
                   0,
                   t32
                   INTEGER
                   DEFAULT
                   0,
                   t33
                   INTEGER
                   DEFAULT
                   0,
                   t34
                   INTEGER
                   DEFAULT
                   0,
                   t35
                   INTEGER
                   DEFAULT
                   0,
                   t41
                   INTEGER
                   DEFAULT
                   0,
                   t42
                   INTEGER
                   DEFAULT
                   0,
                   t43
                   INTEGER
                   DEFAULT
                   0,
                   t44
                   INTEGER
                   DEFAULT
                   0,
                   t45
                   INTEGER
                   DEFAULT
                   0,
                   t51
                   INTEGER
                   DEFAULT
                   0,
                   t52
                   INTEGER
                   DEFAULT
                   0,
                   t53
                   INTEGER
                   DEFAULT
                   0,
                   t54
                   INTEGER
                   DEFAULT
                   0,
                   t55
                   INTEGER
                   DEFAULT
                   0
               )
               ''')
conn.commit()

print(f"✅ БД подключена: {DB_PATH}")
print("🧪 ТЕСТ БД...")
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row[0] for row in cursor.fetchall()]
print(f"📋 Таблицы: {tables}")

cursor.execute("SELECT COUNT(*) FROM tasks")
total_users = cursor.fetchone()[0]
print(f"👥 Пользователей в БД: {total_users}")

if total_users > 0:
    cursor.execute("SELECT id FROM tasks LIMIT 1")
    sample_user = cursor.fetchone()
    print(f"📝 Пример записи: {sample_user}")

    cursor.execute("SELECT * FROM tasks LIMIT 1")
    sample_row = cursor.fetchone()
    print(f"📊 Первая строка: {sample_row}")
else:
    print("⚠️  БД пуста — создадим тестовую запись")
    cursor.execute("INSERT INTO tasks (id, t11) VALUES (999999, 1)")
    conn.commit()
    print("✅ Тестовая запись создана")

print("✅ БД тест завершен!")

BOT_TOKEN = "8262308547:AAH_yahBO6JtPn3AW2NVtkF2Wqp7gqN0tys"
MINI_APP_URL = "https://psibladdd.github.io/dobro_school/"

# FastAPI
app_api = FastAPI()

# 🔥 CORS для Telegram + GitHub Pages
app_api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

columns = ['t11', 't12', 't13', 't14', 't15', 't21', 't22', 't23', 't24', 't25',
           't31', 't32', 't33', 't34', 't35', 't41', 't42', 't43', 't44', 't45',
           't51', 't52', 't53', 't54', 't55']


def validate_init_data(init_data: str) -> dict:
    print(f"🔍 initData: {init_data[:100]}...")
    if not init_data:
        return {'id': 999999}

    try:
        params = parse_qs(init_data)
        user_str = params.get('user', [''])[0]
        if user_str:
            import ast
            user = ast.literal_eval(user_str)
            user_id = user.get('id', 999999)
            print(f"✅ User ID: {user_id}")
            return {'id': user_id}
    except Exception as e:
        print(f"💥 Парсинг initData: {e}")

    return {'id': 999999}


@app_api.get("/")
async def root():
    return {"message": "FastAPI + Telegram Mini App работает!"}


@app_api.post("/api/tasks")
async def get_tasks(request: Request):
    print("🚀 /api/tasks — ТЕСТ БД!")

    # 🔥 НОВОЕ подключение!
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # ТЕСТ — создаем пользователя
        user_id = 123456789  # Фиктивный
        cursor.execute('INSERT OR IGNORE INTO tasks (id) VALUES (?)', (user_id,))
        conn.commit()

        # Читаем статус
        cursor.execute('SELECT * FROM tasks WHERE id = ?', (user_id,))
        task_row = cursor.fetchone()

        print(f"📊 НАЙДЕНО строк: {len(task_row) if task_row else 0}")
        if task_row:
            print(f"📝 t11={task_row[1]}, t21={task_row[6]}")  # Проверяем колонки

        tasks_list = [{"id": col.replace('t', ''), "done": False} for col in columns]
        return {"tasks": tasks_list, "user_id": user_id}

    except Exception as e:
        print(f"💥 БД ОШИБКА: {e}")
        return {"tasks": [], "user_id": None}
    finally:
        conn.close()


@app_api.post("/api/complete_task")
async def complete_task(request: Request):
    print("✅ /api/complete_task ВЫЗВАН!")

    try:
        data = await request.json()
        init_data = data.get('initData', '')
        task_id = data.get('task_id')

        user_info = validate_init_data(init_data)
        user_id = user_info['id']
        col_name = f"t{task_id}"

        cursor.execute(f'UPDATE tasks SET "{col_name}" = 1 WHERE id = ?', (user_id,))
        conn.commit()

        print(f"✅ Задание {task_id} выполнено для user_id: {user_id}")
        return {"success": True}

    except Exception as e:
        print(f"💥 Complete error: {e}")
        return {"success": False}


# Telegram Bot
async def show_miniapp(update: Update, context):
    user_id = update.message.from_user.id
    name = update.message.from_user.first_name or "Герой"

    # Создаем пользователя
    cursor.execute('INSERT OR IGNORE INTO people (id, username, rating) VALUES (?, ?, 100)', (user_id, name))
    cursor.execute('INSERT OR IGNORE INTO tasks (id) VALUES (?)', (user_id,))
    conn.commit()

    keyboard = [[InlineKeyboardButton("🚀 Прокачать персонажа", web_app=WebAppInfo(url=MINI_APP_URL))]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"Привет, <b>{name}</b>! Здесь ты прокачаешь своего крутого персонажа! 💪",
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )


async def handle_webapp_data(update: Update, context):
    try:
        data = json.loads(update.message.web_app_data.data)
        task_id = data.get("task_id")
        user_name = update.message.from_user.first_name

        if task_id:
            cursor.execute(f'UPDATE tasks SET "t{task_id}" = 1 WHERE id = ?', (update.message.from_user.id,))
            conn.commit()
            await update.message.reply_text(f"✅ <b>{user_name}</b> выполнил задание {task_id}!")
    except Exception as e:
        await update.message.reply_text(f"Ошибка: {e}")


def run_fastapi():
    uvicorn.run("school_game:app_api", host="0.0.0.0", port=8000, log_level="info", reload=False)


async def admin_done(update: Update, context):
    """ /done @username 21 или /done 123456 21 """
    user_id = update.message.from_user.id

    # Только кураторы (замени на свои ID)
    admins = [391743540, 6033842569]  # ТВОЙ ID + кураторы
    if user_id not in admins:
        await update.message.reply_text("❌ Только для кураторов!")
        return

    if len(context.args) < 2:
        await update.message.reply_text(
            "ℹ️ <b>Синтаксис:</b>\n"
            "/done <code>@username</code> <code>21</code>\n"
            "/done <code>123456</code> <code>21</code>\n\n"
            "<b>Примеры:</b>\n"
            "/done @ivanov 21\n"
            "/done 123456789 31",
            parse_mode=ParseMode.HTML
        )
        return

    # Парсим username или ID
    target_arg = context.args[0]
    task_id = context.args[1]

    if target_arg.startswith('@'):
        username = target_arg[1:]
        cursor.execute('SELECT id FROM people WHERE username = ?', (username,))
        result = cursor.fetchone()
        if not result:
            await update.message.reply_text(f"❌ Пользователь @{username} не найден!")
            return
        target_user_id = result[0]
    else:
        try:
            target_user_id = int(target_arg)
        except:
            await update.message.reply_text("❌ Неверный ID или username!")
            return

    # Засчитываем задание
    col_name = f"t{task_id}"
    cursor.execute(f'UPDATE tasks SET "{col_name}" = 1 WHERE id = ?', (target_user_id,))
    affected = cursor.rowcount

    if affected:
        cursor.execute('SELECT username FROM people WHERE id = ?', (target_user_id,))
        user_name = cursor.fetchone()
        user_name = user_name[0] if user_name else f"ID{target_user_id}"

        await update.message.reply_text(
            f"✅ <b>{user_name}</b> — задание <code>{task_id}</code> ЗАСЧТЕНО!",
            parse_mode=ParseMode.HTML
        )
    else:
        await update.message.reply_text(f"❌ Пользователь ID={target_user_id} не найден в БД!")


async def admin_stats(update: Update, context):
    """ /stats — общая статистика """
    user_id = update.message.from_user.id
    admins = [8262308547]  # Только ты!

    if user_id not in admins:
        return

    cursor.execute('SELECT COUNT(DISTINCT id) FROM tasks')
    total_users = cursor.fetchone()[0]

    cursor.execute(
        'SELECT SUM(t11+t12+t13+t14+t15+t21+t22+t23+t24+t25+t31+t32+t33+t34+t35+t41+t42+t43+t44+t45+t51+t52+t53+t54+t55) FROM tasks')
    total_done = cursor.fetchone()[0] or 0

    await update.message.reply_text(
        f"📊 <b>СТАТИСТИКА:</b>\n"
        f"👥 Игроков: {total_users}\n"
        f"✅ Заданий выполнено: {total_done}/{(total_users or 1) * 25}\n"
        f"📈 Прогресс: {(total_done / ((total_users or 1) * 25) * 100):.1f}%",
        parse_mode=ParseMode.HTML
    )

def main():
    fastapi_thread = threading.Thread(target=run_fastapi, daemon=True)
    fastapi_thread.start()

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", show_miniapp))
    app.add_handler(CommandHandler("done", admin_done))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_webapp_data))

    print("🤖 Bot + API запущен!")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
