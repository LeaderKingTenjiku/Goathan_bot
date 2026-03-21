import os
import threading
import telebot
from flask import Flask, request
from openai import OpenAI

# 1. Fetch tokens from Environment Variables
BOT_TOKEN = os.environ.get("BOT_TOKEN")
HF_TOKEN = os.environ.get("HF_TOKEN")

if not BOT_TOKEN or not HF_TOKEN:
    raise ValueError("BOT_TOKEN and HF_TOKEN must be set in environment variables.")

# 2. Initialize Telegram Bot and Flask App
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# Fetch bot info dynamically to get its username for group mentions
bot_info = bot.get_me()
BOT_USERNAME = bot_info.username

# 3. Initialize OpenAI client with Hugging Face endpoint
client = OpenAI(
    base_url="https://router.huggingface.co/v1",
    api_key=HF_TOKEN,
)

# 4. Automatically setup Webhook if running on Render
app_url = os.environ.get("RENDER_EXTERNAL_URL")
if app_url:
    bot.remove_webhook()
    webhook_url = f"{app_url.rstrip('/')}/{BOT_TOKEN}"
    bot.set_webhook(url=webhook_url)

# --- TELEGRAM BOT LOGIC ---

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "Hello! I am an AI chatbot. In groups, mention me or reply to my messages to talk to me!")

@bot.message_handler(func=lambda message: True)
def chat_with_ai(message):
    try:
        text = message.text
        chat_type = message.chat.type

        # --- SMART GROUP LOGIC ---
        if chat_type in['group', 'supergroup']:
            # Check if the bot is mentioned by @username
            is_mentioned = f"@{BOT_USERNAME}" in text
            
            # Check if the user is replying directly to a previous message from the bot
            is_reply_to_bot = False
            if message.reply_to_message and message.reply_to_message.from_user.username == BOT_USERNAME:
                is_reply_to_bot = True
            
            # If the bot is not mentioned and not replied to, ignore the message
            if not (is_mentioned or is_reply_to_bot):
                return
            
            # Remove the @username from the text so it doesn't confuse the AI prompt
            text = text.replace(f"@{BOT_USERNAME}", "").strip()
            
            # If they only tagged the bot without asking a question
            if not text:
                bot.reply_to(message, "Yes? How can I help you?")
                return

        # Show typing status in Telegram
        bot.send_chat_action(message.chat.id, 'typing')
        
        # Call the OpenAI API
        chat_completion = client.chat.completions.create(
            model="deepseek-ai/DeepSeek-R1:novita",
            messages=[
                {
                    "role": "user",
                    "content": text,
                }
            ]
        )
        
        # Extract and send response back to user
        reply_text = chat_completion.choices[0].message.content
        bot.reply_to(message, reply_text)
        
    except Exception as e:
        bot.reply_to(message, f"Sorry, I encountered an error: {str(e)}")


# --- FLASK WEBHOOK ROUTES ---

@app.route('/' + BOT_TOKEN, methods=['POST'])
def receive_update():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    threading.Thread(target=bot.process_new_updates, args=([update],)).start()
    return "!", 200

@app.route('/')
def index():
    return f"Bot @{BOT_USERNAME} is running perfectly!", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
