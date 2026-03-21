import os
import telebot
from flask import Flask, request
from openai import OpenAI

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

bot = telebot.TeleBot(BOT_TOKEN)

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

app = Flask(__name__)

# 🧠 Memory storage (simple dictionary)
user_memory = {}

# 🎭 Tenjiku AI Personality
SYSTEM_PROMPT = """
You are Tenjiku AI 🤖🔥

Personality:
- Cool, confident, slightly edgy
- Friendly but powerful tone
- Speak like a leader of a big network
- Short, impactful replies (not boring long paragraphs)
- Sometimes use emojis like 🔥⚡😈

Rules:
- Help users clearly
- Be smart and slightly dominant tone
- Never act weak or confused
"""

# Start command
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "🔥 Welcome to Tenjiku AI. Ask anything.")

# Chat handler
@bot.message_handler(func=lambda message: True)
def chat(message):
    try:
        # 🛑 Group control (only reply if mentioned or reply)
        if message.chat.type in ["group", "supergroup"]:
            bot_username = bot.get_me().username

            is_mentioned = message.text and f"@{bot_username}" in message.text
            is_reply = message.reply_to_message and message.reply_to_message.from_user.id == bot.get_me().id

            if not (is_mentioned or is_reply):
                return

        user_id = str(message.from_user.id)
        user_text = message.text

        # 🧠 Get previous memory
        if user_id not in user_memory:
            user_memory[user_id] = []

        # Add user message
        user_memory[user_id].append({"role": "user", "content": user_text})

        # Keep last 10 messages only (memory limit)
        user_memory[user_id] = user_memory[user_id][-10:]

        response = client.chat.completions.create(
            model="google/gemini-2.0-flash-exp:free",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                *user_memory[user_id]
            ],
        )

        reply = response.choices[0].message.content

        # Save bot reply to memory
        user_memory[user_id].append({"role": "assistant", "content": reply})

        bot.reply_to(message, reply)

    except Exception as e:
        if "402" in str(e):
            bot.reply_to(message, "⚠️ Tenjiku AI energy low… recharge API.")
        else:
            bot.reply_to(message, "⚠️ Error occurred. Try again.")

# Webhook
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    json_str = request.get_data().decode("UTF-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "OK", 200

@app.route("/")
def index():
    return "Tenjiku AI is running 🔥"

def set_webhook():
    render_url = os.getenv("RENDER_EXTERNAL_URL")
    if render_url:
        bot.remove_webhook()
        bot.set_webhook(url=f"{render_url}/{BOT_TOKEN}")

if __name__ == "__main__":
    set_webhook()
    app.run(host="0.0.0.0", port=10000)
