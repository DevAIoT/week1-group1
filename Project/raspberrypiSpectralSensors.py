#!/usr/bin/env python3
"""
Raspberry Pi - Water Quality MQTT Publisher
- Reads spectral sensor data via serial
- Publishes sensor data to MQTT broker
"""

import serial
import time
import json
import paho.mqtt.client as mqtt
from datetime import datetime
import sys

# Serial Configuration
SERIAL_PORT = '/dev/ttyUSB0'  # Single port for both sensors
BAUD_RATE = 9600

# MQTT Configuration
MQTT_BROKER = "192.168.1.103"  # MQTT broker IP
MQTT_PORT = 1883
MQTT_TOPIC = "group1/water_quality"
MQTT_CLIENT_ID = "group1_raspberry_pi"

# Publish interval
PUBLISH_INTERVAL = 10  # seconds

class WaterQualityPublisher:
    def __init__(self):
        self.spectrum_readings = []  # Store multiple readings for averaging
        
        # Initialize serial connection
        self.setup_serial()
        
        # Initialize MQTT client
        self.setup_mqtt()
    
    def setup_serial(self):
        """Connect to serial port for both sensors"""
        try:
            self.ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=2)
            time.sleep(2)  # Wait for device to reset
            print(f"✓ Connected to serial port on {SERIAL_PORT}")
        except serial.SerialException as e:
            print(f"✗ Error connecting to serial port: {e}")
            sys.exit(1)
    

    
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
    
    def read_sensor_data(self):
        """Read spectral sensor data from serial port and accumulate readings"""
        try:
            if self.ser.in_waiting > 0:
                line = self.ser.readline().decode('utf-8').strip()
                # Expected format: {"A":123.45,"B":234.56,...,"spectrum":180.23}
                if line.startswith('{'):
                    data = json.loads(line)
                    
                    # Check if this is status/error message
                    if 'status' in data or 'error' in data:
                        print(f"ℹ️  {data}")
                        return False
                    
                    # Check if we have spectral data
                    if 'A' in data and 'spectrum' in data:
                        self.spectrum_readings.append(data)
                        print(f"📊 Reading #{len(self.spectrum_readings)}: A={data['A']:.2f}, B={data['B']:.2f}, C={data['C']:.2f}, Avg={data['spectrum']:.2f}")
                        return True
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            print(f"Error reading sensor data: {e}")
        return False
    

    def publish_data(self):
        """Calculate average of all readings and publish to MQTT broker"""
        if not self.spectrum_readings:
            print("⏳ Waiting for spectral sensor data...")
            return
        
        # Calculate average of all readings
        num_readings = len(self.spectrum_readings)
        avg_channels = {
            'A': sum(r['A'] for r in self.spectrum_readings) / num_readings,
            'B': sum(r['B'] for r in self.spectrum_readings) / num_readings,
            'C': sum(r['C'] for r in self.spectrum_readings) / num_readings,
            'D': sum(r['D'] for r in self.spectrum_readings) / num_readings,
            'E': sum(r['E'] for r in self.spectrum_readings) / num_readings,
            'F': sum(r['F'] for r in self.spectrum_readings) / num_readings
        }
        avg_spectrum = sum(r['spectrum'] for r in self.spectrum_readings) / num_readings
        
        payload = {
            "timestamp": datetime.now().isoformat(),
            "sensor_type": "AS7265X_Spectral",
            "channels": {
                "A": round(avg_channels['A'], 2),
                "B": round(avg_channels['B'], 2),
                "C": round(avg_channels['C'], 2),
                "D": round(avg_channels['D'], 2),
                "E": round(avg_channels['E'], 2),
                "F": round(avg_channels['F'], 2)
            },
            "spectrum_average": round(avg_spectrum, 2),
            "readings_count": num_readings,
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
                print(f"✓ Published average of {num_readings} readings: Spectrum Avg={avg_spectrum:.2f}")
                # Clear readings after successful publish
                self.spectrum_readings = []
            else:
                print(f"✗ Publish failed: {result.rc}")
        except Exception as e:
            print(f"✗ Error publishing: {e}")
    
    def run(self):
        """Main publishing loop"""
        print("=" * 60)
        print("Spectral Sensor MQTT Publisher Started")
        print("=" * 60)
        print(f"Publishing to topic: {MQTT_TOPIC}")
        print(f"Interval: {PUBLISH_INTERVAL} seconds")
        print("Press Ctrl+C to stop\n")
        
        last_publish = 0
        
        try:
            while True:
                # Continuously read from serial port
                self.read_sensor_data()
                
                # Publish data at specified interval
                current_time = time.time()
                if current_time - last_publish >= PUBLISH_INTERVAL:
                    self.publish_data()
                    last_publish = current_time
                
                time.sleep(0.1)  # Small delay to prevent CPU overuse
                
        except KeyboardInterrupt:
            print("\n\nShutting down publisher...")
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
            if self.ser:
                self.ser.close()
            print("Goodbye!")

if __name__ == "__main__":
    publisher = WaterQualityPublisher()
    publisher.run()