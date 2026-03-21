import os
import telebot
from flask import Flask, request
from groq import Groq

# 🔐 ENV VARIABLES
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# 🤖 TELEGRAM BOT
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")

# ⚡ GROQ CLIENT
client = Groq(api_key=GROQ_API_KEY)

# 🌐 FLASK APP
app = Flask(__name__)

# 🧠 MEMORY (per user)
user_memory = {}

# 🎭 GOATHAN PERSONALITY
SYSTEM_PROMPT = """
You are Goathan 🤖🔥

Personality:
- Cool, confident, dominant presence
- Speak like a powerful AI leader
- Short, sharp, impactful replies
- Friendly but slightly savage tone 😈
- Use emojis like 🔥⚡😈 sometimes

Rules:
- Help clearly and smartly
- Avoid boring long paragraphs
- Always sound powerful and confident
"""

# 🚀 START COMMAND
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "🔥 Goathan activated. Speak.")

# ⚡ GENERATE REPLY
def generate_reply(messages):
    try:
        response = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=messages,
            temperature=0.7,
            max_tokens=300
        )

        return response.choices[0].message.content.strip()

    except Exception:
        return "⚠️ Goathan is busy… try again."

# 💬 MAIN CHAT HANDLER
@bot.message_handler(func=lambda message: True)
def chat(message):
    try:
        if not message.text:
            return

        # 🛑 GROUP CONTROL (no spam)
        if message.chat.type in ["group", "supergroup"]:
            bot_username = bot.get_me().username

            is_mentioned = f"@{bot_username}" in message.text
            is_reply = (
                message.reply_to_message and
                message.reply_to_message.from_user.id == bot.get_me().id
            )

            if not (is_mentioned or is_reply):
                return

        user_id = str(message.from_user.id)
        user_text = message.text

        # 🧠 INIT MEMORY
        if user_id not in user_memory:
            user_memory[user_id] = []

        # ➕ ADD USER MESSAGE
        user_memory[user_id].append({"role": "user", "content": user_text})

        # 🔒 LIMIT MEMORY (last 8 messages)
        user_memory[user_id] = user_memory[user_id][-8:]

        # ⚡ GENERATE REPLY
        reply = generate_reply([
            {"role": "system", "content": SYSTEM_PROMPT},
            *user_memory[user_id]
        ])

        # 🧠 SAVE BOT REPLY
        user_memory[user_id].append({"role": "assistant", "content": reply})

        # 📤 SEND REPLY
        bot.reply_to(message, reply)

    except Exception:
        bot.reply_to(message, "⚠️ Goathan glitch… try again.")

# 🌐 WEBHOOK ROUTE
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = telebot.types.Update.de_json(request.get_data().decode("utf-8"))
    bot.process_new_updates([update])
    return "OK", 200

# 🌍 HOME ROUTE
@app.route("/")
def home():
    return "Goathan AI running on Groq ⚡"

# 🔗 SET WEBHOOK
def set_webhook():
    url = os.getenv("RENDER_EXTERNAL_URL")
    if url:
        bot.remove_webhook()
        bot.set_webhook(url=f"{url}/{BOT_TOKEN}")

# ▶️ RUN APP
if __name__ == "__main__":
    set_webhook()
    app.run(host="0.0.0.0", port=10000)
