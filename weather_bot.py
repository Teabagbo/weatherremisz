import paho.mqtt.client as mqtt
import json
import requests
import ssl
import os

# 1. ADDED NEW CITIES
# EGLL=London, LFPG=Paris, EDDM=Munich, CYYZ=Toronto, RKSI=Seoul, ZSPD=Shanghai
TARGET_CITIES = ["EGLL", "LFPG", "EDDM", "CYYZ", "RKSI", "ZSPD"]

TG_TOKEN = os.getenv("TG_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {"chat_id": TG_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        # Added timeout to prevent the bot from hanging if Telegram is slow
        requests.post(url, data=payload, timeout=10)
        print(f"Telegram Sent", flush=True)
    except Exception as e:
        print(f"Telegram Error: {e}", flush=True)

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        data_id = payload.get('id', '')

        if any(city in data_id for city in TARGET_CITIES):
            data_url = payload['links'][0]['href']
            report_resp = requests.get(data_url, timeout=10)
            
            if report_resp.status_code == 200:
                raw_text = report_resp.text
                
                # Logic to find the temperature (handles different METAR formats)
                # Usually looking for the XX/XX pattern
                import re
                temp_match = re.search(r'\b([M]?\d{2})/\d{2}\b', raw_text)
                
                if temp_match:
                    temp = temp_match.group(1).replace('M', '-') # Handle negative temps
                    msg_text = f"🚨 *{data_id} Update*\n🌡️ Temp: {temp}°C\n📝 `{raw_text}`"
                else:
                    msg_text = f"🚨 *{data_id} Update*\n📝 `{raw_text}`"
                
                send_telegram(msg_text)
    except Exception as e:
        print(f"Error processing message: {e}", flush=True)

# --- MQTT SETUP ---
client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2, protocol=mqtt.MQTTv5)
client.username_pw_set("everyone", "everyone")
client.on_message = on_message
client.tls_set(cert_reqs=ssl.CERT_REQUIRED)

client.connect("globalbroker.meteo.fr", 8883)

# 2. UPDATED TOPIC
# We changed 'fr-meteofrance' to '+' to listen to ALL countries globally
GLOBAL_TOPIC = "origin/a/wis2/+/data/core/weather/surface-based-observations/metar/#"
client.subscribe(GLOBAL_TOPIC)

print("Bot is live! Monitoring Europe, Canada, and Asia...", flush=True)
# Added a startup notification so you know the deploy worked
send_telegram("🚀 Bot updated! Monitoring: London, Paris, Munich, Toronto, Seoul, Shanghai.")

client.loop_forever()
# Add this right before client.loop_forever()
send_telegram("🚀 Weather Bot has started and is listening for London, Paris, and Munich!")
client.loop_forever()
