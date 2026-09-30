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

# Izveidojam scraper ar lietotāja pārlūka identitāti
scraper = cloudscraper.create_scraper(
    browser={
        'browser': 'chrome',
        'platform': 'windows',
        'desktop': True
    }
)

sio = socketio.Client(
    http_session=scraper,
    reconnection=True,
    reconnection_delay=5,
    logger=True,
    engineio_logger=True
)

@sio.on('connect')
def on_connect():
    print("[INFO] Connected to Skinrave root namespace!")
    send_discord_alert("BOT CONNECTED TO SKINRAVE", {"status": "Connected successfully!"})
    
    try:
        sio.emit("WS_SUBSCRIBE", {"room": "RAIN", "modifiers": [], "currencyType": "TOKEN"})
        sio.emit("WS_SUBSCRIBE", {"room": "GLOBAL", "modifiers": [], "currencyType": "TOKEN"})
        print("[INFO] Subscribed to RAIN and GLOBAL!")
    except Exception as e:
        print(f"[ERROR] Subscription failed: {e}")

@sio.on('connect', namespace='/ws')
def on_connect_ws():
    print("[INFO] Connected to /ws namespace!")
    try:
        sio.emit("WS_SUBSCRIBE", {"room": "RAIN", "modifiers": [], "currencyType": "TOKEN"}, namespace='/ws')
        sio.emit("WS_SUBSCRIBE", {"room": "GLOBAL", "modifiers": [], "currencyType": "TOKEN"}, namespace='/ws')
    except Exception as e:
        print(f"[ERROR] WS Subscription failed: {e}")

@sio.on('*')
def catch_all_root(event, data=None):
    print(f"[EVENT ROOT] {event}: {data}")
    check_and_notify(event, data)

@sio.on('*', namespace='/ws')
def catch_all_ws(event, data=None):
    print(f"[EVENT /ws] {event}: {data}")
    check_and_notify(event, data)

def check_and_notify(event, data):
    event_str = str(event).upper()
    data_str = str(data).upper()
    if "RAIN" in event_str or "RAIN" in data_str or "OPEN" in event_str:
        print(f"[MATCH FOUND] Triggering alert for: {event}")
        send_discord_alert(f"RAIN EVENT DETECTED: {event}", data if isinstance(data, dict) else {"raw": str(data)})

def run_socketio():
    while True:
        try:
            if not sio.connected:
                print("[INFO] Attempting Socket.IO connection...")
                sio.connect(
                    'https://skinrave.com',
                    namespaces=['/', '/ws'],
                    transports=['polling', 'websocket'],
                    headers={
                        "Origin": "https://skinrave.com",
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
                    }
                )
            time.sleep(10)
        except Exception as e:
            print(f"[ERROR] Connection error: {e}. Retrying in 5 seconds...")
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
