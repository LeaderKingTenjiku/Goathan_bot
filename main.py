import os
import telebot
from flask import Flask, request
from openai import OpenAI

# 🔐 ENV VARIABLES
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# 🤖 TELEGRAM BOT
bot = telebot.TeleBot(BOT_TOKEN)

# 🧠 OPENROUTER CLIENT (Gemini optimized)
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
    default_headers={
        "HTTP-Referer": "https://tenjiku-ai.com",
        "X-Title": "Tenjiku AI Bot"
    }
)

# 🌐 FLASK APP (Render)
app = Flask(__name__)

# 🧠 MEMORY (per user)
user_memory = {}

# 🎭 TENJIKU AI PERSONALITY
SYSTEM_PROMPT = """
You are Tenjiku AI 🤖🔥

Personality:
- Cool, confident, slightly dominant
- Friendly but powerful tone
- Speak like a leader of a big network
- Keep replies short, impactful, not boring
- Use emojis like 🔥⚡😈 occasionally

Rules:
- Help clearly and smartly
- Never act weak or confused
"""

# 🚀 START COMMAND
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "🔥 Welcome to Tenjiku AI. Speak.")

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

        # 🔒 LIMIT MEMORY (last 10 messages)
        user_memory[user_id] = user_memory[user_id][-10:]

        # 🤖 PRIMARY MODEL (Gemini Flash)
        try:
            response = client.chat.completions.create(
                model="google/gemini-2.0-flash-exp:free",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    *user_memory[user_id]
                ],
            )
        except:
            # 🔁 FALLBACK MODEL (if Gemini fails)
            response = client.chat.completions.create(
                model="meta-llama/llama-3.1-8b-instruct:free",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    *user_memory[user_id]
                ],
            )

        # 📩 GET REPLY
        reply = response.choices[0].message.content

        # ⚠️ HANDLE EMPTY RESPONSE
        if not reply:
            reply = "⚡ Tenjiku AI is thinking… try again."

        # 🧠 SAVE BOT REPLY
        user_memory[user_id].append({"role": "assistant", "content": reply})

        # 📤 SEND REPLY
        bot.reply_to(message, reply)

    except Exception as e:
        if "402" in str(e):
            bot.reply_to(message, "⚠️ Tenjiku AI energy low… recharge API.")
        else:
            bot.reply_to(message, "⚠️ Error occurred. Try again.")

# 🌐 WEBHOOK ROUTE
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    json_str = request.get_data().decode("UTF-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "OK", 200

# 🌍 HOME ROUTE
@app.route("/")
def index():
    return "Tenjiku AI is running 🔥"

# 🔗 SET WEBHOOK
def set_webhook():
    render_url = os.getenv("RENDER_EXTERNAL_URL")
    if render_url:
        bot.remove_webhook()
        bot.set_webhook(url=f"{render_url}/{BOT_TOKEN}")

# ▶️ RUN APP
if __name__ == "__main__":
    set_webhook()
    app.run(host="0.0.0.0", port=10000)
