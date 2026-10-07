import os
import json
import sqlite3
import urllib.request
from flask import Flask, request, jsonify
from google import genai

app = Flask(__name__)

# Configuration
import os

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Initialize Gemini Client
client = genai.Client(api_key=GEMINI_API_KEY)

# Database path inside the new project directory
DB_PATH = os.path.join(os.path.dirname(__file__), "drivecoach.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scripts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            topic TEXT,
            script_text TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def generate_driving_script(topic):
    system_prompt = f"""
    You are a professional driving instructor and social media content creator.
    Write an engaging 30-second video script (for Reels/TikTok) about: '{topic}'.
    
    Structure the response strictly as:
    🎬 **Topic:** [Topic Name]
    
    🪞 **Hook (0-3s):** 
    [Catchy opening line]
    
    🎥 **Visual Cue:** 
    [What the camera should focus on]
    
    💬 **Body (3-25s):** 
    [Concise, practical driving instruction]
    
    📲 **Call to Action (25-30s):** 
    [Engagement prompt, e.g., 'Save this tip for your next lesson!']
    
    Keep the wording punchy, encouraging, and under 80 words total.
    """
    try:
        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=system_prompt
        )
        return response.text
    except Exception as e:
        return f"⚠️ Error generating script: {str(e)}"

def save_script(chat_id, topic, script_text):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO scripts (chat_id, topic, script_text) VALUES (?, ?, ?)',
        (chat_id, topic, script_text)
    )
    conn.commit()
    conn.close()

def send_reply(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "reply_markup": json.dumps({
            "keyboard": [
                [{"text": "🎬 Mirror Adjustments"}, {"text": "🅿️ Parallel Parking"}],
                [{"text": "🚗 Driving Posture"}, {"text": "🏎️ Steering Technique"}]
            ],
            "resize_keyboard": True
        })
    }
    payload_bytes = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=payload_bytes, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.getcode() == 200
    except Exception:
        return False

@app.route('/webhook', methods=['POST'])
def telegram_webhook():
    try:
        update = request.get_json()
        if "message" in update and "text" in update["message"]:
            chat_id = update["message"]["chat"]["id"]
            user_text = update["message"]["text"]
            
            if user_text.startswith("/start"):
                send_reply(chat_id, "🚗 *Welcome to DriveCoach!*\n\nTap a topic button below or type any custom driving topic to generate a short video script.")
            else:
                topic = user_text.replace("🎬 ", "").replace("🅿️ ", "").replace("🚗 ", "").replace("🏎️ ", "")
                script = generate_driving_script(topic)
                save_script(chat_id, topic, script)
                send_reply(chat_id, script)
                
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

init_db()

if __name__ == '__main__':
    app.run(port=5000, debug=True)

