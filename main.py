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

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_TOKEN,
)

app_url = os.environ.get("RENDER_EXTERNAL_URL")
if app_url:
    bot.remove_webhook()
    bot.set_webhook(url=f"{app_url.rstrip('/')}/{BOT_TOKEN}")


# ==========================================
# 🧠 BOT MEMORY SYSTEM
# ==========================================
# This dictionary stores the history of conversations for each chat.
chat_memory = {}
MAX_HISTORY = 6  # Remembers the last 6 messages to save your API tokens

def get_chat_history(chat_id):
    if chat_id not in chat_memory:
        chat_memory[chat_id] =[]
    return chat_memory[chat_id]


# ==========================================
# 🤖 TELEGRAM BOT LOGIC
# ==========================================

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "Hello! I am an upgraded human-like AI. I now have memory and can hold a real conversation with you!")

@bot.message_handler(func=lambda message: True)
def chat_with_ai(message):
    try:
        text = message.text
        if not text:
            return 

        chat_id = message.chat.id
        user_name = message.from_user.first_name  # Grab the user's actual name!

        # Smart Group Logic
        if message.chat.type in ['group', 'supergroup']:
            is_mentioned = f"@{BOT_USERNAME}" in text
            is_reply = message.reply_to_message and message.reply_to_message.from_user.username == BOT_USERNAME
            
            if not (is_mentioned or is_reply):
                return
            
            text = text.replace(f"@{BOT_USERNAME}", "").strip()
            if not text:
                bot.reply_to(message, f"Yes, {user_name}? How can I help you?")
                return

        bot.send_chat_action(chat_id, 'typing')
        
        # --- 1. FETCH MEMORY ---
        history = get_chat_history(chat_id)
        
        # --- 2. ADD USER MESSAGE TO MEMORY ---
        # We include the user's name so the AI learns who is talking!
        history.append({"role": "user", "content": f"[{user_name} says]: {text}"})
        
        # Keep memory from getting too big (prevents token limit crashes)
        if len(history) > MAX_HISTORY:
            history.pop(0)

        # --- 3. SYSTEM PROMPT (Rules for the AI) ---
        system_prompt = {
            "role": "system",
            "content": (
                "You are a friendly, highly intelligent, and conversational human-like assistant in a Telegram chat. "
                "You have a great personality. Pay attention to the names of the people talking to you (provided in brackets). "
                "IMPORTANT: Keep your answers concise, ideally around 100 to 150 words so it feels like a text message. "
                "However, if the user explicitly asks for a long story, a big explanation, or detailed code, you are allowed to give a long reply."
            )
        }

        # Combine rules + memory history
        messages = [system_prompt] + history

        # --- 4. CALL OPENROUTER API ---
        chat_completion = client.chat.completions.create(
            model="openrouter/free", 
            messages=messages
        )
        
        reply_text = chat_completion.choices[0].message.content
        
        # --- 5. ADD AI'S REPLY TO MEMORY ---
        history.append({"role": "assistant", "content": reply_text})
        
        bot.reply_to(message, reply_text)
        
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg:
            bot.reply_to(message, "Oops! I've talked so much that I hit my daily limit of 50 free messages. I will wake up again tomorrow!")
        else:
            bot.reply_to(message, f"Sorry, I encountered an error: {error_msg}")

# ==========================================
# 🌐 FLASK SERVER
# ==========================================

@app.route('/' + BOT_TOKEN, methods=['POST'])
def receive_update():
    update = telebot.types.Update.de_json(request.get_data().decode('utf-8'))
    threading.Thread(target=bot.process_new_updates, args=([update],)).start()
    return "!", 200

@app.route('/')
def index():
    return "Bot is running securely with memory!", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
