#!/usr/bin/env python3
"""
Sensor Data Simulator
Simulates good and bad water quality payloads for testing
"""

import paho.mqtt.client as mqtt
import json
from datetime import datetime
import time
import sys

# MQTT Configuration (same as computeNode.py)
MQTT_BROKER = "192.168.1.103"
MQTT_PORT = 1883
MQTT_TOPIC = "group1/water_quality"
MQTT_CLIENT_ID = "simulator_client"

class SensorSimulator:
    def __init__(self):
        self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, MQTT_CLIENT_ID)
        self.mqtt_client.on_connect = self.on_connect
        
        try:
            print(f"Connecting to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}...")
            self.mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
            self.mqtt_client.loop_start()
            time.sleep(2)  # Wait for connection
        except Exception as e:
            print(f"✗ Error connecting to MQTT broker: {e}")
            sys.exit(1)
    
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f"✓ Connected to MQTT broker")
        else:
            print(f"✗ Failed to connect, return code: {rc}")
    
    def send_good_payload(self):
        """Send a payload with good water quality"""
        payload = {
            "timestamp": datetime.now().isoformat(),
            "turbidity": 2.5,  # Below threshold (5.0)
            "light_intensity": 300.0,  # Within range (50-800)
            "location": "test_simulator"
        }
        
        print("\n📤 Sending GOOD water quality payload:")
        print(f"   Turbidity: {payload['turbidity']} NTU (threshold: 5.0)")
        print(f"   Light: {payload['light_intensity']} (range: 50-800)")
        
        result = self.mqtt_client.publish(MQTT_TOPIC, json.dumps(payload), qos=1)
        
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            print("   ✓ Published successfully")
        else:
            print(f"   ✗ Publish failed: {result.rc}")
    
    def send_bad_payload(self):
        """Send a payload with poor water quality (triggers alert)"""
        payload = {
            "timestamp": datetime.now().isoformat(),
            "turbidity": 12.5,  # Above threshold (5.0) - severely turbid
            "light_intensity": 35.0,  # Below minimum (50) - low light transmission
            "location": "test_simulator"
        }
        
        print("\n📤 Sending BAD water quality payload (should trigger alert):")
        print(f"   Turbidity: {payload['turbidity']} NTU (threshold: 5.0) ⚠️")
        print(f"   Light: {payload['light_intensity']} (min: 50) ⚠️")
        
        result = self.mqtt_client.publish(MQTT_TOPIC, json.dumps(payload), qos=1)
        
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            print("   ✓ Published successfully")
        else:
            print(f"   ✗ Publish failed: {result.rc}")
    
    def send_moderately_bad_payload(self):
        """Send a payload with moderately bad water quality"""
        payload = {
            "timestamp": datetime.now().isoformat(),
            "turbidity": 7.2,  # Above threshold but not severe
            "light_intensity": 150.0,  # Within acceptable range
            "location": "test_simulator"
        }
        
        print("\n📤 Sending MODERATELY BAD water quality payload:")
        print(f"   Turbidity: {payload['turbidity']} NTU (threshold: 5.0) ⚠️")
        print(f"   Light: {payload['light_intensity']} (OK)")
        
        result = self.mqtt_client.publish(MQTT_TOPIC, json.dumps(payload), qos=1)
        
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            print("   ✓ Published successfully")
        else:
            print(f"   ✗ Publish failed: {result.rc}")
    
    def interactive_menu(self):
        """Interactive menu for testing"""
        print("\n" + "=" * 60)
        print("Water Quality Sensor Simulator")
        print("=" * 60)
        print(f"Broker: {MQTT_BROKER}:{MQTT_PORT}")
        print(f"Topic: {MQTT_TOPIC}")
        print("\nMake sure computeNode.py is running to receive messages!")
        
        while True:
            print("\n" + "-" * 60)
            print("Options:")
            print("  1. Send GOOD payload (clean water)")
            print("  2. Send BAD payload (dirty water - triggers alert)")
            print("  3. Send MODERATELY BAD payload")
            print("  4. Send custom payload")
            print("  5. Exit")
            print("-" * 60)
            
            choice = input("\nEnter your choice (1-5): ").strip()
            
            if choice == "1":
                self.send_good_payload()
            elif choice == "2":
                self.send_bad_payload()
            elif choice == "3":
                self.send_moderately_bad_payload()
            elif choice == "4":
                self.send_custom_payload()
            elif choice == "5":
                print("\nShutting down simulator...")
                self.mqtt_client.loop_stop()
                self.mqtt_client.disconnect()
                print("Goodbye!")
                break
            else:
                print("❌ Invalid choice, please try again")
    
    def send_custom_payload(self):
        """Send a custom payload with user-defined values"""
        print("\n📝 Custom Payload:")
        try:
            turbidity = float(input("   Enter turbidity (NTU, e.g., 3.5): "))
            light = float(input("   Enter light intensity (e.g., 200): "))
            
            payload = {
                "timestamp": datetime.now().isoformat(),
                "turbidity": turbidity,
                "light_intensity": light,
                "location": "test_simulator"
            }
            
            print(f"\n📤 Sending custom payload:")
            print(f"   Turbidity: {turbidity} NTU")
            print(f"   Light: {light}")
            
            result = self.mqtt_client.publish(MQTT_TOPIC, json.dumps(payload), qos=1)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                print("   ✓ Published successfully")
            else:
                print(f"   ✗ Publish failed: {result.rc}")
                
        except ValueError:
            print("   ❌ Invalid input, please enter numeric values")
        except Exception as e:
            print(f"   ❌ Error: {e}")

def main():
    if len(sys.argv) > 1:
        # Command line mode
        simulator = SensorSimulator()
        
        if sys.argv[1] == "good":
            simulator.send_good_payload()
        elif sys.argv[1] == "bad":
            simulator.send_bad_payload()
        elif sys.argv[1] == "moderate":
            simulator.send_moderately_bad_payload()
        else:
            print("Usage: python3 simulate_sensor_data.py [good|bad|moderate]")
            print("   Or run without arguments for interactive mode")
        
        time.sleep(1)
        simulator.mqtt_client.loop_stop()
        simulator.mqtt_client.disconnect()
    else:
        # Interactive mode
        simulator = SensorSimulator()
        simulator.interactive_menu()

if __name__ == "__main__":
    main()
