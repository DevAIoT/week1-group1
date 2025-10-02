#!/usr/bin/env python3
"""
Raspberry Pi - Water Quality MQTT Publisher
- Reads turbidity data from Arduino via serial
- Reads spectral sensor data from SparkFun RedBoard via serial
- Publishes combined data to MQTT broker
"""

import serial
import time
import json
import paho.mqtt.client as mqtt
from datetime import datetime
import sys

# Serial Configuration
ARDUINO_PORT = '/dev/ttyUSB0'  # Arduino with turbidity sensor
SPARKFUN_PORT = '/dev/ttyUSB1'  # SparkFun RedBoard with spectral sensor
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
        self.turbidity = None
        self.spectrum_sensor = None
        
        # Initialize serial connections to both boards
        self.setup_serial()
        
        # Initialize MQTT client
        self.setup_mqtt()
    
    def setup_serial(self):
        """Connect to Arduino and SparkFun RedBoard"""
        # Connect to Arduino (Turbidity Sensor)
        try:
            self.arduino_ser = serial.Serial(ARDUINO_PORT, BAUD_RATE, timeout=2)
            time.sleep(2)  # Wait for Arduino to reset
            print(f"✓ Connected to Arduino on {ARDUINO_PORT}")
        except serial.SerialException as e:
            print(f"✗ Error connecting to Arduino: {e}")
            sys.exit(1)
        
        # Connect to SparkFun RedBoard (Spectral Sensor)
        try:
            self.sparkfun_ser = serial.Serial(SPARKFUN_PORT, BAUD_RATE, timeout=2)
            time.sleep(2)  # Wait for SparkFun to reset
            print(f"✓ Connected to SparkFun RedBoard on {SPARKFUN_PORT}")
        except serial.SerialException as e:
            print(f"✗ Error connecting to SparkFun RedBoard: {e}")
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
    
    def read_arduino_turbidity(self):
        """Read turbidity data from Arduino"""
        try:
            if self.arduino_ser.in_waiting > 0:
                line = self.arduino_ser.readline().decode('utf-8').strip()
                # Expected format: {"turbidity":2.5}
                if line.startswith('{'):
                    data = json.loads(line)
                    if 'turbidity' in data:
                        self.turbidity = data['turbidity']
                        return True
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            print(f"Error reading Arduino: {e}")
        return False
    
    def read_sparkfun_spectrum(self):
        """Read spectral sensor data from SparkFun RedBoard"""
        try:
            if self.sparkfun_ser.in_waiting > 0:
                line = self.sparkfun_ser.readline().decode('utf-8').strip()
                # Expected format: {"spectrum":123.45} or {"spectral":123.45}
                if line.startswith('{'):
                    data = json.loads(line)
                    # Check for various possible key names
                    if 'spectrum' in data:
                        self.spectrum_sensor = data['spectrum']
                        return True
                    elif 'spectral' in data:
                        self.spectrum_sensor = data['spectral']
                        return True
                    elif 'spectrum_sensor' in data:
                        self.spectrum_sensor = data['spectrum_sensor']
                        return True
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            print(f"Error reading SparkFun: {e}")
        return False
    

    
    def publish_data(self):
        """Publish sensor data to MQTT broker"""
        if self.turbidity is None or self.spectrum_sensor is None:
            print("⏳ Waiting for sensor data...")
            return
        
        payload = {
            "timestamp": datetime.now().isoformat(),
            "turbidity_sensor": round(self.turbidity, 2),
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
                print(f"✓ Published: Turbidity={self.turbidity:.2f} NTU, Spectrum={self.spectrum_sensor:.2f}")
            else:
                print(f"✗ Publish failed: {result.rc}")
        except Exception as e:
            print(f"✗ Error publishing: {e}")
    
    def run(self):
        """Main publishing loop"""
        print("=" * 60)
        print("Water Quality MQTT Publisher Started")
        print("=" * 60)
        print(f"Publishing to topic: {MQTT_TOPIC}")
        print(f"Interval: {PUBLISH_INTERVAL} seconds")
        print("Press Ctrl+C to stop\n")
        
        last_publish = 0
        
        try:
            while True:
                # Continuously read from both Arduino and SparkFun
                self.read_arduino_turbidity()
                self.read_sparkfun_spectrum()
                
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
            if self.arduino_ser:
                self.arduino_ser.close()
            if self.sparkfun_ser:
                self.sparkfun_ser.close()
            print("Goodbye!")

if __name__ == "__main__":
    publisher = WaterQualityPublisher()
    publisher.run()