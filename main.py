import socketio
import requests
import os
import time
import threading
from flask import Flask

# Flask server configuration to keep Render Free Tier happy
app = Flask(__name__)

@app.route('/')
def home():
    return "Skinrave Rain Bot is active!"

DISCORD_WEBHOOK_URL = os.environ.get(
    "DISCORD_WEBHOOK_URL", 
    "https://discord.com/api/webhooks/1554786560568852500/xkrAyOj-AmwID_h4XFH5gmzY5LYazXlavCiRroW_rEVBxmAyCKrvmdpZCWyqgHW3F_5P"
)

sio = socketio.Client(reconnection=True, reconnection_delay=5)

def send_rain_alert(pool_id, end_time):
    payload = {
        "content": f"🚨 @everyone **SKINRAVE RAIN IS NOW OPEN!** 🚨\n"
                   f"**Pool ID:** `{pool_id}`\n"
                   f"**Ends At:** `{end_time}`\n"
                   f"👉 Join here: https://skinrave.com"
    }
    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
        if response.status_code in [200, 204]:
            print("[OK] Alert successfully sent to Discord!")
        else:
            print(f"[ERROR] Failed to send alert to Discord. Status code: {response.status_code}")
    except Exception as e:
        print(f"[ERROR] Exception while sending to Discord: {e}")

@sio.on('connect', namespace='/ws')
def on_connect():
    print("[INFO] Connected to /ws namespace. Subscribing to RAIN room...")
    sio.emit("WS_SUBSCRIBE", {"room": "RAIN", "modifiers": [], "currencyType": "TOKEN"}, namespace='/ws')

@sio.on('DOMAIN_RAIN_OPEN_EVENT', namespace='/ws')
def on_rain_open(data):
    print(f"\n[EVENT] DOMAIN_RAIN_OPEN_EVENT received: {data}")
    pool_id = data.get('rainPoolId', 'N/A')
    end_time = data.get('rainPoolEndTime', 'N/A')
    send_rain_alert(pool_id, end_time)

def run_socketio():
    while True:
        try:
            print("[INFO] Connecting to Skinrave WebSocket...")
            sio.connect(
                'https://skinrave.com',
                namespaces=['/ws'],
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'},
                socketio_path='socket.io'
            )
            sio.wait()
        except Exception as e:
            print(f"[ERROR] Connection failed: {e}. Retrying in 10 seconds...")
            time.sleep(10)

# Start WebSocket listener in a background thread
threading.Thread(target=run_socketio, daemon=True).start()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
