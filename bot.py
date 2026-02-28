import asyncio
import logging
import aiohttp
import sqlite3
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = "8262308547:AAH_yahBO6JtPn3AW2NVtkF2Wqp7gqN0tys"
API_BASE_URL = "https://dobro-school.onrender.com"

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id

    await update.message.reply_text(
        f"🎮 Привет, {user.first_name}!\n"
        f"👤 ID: `{user_id}`\n\n"
        f"🔄 Проверяем регистрацию..."
    )

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_BASE_URL}/api/tasks?user_id={user_id}") as response:
                if response.status == 200:
                    data = await response.json()
                    done_count = len(data.get("done_tasks", []))
                    await update.message.reply_text(
                        f"✅ Ты уже зарегистрирован!\n"
                        f"📊 Выполнено: {done_count}/25 заданий\n\n"
                    )
                    return
    except Exception as e:
        logger.error(f"GET check error: {e}")

    await update.message.reply_text(
        f"🎉 Регистрация завершена!\n\n"
        f"👤 ID: `{user_id}`\n"
        f"📋 Профиль создан (25/25 заданий доступны)\n\n",
        parse_mode='Markdown'
    )


async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != 6033842569:
        return
    if not context.args or len(context.args) != 2:
        await update.message.reply_text(
            "❌ **Формат:** `/done USER_ID TASK_ID`\n"
            "📝 **Пример:** `/done 5551234567 11`",
            parse_mode='Markdown'
        )
        return

    try:
        target_user_id = int(context.args[0])
        task_id = context.args[1]

        await update.message.reply_text(f"🔄 Засчитываем {target_user_id} → {task_id}...")

        async with aiohttp.ClientSession() as session:
            async with session.post(
                    f"{API_BASE_URL}/api/tasks/complete",
                    data={
                        "user_id": str(target_user_id),
                        "task_id": task_id
                    }
            ) as response:
                data = await response.json()
                if response.status == 200 and data.get("status") == "success":
                    await update.message.reply_text(
                        f"✅ {data['message']}\n"
                        f"⏰ Время засчитано: {data.get('affected_rows', 0)} строк",
                        parse_mode='Markdown'
                    )
                else:
                    await update.message.reply_text(f"❌ {data.get('message', f'HTTP {response.status}')}")

        logger.info(f"Task {task_id} completed for user {target_user_id}")

    except ValueError:
        await update.message.reply_text("❌ USER_ID и TASK_ID должны быть числами!")
    except Exception as e:
        logger.error(f"DONE error: {e}")
        await update.message.reply_text("❌ Ошибка засчета задания.")


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != 6033842569:
        return
    if not context.args:
        await update.message.reply_text("❌ **Формат:** `/stats USER_ID`")
        return

    try:
        user_id = int(context.args[0])

        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_BASE_URL}/api/tasks?user_id={user_id}") as response:
                if response.status != 200:
                    await update.message.reply_text(f"❌ Игрок {user_id} не найден!")
                    return

                data = await response.json()
                done_count = len(data.get("done_tasks", []))
                total = len(data.get("all_tasks", []))

                await update.message.reply_text(
                    f"📊 **Статистика игрока {user_id}:**\n"
                    f"✅ Выполнено: **{done_count}/{total}**\n"
                    f"📈 Осталось: **{total - done_count}**\n\n"
                    f"🔗 [API]({API_BASE_URL}/api/tasks?user_id={user_id})",
                    parse_mode='Markdown'
                )

    except ValueError:
        await update.message.reply_text("❌ USER_ID должен быть числом!")
    except Exception as e:
        logger.error(f"STATS error: {e}")
        await update.message.reply_text("❌ Ошибка получения статистики.")


async def top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != 6033842569:
        return
    try:
        await update.message.reply_text("🔄 Загружаем лидерборд...")

        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_BASE_URL}/api/leaderboard") as response:
                if response.status != 200:
                    await update.message.reply_text("❌ Ошибка загрузки лидерборда!")
                    return

                data = await response.json()
                top_players = data.get("top_players", [])

                if not top_players:
                    await update.message.reply_text("📊 Пустой лидерборд!")
                    return

                message = "🏆 **Лидерборд ШВД'26**\n\n"
                for player in top_players[:10]:
                    rank_emoji = "🥇🥈🥉"[player["rank"] - 1] if player["rank"] <= 3 else f"{player['rank']}."
                    message += f"{rank_emoji} **{player['username']}** — {player['done_count']}/25\n"

                message += f"\n👥 Всего игроков: {data.get('total_players', 0)}"

                await update.message.reply_text(message, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"TOP error: {e}")
        await update.message.reply_text("❌ Ошибка лидерборда.")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
🤖 **Бот ШВД'26 — помощник по геймификации**

📖 **Команды:**
• `/start` — регистрация в игре
• `/done USER_ID TASK_ID` — засчитать задание
• `/stats USER_ID` — статистика игрока  
• `/top` — лидерборд
• `/help` — это сообщение

📝 **Примеры:**
`/done 5551234567 11`
`/stats 5551234567` 
`/top`

🎯 **Задания:** t11-t55 (5 категорий × 5 заданий)
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')


def main():
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("done", done))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("top", top))
    application.add_handler(CommandHandler("help", help_command))

    print("🤖 Бот ШВД26 запущен!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
