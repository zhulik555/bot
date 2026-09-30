import asyncio
import json
import os
import requests
import threading
import time
from flask import Flask
import aiohttp

app = Flask(__name__)

DISCORD_WEBHOOK_URL = os.environ.get(
    "DISCORD_WEBHOOK_URL", 
    "https://discord.com/api/webhooks/1554786560568852500/xkrAyOj-AmwID_h4XFH5gmzY5LYazXlavCiRroW_rEVBxmAyCKrvmdpZCWyqgHW3F_5P"
)

bot_started = False

@app.route('/')
def home():
    return "Skinrave Rain Bot is active!"

def send_discord_alert(title, data_str):
    payload = {
        "content": f"🚨 **{title}** 🚨\n```json\n{data_str[:1500]}\n```\n👉 https://skinrave.com"
    }
    try:
        resp = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=5)
        print(f"[OK] Sent alert to Discord: {title} (Status: {resp.status_code})")
    except Exception as e:
        print(f"[ERROR] Discord post failed: {e}")

async def listen_ws():
    uri = "wss://skinrave.com/socket.io/?EIO=4&transport=websocket"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Origin": "https://skinrave.com"
    }

    while True:
        try:
            print("[INFO] Connecting to Skinrave Direct WSS via aiohttp...")
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(uri, headers=headers) as ws:
                    print("[INFO] Direct WSS connected successfully!")
                    
                    # Send Discord test message immediately
                    send_discord_alert("BOT CONNECTED TO SKINRAVE", "Bots veiksmīgi pieslēdzās caur aiohttp un klausās notikumus!")

                    # Receive Engine.IO handshake
                    msg = await ws.receive()
                    print(f"[WS HANDSHAKE] {msg.data}")

                    # Connect to /ws namespace
                    await ws.send_str('40/ws,')

                    # Subscribe to RAIN & GLOBAL rooms
                    await ws.send_str('42/ws,["WS_SUBSCRIBE",{"room":"RAIN","modifiers":[],"currencyType":"TOKEN"}]')
                    await ws.send_str('42/ws,["WS_SUBSCRIBE",{"room":"GLOBAL","modifiers":[],"currencyType":"TOKEN"}]')
                    print("[INFO] Subscribed to RAIN and GLOBAL rooms!")

                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            data = msg.data
                            
                            # Heartbeat Ping -> Pong
                            if data == '2':
                                await ws.send_str('3')
                                continue

                            if 'ws' in data:
                                print(f"[RAW MSG] {data}")

                            if data.startswith('42/ws,'):
                                try:
                                    payload_str = data[6:]
                                    data_json = json.loads(payload_str)
                                    event_name = data_json[0]
                                    event_data = data_json[1] if len(data_json) > 1 else {}
                                    
                                    event_upper = str(event_name).upper()
                                    data_upper = str(event_data).upper()

                                    if "RAIN" in event_upper or "RAIN" in data_upper or "OPEN" in event_upper:
                                        print(f"[MATCH FOUND!] {event_name}")
                                        send_discord_alert(f"RAIN DETECTED: {event_name}", json.dumps(event_data, indent=2))
                                except Exception as parse_err:
                                    print(f"[PARSE ERR] {parse_err}")

                        elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                            print("[INFO] WebSocket closed or error")
                            break

        except Exception as e:
            print(f"[ERROR] Connection lost: {e}. Reconnecting in 5s...")
            await asyncio.sleep(5)

def start_async_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(listen_ws())

def start_bot_once():
    global bot_started
    if not bot_started:
        bot_started = True
        threading.Thread(target=start_async_loop, daemon=True).start()

start_bot_once()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
