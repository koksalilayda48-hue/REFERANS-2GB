import os
import json
import time
import telebot
import threading
import requests
from flask import Flask
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

# ---------------- ENV ----------------
TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
RENDER_URL = os.environ.get("RENDER_URL")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

KANAL_LINK = "@bedavakampanyalarorg"
GRUP_LINK = "vipgrubum"

# ---------------- WEB ----------------
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
        return {"refs": {}, "users": {}, "joined": [], "banned": [], "points": {}}

DATA = load_data()

def save_data():
    try:
        with open("ref.json", "r") as f:
            old = json.load(f)
    except:
        old = {"refs": {}, "users": {}, "joined": [], "banned": [], "points": {}}

    old["refs"].update(DATA["refs"])
    old["users"].update(DATA["users"])
    old["points"].update(DATA["points"])
    old["joined"] = list(set(old["joined"] + DATA["joined"]))
    old["banned"] = list(set(old["banned"] + DATA["banned"]))

    with open("ref.json", "w") as f:
        json.dump(old, f)

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

# ---------------- MENU ----------------
def main_menu():
    m = InlineKeyboardMarkup()
    m.add(
        InlineKeyboardButton("👥 Referansım", callback_data="ref"),
        InlineKeyboardButton("🪙 Puanım", callback_data="puan")
    )
    m.add(
        InlineKeyboardButton("🏆 Liderlik", callback_data="top")
    )
    m.add(
        InlineKeyboardButton("🔗 Linkim", callback_data="link")
    )
    return m

def start_buttons():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("/komutlist"))
    return kb

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

# ---------------- CHECK ----------------
def check_join(user_id):
    try:
        k = bot.get_chat_member(KANAL_LINK, user_id)
        g = bot.get_chat_member(GRUP_LINK, user_id)
        return k.status in ["member", "creator", "administrator"] and g.status in ["member", "creator", "administrator"]
    except:
        return False

def get_link(user_id):
    return f"https://t.me/{bot.get_me().username}?start={user_id}"

# ---------------- START ----------------
@bot.message_handler(commands=["start"])
def start(message):
    user_id = str(message.from_user.id)

    if user_id in DATA["banned"]:
        return

    username = message.from_user.username

    if message.text.startswith("/start "):
        ref = message.text.split()[1]
        if ref != user_id:
            add_ref(ref, user_id, username)

    if not check_join(message.from_user.id):
        safe_send(message.chat.id, f"📢 Katıl:\n{KANAL_LINK}\n{GRUP_LINK}")
        return

    bot.send_message(
        message.chat.id,
        "🎉 Hoşgeldin!\n\n📋 Komutları görmek için aşağıya bas\n👇 Menü:",
        reply_markup=start_buttons()
    )

    safe_send(message.chat.id, "👇 Tıklamalı menü:", main_menu())

# ---------------- /komutlist ----------------
@bot.message_handler(commands=["komutlist"])
def komutlist(message):
    safe_send(
        message.chat.id,
        "📋 Komutlar:\n\n"
        "/start - Başlat\n"
        "/komutlist - Komutlar\n"
        "/puan - Puanın\n"
        "/top - Liderlik\n",
        main_menu()
    )

# ---------------- BUTTON ----------------
@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    uid = str(call.from_user.id)

    if call.data == "ref":
        safe_send(call.message.chat.id, f"👥 Referans: {DATA['refs'].get(uid,0)}", main_menu())
    elif call.data == "puan":
        safe_send(call.message.chat.id, f"🪙 Puan: {DATA['points'].get(uid,0)}", main_menu())
    elif call.data == "top":
        top = sorted(DATA["refs"].items(), key=lambda x: x[1], reverse=True)[:10]
        msg = "🏆 Liderlik\n\n"
        for i,(u,c) in enumerate(top,1):
            name = DATA["users"].get(u,"Anon")
            msg += f"{i}. {name} - {c}\n"
        safe_send(call.message.chat.id, msg, main_menu())
    elif call.data == "link":
        safe_send(call.message.chat.id, get_link(uid), main_menu())

# ---------------- ADMIN ----------------
@bot.message_handler(commands=["broadcast"])
def bc(message):
    if message.from_user.id != ADMIN_ID:
        return
    text = message.text.replace("/broadcast ","")
    for u in DATA["joined"]:
        safe_send(u, text)
    safe_send(message.chat.id,"Gönderildi")

# ---------------- SELF PING ----------------
def self_ping():
    while True:
        try:
            if RENDER_URL:
                requests.get(RENDER_URL)
        except:
            pass
        time.sleep(60)

# ---------------- BOT LOOP ----------------
def run_bot():
    while True:
        try:
            bot.infinity_polling(skip_pending=True)
        except Exception as e:
            print("Hata:", e)
            time.sleep(5)

# ---------------- START ----------------
if __name__ == "__main__":
    threading.Thread(target=run_web).start()
    threading.Thread(target=self_ping).start()
    run_bot()
