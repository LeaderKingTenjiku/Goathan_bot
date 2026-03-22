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

# Dynamically get the bot's username so it knows when it's being mentioned
bot_info = bot.get_me()
BOT_USERNAME = bot_info.username

# Connect to OpenRouter
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_TOKEN,
)

# Automatically set up the Webhook for Render
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
    welcome_text = (
        "Hello! I am an AI chatbot powered by DeepSeek-R1.\n\n"
        "In private messages, you can just talk to me normally.\n"
        f"In groups, please mention me (`@{BOT_USERNAME}`) or reply to my messages so I know you are talking to me!"
    )
    bot.reply_to(message, welcome_text, parse_mode="Markdown")

@bot.message_handler(commands=['ping'])
def ping_bot(message):
    bot.reply_to(message, f"Pong! I am online, awake, and connected to OpenRouter.\nMy username is @{BOT_USERNAME}")

@bot.message_handler(func=lambda message: True)
def chat_with_ai(message):
    try:
        text = message.text
        
        # Ignore non-text messages (photos, stickers, etc.)
        if not text:
            return 

        chat_type = message.chat.type

        # --- SMART GROUP LOGIC ---
        # If in a group, only reply if the bot is mentioned or replied to
        if chat_type in['group', 'supergroup']:
            is_mentioned = f"@{BOT_USERNAME}" in text
            
            is_reply_to_bot = False
            if message.reply_to_message and message.reply_to_message.from_user.username == BOT_USERNAME:
                is_reply_to_bot = True
            
            if not (is_mentioned or is_reply_to_bot):
                return
            
            # Remove the bot's @username from the text so the AI doesn't get confused
            text = text.replace(f"@{BOT_USERNAME}", "").strip()
            
            # If they just tagged the bot but didn't say anything
            if not text:
                bot.reply_to(message, "Yes? How can I help you?")
                return

        # Show the "typing..." status in Telegram
        bot.send_chat_action(message.chat.id, 'typing')
        
        # --- OPENROUTER API CALL (100% FREE MODEL) ---
        chat_completion = client.chat.completions.create(
            model="deepseek/deepseek-r1:free", 
            messages=[
                {
                    "role": "user",
                    "content": text,
                }
            ]
        )
        
        # Extract the AI's response and send it back
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
    
    # Process messages in a background thread.
    # DeepSeek-R1 takes time to "think". If we don't use a thread, Telegram times out.
    threading.Thread(target=bot.process_new_updates, args=([update],)).start()
    return "!", 200

@app.route('/')
def index():
    return f"Bot @{BOT_USERNAME} is currently running securely and awake!", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
