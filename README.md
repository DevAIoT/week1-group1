# Water Quality Monitoring System

Real-time water quality monitoring with IoT sensors and live dashboard visualization.

## System Architecture

```
Arduino (Turbidity) → Raspberry Pi (Publisher) → MQTT Broker (192.168.1.103:1883)
                            ↓                            ↓
            AS7265X Spectral Sensor (on Pi)    WebSocket Bridge Server
                                                         ↓
                                                  Next.js Dashboard
                                                  (Live Visualization)
```

## Components

1. **Arduino**: Reads turbidity sensor, sends data to Pi via serial
2. **Raspberry Pi**: Reads Arduino data + spectral sensor, publishes to MQTT broker
3. **MQTT Broker**: Central message broker at `192.168.1.103:1883`
4. **WebSocket Bridge**: Python FastAPI server that bridges MQTT to WebSocket
5. **Dashboard**: Next.js web application with real-time data visualization

---

## Quick Start Guide

### Prerequisites
- MQTT Broker running at `192.168.1.103:1883` (Mosquitto)
- Python 3.8+ with pip
- Node.js 18+ with npm
- Arduino with turbidity sensor
- Raspberry Pi with spectral sensor module

### 1. Setup WebSocket Bridge Server

The bridge server connects to the MQTT broker and exposes WebSocket endpoint for the dashboard.

```bash
cd Project

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment (optional)
export MQTT_BROKER=192.168.1.103
export MQTT_PORT=1883
export MQTT_TOPIC=group1/water_quality

# Run the bridge server
python websocket_bridge.py
```

The bridge will be available at `http://localhost:8000` with WebSocket at `ws://localhost:8000/ws`

### 2. Setup Dashboard

```bash
cd dashboard

# Install dependencies
npm install

# Configure environment
# Edit .env.local to set:
# NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws

# Run development server
npm run dev
```

Open http://localhost:3000 in your browser to see the live dashboard.

### 3. Setup Raspberry Pi Publisher

```bash
# On Raspberry Pi
pip3 install pyserial paho-mqtt

# Edit configuration in raspberrypi.py
nano raspberrypi.py

# Update:
# - ARDUINO_PORT (check with: ls /dev/ttyUSB* /dev/ttyACM*)
# - MQTT_BROKER (192.168.1.103)

# Run publisher
python3 raspberrypi.py
```

---

## Testing the System

### 1. Test WebSocket Bridge
Visit http://localhost:8000 to see bridge status and active connections.

### 2. Simulate Sensor Data
```bash
cd Project
python simulate_sensor_data.py
```
This publishes test data to the MQTT broker.

### 3. Monitor MQTT Traffic
```bash
mosquitto_sub -h 192.168.1.103 -t group1/water_quality -v
```

You should see messages like:
```json
{
  "timestamp": "2025-10-02T10:30:00",
  "location": "raspberry_pi_1",
  "turbidity": 2.5,
  "spectrum": {
    "sensor_type": "AS7265X_Spectral",
    "channels": {
      "A": 174.2,
      "B": 240.1,
      "C": 20.7,
      "D": 392.0,
      "E": 82.3,
      "F": 37.5
    },
    "average": 157.8,
    "readings_count": 6
  }
}
```

---

## Project Structure

```
week1-group1/
├── Project/
│   ├── websocket_bridge.py      # WebSocket bridge server (FastAPI)
│   ├── raspberrypi.py            # Raspberry Pi publisher
│   ├── simulate_sensor_data.py  # Test data simulator
│   ├── requirements.txt          # Python dependencies
│   └── venv/                     # Virtual environment
├── dashboard/
│   ├── src/
│   │   ├── app/                  # Next.js pages
│   │   ├── components/           # React components
│   │   │   └── WaterQualityDashboard.tsx
│   │   ├── hooks/
│   │   │   └── useMQTTWaterQuality.ts  # WebSocket hook
│   │   ├── lib/
│   │   │   └── water-quality-analyzer.ts
│   │   └── types/
│   │       └── water-quality.ts
│   ├── .env.local                # Environment variables
│   └── package.json
└── README.md

---

## Configuration Files

### `.env.local` (Dashboard)
```bash
# WebSocket Bridge URL
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws

# MQTT Topic (for reference)
NEXT_PUBLIC_MQTT_TOPIC=group1/water_quality
```

### Environment Variables (Bridge Server)
```bash
export MQTT_BROKER=192.168.1.103  # MQTT broker IP
export MQTT_PORT=1883              # MQTT broker port
export MQTT_TOPIC=group1/water_quality
export MQTT_CLIENT_ID=websocket_bridge
```

---

## Dashboard Features

- **Real-time Monitoring**: Live updates via WebSocket
- **Water Quality Status**: Overall quality score with color-coded indicators
- **Metrics Display**: 
  - Turbidity levels (NTU)
  - Spectral intensity averages and channel breakdowns
- **Historical Trends**: Line chart showing last 20 readings
- **Alert System**: Visual alerts for water quality issues
- **Connection Status**: Shows WebSocket connection state

### Water Quality Thresholds

- **Turbidity**: 
  - Clean: < 1 NTU
  - Slightly turbid: 1-5 NTU
  - Dirty: > 5 NTU
- **Spectral Intensity**:
  - Normal range (average): 50-800 units
  - Individual channels outside 20-1000 units trigger warnings

---

## Running as Services (Production)

### WebSocket Bridge Service

```bash
sudo nano /etc/systemd/system/water-bridge.service
```

```ini
[Unit]
Description=Water Quality WebSocket Bridge
After=network.target

