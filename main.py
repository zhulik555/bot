import asyncio
import json
import os
import requests
import threading
import time
from flask import Flask
import websockets

app = Flask(__name__)

DISCORD_WEBHOOK_URL = os.environ.get(
    "DISCORD_WEBHOOK_URL", 
    "https://discord.com/api/webhooks/1554786560568852500/xkrAyOj-AmwID_h4XFH5gmzY5LYazXlavCiRroW_rEVBxmAyCKrvmdpZCWyqgHW3F_5P"
)

bot_started = False

@app.route('/')
def home():
    return "Skinrave Rain Bot is active!"

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

async def listen_ws():
    uri = "wss://skinrave.com/socket.io/?EIO=4&transport=websocket"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Origin": "https://skinrave.com"
    }

    while True:
        try:
            print("[INFO] Connecting to Skinrave Direct WSS...")
            async with websockets.connect(uri, extra_headers=headers) as ws:
                print("[INFO] Direct WSS connected successfully!")
                
                # Receive Engine.IO handshake (40 response)
                response = await ws.recv()
                print(f"[WS HANDSHAKE] {response}")

                # Connect to /ws namespace
                await ws.send('40/ws,')

                # Maintain connection and handle events
                while True:
                    msg = await ws.recv()
                    
                    # Ping / Pong Engine.IO heartbeat
                    if msg == '2':
                        await ws.send('3') # Reply with Pong
                        continue

                    # Handle Socket.IO messages
                    if msg.startswith('42/ws,'):
                        try:
                            payload_str = msg[6:]
                            data_json = json.loads(payload_str)
                            event_name = data_json[0]
                            event_data = data_json[1] if len(data_json) > 1 else {}
                            
                            print(f"[EVENT LOG] Received: {event_name} -> {event_data}")
                            
                            if "RAIN" in str(event_name).upper():
                                print(f"[MATCH FOUND] Triggering alert for: {event_name}")
                                send_rain_alert(event_name, event_data)
                        except Exception as parse_err:
                            print(f"[PARSE ERROR] {parse_err} | Msg: {msg}")

                    # Subscribe regularly if needed
                    await asyncio.sleep(0.1)

        except Exception as e:
            print(f"[ERROR] Connection lost: {e}. Reconnecting in 5 seconds...")
            await asyncio.sleep(5)

def start_async_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(listen_ws())

# Ensure background worker starts only once
def start_bot_once():
    global bot_started
    if not bot_started:
        bot_started = True
        threading.Thread(target=start_async_loop, daemon=True).start()

start_bot_once()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
