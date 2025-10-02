#!/usr/bin/env python3
"""
Compute Node - Water Quality MQTT Subscriber
- Subscribes to MQTT broker for water quality data
- Analyzes data for water quality issues
- Sends email alerts when water is dirty
"""

import paho.mqtt.client as mqtt
import json
import time
import requests
from datetime import datetime
import os
# MQTT Configuration
MQTT_BROKER = os.environ.get('MQTT_BROKER', '192.168.1.103')
MQTT_PORT = int(os.environ.get('MQTT_PORT', 1883))
MQTT_TOPIC = os.environ.get('MQTT_TOPIC', 'group1/water_quality')
MQTT_CLIENT_ID = os.environ.get('MQTT_CLIENT_ID', 'group1_compute_node')

# Resend API Configuration
RESEND_API_KEY = os.environ.get('RESEND_API_KEY', 'your_resend_api_key_here')
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'onboarding@resend.dev')
RECIPIENT_EMAIL = os.environ.get('RECIPIENT_EMAIL', 'chongyong321@gmail.com')

# Water quality thresholds
TURBIDITY_THRESHOLD = float(os.environ.get('TURBIDITY_THRESHOLD', 5.0))  # NTU
                           # Clean water: < 1 NTU
                           # Slightly turbid: 1-5 NTU
                           # Dirty water: > 5 NTU

LIGHT_INTENSITY_MIN = int(os.environ.get('LIGHT_INTENSITY_MIN', 50))   # Minimum acceptable light intensity
LIGHT_INTENSITY_MAX = int(os.environ.get('LIGHT_INTENSITY_MAX', 800))  # Maximum acceptable light intensity

# Alert cooldown to prevent spam
ALERT_COOLDOWN = int(os.environ.get('ALERT_COOLDOWN', 3600))  # seconds (1 hour)
last_alert_time = 0

