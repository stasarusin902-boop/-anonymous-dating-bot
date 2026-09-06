import asyncio
import os
import sqlite3
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", "10000"))

if not TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

bot = Bot(TOKEN)
dp = Dispatcher()

db = sqlite3.connect("bot.db", check_same_thread=False)

db.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    name TEXT,
    age INTEGER,
    city TEXT,
    gender TEXT,
    looking TEXT
)
""")

db.execute("""
CREATE TABLE IF NOT EXISTS blocks (
    user_id INTEGER,
    blocked_id INTEGER,
    PRIMARY KEY(user_id, blocked_id)
)
""")

db.commit()

waiting = set()
partners = {}
state = {}
def menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔎 Найти собеседника")],
            [KeyboardButton(text="👤 Моя анкета")],
            [KeyboardButton(text="⏭ Следующий"), KeyboardButton(text="🛑 Остановить чат")]
        ],
        resize_keyboard=True
    )

def genders():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👨 Мужчина"), KeyboardButton(text="👩 Женщина")],
            [KeyboardButton(text="⚪ Неважно")]
        ],
        resize_keyboard=True
    )

def user(uid):
    return db.execute(
        "SELECT * FROM users WHERE user_id=?", (uid,)
    ).fetchone()

def is_blocked(a, b):
    return db.execute(
        "SELECT 1 FROM blocks WHERE user_id=? AND blocked_id=?",
        (a, b)
    ).fetchone() is not None

def compatible(a, b):
    x, y = user(a), user(b)

    if not x or not y:
        return False

    if is_blocked(a, b) or is_blocked(b, a):
        return False

    return (
        (x[5] == "any" or x[5] == y[4])
        and
        (y[5] == "any" or y[5] == x[4])
    )

async def find(uid):
    for candidate in list(waiting):
        if candidate != uid and compatible(uid, candidate):
            waiting.discard(candidate)
            partners[uid] = candidate
            partners[candidate] = uid
            return candidate

    waiting.add(uid)
    return None
  @dp.message(CommandStart())
async def start(m: Message):
    uid = m.from_user.id

    if user(uid):
        await m.answer(
            "Ты уже зарегистрирован.",
            reply_markup=menu()
        )
        return

    state[uid] = {"step": "name"}

    await m.answer(
        "🔞 Анонимный чат 18+\n\n"
        "Придумай имя или псевдоним:"
    )


@dp.message(F.text == "👤 Моя анкета")
async def profile(m: Message):
    u = user(m.from_user.id)

    if not u:
        await m.answer("Сначала нажми /start")
        return

    names = {
        "male": "Мужчина",
        "female": "Женщина",
        "any": "Неважно"
    }

    await m.answer(
        f"👤 {u[1]}\n"
        f"🎂 {u[2]}\n"
        f"📍 {u[3]}\n"
        f"⚧ {names.get(u[4], u[4])}\n"
        f"❤️ Ищу: {names.get(u[5], u[5])}",
        reply_markup=menu()
    )
  @dp.message(CommandStart())
async def start(m: Message):
    uid = m.from_user.id

    if user(uid):
        await m.answer(
            "Ты уже зарегистрирован.",
            reply_markup=menu()
        )
        return

    state[uid] = {"step": "name"}

    await m.answer(
        "🔞 Анонимный чат 18+\n\n"
        "Придумай имя или псевдоним:"
    )


@dp.message(F.text == "👤 Моя анкета")
async def profile(m: Message):
    u = user(m.from_user.id)

    if not u:
        await m.answer("Сначала нажми /start")
        return

    names = {
        "male": "Мужчина",
        "female": "Женщина",
        "any": "Неважно"
    }

    await m.answer(
        f"👤 {u[1]}\n"
        f"🎂 {u[2]}\n"
        f"📍 {u[3]}\n"
        f"⚧ {names.get(u[4], u[4])}\n"
        f"❤️ Ищу: {names.get(u[5], u[5])}",
        reply_markup=menu()
    )
      s = state.get(uid)

    if not s:
        return

    if s["step"] == "name":
        if not text or len(text) > 30:
            await m.answer("Имя должно быть от 1 до 30 символов.")
            return

        s["name"] = text
        s["step"] = "age"

        await m.answer("Сколько тебе лет? Только 18+")

    elif s["step"] == "age":
        try:
            age = int(text)
        except ValueError:
            await m.answer("Напиши возраст числом.")
            return

        if not 18 <= age <= 99:
            await m.answer("Бот только для пользователей 18+.")
            return

        s["age"] = age
        s["step"] = "city"

        await m.answer("Из какого ты города?")

    elif s["step"] == "city":
        s["city"] = text[:50]
        s["step"] = "gender"

        await m.answer(
            "Укажи свой пол:",
            reply_markup=genders()
        )

    elif s["step"] == "gender":
        vals = {
            "👨 Мужчина": "male",
            "👩 Женщина": "female",
            "⚪ Неважно": "any"
        }

        if text not in vals:
            await m.answer("Выбери вариант кнопкой.")
            return

        s["gender"] = vals[text]
        s["step"] = "looking"

        await m.answer(
            "Кого хочешь найти?",
            reply_markup=genders()
        )

    elif s["step"] == "looking":
        vals = {
            "👨 Мужчина": "male",
            "👩 Женщина": "female",
            "⚪ Неважно": "any"
        }

        if text not in vals:
            await m.answer("Выбери вариант кнопкой.")
            return

        db.execute(
            "INSERT OR REPLACE INTO users VALUES (?,?,?,?,?,?)",
            (
                uid,
                s["name"],
                s["age"],
                s["city"],
                s["gender"],
                vals[text]
            )
        )

        db.commit()
        state.pop(uid, None)

        await m.answer(
            "✅ Анкета создана!",
            reply_markup=menu()
        )
      async def health(request):
    return web.Response(text="OK")


async def main():
    app = web.Application()

    app.router.add_get("/", health)
    app.router.add_get("/health", health)

    runner = web.AppRunner(app)
    await runner.setup()

    await web.TCPSite(
        runner,
        "0.0.0.0",
        PORT
    ).start()

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
