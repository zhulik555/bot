import os
import json
import sys
import asyncio
import threading
import requests
import time
from flask import Flask
from playwright.async_api import async_playwright

os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "0"

app = Flask(__name__)

DISCORD_WEBHOOK_URL = os.environ.get(
    "DISCORD_WEBHOOK_URL", 
    "https://discord.com/api/webhooks/1554786560568852500/xkrAyOj-AmwID_h4XFH5gmzY5LYazXlavCiRroW_rEVBxmAyCKrvmdpZCWyqgHW3F_5P"
)

bot_started = False
last_alert_time = 0  # Laika zīmogs pēdējam paziņojumam

@app.route('/')
def home():
    return "Skinrave Rain Bot is active via Playwright!"

def send_discord_alert(title, data_dict):
    payload = {
        "content": f"🚨 **{title}** 🚨\n```json\n{json.dumps(data_dict, indent=2)[:1500]}\n```\n👉 https://skinrave.com"
    }
    try:
        resp = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=5)
        print(f"[OK] Sent alert to Discord: {title} (Status: {resp.status_code})")
    except Exception as e:
        print(f"[ERROR] Discord post failed: {e}")

async def run_browser_bot():
    global last_alert_time
    print("[INFO] Starting Playwright Headless Browser...")
    send_discord_alert("BOT INITIALIZING", {"status": "Launching Playwright Browser..."})
    
    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
            )
        except Exception as e:
            print(f"[WARN] Chromium missing in runtime: {e}. Downloading on the fly...")
            os.system("python -m playwright install chromium")
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
            )

        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        def handle_ws_msg(ws):
            print(f"[INFO] WebSocket opened: {ws.url}")
            send_discord_alert("BOT CONNECTED TO SKINRAVE", {"url": ws.url})

            def on_frame_received(payload):
                global last_alert_time
                try:
                    payload_str = payload if isinstance(payload, str) else payload.decode('utf-8', errors='ignore')
                    
                    # Meklējam konkrētu Socket.IO ziņojumu par Rain sākumu un pārbaudām cooldown (piem., vismaz 60s starp ziņojumiem)
                    current_time = time.time()
                    if ("rain" in payload_str.lower() and "active" in payload_str.lower()) or "rain_created" in payload_str.lower():
                        if current_time - last_alert_time > 60:
                            last_alert_time = current_time
                            print(f"[RAIN MATCH] {payload_str}")
                            send_discord_alert("🌧️ RAIN DETECTED!", {"payload": payload_str})
                except Exception as err:
                    print(f"[FRAME PARSE ERR] {err}")

            ws.on("framereceived", on_frame_received)

        page.on("websocket", handle_ws_msg)

        while True:
            try:
                print("[INFO] Navigating to Skinrave.com...")
                await page.goto("https://skinrave.com", wait_until="networkidle", timeout=60000)
                print("[INFO] Page loaded successfully!")
                
                while True:
                    await asyncio.sleep(30)
                    await page.evaluate("() => window.scrollTo(0, 100)")
            except Exception as e:
                print(f"[ERROR] Browser error: {e}. Reloading page in 10s...")
                await asyncio.sleep(10)

def start_async_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_browser_bot())

def start_bot_once():
    global bot_started
    if not bot_started:
        bot_started = True
        threading.Thread(target=start_async_loop, daemon=True).start()

start_bot_once()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
