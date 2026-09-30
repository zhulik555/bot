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

# Enable automatic reconnection with lower delay
sio = socketio.Client(reconnection=True, reconnection_delay=2, logger=False, engineio_logger=False)

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
                   f"**Ends At:** `{end_time}`\n"
                   f"👉 Join here: https://skinrave.com"
    }
    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
        if response.status_code in [200, 204]:
            print(f"[OK] Alert successfully sent to Discord for event: {event_name}")
        else:
            print(f"[ERROR] Failed to send alert: {response.status_code}")
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
    print("[WARNING] Disconnected from /ws namespace. Reconnecting will occur automatically...")

# Catch-all event listener for any WebSocket message
@sio.on('*', namespace='/ws')
def catch_all(event, data):
    print(f"[EVENT LOG] Received event '{event}': {data}")
    # Trigger alert if the event is related to RAIN
    event_str = str(event).upper()
    if "RAIN" in event_str or "OPEN" in event_str:
        print(f"[MATCH FOUND] Triggering alert for event: {event}")
        send_rain_alert(event, data)

# Dedicated handler for standard rain open event
@sio.on('DOMAIN_RAIN_OPEN_EVENT', namespace='/ws')
def on_rain_open(data):
    print(f"[EVENT] Explicit DOMAIN_RAIN_OPEN_EVENT received: {data}")
    send_rain_alert('DOMAIN_RAIN_OPEN_EVENT', data)

def run_socketio():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Origin': 'https://skinrave.com',
        'Referer': 'https://skinrave.com/'
    }
    
    while True:
        try:
            if not sio.connected:
                print("[INFO] Connecting to Skinrave WebSocket...")
                sio.connect(
                    'https://skinrave.com',
                    namespaces=['/ws'],
                    headers=headers,
                    transports=['websocket', 'polling'],
                    socketio_path='socket.io'
                )
            
            # Periodically re-subscribe every 2 minutes to keep connection/room active
            time.sleep(120)
            if sio.connected:
                subscribe_rain()
                
        except Exception as e:
            print(f"[ERROR] WebSocket connection error: {e}. Retrying in 5 seconds...")
            time.sleep(5)

# Start WebSocket thread
threading.Thread(target=run_socketio, daemon=True).start()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
