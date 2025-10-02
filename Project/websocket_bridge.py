#!/usr/bin/env python3
"""
WebSocket Bridge Server - Water Quality Data
- Subscribes to MQTT broker for water quality data
- Exposes WebSocket endpoint for dashboard clients
- Broadcasts MQTT messages to all connected WebSocket clients
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import paho.mqtt.client as mqtt
import json
import asyncio
import os
from collections import deque
from datetime import datetime
from typing import Any, Deque, Dict, Optional, Set
import uvicorn
from asyncio import AbstractEventLoop

# MQTT Configuration
MQTT_BROKER = os.environ.get('MQTT_BROKER', '192.168.1.103')
MQTT_PORT = int(os.environ.get('MQTT_PORT', 1883))
MQTT_TOPIC = os.environ.get('MQTT_TOPIC', 'group1/water_quality')
MQTT_CLIENT_ID = os.environ.get('MQTT_CLIENT_ID', 'websocket_bridge')

# History configuration
HISTORY_LIMIT = int(os.environ.get('HISTORY_LIMIT', 100))

# FastAPI app
app = FastAPI(title="Water Quality WebSocket Bridge")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your dashboard URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store active WebSocket connections
active_connections: Set[WebSocket] = set()

# Store latest message and limited history buffer
latest_message: Optional[Dict[str, Any]] = None
message_history: Deque[Dict[str, Any]] = deque(maxlen=HISTORY_LIMIT)

# Event loop reference for MQTT bridge
event_loop: Optional[AbstractEventLoop] = None

class MQTTBridge:
    def __init__(self):
        self.mqtt_client = None
        self.setup_mqtt()
    
    def setup_mqtt(self):
        """Initialize MQTT client"""
        self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, MQTT_CLIENT_ID)
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message
        self.mqtt_client.on_disconnect = self.on_disconnect
        
        try:
            print(f"Connecting to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}...")
            self.mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
            self.mqtt_client.loop_start()
        except Exception as e:
            print(f"✗ Error connecting to MQTT broker: {e}")
    
    def on_connect(self, client, userdata, flags, reason_code, properties):
        """Callback when connected to MQTT broker"""
        if reason_code == 0:
            print(f"✓ Connected to MQTT broker")
            print(f"✓ Subscribing to topic: {MQTT_TOPIC}")
            client.subscribe(MQTT_TOPIC, qos=1)
        else:
            print(f"✗ Failed to connect, reason code: {reason_code}")
    
    def on_disconnect(self, client, userdata, flags, reason_code, properties):
        """Callback when disconnected from MQTT broker"""
        if reason_code != 0:
            print("⚠ Unexpected disconnection from MQTT broker")
    
    def on_message(self, client, userdata, msg):
        """Callback when message is received from MQTT"""
        global latest_message
        try:
            payload = msg.payload.decode('utf-8')
            data = json.loads(payload)
            timestamp = data.get('timestamp', datetime.now().isoformat())

            def coerce_float(value: Any) -> Optional[float]:
                try:
                    return float(value)
                except (TypeError, ValueError):
                    return None

            turbidity = coerce_float(data.get('turbidity'))
            light_intensity = coerce_float(data.get('light_intensity'))

            sanitized: Dict[str, Any] = {
                'timestamp': timestamp,
                'turbidity': turbidity,
                'light_intensity': light_intensity,
                'location': data.get('location'),
            }

            if turbidity is not None and light_intensity is not None:
                print(
                    f"[{datetime.now().strftime('%H:%M:%S')}] Received: "
                    f"Turbidity={turbidity:.2f}, Light={light_intensity:.2f}"
                )
            else:
                print(
                    f"[{datetime.now().strftime('%H:%M:%S')}] Received payload with missing values: {sanitized}"
                )

            message_history.append(sanitized)
            latest_message = sanitized

            # Broadcast to all connected WebSocket clients (thread-safe)
            if event_loop and active_connections:
                asyncio.run_coroutine_threadsafe(
                    broadcast_message(json.dumps(sanitized)),
                    event_loop
                )

        except json.JSONDecodeError as e:
            print(f"✗ Error parsing message: {e}")
        except Exception as e:
            print(f"✗ Error processing message: {e}")

# Initialize MQTT bridge
mqtt_bridge = MQTTBridge()

async def broadcast_message(message: str):
    """Send message to all connected WebSocket clients"""
    disconnected = set()
    for connection in active_connections:
        try:
            await connection.send_text(message)
        except Exception as e:
            print(f"Error sending to client: {e}")
            disconnected.add(connection)
    
    # Remove disconnected clients
    for connection in disconnected:
        active_connections.discard(connection)

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "running",
        "service": "Water Quality WebSocket Bridge",
        "mqtt_broker": f"{MQTT_BROKER}:{MQTT_PORT}",
        "mqtt_topic": MQTT_TOPIC,
        "active_connections": len(active_connections),
        "history_size": len(message_history),
        "history_limit": HISTORY_LIMIT,
    }


@app.get("/history")
async def get_history():
    """Return the current buffered history of messages."""
    return {
        "data": list(message_history),
        "count": len(message_history),
        "limit": HISTORY_LIMIT,
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for dashboard clients"""
    await websocket.accept()
    active_connections.add(websocket)
    print(f"✓ New WebSocket client connected. Total: {len(active_connections)}")
    
    try:
        # Send historical buffer first so clients can render immediately
        if message_history:
            history_payload = {
                "type": "history",
                "data": list(message_history),
            }
            await websocket.send_text(json.dumps(history_payload))

        # Send the latest message (in case clients expect single payload)
        if latest_message:
            await websocket.send_text(json.dumps(latest_message))
        
        # Keep connection alive and listen for client messages
        while True:
            # Wait for any client message (keep-alive)
            try:
                data = await websocket.receive_text()
                # Echo back or handle client messages if needed
            except WebSocketDisconnect:
                break
            
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        active_connections.discard(websocket)
        print(f"✗ WebSocket client disconnected. Total: {len(active_connections)}")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    if mqtt_bridge.mqtt_client:
        mqtt_bridge.mqtt_client.loop_stop()
        mqtt_bridge.mqtt_client.disconnect()
    print("Shutting down...")

@app.on_event("startup")
async def startup_event():
    """Set event loop reference on startup"""
    global event_loop
    event_loop = asyncio.get_event_loop()
    print("Event loop initialized for MQTT bridge")

if __name__ == "__main__":
    print("=" * 60)
    print("Water Quality WebSocket Bridge Server")
    print("=" * 60)
    print(f"MQTT Broker: {MQTT_BROKER}:{MQTT_PORT}")
    print(f"MQTT Topic: {MQTT_TOPIC}")
    print(f"WebSocket URL: ws://localhost:8000/ws")
    print("=" * 60)
    print()
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
