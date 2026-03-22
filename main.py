import os
import threading
import telebot
from flask import Flask, request
from openai import OpenAI

# 1. LOAD TOKENS
BOT_TOKEN = os.environ.get("BOT_TOKEN")
OPENROUTER_TOKEN = os.environ.get("OPENROUTER_TOKEN")

if not BOT_TOKEN or not OPENROUTER_TOKEN:
    raise ValueError("Missing BOT_TOKEN or OPENROUTER_TOKEN in Render Environment Variables.")

# 2. INITIALIZE BOT
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)
BOT_USERNAME = bot.get_me().username

# 3. OPENROUTER CONNECTION (NOT HUGGING FACE!)
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",  # <--- This guarantees it uses OpenRouter
    api_key=OPENROUTER_TOKEN,
)

# 4. RENDER WEBHOOK
app_url = os.environ.get("RENDER_EXTERNAL_URL")
if app_url:
    bot.remove_webhook()
    bot.set_webhook(url=f"{app_url.rstrip('/')}/{BOT_TOKEN}")

# --- TELEGRAM BOT LOGIC ---

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "Hello! I am a free AI chatbot. Ask me anything!")

@bot.message_handler(commands=['debug'])
def debug_bot(message):
    # This command will prove to you which server the bot is actually using!
    bot.reply_to(message, f"Current API URL: {client.base_url}\nCurrent Model: openrouter/free")

@bot.message_handler(func=lambda message: True)
def chat_with_ai(message):
    try:
        text = message.text
        if not text:
            return 

        # Smart Group Logic
        if message.chat.type in ['group', 'supergroup']:
            is_mentioned = f"@{BOT_USERNAME}" in text
            is_reply = message.reply_to_message and message.reply_to_message.from_user.username == BOT_USERNAME
            
            if not (is_mentioned or is_reply):
                return
            
            text = text.replace(f"@{BOT_USERNAME}", "").strip()
            if not text:
                bot.reply_to(message, "Yes?")
                return

        bot.send_chat_action(message.chat.id, 'typing')
        
        # --- THE INVINCIBLE AUTO-FREE ROUTER ---
        chat_completion = client.chat.completions.create(
            model="openrouter/free", 
            messages=[{"role": "user", "content": text}]
        )
        
        reply_text = chat_completion.choices[0].message.content
        bot.reply_to(message, reply_text)
        
    except Exception as e:
        # If an error happens, we print it to Telegram
        bot.reply_to(message, f"Sorry, I encountered an error: {str(e)}")

# --- FLASK SERVER ---

@app.route('/' + BOT_TOKEN, methods=['POST'])
def receive_update():
    update = telebot.types.Update.de_json(request.get_data().decode('utf-8'))
    threading.Thread(target=bot.process_new_updates, args=([update],)).start()
    return "!", 200

@app.route('/')
def index():
    return "Bot is running securely!", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
