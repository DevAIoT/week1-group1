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
        self.spectrum_sensor = None
        
        # Initialize serial connections to both boards
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
        """Read spectral sensor data from serial port"""
        try:
            if self.ser.in_waiting > 0:
                line = self.ser.readline().decode('utf-8').strip()
                # Expected format: {"spectrum":123.45}
                if line.startswith('{'):
                    data = json.loads(line)
                    
                    # Update spectrum if present
                    if 'spectrum' in data:
                        self.spectrum_sensor = data['spectrum']
                        print(f"📊 Received spectrum: {self.spectrum_sensor}")
                        return True
                    elif 'spectral' in data:
                        self.spectrum_sensor = data['spectral']
                        print(f"📊 Received spectrum: {self.spectrum_sensor}")
                        return True
                    elif 'spectrum_sensor' in data:
                        self.spectrum_sensor = data['spectrum_sensor']
                        print(f"📊 Received spectrum: {self.spectrum_sensor}")
                        return True
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            print(f"Error reading sensor data: {e}")
        return False
    

    
    def publish_data(self):
        """Publish sensor data to MQTT broker"""
        if self.spectrum_sensor is None:
            print("⏳ Waiting for spectral sensor data...")
            return
        
        payload = {
            "timestamp": datetime.now().isoformat(),
            "spectrum_sensor": round(self.spectrum_sensor, 2),
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
                print(f"✓ Published: Spectrum={self.spectrum_sensor:.2f}")
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