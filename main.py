import os
import threading
import telebot
from flask import Flask, request
from openai import OpenAI

# ==========================================
# 1. LOAD ENVIRONMENT VARIABLES SECURELY
# ==========================================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
OPENROUTER_TOKEN = os.environ.get("OPENROUTER_TOKEN")

if not BOT_TOKEN or not OPENROUTER_TOKEN:
    raise ValueError("CRITICAL ERROR: BOT_TOKEN and OPENROUTER_TOKEN must be set in Render Environment Variables.")

# ==========================================
# 2. INITIALIZE BOT, FLASK, & OPENROUTER
# ==========================================
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

bot_info = bot.get_me()
BOT_USERNAME = bot_info.username

# This connects to OpenRouter using your OPENROUTER_TOKEN
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_TOKEN,
)

# Automatically set up the Webhook so Render keeps the bot alive instantly
app_url = os.environ.get("RENDER_EXTERNAL_URL")
if app_url:
    bot.remove_webhook()
    webhook_url = f"{app_url.rstrip('/')}/{BOT_TOKEN}"
    bot.set_webhook(url=webhook_url)

# ==========================================
# 3. TELEGRAM BOT LOGIC
# ==========================================

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "Hello! I am an AI chatbot. I am currently running DeepSeek-R1. In groups, mention me or reply to my messages to talk to me!")

@bot.message_handler(commands=['ping'])
def ping_bot(message):
    bot.reply_to(message, f"Pong! I am online and connected to OpenRouter.\nMy username is @{BOT_USERNAME}")

@bot.message_handler(func=lambda message: True)
def chat_with_ai(message):
    try:
        text = message.text
        
        # Ignore non-text messages (photos, stickers, etc.)
        if not text:
            return 

        chat_type = message.chat.type

        # SMART GROUP LOGIC: Only reply if mentioned or directly replied to
        if chat_type in ['group', 'supergroup']:
            is_mentioned = f"@{BOT_USERNAME}" in text
            
            is_reply_to_bot = False
            if message.reply_to_message and message.reply_to_message.from_user.username == BOT_USERNAME:
                is_reply_to_bot = True
            
            if not (is_mentioned or is_reply_to_bot):
                return
            
            # Remove the @username so it doesn't confuse the AI
            text = text.replace(f"@{BOT_USERNAME}", "").strip()
            
            if not text:
                bot.reply_to(message, "Yes? How can I help you?")
                return

        # Show the "typing..." status in Telegram
        bot.send_chat_action(message.chat.id, 'typing')
        
        # Call the OpenRouter Free API (Using DeepSeek-R1 Free)
        chat_completion = client.chat.completions.create(
            model="deepseek/deepseek-r1:free", 
            messages=[
                {
                    "role": "user",
                    "content": text,
                }
            ]
        )
        
        # Send the AI's response back to Telegram
        reply_text = chat_completion.choices[0].message.content
        bot.reply_to(message, reply_text)
        
    except Exception as e:
        print(f"API ERROR: {str(e)}")
        bot.reply_to(message, f"Sorry, the API encountered an error: {str(e)}")

# ==========================================
# 4. FLASK WEBHOOK ROUTES FOR RENDER
# ==========================================

@app.route('/' + BOT_TOKEN, methods=['POST'])
def receive_update():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    # Process messages in a background thread so Telegram doesn't timeout
    threading.Thread(target=bot.process_new_updates, args=([update],)).start()
    return "!", 200

@app.route('/')
def index():
    return f"Bot @{BOT_USERNAME} is running securely!", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
