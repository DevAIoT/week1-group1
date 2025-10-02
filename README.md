# Water Quality Monitoring System

## System Architecture

```
Arduino (Turbidity) → Raspberry Pi (Publisher) → MQTT Broker
                            ↓
                    Light Sensor (on Pi)
                            ↓
                      [MQTT Broker]
                            ↓
                   Compute Node (Subscriber) → Email Alerts
```

## Components

1. **Arduino**: Reads turbidity sensor, sends to Pi via serial
2. **Raspberry Pi**: Reads Arduino + light sensor, publishes to MQTT
3. **Compute Node**: Subscribes to MQTT, sends email alerts

---

## Installation Steps

### 1. Setup MQTT Broker (Mosquitto)

**On any machine (can be the Pi or compute node):**

```bash
# Install Mosquitto
sudo apt-get update
sudo apt-get install mosquitto mosquitto-clients

# Start broker
sudo systemctl start mosquitto
sudo systemctl enable mosquitto

# Test broker
mosquitto_sub -h localhost -t test &
mosquitto_pub -h localhost -t test -m "Hello MQTT"
```

**Find broker IP:**
```bash
hostname -I
```

---

### 2. Setup Arduino

1. Upload `arduino_turbidity.ino` to your Arduino
2. Connect turbidity sensor to pin A0
3. Connect Arduino to Raspberry Pi via USB

---

### 3. Setup Raspberry Pi (Publisher)

**Install dependencies:**
```bash
sudo apt-get install python3-pip
pip3 install pyserial paho-mqtt

# If using ADC (MCP3008):
pip3 install spidev

# Enable SPI
sudo raspi-config
# → Interface Options → SPI → Enable

# If using I2C sensor (TSL2561):
pip3 install adafruit-circuitpython-tsl2561

# Enable I2C
sudo raspi-config
# → Interface Options → I2C → Enable
```

**Hardware connections:**
- Arduino USB → Raspberry Pi USB port
- Light sensor:
  - **Option A - ADC (MCP3008):** Connect via SPI
  - **Option B - I2C sensor:** Connect via I2C pins

**Configure and run:**
```bash
# Edit the Python script
nano raspberry_pi_publisher.py

# Update these values:
# - ARDUINO_PORT (check with: ls /dev/ttyUSB* /dev/ttyACM*)
# - MQTT_BROKER (IP address of broker)
# - USE_ADC (True for MCP3008, False for I2C)

# Run publisher
python3 raspberry_pi_publisher.py
```

---

### 4. Setup Compute Node (Subscriber)

**On your local machine (laptop/desktop/another Pi):**

```bash
# Install dependencies
pip3 install paho-mqtt requests

# Get Resend API key
# 1. Sign up at https://resend.com
# 2. Create API key in dashboard
# 3. Copy key

# Configure script
nano compute_node_subscriber.py

# Update these values:
# - MQTT_BROKER (IP of your broker)
# - RESEND_API_KEY (from resend.com)
# - SENDER_EMAIL (use onboarding@resend.dev for testing)
# - RECIPIENT_EMAIL (your email)
# - Thresholds if needed

# Run subscriber
python3 compute_node_subscriber.py
```

---

## Testing the System

### Test MQTT Connection
```bash
# Subscribe to the topic
mosquitto_sub -h <BROKER_IP> -t water/quality -v

# You should see messages like:
# water/quality {"timestamp":"2025-10-02T10:30:00","turbidity":2.5,"light_intensity":450.0,"location":"raspberry_pi_1"}
```

### Test with Manual Publish
```bash
mosquitto_pub -h <BROKER_IP> -t water/quality -m '{"turbidity":10.5,"light_intensity":30.0}'
```
This should trigger an email alert!

---

## Running as Services (Auto-start on boot)

### Raspberry Pi Publisher Service

```bash
sudo nano /etc/systemd/system/water-publisher.service
```

Add:
```ini
[Unit]
Description=Water Quality MQTT Publisher
After=network.target mosquitto.service

[Service]
ExecStart=/usr/bin/python3 /home/pi/raspberry_pi_publisher.py
WorkingDirectory=/home/pi
StandardOutput=inherit
StandardError=inherit
Restart=always
User=pi

[Install]
WantedBy=multi-user.target
```

Enable:
```bash
sudo systemctl daemon-reload
sudo systemctl enable water-publisher.service
sudo systemctl start water-publisher.service

# Check status
sudo systemctl status water-publisher.service

# View logs
sudo journalctl -u water-publisher.service -f
```

### Compute Node Subscriber Service

Same process on compute node:
```bash
sudo nano /etc/systemd/system/water-subscriber.service
```

```ini
[Unit]
Description=Water Quality MQTT Subscriber
After=network.target

[Service]
ExecStart=/usr/bin/python3 /home/user/compute_node_subscriber.py
WorkingDirectory=/home/user
StandardOutput=inherit
StandardError=inherit
Restart=always
User=user

[Install]
WantedBy=multi-user.target
```

---

## Monitoring & Troubleshooting

### Check MQTT broker status
```bash
sudo systemctl status mosquitto
```

### Monitor MQTT traffic
```bash
mosquitto_sub -h <BROKER_IP> -t '#' -v
```

### Check publisher logs
```bash
# If running as service
sudo journalctl -u water-publisher.service -f

# If running manually, check terminal output
```

### Common Issues

**"Connection refused" on MQTT:**
- Check broker is running: `sudo systemctl status mosquitto`
- Check firewall: `sudo ufw allow 1883`
- Verify broker IP is correct

**No data from Arduino:**
- Check serial port: `ls /dev/ttyUSB* /dev/ttyACM*`
- Test serial: `cat /dev/ttyUSB0` (should see JSON data)
- Check Arduino Serial Monitor first

**Light sensor not working:**
- Verify connections
- Check if SPI/I2C is enabled
- Test with simple read script

**Email not sending:**
- Verify Resend API key
- Check API key permissions
- Test with curl:
```bash
curl -X POST 'https://api.resend.com/emails' \
  -H 'Authorization: Bearer YOUR_KEY' \
  -H 'Content-Type: application/json' \
  -d '{"from":"onboarding@resend.dev","to":"you@example.com","subject":"Test","text":"Test"}'
```

---

## Calibration

### Turbidity Sensor
1. Test with clean distilled water (should read ~0 NTU)
2. Test with known turbid water samples
3. Adjust formula in Arduino code if needed

### Light Sensor
1. Test in clean water with consistent light source
2. Note baseline reading
3. Adjust `LIGHT_INTENSITY_MIN` and `LIGHT_INTENSITY_MAX` in compute node

---

## Data Flow Summary

1. **Arduino** reads turbidity every 5 seconds → sends JSON via serial
2. **Raspberry Pi** reads serial + light sensor → publishes to MQTT every 10 seconds
3. **MQTT Broker** receives and distributes messages
4. **Compute Node** subscribes → analyzes data → sends email if dirty water detected

---

## System Diagram

```
┌─────────────┐
│   Arduino   │
│  Turbidity  │
└──────┬──────┘
       │ USB/Serial
       ↓
┌─────────────────────┐       ┌──────────────┐
│   Raspberry Pi      │       │ MQTT Broker  │
│  - Serial Reader    │◄─────►│  (Mosquitto) │
│  - Light Sensor     │ WiFi  │              │
│  - MQTT Publisher   │       └──────┬───────┘
└─────────────────────┘              │
                                     │ WiFi/Network
                                     ↓
                              ┌──────────────┐
                              │ Compute Node │
                              │ - Subscriber │
                              │ - Analyzer   │
                              │ - Email Alert│
                              └──────────────┘
```