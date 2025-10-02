import paho.mqtt.client as mqtt
import random
import time
import json
from datetime import datetime

# MQTT Broker settings
BROKER = "192.168.1.103"  # IP address of the MQTT broker
PORT = 1883              # Default MQTT port
TOPIC_SUBSCRIBE = "LivingRoom/events/rpc"  # Topic to subscribe to (adjust based on your broker configuration)
TOPIC_PUBLISH = "group1/"  # Unique topic to publish data to

# Callback function to handle incoming messages
def on_message(client, userdata, msg):
    try:
        # Assume the message is a JSON string with an energy value
        data = json.loads(msg.payload.decode())
        s = data.get("aenergy", None)
        
        if s is not None:
            print(f"Received energy consumption: {s} at {datetime.now()}")
            # Create a message with energy value and timestamp
            message = {
                "energy": s,
                "timestamp": datetime.now().isoformat()
            }
            # Publish the data to a unique topic
            #client.publish(TOPIC_PUBLISH, json.dumps(message))
            print(f"Published: {message}")
        else:
            print("No valid energy data received.")
    except Exception as e:
        print(f"Error processing message: {e}")


# Initialize the MQTT client
client = mqtt.Client()

# Set the callback functions
client.on_message = on_message

# Connect to the MQTT broker
client.connect(BROKER, PORT, 60)

client.subscribe(TOPIC_SUBSCRIBE)

# Start the MQTT loop in a non-blocking way
client.loop_start()

while True:
        # Sleep for a random time between 10-15 seconds
        sleep_time = random.randint(10,15)
        time.sleep(sleep_time)
