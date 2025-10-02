import paho.mqtt.client as mqtt
import time
import random
import json
from datetime import datetime

# MQTT Broker info
BROKER_IP = "192.168.1.103"
SOURCE_TOPIC = "LivingRoom/events/rpc"   # Topic Shelly Plug publishes to
GROUP_TOPIC = "group1/energy_log"        # Replace groupX with your group name

def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode()
        data = json.loads(payload)

        # Navigate to the power plug data (if present)
        if "params" in data and "switch:0" in data["params"]:
            plug_data = data["params"]["switch:0"]

            apower = plug_data.get("apower", 0.0)               # Current power in W
            aenergy = plug_data.get("aenergy", {}).get("total", 0.0)  # Accumulated Wh
            voltage = plug_data.get("voltage", None)
            current = plug_data.get("current", None)

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            message = {
                "timestamp": timestamp,
                "apower_W": apower,
                "aenergy_Wh": aenergy,
                "voltage_V": voltage,
                "current_A": current
            }

            # Publish under group topic
            client.publish(GROUP_TOPIC, json.dumps(message))
            print(f"Received from Shelly → Published: {message}")

    except Exception as e:
        print("Error processing message:", e)

# Setup MQTT client
client = mqtt.Client()
client.on_message = on_message
client.connect(BROKER_IP, 1883, 60)
client.subscribe(SOURCE_TOPIC)
client.loop_start()

# Main loop
while True:
    sleep_time = random.randint(10, 15)  # Sleep between 10–15s
    time.sleep(sleep_time)

