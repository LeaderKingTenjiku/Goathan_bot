import os
import telebot
from flask import Flask, request
from openai import OpenAI

# 1. Get tokens from environment variables
BOT_TOKEN = os.environ.get("BOT_TOKEN")
HF_TOKEN = os.environ.get("HF_TOKEN")

# Render automatically sets this environment variable for your web service (e.g., https://your-app.onrender.com)
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL") 

# 2. Initialize Telegram Bot and Flask App
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# 3. Initialize OpenAI client pointing to Hugging Face router
client = OpenAI(
    base_url="https://router.huggingface.co/v1",
    api_key=HF_TOKEN,
)

# 4. Define the Telegram Message Handler
@bot.message_handler(func=lambda message: True)
def handle_chat(message):
    try:
        # Show "typing..." status in Telegram while waiting for the AI
        bot.send_chat_action(message.chat.id, 'typing')
        
        # Call the Hugging Face AI API
        chat_completion = client.chat.completions.create(
            model="deepseek-ai/DeepSeek-R1:novita",
            messages=[
                {"role": "user", "content": message.text}
            ]
        )
        
        # Extract response and reply to the user
        reply_text = chat_completion.choices[0].message.content
        bot.reply_to(message, reply_text)
        
    except Exception as e:
        bot.reply_to(message, f"Sorry, I encountered an error: {str(e)}")
        print(f"Error: {e}")

# 5. Flask Routes for Webhook
@app.route('/' + BOT_TOKEN, methods=['POST'])
def receive_updates():
    """This route receives updates from Telegram"""
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return {'ok': True}, 200

@app.route('/')
def index():
    """Simple health check route"""
    return "Bot is running and webhook is active!", 200

# 6. Set Webhook automatically on startup
bot.remove_webhook()
if RENDER_EXTERNAL_URL:
    webhook_url = f"{RENDER_EXTERNAL_URL}/{BOT_TOKEN}"
    bot.set_webhook(url=webhook_url)
    print(f"Webhook set to: {webhook_url}")

# Run the app locally (Render uses gunicorn to run it in production)
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
