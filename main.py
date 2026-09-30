import socketio
import requests
import os
import time

# Discord Webhook URL
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
    # Send subscription payload for RAIN room
    sio.emit("WS_SUBSCRIBE", {"room": "RAIN", "modifiers": [], "currencyType": "TOKEN"}, namespace='/ws')

@sio.on('disconnect', namespace='/ws')
def on_disconnect():
    print("[WARNING] Disconnected from WebSocket. Reconnecting...")

# Listen specifically for the Rain open event
@sio.on('DOMAIN_RAIN_OPEN_EVENT', namespace='/ws')
def on_rain_open(data):
    print(f"\n[EVENT] DOMAIN_RAIN_OPEN_EVENT received: {data}")
    pool_id = data.get('rainPoolId', 'N/A')
    end_time = data.get('rainPoolEndTime', 'N/A')
    
    send_rain_alert(pool_id, end_time)

if __name__ == '__main__':
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