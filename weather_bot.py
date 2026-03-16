import paho.mqtt.client as mqtt
import json, requests, ssl, os, re

# --- 1. TARGETS & CONFIG ---
TARGET_CITIES = ["EGLL", "LFPG", "EDDM", "CYYZ", "RKSI", "ZSPD"]
TG_TOKEN = os.getenv("TG_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {"chat_id": TG_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        r = requests.post(url, data=payload, timeout=10)
        print(f"Telegram Sent: {r.status_code}", flush=True)
    except Exception as e:
        print(f"Telegram Error: {e}", flush=True)

# --- 2. THE ENGINE ---
def on_connect(client, userdata, flags, rc, properties=None):
    """Triggered when connection is successful."""
    print(f"✅ Connected to WIS 2.0 Broker (Code: {rc})", flush=True)
    
    # SUBSCRIBE TO GLOBAL CACHE (The 2026 standard for METARs)
    # We use wildcards to catch any centre ID providing these cities
    topics = [
        "cache/a/wis2/+/data/core/weather/surface-based-observations/metar/#",
        "origin/a/wis2/+/data/core/weather/surface-based-observations/metar/#"
    ]
    for t in topics:
        client.subscribe(t)
        print(f"📡 Subscribed to: {t}", flush=True)
    
    send_telegram("🚀 **Bot is Online!** Watching London, Paris, Munich, Toronto, Seoul, Shanghai.")

def on_message(client, userdata, msg):
    """Triggered when a weather notification arrives."""
    # DEBUG: See every topic that hits the bot
    print(f"📥 Message received on: {msg.topic}", flush=True)
    
    try:
        payload = json.loads(msg.payload.decode())
        data_id = payload.get('id', '')

        # Check for our cities in the URN/ID
        if any(city in data_id for city in TARGET_CITIES):
            print(f"🎯 TARGET HIT: {data_id}", flush=True)
            
            # WIS 2.0 messages contain a link to the data
            data_url = payload['links'][0]['href']
            report_resp = requests.get(data_url, timeout=10)
            
            if report_resp.status_code == 200:
                raw_text = report_resp.text
                
                # Extract Temp (Handles M for minus, e.g., M02/M05)
                temp_match = re.search(r'\b([M]?\d{2})/\d{2}\b', raw_text)
                temp = temp_match.group(1).replace('M', '-') if temp_match else "??"
                
                msg_text = (
                    f"🌡️ *{data_id} Update*\n"
                    f"Temp: `{temp}°C`\n"
                    f"Code: `{raw_text}`"
                )
                send_telegram(msg_text)

    except Exception as e:
        print(f"❌ Processing Error: {e}", flush=True)

# --- 3. EXECUTION ---
# Use CallbackAPIVersion.VERSION2 for 2026 paho-mqtt standards
client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2, protocol=mqtt.MQTTv5)
client.username_pw_set("everyone", "everyone")
client.on_connect = on_connect
client.on_message = on_message

# Secure TLS 1.3 settings
client.tls_set(cert_reqs=ssl.CERT_REQUIRED)

try:
    print("Connecting to Global Broker...", flush=True)
    # 60 second keepalive ensures the connection stays open on Render
    client.connect("globalbroker.meteo.fr", 8883, keepalive=60)
    client.loop_forever()
except Exception as e:
    print(f"💥 Critical Failure: {e}", flush=True)
