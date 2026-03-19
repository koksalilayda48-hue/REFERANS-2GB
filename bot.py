import os
import json
import time
from datetime import date
import telebot
import threading
from flask import Flask
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

KANAL_LINK = "@bedavakampanyalarorg"
GRUP_LINK = "vipgrubum"

# ---------------- KEEP ALIVE ----------------
@app.route('/')
def home():
    return "Bot aktif!"

def run_web():
    app.run(host="0.0.0.0", port=10000)

# ---------------- DATA ----------------
def load_data():
    try:
        with open("ref.json", "r") as f:
            return json.load(f)
    except:
        return {
            "refs": {},
            "users": {},
            "joined": [],
            "banned": [],
            "points": {}
        }

def save_data():
    with open("ref.json", "w") as f:
        json.dump(DATA, f)

DATA = load_data()

# ---------------- SAFE SEND ----------------
def safe_send(chat_id, text, markup=None):
    try:
        bot.send_message(chat_id, text, reply_markup=markup)
    except Exception as e:
        if "blocked by the user" in str(e):
            if str(chat_id) in DATA["joined"]:
                DATA["joined"].remove(str(chat_id))
                save_data()
        print("Hata:", e)

# ---------------- BUTTON MENU ----------------
def main_menu():
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("👥 Referansım", callback_data="ref"),
        InlineKeyboardButton("🪙 Puanım", callback_data="puan")
    )
    markup.add(
        InlineKeyboardButton("🏆 Liderlik", callback_data="top")
    )
    markup.add(
        InlineKeyboardButton("🔗 Linkim", callback_data="link")
    )
    return markup

# ---------------- REFERANS ----------------
def add_ref(ref_id, new_user_id, username=None):
    ref_id = str(ref_id)
    new_user_id = str(new_user_id)

    if new_user_id in DATA["joined"]:
        return

    DATA["joined"].append(new_user_id)

    DATA["refs"][ref_id] = DATA["refs"].get(ref_id, 0) + 1
    DATA["points"][ref_id] = DATA["points"].get(ref_id, 0) + 1

    if username:
        DATA["users"][ref_id] = username

    save_data()

# ---------------- KONTROL ----------------
def check_join(user_id):
    try:
        k = bot.get_chat_member(KANAL_LINK, user_id)
        g = bot.get_chat_member(GRUP_LINK, user_id)
        return k.status in ["member", "creator", "administrator"] and g.status in ["member", "creator", "administrator"]
    except:
        return False

def get_ref_link(user_id):
    return f"https://t.me/{bot.get_me().username}?start={user_id}"

# ---------------- START ----------------
@bot.message_handler(commands=["start"])
def start_handler(message):
    user_id = str(message.from_user.id)

    if user_id in DATA["banned"]:
        return

    username = message.from_user.username

    if message.text.startswith("/start "):
        ref_id = message.text.split()[1]
        if ref_id != user_id:
            add_ref(ref_id, user_id, username)

    if not check_join(message.from_user.id):
        safe_send(message.chat.id, f"📢 Katıl:\n{KANAL_LINK}\n{GRUP_LINK}")
        return

    safe_send(
        message.chat.id,
        f"""
🎉 Hoşgeldin!

💎 Arkadaşlarını davet et, puan kazan!

👇 Menüden seçim yap:
""",
        main_menu()
    )

# ---------------- BUTTON HANDLER ----------------
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = str(call.from_user.id)

    if call.data == "ref":
        count = DATA["refs"].get(user_id, 0)
        bot.answer_callback_query(call.id)
        safe_send(call.message.chat.id, f"👥 Referansın: {count}", main_menu())

    elif call.data == "puan":
        p = DATA["points"].get(user_id, 0)
        bot.answer_callback_query(call.id)
        safe_send(call.message.chat.id, f"🪙 Puanın: {p}", main_menu())

    elif call.data == "top":
        top = sorted(DATA["refs"].items(), key=lambda x: x[1], reverse=True)[:10]
        msg = "🏆 Liderlik:\n\n"
        for i, (uid, count) in enumerate(top, 1):
            name = DATA["users"].get(uid, "Anon")
            msg += f"{i}. {name} - {count}\n"

        bot.answer_callback_query(call.id)
        safe_send(call.message.chat.id, msg, main_menu())

    elif call.data == "link":
        link = get_ref_link(user_id)
        bot.answer_callback_query(call.id)
        safe_send(call.message.chat.id, f"🔗 Linkin:\n{link}", main_menu())

# ---------------- ADMIN ----------------
@bot.message_handler(commands=["broadcast"])
def broadcast(message):
    if message.from_user.id != ADMIN_ID:
        return

    text = message.text.replace("/broadcast ", "")
    for user in DATA["joined"]:
        safe_send(user, text)

    safe_send(message.chat.id, "✅ Gönderildi")

@bot.message_handler(commands=["ban"])
def ban_user(message):
    if message.from_user.id != ADMIN_ID:
        return

    try:
        uid = message.text.split()[1]
        DATA["banned"].append(uid)
        save_data()
        safe_send(message.chat.id, "🚫 Banlandı")
    except:
        safe_send(message.chat.id, "❌ Hata")

# ---------------- LOOP ----------------
def run_bot():
    while True:
        try:
            bot.infinity_polling(timeout=10, long_polling_timeout=5)
        except Exception as e:
            print("Bot hata:", e)
            time.sleep(5)

# ---------------- START ----------------
if __name__ == "__main__":
    threading.Thread(target=run_web).start()
    threading.Thread(target=run_bot).start()
