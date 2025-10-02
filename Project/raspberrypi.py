#!/usr/bin/env python3
"""
Raspberry Pi - Water Quality MQTT Publisher
- Reads turbidity data from Arduino via serial
- Reads light/spectral sensor directly connected to Pi
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
BAUD_RATE = 9600

# Light/Spectral Sensor Configuration (connected directly to Pi)
# If using I2C sensor (like TSL2561), adjust accordingly
# For this example, we'll use a simple ADC approach
USE_ADC = True  # Set to True if using MCP3008 or similar ADC

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
        self.light_intensity = None
        
        # Initialize serial connection to Arduino
        self.setup_serial()
        
        # Initialize light sensor
        self.setup_light_sensor()
        
        # Initialize MQTT client
        self.setup_mqtt()
    
    def setup_serial(self):
        """Connect to Arduino"""
        try:
            self.ser = serial.Serial(ARDUINO_PORT, BAUD_RATE, timeout=2)
            time.sleep(2)  # Wait for Arduino to reset
            print(f"✓ Connected to Arduino on {ARDUINO_PORT}")
        except serial.SerialException as e:
            print(f"✗ Error connecting to Arduino: {e}")
            sys.exit(1)
    
    def setup_light_sensor(self):
        """Initialize light/spectral sensor"""
        if USE_ADC:
            try:
                # Using MCP3008 ADC with SPI
                import spidev
                self.spi = spidev.SpiDev()
                self.spi.open(0, 0)  # Bus 0, Device 0
                self.spi.max_speed_hz = 1350000
                print("✓ Light sensor (ADC) initialized")
            except Exception as e:
                print(f"⚠ Warning: Could not initialize ADC: {e}")
                print("  Install with: pip3 install spidev")
                self.spi = None
        else:
            # Using I2C sensor (example: TSL2561)
            try:
                import board
                import adafruit_tsl2561
                i2c = board.I2C()
                self.light_sensor = adafruit_tsl2561.TSL2561(i2c)
                print("✓ Light sensor (I2C) initialized")
            except Exception as e:
                print(f"⚠ Warning: Could not initialize I2C sensor: {e}")
                print("  Install with: pip3 install adafruit-circuitpython-tsl2561")
                self.light_sensor = None
    
    def setup_mqtt(self):
        """Initialize MQTT client"""
        self.mqtt_client = mqtt.Client(MQTT_CLIENT_ID)
        self.mqtt_client.on_connect = self.on_mqtt_connect
        self.mqtt_client.on_disconnect = self.on_mqtt_disconnect
        
        try:
            self.mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
            self.mqtt_client.loop_start()
            print(f"✓ Connecting to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}")
        except Exception as e:
            print(f"✗ Error connecting to MQTT broker: {e}")
            sys.exit(1)
    
    def on_mqtt_connect(self, client, userdata, flags, rc):
        """Callback when connected to MQTT broker"""
        if rc == 0:
            print("✓ Connected to MQTT broker")
        else:
            print(f"✗ Failed to connect to MQTT broker, code: {rc}")
    
    def on_mqtt_disconnect(self, client, userdata, rc):
        """Callback when disconnected from MQTT broker"""
        print("⚠ Disconnected from MQTT broker")
    
    def read_arduino_turbidity(self):
        """Read turbidity data from Arduino"""
        try:
            if self.ser.in_waiting > 0:
                line = self.ser.readline().decode('utf-8').strip()
                # Expected format: {"turbidity":2.5}
                if line.startswith('{'):
                    data = json.loads(line)
                    if 'turbidity' in data:
                        self.turbidity = data['turbidity']
                        return True
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            print(f"Error reading Arduino: {e}")
        return False
    
    def read_light_sensor_adc(self):
        """Read light sensor via ADC (MCP3008)"""
        if not self.spi:
            return None
        
        try:
            # Read from channel 0 of MCP3008
            channel = 0
            adc = self.spi.xfer2([1, (8 + channel) << 4, 0])
            data = ((adc[1] & 3) << 8) + adc[2]
            
            # Convert to light intensity (0-1023 range)
            # Adjust conversion based on your sensor
            voltage = data * 3.3 / 1023.0
            
            # For photoresistor with 10K pulldown
            if voltage > 0:
                resistance = (3.3 - voltage) * 10000.0 / voltage
                light_intensity = 500000.0 / resistance
            else:
                light_intensity = 0
            
            return light_intensity
        except Exception as e:
            print(f"Error reading ADC: {e}")
            return None
    
    def read_light_sensor_i2c(self):
        """Read light sensor via I2C (TSL2561)"""
        if not hasattr(self, 'light_sensor') or not self.light_sensor:
            return None
        
        try:
            # Read lux value
            lux = self.light_sensor.lux
            return lux if lux is not None else 0
        except Exception as e:
            print(f"Error reading I2C sensor: {e}")
            return None
    
    def read_light_sensor(self):
        """Read light/spectral sensor"""
        if USE_ADC:
            self.light_intensity = self.read_light_sensor_adc()
        else:
            self.light_intensity = self.read_light_sensor_i2c()
    
    def publish_data(self):
        """Publish sensor data to MQTT broker"""
        if self.turbidity is None or self.light_intensity is None:
            print("⏳ Waiting for sensor data...")
            return
        
        payload = {
            "timestamp": datetime.now().isoformat(),
            "turbidity": round(self.turbidity, 2),
            "light_intensity": round(self.light_intensity, 2),
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
                print(f"✓ Published: Turbidity={self.turbidity:.2f} NTU, Light={self.light_intensity:.2f}")
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
                # Continuously read from Arduino
                self.read_arduino_turbidity()
                
                # Read light sensor
                current_time = time.time()
                if current_time - last_publish >= PUBLISH_INTERVAL:
                    self.read_light_sensor()
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
    # Check for alternative simple mode (simulated sensor for testing)
    if len(sys.argv) > 1 and sys.argv[1] == "--simulate":
        print("Running in simulation mode...")
        USE_ADC = False
        
    publisher = WaterQualityPublisher()
    publisher.run()