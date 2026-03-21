import os
import telebot
from flask import Flask, request
from openai import OpenAI

# 🔐 ENV VARIABLES
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# 🤖 TELEGRAM BOT
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")

# ⚡ OPENROUTER CLIENT (optimized)
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
    default_headers={
        "HTTP-Referer": "https://tenjiku-ai.com",
        "X-Title": "Tenjiku AI Bot"
    }
)

# 🌐 FLASK APP
app = Flask(__name__)

# 🧠 MEMORY (per user)
user_memory = {}

# 🎭 TENJIKU AI PERSONALITY
SYSTEM_PROMPT = """
You are Tenjiku AI 🤖🔥

Personality:
- Cool, confident, slightly dominant
- Friendly but powerful tone
- Short, impactful replies
- Use emojis like 🔥⚡😈 sometimes

Rules:
- Help clearly and smartly
- No boring long paragraphs
"""

# 🚀 START COMMAND
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "🔥 Tenjiku AI activated. Speak.")

# ⚡ FAST MULTI-MODEL GENERATOR
def generate_reply(messages):
    models = [
        "meta-llama/llama-3.1-8b-instruct:free",
        "mistralai/mistral-7b-instruct:free",
        "google/gemini-2.0-flash-exp:free"
    ]

    for model in models:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                timeout=15
            )

            reply = response.choices[0].message.content
            if reply:
                return reply.strip()

        except Exception:
            continue  # try next model

    return "⚠️ All AI models are busy right now. Try again later."

# 💬 MAIN CHAT HANDLER
@bot.message_handler(func=lambda message: True)
def chat(message):
    try:
        if not message.text:
            return

        # 🛑 GROUP CONTROL
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

        # 🔒 LIMIT MEMORY (last 8 messages for speed)
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
        bot.reply_to(message, "⚠️ Tenjiku AI glitch… try again.")

# 🌐 WEBHOOK
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    json_str = request.get_data().decode("utf-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "OK", 200

# 🌍 HOME
@app.route("/")
def home():
    return "Tenjiku AI is running 🔥"

# 🔗 SET WEBHOOK
def set_webhook():
    url = os.getenv("RENDER_EXTERNAL_URL")
    if url:
        bot.remove_webhook()
        bot.set_webhook(url=f"{url}/{BOT_TOKEN}")

# ▶️ RUN
if __name__ == "__main__":
    set_webhook()
    app.run(host="0.0.0.0", port=10000)