[Service]
ExecStart=/path/to/venv/bin/python /path/to/websocket_bridge.py
WorkingDirectory=/path/to/Project
Environment="MQTT_BROKER=192.168.1.103"
Environment="MQTT_PORT=1883"
Environment="MQTT_TOPIC=group1/water_quality"
Restart=always
User=your-user

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable water-bridge.service
sudo systemctl start water-bridge.service
sudo systemctl status water-bridge.service
```

### Dashboard Production Build

```bash
cd dashboard
npm run build
npm start  # Or use PM2/systemd
```

---

## Troubleshooting

### WebSocket Bridge Issues

**"Error connecting to MQTT broker"**
- Verify MQTT broker is running at `192.168.1.103:1883`
- Check network connectivity: `ping 192.168.1.103`
- Verify broker allows connections: `mosquitto_sub -h 192.168.1.103 -t test`

**Bridge server won't start**
```bash
# Check if port 8000 is in use
lsof -i :8000

# Kill process if needed
kill -9 <PID>
```

### Dashboard Issues

**"Disconnected" status**
- Ensure WebSocket bridge is running: `curl http://localhost:8000`
- Check `.env.local` has correct `NEXT_PUBLIC_WS_URL`
- Restart Next.js dev server after changing `.env.local`

**No data showing**
- Verify Raspberry Pi publisher is running and sending data
- Monitor MQTT: `mosquitto_sub -h 192.168.1.103 -t group1/water_quality -v`
- Check bridge server logs for incoming messages

### Raspberry Pi Publisher Issues

**"Connection refused" on MQTT**
- Check broker IP is correct in `raspberrypi.py`
- Verify broker is accessible from Pi network

**No data from Arduino**
- Check serial port: `ls /dev/ttyUSB* /dev/ttyACM*`
- Test serial connection: `cat /dev/ttyUSB0`
- Verify Arduino is running and connected

### Network Issues

**Components on different networks**
- All components must be on same network or have proper routing
- MQTT broker at `192.168.1.103` must be accessible
- Check firewalls aren't blocking port 1883 or 8000

---

## API Endpoints (WebSocket Bridge)

### GET `/`
Health check and server status
```json
{
  "status": "running",
  "service": "Water Quality WebSocket Bridge",
  "mqtt_broker": "192.168.1.103:1883",
  "mqtt_topic": "group1/water_quality",
  "active_connections": 1
}
```

### WebSocket `/ws`
WebSocket endpoint for real-time data streaming. Messages are in JSON format:
```json
{
  "timestamp": "2025-10-02T10:30:00",
  "location": "raspberry_pi_1",
  "turbidity": 2.5,
  "spectrum": {
    "sensor_type": "AS7265X_Spectral",
    "channels": {
      "A": 174.2,
      "B": 240.1,
      "C": 20.7,
      "D": 392.0,
      "E": 82.3,
      "F": 37.5
    },
    "average": 157.8,
    "readings_count": 6
  }
}
```

---

## Data Flow

1. **Arduino** → Reads turbidity sensor → Sends JSON via serial (5s intervals)
2. **Raspberry Pi** → Reads serial + spectral sensor → Publishes to MQTT (10s intervals)
3. **MQTT Broker** → Receives messages on `group1/water_quality` topic
4. **WebSocket Bridge** → Subscribes to MQTT → Broadcasts to WebSocket clients
5. **Dashboard** → Connects via WebSocket → Displays real-time data & analysis

---

## Technology Stack

### Backend
- **Python 3.8+**
- **FastAPI** - Modern web framework for WebSocket bridge
- **Paho MQTT** - MQTT client library
- **Uvicorn** - ASGI server

### Frontend
- **Next.js 15** - React framework
- **TypeScript** - Type-safe JavaScript
- **Tailwind CSS** - Utility-first CSS
- **Recharts** - Data visualization
- **Lucide React** - Icon library

### Hardware
- Arduino (turbidity sensor)
- Raspberry Pi (spectral sensor + serial reader)
- MQTT Broker (Mosquitto)

---

## Development Tips

### Hot Reload Dashboard
The Next.js development server supports hot reload. Changes to components will reflect immediately.

### Debug WebSocket Connection
```javascript
// Open browser console on dashboard page
// WebSocket connection logs will appear
```

### Monitor All System Components
```bash
# Terminal 1: Bridge server
cd Project && ./venv/bin/python websocket_bridge.py

# Terminal 2: Dashboard
cd dashboard && npm run dev

# Terminal 3: MQTT monitor
mosquitto_sub -h 192.168.1.103 -t group1/water_quality -v

# Terminal 4: Simulate data (for testing)
cd Project && python simulate_sensor_data.py
```

---

## License

This project is part of SMU FYP Y3S1 - Week 1 Group 1.

---

## Contributors

DevAIoT Team - Week 1 Group 1
