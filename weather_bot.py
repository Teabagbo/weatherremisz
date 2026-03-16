import paho.mqtt.client as mqtt
import json
import requests
import ssl
import os
import re

# --- 1. TARGETS ---
# London (EGLL), Paris (LFPG), Munich (EDDM), Toronto (CYYZ), Seoul (RKSI), Shanghai (ZSPD)
TARGET_CITIES = ["EGLL", "LFPG", "EDDM", "CYYZ", "RKSI", "ZSPD"]

# Credentials from Render Environment Variables
TG_TOKEN = os.getenv("TG_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")

def send_telegram(message):
    """Sends a notification to your Telegram phone."""
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {"chat_id": TG_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        r = requests.post(url, data=payload, timeout=10)
        print(f"Telegram Post: {r.status_code}", flush=True)
    except Exception as e:
        print(f"Telegram Error: {e}", flush=True)

def on_message(client, userdata, msg):
    """Triggered when the Global Broker pushes new data."""
    try:
        payload = json.loads(msg.payload.decode())
        data_id = payload.get('id', '')

        # Check if the update is for one of our cities
        if any(city in data_id for city in TARGET_CITIES):
            data_url = payload['links'][0]['href']
            
            # Download the actual METAR text
            report_resp = requests.get(data_url, timeout=10)
            if report_resp.status_code == 200:
                raw_text = report_resp.text
                
                # EXTRACT TEMPERATURE: 
                # Looks for pattern like 15/08 or M02/M05 (Negative temps)
                temp_match = re.search(r'\b([M]?\d{2})/\d{2}\b', raw_text)
                if temp_match:
                    temp_val = temp_match.group(1).replace('M', '-')
                    temp_str = f"{temp_val}°C"
                else:
                    temp_str = "Unknown"

                # Check if it's a SPECI (Special/Emergency update)
                is_speci = "SPECI" in raw_text
                icon = "🚨 SPECI" if is_speci else "🌡️"

                msg_text = (
                    f"{icon} *{data_id} Update*\n"
                    f"Temperature: `{temp_str}`\n"
                    f"Raw: `{raw_text}`"
                )
                send_telegram(msg_text)

    except Exception as e:
        print(f"Error in message loop: {e}", flush=True)

# --- 2. MQTT ENGINE SETUP ---
client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2, protocol=mqtt.MQTTv5)
client.username_pw_set("everyone", "everyone")
client.on_message = on_message
client.tls_set(cert_reqs=ssl.CERT_REQUIRED)

# Connect to the Météo-France Global Hub
client.connect("globalbroker.meteo.fr", 8883)

# --- 3. THE SUBSCRIPTION TOPICS ---
# Using specific feeds ensures reliability and avoids broker 'throttling'
# We listen to the French broker's global cache which covers all target regions
client.subscribe("origin/a/wis2/fr-meteofrance/#") # Global Mirror
client.subscribe("origin/a/wis2/ca-eccc-msc/#")   # Canada Direct
client.subscribe("origin/a/wis2/kr-kma/#")        # Korea Direct
client.subscribe("origin/a/wis2/cn-cma/#")        # China Direct

print("--- BOT IS LIVE AND WATCHING THE SKIES ---", flush=True)

# Immediate alert so you know the code started correctly
send_telegram("🚀 **Bot is Online!** Monitoring London, Paris, Munich, Toronto, Seoul, and Shanghai.")

client.loop_forever()
