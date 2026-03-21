import os
import telebot
from flask import Flask, request
from openai import OpenAI

# Load environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Telegram bot setup
bot = telebot.TeleBot(BOT_TOKEN)

# OpenRouter setup (using OpenAI-compatible API)
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

# Flask app (for Render)
app = Flask(__name__)

# Start command
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Hello 👋 I'm your AI bot! Ask me anything.")

# Handle all messages
@bot.message_handler(func=lambda message: True)
def chat(message):
    user_text = message.text

    try:
        response = client.chat.completions.create(
            model="deepseek/deepseek-r1",
            messages=[
                {"role": "user", "content": user_text}
            ],
        )

        reply = response.choices[0].message.content
        bot.reply_to(message, reply)

    except Exception as e:
        bot.reply_to(message, f"Error: {str(e)}")

# Webhook route
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    json_str = request.get_data().decode("UTF-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "OK", 200

# Home route
@app.route("/")
def index():
    return "Bot is running!"

# Set webhook (IMPORTANT for Render)
def set_webhook():
    render_url = os.getenv("RENDER_EXTERNAL_URL")
    if render_url:
        bot.remove_webhook()
        bot.set_webhook(url=f"{render_url}/{BOT_TOKEN}")

if __name__ == "__main__":
    set_webhook()
    app.run(host="0.0.0.0", port=10000)
