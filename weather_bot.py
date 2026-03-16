import paho.mqtt.client as mqtt
import json
import requests
import ssl
import os

# --- CONFIG ---
TARGET_CITIES = ["EGLL", "LFPG", "EDDM"]
# Tip: On Render, we use "Environment Variables" for security
TG_TOKEN = os.getenv("TG_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {"chat_id": TG_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    requests.post(url, data=payload)

def on_message(client, userdata, msg):
    payload = json.loads(msg.payload.decode())
    data_id = payload.get('id', '')

    if any(city in data_id for city in TARGET_CITIES):
        data_url = payload['links'][0]['href']
        report_resp = requests.get(data_url)
        
        if report_resp.status_code == 200:
            raw_text = report_resp.text
            # Extract Temp (Look for 12/08 pattern)
            try:
                temp = raw_text.split("/")[0].split(" ")[-1][-2:]
                msg_text = f"🚨 *{data_id} Update*\n🌡️ Temp: {temp}°C\n📝 `{raw_text}`"
                send_telegram(msg_text)
                print(f"Sent alert for {data_id}")
            except:
                send_telegram(f"New report for {data_id} but couldn't parse temp automatically.\n`{raw_text}`")

# --- MQTT SETUP ---
client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2, protocol=mqtt.MQTTv5)
client.username_pw_set("everyone", "everyone")
client.on_message = on_message
client.tls_set(cert_reqs=ssl.CERT_REQUIRED)

client.connect("globalbroker.meteo.fr", 8883)
client.subscribe("origin/a/wis2/+/data/core/weather/surface-based-observations/metar/#")

print("Bot is live and watching the skies...")
client.loop_forever()
# Add this right before client.loop_forever()
send_telegram("🚀 Weather Bot has started and is listening for London, Paris, and Munich!")
client.loop_forever()
