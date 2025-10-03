#!/usr/bin/env python3
"""
WebSocket Bridge Server - Water Quality Data
- Subscribes to MQTT broker for water quality data
- Exposes WebSocket endpoint for dashboard clients
- Broadcasts MQTT messages to all connected WebSocket clients
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
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

# Reconnection configuration
MQTT_RECONNECT_INTERVAL = int(os.environ.get('MQTT_RECONNECT_INTERVAL', 5))  # seconds
MQTT_RECONNECT_MAX_ATTEMPTS = int(os.environ.get('MQTT_RECONNECT_MAX_ATTEMPTS', 0))  # 0 = infinite

# History configuration
HISTORY_LIMIT = int(os.environ.get('HISTORY_LIMIT', 100))

# FastAPI app will be initialized later with lifespan context

# CORS middleware will be added after app initialization

# Store active WebSocket connections
active_connections: Set[WebSocket] = set()

# Store latest message and limited history buffer
latest_message: Optional[Dict[str, Any]] = None
message_history: Deque[Dict[str, Any]] = deque(maxlen=HISTORY_LIMIT)

# Event loop reference for MQTT bridge
event_loop: Optional[AbstractEventLoop] = None

# MQTT connection status
mqtt_connected: bool = False

# Reconnection task reference
reconnect_task: Optional[asyncio.Task] = None

class MQTTBridge:
    def __init__(self):
        self.mqtt_client = None
        self.reconnect_attempts = 0
        self.is_reconnecting = False
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
            # Start reconnection attempts
            self.schedule_reconnect()
    
    def on_connect(self, client, userdata, flags, reason_code, properties):
        """Callback when connected to MQTT broker"""
        global mqtt_connected
        if reason_code == 0:
            print(f"✓ Connected to MQTT broker")
            print(f"✓ Subscribing to topic: {MQTT_TOPIC}")
            client.subscribe(MQTT_TOPIC, qos=1)
            mqtt_connected = True
            # Reset reconnection attempts on successful connection
            self.reconnect_attempts = 0
            self.is_reconnecting = False
            # Broadcast status to all connected clients
            if event_loop and active_connections:
                asyncio.run_coroutine_threadsafe(
                    broadcast_status_update(),
                    event_loop
                )
        else:
            print(f"✗ Failed to connect, reason code: {reason_code}")
            mqtt_connected = False
            if event_loop and active_connections:
                asyncio.run_coroutine_threadsafe(
                    broadcast_status_update(),
                    event_loop
                )
            # Schedule reconnection attempt
            self.schedule_reconnect()
    
    def on_disconnect(self, client, userdata, flags, reason_code, properties):
        """Callback when disconnected from MQTT broker"""
        global mqtt_connected
        mqtt_connected = False
        if reason_code != 0:
            print("⚠ Unexpected disconnection from MQTT broker")
            # Schedule reconnection attempt on unexpected disconnect
            self.schedule_reconnect()
        # Broadcast status to all connected clients
        if event_loop and active_connections:
            asyncio.run_coroutine_threadsafe(
                broadcast_status_update(),
                event_loop
            )
    
    def schedule_reconnect(self):
        """Schedule a reconnection attempt"""
        global reconnect_task
        if self.is_reconnecting:
            return  # Already attempting to reconnect
        
        self.is_reconnecting = True
        if event_loop:
            # Cancel existing reconnect task if any
            if reconnect_task and not reconnect_task.done():
                reconnect_task.cancel()
            reconnect_task = asyncio.run_coroutine_threadsafe(
                self.reconnect_loop(),
                event_loop
            )
    
    async def reconnect_loop(self):
        """Attempt to reconnect to MQTT broker at intervals"""
        while True:
            # Check if we should stop trying
            if MQTT_RECONNECT_MAX_ATTEMPTS > 0 and self.reconnect_attempts >= MQTT_RECONNECT_MAX_ATTEMPTS:
                print(f"✗ Maximum reconnection attempts ({MQTT_RECONNECT_MAX_ATTEMPTS}) reached. Stopping reconnection attempts.")
                self.is_reconnecting = False
                break
            
            # Check if already connected
            if mqtt_connected:
                self.is_reconnecting = False
                break
            
            self.reconnect_attempts += 1
            print(f"⟳ Reconnection attempt {self.reconnect_attempts}/{MQTT_RECONNECT_MAX_ATTEMPTS if MQTT_RECONNECT_MAX_ATTEMPTS > 0 else '∞'} in {MQTT_RECONNECT_INTERVAL} seconds...")
            await asyncio.sleep(MQTT_RECONNECT_INTERVAL)
            
            try:
                print(f"⟳ Attempting to reconnect to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}...")
                # Stop the current loop before reconnecting
                self.mqtt_client.loop_stop()
                # Try to disconnect cleanly first
                try:
                    self.mqtt_client.disconnect()
                except:
                    pass
                # Create a fresh connection
                self.mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
                self.mqtt_client.loop_start()
            except Exception as e:
                print(f"✗ Reconnection failed: {e}")
    
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

            def coerce_int(value: Any) -> Optional[int]:
                try:
                    integer = int(value)
                    return integer
                except (TypeError, ValueError):
                    return None

            def sanitize_channels(raw: Any) -> Optional[Dict[str, float]]:
                if not isinstance(raw, dict):
                    return None

                sanitized_channels: Dict[str, float] = {}
                for key, value in raw.items():
                    numeric_value = coerce_float(value)
                    if numeric_value is not None:
                        sanitized_channels[str(key)] = numeric_value

                return sanitized_channels or None

            # Extract pH
            pH = coerce_float(data.get('pH')) or coerce_float(data.get('ph'))
            
            # Extract turbidity - just pass through raw voltage or NTU, no conversion
            turbidity_voltage = None
            turbidity_ntu = None
            
            turbidity_container = data.get('turbidity_sensor') or data.get('turbiditySensor')
            if isinstance(turbidity_container, dict):
                turbidity_voltage = coerce_float(turbidity_container.get('voltage'))
                turbidity_ntu = coerce_float(turbidity_container.get('ntu'))
            
            # Fallback to top-level fields
            if turbidity_voltage is None:
                turbidity_voltage = coerce_float(
                    data.get('turbidity_voltage') or data.get('turbidityVoltage')
                )
            if turbidity_ntu is None:
                turbidity_ntu = coerce_float(data.get('turbidity'))
            
            # Extract spectrum data
            spectrum_source: Optional[Dict[str, Any]] = None
            for key in ('spectrum', 'spectrum_sensor', 'spectrumSensor', 'spectral'):
                candidate = data.get(key)
                if isinstance(candidate, dict):
                    spectrum_source = candidate
                    break

            channels = sanitize_channels(
                data.get('channels')
                if data.get('channels') is not None
                else (spectrum_source.get('channels') if spectrum_source else None)
            )

            spectrum_average = coerce_float(
                data.get('spectrum_average')
                if data.get('spectrum_average') is not None
                else data.get('spectrumAverage')
            )
            if spectrum_average is None and spectrum_source:
                for avg_key in ('average', 'avg', 'mean'):
                    spectrum_average = coerce_float(spectrum_source.get(avg_key))
                    if spectrum_average is not None:
                        break

            readings_count = coerce_int(
                data.get('readings_count')
                if data.get('readings_count') is not None
                else data.get('readingsCount')
            )
            if readings_count is None and spectrum_source:
                for count_key in ('readings_count', 'readingsCount', 'count', 'samples'):
                    readings_count = coerce_int(spectrum_source.get(count_key))
                    if readings_count is not None:
                        break

            sensor_type_value = data.get('sensor_type') or data.get('sensorType')
            if not sensor_type_value and spectrum_source:
                for type_key in ('sensor_type', 'sensorType', 'name', 'type'):
                    value = spectrum_source.get(type_key)
                    if isinstance(value, str):
                        sensor_type_value = value
                        break

            if spectrum_average is None and channels:
                spectrum_average = sum(channels.values()) / len(channels)

            # Build sanitized payload
            sanitized: Dict[str, Any] = {
                'timestamp': timestamp,
                'location': data.get('location', 'unknown'),
            }
            
            if pH is not None:
                sanitized['pH'] = pH

            # Add turbidity object if we have any turbidity data
            if turbidity_voltage is not None or turbidity_ntu is not None:
                turbidity_payload: Dict[str, Any] = {}
                if turbidity_voltage is not None:
                    turbidity_payload['voltage'] = turbidity_voltage
                if turbidity_ntu is not None:
                    turbidity_payload['ntu'] = turbidity_ntu
                sanitized['turbidity'] = turbidity_payload

            # Add spectrum data if available
            if any((sensor_type_value, channels, spectrum_average, readings_count is not None)):
                spectrum_payload: Dict[str, Any] = {}
                if sensor_type_value:
                    spectrum_payload['sensor_type'] = sensor_type_value
                if channels is not None:
                    spectrum_payload['channels'] = channels
                if spectrum_average is not None:
                    spectrum_payload['average'] = spectrum_average
                if readings_count is not None:
                    spectrum_payload['readings_count'] = readings_count
                sanitized['spectrum'] = spectrum_payload

            # Check if we have meaningful metrics
            has_metrics = any(
                value is not None
                for value in (
                    turbidity_voltage,
                    turbidity_ntu,
                    pH,
                    spectrum_average,
                    channels,
                )
            )

            if has_metrics:
                display_parts = []
                if turbidity_voltage is not None:
                    display_parts.append(f"Turbidity(V)={turbidity_voltage:.3f}")
                if turbidity_ntu is not None:
                    display_parts.append(f"Turbidity(NTU)={turbidity_ntu:.2f}")
                if spectrum_average is not None:
                    display_parts.append(f"SpectralAvg={spectrum_average:.2f}")
                if channels:
                    display_parts.append(f"Channels={len(channels)}")

                print(
                    f"[{datetime.now().strftime('%H:%M:%S')}] Received: "
                    + ', '.join(display_parts)
                )
            else:
                print(
                    f"[{datetime.now().strftime('%H:%M:%S')}] Received payload with insufficient data"
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

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events"""
    global event_loop, reconnect_task
    
    # Startup
    event_loop = asyncio.get_event_loop()
    print("Event loop initialized for MQTT bridge")
    
    yield
    
    # Shutdown
    if reconnect_task and not reconnect_task.done():
        reconnect_task.cancel()
    if mqtt_bridge.mqtt_client:
        mqtt_bridge.mqtt_client.loop_stop()
        mqtt_bridge.mqtt_client.disconnect()
    print("Shutting down...")

