import os
import time
import json
import threading
import requests
import cloudscraper
import socketio
from flask import Flask

app = Flask(__name__)

DISCORD_WEBHOOK_URL = os.environ.get(
    "DISCORD_WEBHOOK_URL", 
    "https://discord.com/api/webhooks/1554786560568852500/xkrAyOj-AmwID_h4XFH5gmzY5LYazXlavCiRroW_rEVBxmAyCKrvmdpZCWyqgHW3F_5P"
)

bot_started = False

@app.route('/')
def home():
    return "Skinrave Rain Bot is active!"

def send_discord_alert(title, data_dict):
    payload = {
        "content": f"🚨 **{title}** 🚨\n```json\n{json.dumps(data_dict, indent=2)[:1500]}\n```\n👉 https://skinrave.com"
    }
    try:
        resp = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=5)
        print(f"[OK] Sent alert to Discord: {title} (Status: {resp.status_code})")
    except Exception as e:
        print(f"[ERROR] Discord post failed: {e}")

# Izveidojam cloudscraper sesiju Cloudflare apiešanai
scraper = cloudscraper.create_scraper()

sio = socketio.Client(
    http_session=scraper,
    reconnection=True,
    reconnection_delay=5,
    logger=False,
    engineio_logger=False
)

@sio.on('connect', namespace='/ws')
def on_connect():
    print("[INFO] Connected successfully to Skinrave /ws namespace!")
    
    # Nosūtam testa ziņu uz Discord uzreiz pēc pieslēgšanās
    send_discord_alert("BOT CONNECTED TO SKINRAVE", {"status": "Connected via Socket.IO /ws namespace"})
    
    # Abonējam visas iespējamās telpas
    try:
        sio.emit("WS_SUBSCRIBE", {"room": "RAIN", "modifiers": [], "currencyType": "TOKEN"}, namespace='/ws')
        sio.emit("WS_SUBSCRIBE", {"room": "GLOBAL", "modifiers": [], "currencyType": "TOKEN"}, namespace='/ws')
        print("[INFO] Sent subscription requests for RAIN and GLOBAL rooms!")
    except Exception as e:
        print(f"[ERROR] Failed to subscribe: {e}")

@sio.on('disconnect', namespace='/ws')
def on_disconnect():
    print("[WARNING] Disconnected from Skinrave /ws namespace")

@sio.on('*', namespace='/ws')
def catch_all(event, data):
    print(f"[EVENT LOG] Received event '{event}': {data}")
    event_str = str(event).upper()
    data_str = str(data).upper()
    
    if "RAIN" in event_str or "RAIN" in data_str or "OPEN" in event_str:
        print(f"[MATCH FOUND] Triggering alert for: {event}")
        send_discord_alert(f"RAIN EVENT DETECTED: {event}", data if isinstance(data, dict) else {"raw": str(data)})

def run_socketio():
    while True:
        try:
            if not sio.connected:
                print("[INFO] Connecting to Skinrave via Cloudscraper Polling...")
                sio.connect(
                    'https://skinrave.com',
                    namespaces=['/ws'],
                    socketio_path='socket.io',
                    transports=['polling', 'websocket']
                )
            time.sleep(10)
        except Exception as e:
            print(f"[ERROR] Connection attempt failed: {e}. Retrying in 5 seconds...")
            time.sleep(5)

def start_bot_once():
    global bot_started
    if not bot_started:
        bot_started = True
        threading.Thread(target=run_socketio, daemon=True).start()

start_bot_once()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
