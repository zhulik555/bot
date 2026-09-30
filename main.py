import socketio
import requests
import os
import time
import threading
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "Skinrave Rain Bot is active!"

DISCORD_WEBHOOK_URL = os.environ.get(
    "DISCORD_WEBHOOK_URL", 
    "https://discord.com/api/webhooks/1554786560568852500/xkrAyOj-AmwID_h4XFH5gmzY5LYazXlavCiRroW_rEVBxmAyCKrvmdpZCWyqgHW3F_5P"
)

sio = socketio.Client(
    reconnection=True, 
    reconnection_delay=3, 
    reconnection_delay_max=10, 
    logger=False, 
    engineio_logger=False
)

def send_rain_alert(event_name, data):
    pool_id = 'N/A'
    end_time = 'N/A'
    
    if isinstance(data, dict):
        pool_id = data.get('rainPoolId', data.get('id', data.get('poolId', 'N/A')))
        end_time = data.get('rainPoolEndTime', data.get('endTime', 'N/A'))

    payload = {
        "content": f"🚨 @everyone **SKINRAVE RAIN IS NOW OPEN!** 🚨\n"
                   f"**Event:** `{event_name}`\n"
                   f"**Pool ID:** `{pool_id}`\n"
                   f"👉 Join here: https://skinrave.com"
    }
    try:
        requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=5)
        print(f"[OK] Alert sent to Discord for event: {event_name}")
    except Exception as e:
        print(f"[ERROR] Exception sending alert: {e}")

@sio.on('connect', namespace='/ws')
def on_connect():
    print("[INFO] Connected successfully to /ws namespace!")
    subscribe_rain()

def subscribe_rain():
    try:
        print("[INFO] Subscribing to RAIN room...")
        sio.emit("WS_SUBSCRIBE", {"room": "RAIN", "modifiers": [], "currencyType": "TOKEN"}, namespace='/ws')
    except Exception as e:
        print(f"[ERROR] Failed to emit subscribe: {e}")

@sio.on('disconnect', namespace='/ws')
def on_disconnect():
    print("[WARNING] Disconnected from /ws namespace. Reconnecting...")

@sio.on('*', namespace='/ws')
def catch_all(event, data):
    print(f"[EVENT LOG] Received event '{event}': {data}")
    if "RAIN" in str(event).upper():
        print(f"[MATCH FOUND] Triggering alert for event: {event}")
        send_rain_alert(event, data)

@sio.on('DOMAIN_RAIN_OPEN_EVENT', namespace='/ws')
def on_rain_open(data):
    print(f"[EVENT] Explicit DOMAIN_RAIN_OPEN_EVENT received: {data}")
    send_rain_alert('DOMAIN_RAIN_OPEN_EVENT', data)

def run_socketio():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Origin': 'https://skinrave.com',
        'Accept-Language': 'en-US,en;q=0.9'
    }
    
    while True:
        try:
            if not sio.connected:
                print("[INFO] Connecting to Skinrave WebSocket (WebSocket mode only)...")
                sio.connect(
                    'https://skinrave.com',
                    namespaces=['/ws'],
                    headers=headers,
                    transports=['websocket'],
                    socketio_path='socket.io'
                )
            
            time.sleep(60)
            if sio.connected:
                subscribe_rain()
                
        except Exception as e:
            print(f"[ERROR] Connection failed: {e}. Retrying in 5 seconds...")
            time.sleep(5)

threading.Thread(target=run_socketio, daemon=True).start()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
