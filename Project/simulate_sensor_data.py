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
import random

# MQTT Configuration
MQTT_BROKER = "192.168.1.103"
MQTT_PORT = 1883
MQTT_TOPIC = "group1/water_quality"
MQTT_CLIENT_ID = "simulator_client"

class SensorSimulator:
    def __init__(self):
        self.mqtt_client = mqtt.Client(
            client_id=MQTT_CLIENT_ID,
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        )
        self.mqtt_client.on_connect = self.on_connect

        try:
            print(f"Connecting to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}...")
            self.mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
            self.mqtt_client.loop_start()
            time.sleep(2)  # Wait for connection
        except Exception as e:
            print(f"✗ Error connecting to MQTT broker: {e}")
            sys.exit(1)
    
    def on_connect(self, client, userdata, flags, reason_code, properties=None):
        if reason_code == 0:
            print(f"✓ Connected to MQTT broker")
        else:
            print(f"✗ Failed to connect, return code: {reason_code}")
    
    def send_good_payload(self):
        """Send a payload with good water quality"""
        # Custom calibration: V₀=3.385V (0 NTU clean water baseline)
        # Good water: 3.38-3.39V → 0-35 NTU (well below WHO 5 NTU guideline)
        voltage = round(random.uniform(3.38, 3.39), 3)
        readings_count = random.randint(15, 25)

        # Good pH: 7.0 - 8.5 (optimal range for drinking water)
        pH = round(random.uniform(7.0, 8.5), 2)
        
        # Spectrum sensor: Good water has high light transmission (400-750)
        # Each channel should be well above SPECTRUM_CHANNEL_MIN (20)
        # Analyzer expects LIGHT_INTENSITY_MIN=50, MAX=800
        base_spectrum = random.uniform(500, 700)
        channels = {
            "A": round(base_spectrum + random.uniform(-100, 100), 2),
            "B": round(base_spectrum + random.uniform(-100, 100), 2),
            "C": round(base_spectrum + random.uniform(-100, 100), 2),
            "D": round(base_spectrum + random.uniform(-100, 100), 2),
            "E": round(base_spectrum + random.uniform(-100, 100), 2),
            "F": round(base_spectrum + random.uniform(-100, 100), 2),
        }
        # Ensure all channels are within valid range
        for key in channels:
            channels[key] = max(400, min(750, channels[key]))
        
        spectrum_average = round(sum(channels.values()) / len(channels), 2)
        spectrum_readings = random.randint(5, 10)
        
        payload = {
            "timestamp": datetime.now().isoformat(),
            "turbidity_sensor": {
                "voltage": voltage,
                "readings_count": readings_count
            },
            "pH": pH,
            "spectrum_sensor": {
                "channels": channels,
                "average": spectrum_average,
                "readings_count": spectrum_readings
            },
            "location": "test_simulator"
        }
        
        # Calculate actual NTU for display
        ntu = round((3.385 - voltage) / 0.00014, 1)
        
        print("\n📤 Sending GOOD water quality payload:")
        print(f"   Turbidity Voltage: {voltage}V → {ntu} NTU (< 5 NTU WHO guideline) ✓")
        print(f"   pH: {pH} (optimal: 7.0-8.5) ✓")
        print(f"   Spectrum Average: {spectrum_average} (min: 50, optimal: 400-750) ✓")
        
        result = self.mqtt_client.publish(MQTT_TOPIC, json.dumps(payload), qos=1)
        
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            print("   ✓ Published successfully")
        else:
            print(f"   ✗ Publish failed: {result.rc}")
    
    def send_bad_payload(self):
        """Send a payload with poor water quality (triggers alert)"""
        # Custom calibration: 3.245V → ~1000 NTU (coffee-level turbidity)
        # Bad water: 3.15-3.25V → 950-1650 NTU (severely turbid)
        voltage = round(random.uniform(3.15, 3.25), 3)
        readings_count = random.randint(15, 25)
        
        # Bad pH: outside acceptable range (< 6.5 or > 8.5)
        if random.random() > 0.5:
            pH = round(random.uniform(4.5, 6.4), 2)  # Acidic
        else:
            pH = round(random.uniform(8.6, 10.0), 2)  # Alkaline
        
        # Spectrum sensor: Bad water has low light transmission (below 50 triggers alert)
        # Analyzer flags < 50 as "Low light transmission - possible contamination"
        base_spectrum = random.uniform(20, 45)
        channels = {
            "A": round(base_spectrum + random.uniform(-10, 10), 2),
            "B": round(base_spectrum + random.uniform(-10, 10), 2),
            "C": round(base_spectrum + random.uniform(-10, 10), 2),
            "D": round(base_spectrum + random.uniform(-10, 10), 2),
            "E": round(base_spectrum + random.uniform(-10, 10), 2),
            "F": round(base_spectrum + random.uniform(-10, 10), 2),
        }
        # Ensure all channels are in contaminated range
        for key in channels:
            channels[key] = max(10, min(45, channels[key]))
        
        spectrum_average = round(sum(channels.values()) / len(channels), 2)
        spectrum_readings = random.randint(5, 10)
        
        payload = {
            "timestamp": datetime.now().isoformat(),
            "turbidity_sensor": {
                "voltage": voltage,
                "readings_count": readings_count
            },
            "pH": pH,
            "spectrum_sensor": {
                "channels": channels,
                "average": spectrum_average,
                "readings_count": spectrum_readings
            },
            "location": "test_simulator"
        }

        # Calculate actual NTU for display
        ntu = round((3.385 - voltage) / 0.00014, 1)
        
        print("\n📤 Sending BAD water quality payload (should trigger alert):")
        print(f"   Turbidity Voltage: {voltage}V → {ntu} NTU (>> 10 NTU critical threshold) ⚠️")
        print(f"   pH: {pH} (acceptable: 6.5-8.5) ⚠️")
        print(f"   Spectrum Average: {spectrum_average} (min: 50) ⚠️")
        
        result = self.mqtt_client.publish(MQTT_TOPIC, json.dumps(payload), qos=1)
        
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            print("   ✓ Published successfully")
        else:
            print(f"   ✗ Publish failed: {result.rc}")
    
    def send_moderately_bad_payload(self):
        """Send a payload with moderately bad water quality"""
        # Custom calibration: Moderate turbidity (50-500 NTU)
        # 3.30-3.37V → 100-600 NTU (above WHO 5 NTU but not critical)
        voltage = round(random.uniform(3.30, 3.37), 3)
        readings_count = random.randint(15, 25)
        
        # Moderately bad pH: at edge of acceptable range for drinking water
        if random.random() > 0.5:
            pH = round(random.uniform(6.5, 6.9), 2)  # Lower edge
        else:
            pH = round(random.uniform(8.1, 8.5), 2)  # Upper edge
        
        # Spectrum sensor: Moderate water has borderline light transmission (50-100)
        # Analyzer flags < 60 as "Light transmission below optimal range"
        base_spectrum = random.uniform(55, 90)
        channels = {
            "A": round(base_spectrum + random.uniform(-20, 20), 2),
            "B": round(base_spectrum + random.uniform(-20, 20), 2),
            "C": round(base_spectrum + random.uniform(-20, 20), 2),
            "D": round(base_spectrum + random.uniform(-20, 20), 2),
            "E": round(base_spectrum + random.uniform(-20, 20), 2),
            "F": round(base_spectrum + random.uniform(-20, 20), 2),
        }
        # Ensure all channels are in moderate range
        for key in channels:
            channels[key] = max(50, min(100, channels[key]))
        
        spectrum_average = round(sum(channels.values()) / len(channels), 2)
        spectrum_readings = random.randint(5, 10)
        
        payload = {
            "timestamp": datetime.now().isoformat(),
            "turbidity_sensor": {
                "voltage": voltage,
                "readings_count": readings_count
            },
            "pH": pH,
            "spectrum_sensor": {
                "channels": channels,
                "average": spectrum_average,
                "readings_count": spectrum_readings
            },
            "location": "test_simulator"
        }

        # Calculate actual NTU for display
        ntu = round((3.385 - voltage) / 0.00014, 1)
        
        print("\n📤 Sending MODERATELY BAD water quality payload:")
        print(f"   Turbidity Voltage: {voltage}V → {ntu} NTU (above WHO 5 NTU guideline) ⚠️")
        print(f"   pH: {pH} (acceptable range)")
        print(f"   Spectrum Average: {spectrum_average} (borderline: 50-100)")
        
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
        print("   Calibrated Sensor Reference:")
        print("   - 3.385V = 0 NTU (clean water baseline)")
        print("   - 3.38V = 35 NTU (good), 3.37V = 100 NTU (moderate)")
        print("   - 3.25V = 950 NTU (dirty), 3.245V = 1000 NTU (coffee)")
        print("   Formula: NTU = (3.385 - V) / 0.00014")
        print("   Spectrum Range: < 50 = contaminated, 50-400 = acceptable, 400-750 = good")
        try:
            voltage = float(input("   Enter turbidity voltage (2.5-3.5V, e.g., 3.38): "))
            readings_count = int(input("   Enter readings count (e.g., 20): "))
            pH = float(input("   Enter pH (0-14, e.g., 7.2): "))
            spectrum_avg = float(input("   Enter spectrum average (e.g., 500): "))

            # Generate channels around the average
            channels = {
                "A": round(spectrum_avg + random.uniform(-50, 50), 2),
                "B": round(spectrum_avg + random.uniform(-50, 50), 2),
                "C": round(spectrum_avg + random.uniform(-50, 50), 2),
                "D": round(spectrum_avg + random.uniform(-50, 50), 2),
                "E": round(spectrum_avg + random.uniform(-50, 50), 2),
                "F": round(spectrum_avg + random.uniform(-50, 50), 2),
            }
            
            payload = {
                "timestamp": datetime.now().isoformat(),
                "turbidity_sensor": {
                    "voltage": voltage,
                    "readings_count": readings_count
                },
                "pH": pH,
                "spectrum_sensor": {
                    "channels": channels,
                    "average": spectrum_avg,
                    "readings_count": 6
                },
                "location": "test_simulator"
            }

            # Calculate actual NTU for display
            ntu = round((3.385 - voltage) / 0.00014, 1)
            
            print(f"\n📤 Sending custom payload:")
            print(f"   Turbidity Voltage: {voltage}V → {ntu} NTU")
            print(f"   pH: {pH}")
            print(f"   Spectrum Average: {spectrum_avg}")
            
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