class WaterQualitySubscriber:
    def __init__(self):
        self.setup_mqtt()
    
    def setup_mqtt(self):
        """Initialize MQTT client"""
        self.mqtt_client = mqtt.Client(MQTT_CLIENT_ID)
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message
        self.mqtt_client.on_disconnect = self.on_disconnect
        
        try:
            print(f"Connecting to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}...")
            self.mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        except Exception as e:
            print(f"✗ Error connecting to MQTT broker: {e}")
            print("Make sure the broker is running and accessible")
            exit(1)
    
    def on_connect(self, client, userdata, flags, rc):
        """Callback when connected to MQTT broker"""
        if rc == 0:
            print(f"✓ Connected to MQTT broker")
            print(f"✓ Subscribing to topic: {MQTT_TOPIC}")
            client.subscribe(MQTT_TOPIC, qos=1)
        else:
            print(f"✗ Failed to connect, return code: {rc}")
    
    def on_disconnect(self, client, userdata, rc):
        """Callback when disconnected from MQTT broker"""
        if rc != 0:
            print("⚠ Unexpected disconnection from MQTT broker")
            print("Attempting to reconnect...")
    
    def on_message(self, client, userdata, msg):
        """Callback when message is received"""
        try:
            # Parse JSON payload
            payload = json.loads(msg.payload.decode('utf-8'))
            
            timestamp = payload.get('timestamp', datetime.now().isoformat())
            turbidity = payload.get('turbidity')
            light_intensity = payload.get('light_intensity')
            location = payload.get('location', 'unknown')
            
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Received data from {location}:")
            print(f"  Turbidity: {turbidity:.2f} NTU")
            print(f"  Light Intensity: {light_intensity:.2f}")
            
            # Check water quality
            issues = self.check_water_quality(turbidity, light_intensity)
            
            if issues:
                print("  ⚠️  DIRTY WATER DETECTED!")
                for issue in issues:
                    print(f"     - {issue}")
                
                # Send alert email
                self.send_alert_email(turbidity, light_intensity, issues, location)
                
                # Log to file
                self.log_alert(timestamp, turbidity, light_intensity, issues, location)
            else:
                print("  ✓ Water quality OK")
            
        except json.JSONDecodeError as e:
            print(f"✗ Error parsing message: {e}")
        except Exception as e:
            print(f"✗ Error processing message: {e}")
    
    def check_water_quality(self, turbidity, light_intensity):
        """Analyze water quality and return list of issues"""
        issues = []
        
        if turbidity is not None:
            if turbidity > TURBIDITY_THRESHOLD:
                level = "severely" if turbidity > 10 else "moderately"
                issues.append(
                    f"Water is {level} turbid ({turbidity:.2f} NTU, "
                    f"threshold: {TURBIDITY_THRESHOLD})"
                )
        
        if light_intensity is not None:
            if light_intensity < LIGHT_INTENSITY_MIN:
                issues.append(
                    f"Low light transmission ({light_intensity:.2f}, "
                    f"minimum: {LIGHT_INTENSITY_MIN}) - water may be "
                    f"discolored or contaminated"
                )
            elif light_intensity > LIGHT_INTENSITY_MAX:
                issues.append(
                    f"Abnormal light reading ({light_intensity:.2f}, "
                    f"max: {LIGHT_INTENSITY_MAX})"
                )
        
        return issues
    
    def send_alert_email(self, turbidity, light_intensity, issues, location):
        """Send email alert using Resend API"""
        global last_alert_time
        
        current_time = time.time()
        if current_time - last_alert_time < ALERT_COOLDOWN:
            remaining = int((ALERT_COOLDOWN - (current_time - last_alert_time)) / 60)
            print(f"  ⏳ Alert cooldown active ({remaining} min remaining)")
            return
        
        try:
            url = "https://api.resend.com/emails"
            
            # Create email body
            body_text = f"""Water Quality Alert
==================
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Location: {location}

Current Readings:
- Turbidity: {turbidity:.2f} NTU
- Light Intensity: {light_intensity:.2f}

Issues Detected:
"""
            for issue in issues:
                body_text += f"• {issue}\n"
            
            body_text += """
Recommended Actions:
1. Inspect the water source immediately
2. Check filtration systems
3. Test for contamination if turbidity remains high
4. Review recent maintenance logs

---
This is an automated alert from your Water Quality Monitoring System.
Next alert will be sent after cooldown period (1 hour).
"""
            
            payload = {
                "from": SENDER_EMAIL,
                "to": [RECIPIENT_EMAIL],
                "subject": f"⚠️ Water Quality Alert - {location}",
                "text": body_text
            }
            
            headers = {
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(url, json=payload, headers=headers)
            
            if response.status_code == 200:
                print("  ✓ Alert email sent successfully")
                last_alert_time = current_time
            else:
                print(f"  ✗ Email error: {response.status_code} - {response.text}")
            
        except Exception as e:
            print(f"  ✗ Error sending email: {e}")
    
    def log_alert(self, timestamp, turbidity, light_intensity, issues, location):
        """Log alert to file"""
        log_entry = {
            'timestamp': timestamp,
            'location': location,
            'turbidity': turbidity,
            'light_intensity': light_intensity,
            'issues': issues,
            'alert_sent': True
        }
        
        try:
            with open('water_quality_alerts.json', 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
        except Exception as e:
            print(f"  ⚠ Could not write to log file: {e}")
    
    def run(self):
        """Start the subscriber"""
        print("=" * 60)
        print("Water Quality MQTT Subscriber - Compute Node")
        print("=" * 60)
        print(f"Broker: {MQTT_BROKER}:{MQTT_PORT}")
        print(f"Topic: {MQTT_TOPIC}")
        print(f"Turbidity threshold: {TURBIDITY_THRESHOLD} NTU")
        print(f"Light range: {LIGHT_INTENSITY_MIN}-{LIGHT_INTENSITY_MAX}")
        print(f"Alert cooldown: {ALERT_COOLDOWN/60:.0f} minutes")
        print("\nWaiting for messages... (Press Ctrl+C to stop)\n")
        
        try:
            # Start the MQTT loop
            self.mqtt_client.loop_forever()
            
        except KeyboardInterrupt:
            print("\n\nShutting down subscriber...")
            self.mqtt_client.disconnect()
            print("Goodbye!")

if __name__ == "__main__":
    subscriber = WaterQualitySubscriber()
    subscriber.run()