# Create FastAPI app with lifespan
app = FastAPI(
    title="Water Quality WebSocket Bridge",
    lifespan=lifespan
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your dashboard URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def broadcast_status_update():
    """Broadcast MQTT connection status to all WebSocket clients"""
    status_message = json.dumps({
        "type": "status",
        "mqtt_connected": mqtt_connected
    })
    await broadcast_message(status_message)

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
        "mqtt_connected": mqtt_connected,
        "reconnect_attempts": mqtt_bridge.reconnect_attempts,
        "is_reconnecting": mqtt_bridge.is_reconnecting,
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
        # Send MQTT connection status first
        status_payload = {
            "type": "status",
            "mqtt_connected": mqtt_connected
        }
        await websocket.send_text(json.dumps(status_payload))
        
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

if __name__ == "__main__":
    print("=" * 60)
    print("Water Quality WebSocket Bridge Server")
    print("=" * 60)
    print(f"MQTT Broker: {MQTT_BROKER}:{MQTT_PORT}")
    print(f"MQTT Topic: {MQTT_TOPIC}")
    print(f"Reconnect Interval: {MQTT_RECONNECT_INTERVAL}s")
    print(f"Max Reconnect Attempts: {MQTT_RECONNECT_MAX_ATTEMPTS if MQTT_RECONNECT_MAX_ATTEMPTS > 0 else 'Infinite'}")
    print(f"WebSocket URL: ws://localhost:8000/ws")
    print("=" * 60)
    print()
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
