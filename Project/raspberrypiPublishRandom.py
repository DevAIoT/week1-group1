#!/usr/bin/env python3
"""
Raspberry Pi - Water Quality MQTT Publisher (Random Data Mode)
- Generates random sensor data for testing
- Publishes data to MQTT broker
"""

import time
import json
import random
import paho.mqtt.client as mqtt
from datetime import datetime
import sys

# MQTT Configuration
MQTT_BROKER = "192.168.1.103"  # MQTT broker IP
MQTT_PORT = 1883
MQTT_TOPIC = "Group1_FilterProject"
MQTT_CLIENT_ID = "group1_raspberry_pi"

# Publish interval
PUBLISH_INTERVAL = 10  # seconds

class WaterQualityPublisher:
    def __init__(self):
        # Initialize MQTT client
        self.setup_mqtt()
        print("✓ Random data generator initialized")
    

    
    def setup_mqtt(self):
        """Initialize MQTT client"""
        self.mqtt_client = mqtt.Client(client_id=MQTT_CLIENT_ID, callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
        self.mqtt_client.on_connect = self.on_mqtt_connect
        self.mqtt_client.on_disconnect = self.on_mqtt_disconnect
        
        try:
            self.mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
            self.mqtt_client.loop_start()
            print(f"✓ Connecting to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}")
        except Exception as e:
            print(f"✗ Error connecting to MQTT broker: {e}")
            sys.exit(1)
    
    def on_mqtt_connect(self, client, userdata, flags, rc, properties=None):
        """Callback when connected to MQTT broker"""
        if rc == 0:
            print("✓ Connected to MQTT broker")
        else:
            print(f"✗ Failed to connect to MQTT broker, code: {rc}")
    
    def on_mqtt_disconnect(self, client, userdata, rc, properties=None):
        """Callback when disconnected from MQTT broker"""
        print("⚠ Disconnected from MQTT broker")
    
    def generate_random_data(self):
        """Generate random sensor data for testing"""
        # Generate random turbidity value (0-10 NTU range)
        turbidity = round(random.uniform(0.5, 10.0), 2)
        
        # Generate random spectrum value (0-1000 range)
        spectrum = round(random.uniform(50.0, 1000.0), 2)
        
        return turbidity, spectrum
    

    
    def publish_data(self):
        """Generate and publish random sensor data to MQTT broker"""
        # Generate random sensor values
        turbidity, spectrum = self.generate_random_data()
        
        payload = {
            "timestamp": datetime.now().isoformat(),
            "turbidity_sensor": turbidity,
            "spectrum_sensor": spectrum,
            "location": "raspberry_pi_1"
        }
        
        try:
            result = self.mqtt_client.publish(
                MQTT_TOPIC,
                json.dumps(payload),
                qos=1,
                retain=False
            )
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                print(f"✓ Published: Turbidity={turbidity:.2f} NTU, Spectrum={spectrum:.2f}")
            else:
                print(f"✗ Publish failed: {result.rc}")
        except Exception as e:
            print(f"✗ Error publishing: {e}")
    
    def run(self):
        """Main publishing loop"""
        print("=" * 60)
        print("Water Quality MQTT Publisher (Random Data Mode)")
        print("=" * 60)
        print(f"Publishing to topic: {MQTT_TOPIC}")
        print(f"Interval: {PUBLISH_INTERVAL} seconds")
        print("Press Ctrl+C to stop\n")
        
        try:
            while True:
                # Generate and publish random data
                self.publish_data()
                
                # Wait for next publish interval
                time.sleep(PUBLISH_INTERVAL)
                
        except KeyboardInterrupt:
            print("\n\nShutting down publisher...")
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
            print("Goodbye!")

if __name__ == "__main__":
    publisher = WaterQualityPublisher()
    publisher.run()