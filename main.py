import os
import telebot
import requests
from flask import Flask, request

# 🔐 ENV VARIABLES
BOT_TOKEN = os.getenv("BOT_TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")

# 🤖 TELEGRAM BOT
bot = telebot.TeleBot(BOT_TOKEN)

# 🌐 FLASK APP
app = Flask(__name__)

# 🧠 MEMORY
user_memory = {}

# 🎭 TENJIKU AI PERSONALITY
SYSTEM_PROMPT = """
You are Tenjiku AI 🤖🔥
- Cool, confident, slightly dominant
- Short, powerful replies
- Friendly but strong tone
- Use emojis like 🔥⚡😈 sometimes
"""

# 🤖 HUGGING FACE API (DeepSeek Distilled)
API_URL = "https://api-inference.huggingface.co/models/deepseek-ai/DeepSeek-R1-Distill-Qwen-7B"

HEADERS = {
    "Authorization": f"Bearer {HF_TOKEN}"
}

# ⚡ Generate reply
def generate_reply(prompt):
    try:
        response = requests.post(
            API_URL,
            headers=HEADERS,
            json={
                "inputs": prompt,
                "parameters": {
                    "max_new_tokens": 200,
                    "temperature": 0.7
                }
            },
            timeout=20
        )

        data = response.json()

        if isinstance(data, list):
            return data[0]["generated_text"].replace(prompt, "").strip()

        return "⚠️ AI busy… try again."

    except Exception:
        return "⚠️ Server error… try again."

# 🚀 START
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "🔥 Tenjiku AI (DeepSeek) activated.")

# 💬 CHAT HANDLER
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

        user_memory[user_id].append(user_text)
        user_memory[user_id] = user_memory[user_id][-5:]

        # 🧠 BUILD PROMPT
        conversation = "\n".join(user_memory[user_id])
        prompt = f"{SYSTEM_PROMPT}\n\nConversation:\n{conversation}\nAI:"

        # ⚡ GET REPLY
        reply = generate_reply(prompt)

        # SAVE MEMORY
        user_memory[user_id].append(reply)

        # SEND
        bot.reply_to(message, reply)

    except Exception:
        bot.reply_to(message, "⚠️ Tenjiku AI glitch… try again.")

# 🌐 WEBHOOK
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = telebot.types.Update.de_json(request.get_data().decode("utf-8"))
    bot.process_new_updates([update])
    return "OK", 200

# 🌍 HOME
@app.route("/")
def home():
    return "Tenjiku AI running (HF DeepSeek) 🔥"

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
