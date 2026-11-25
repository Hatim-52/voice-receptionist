"""
server.py - FastAPI Server for Voice AI Doctor Appointment Assistant.

Endpoints:
- POST /api/offer : WebRTC offer endpoint for SmallWebRTC
- PATCH /api/offer: WebRTC ICE candidate trickling
- GET /api/doctors : Doctor list with 7-day slot availability
- GET /api/appointments: All booked appointments
- POST /api/reset : Reset database to clean seed state
- GET /api/events : Live Server-Sent Events (SSE) channel for real-time dashboard updates & transcripts
- WS /ws : Live WebSocket channel for real-time dashboard updates & transcripts
- GET /api/health : Server health status
"""

import json
import asyncio
from typing import Set, Dict, Any, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

# Pipecat WebRTC components
from pipecat.transports.smallwebrtc.connection import SmallWebRTCConnection, IceServer
from pipecat.transports.smallwebrtc.request_handler import (
    SmallWebRTCRequestHandler,
    SmallWebRTCRequest,
    SmallWebRTCPatchRequest,
    IceCandidate
)

# Local imports
from backend import db, tools
from backend.bot import run_bot_pipeline

# Track active live streaming connections (SSE and WebSockets)
_sse_subscribers: Set[asyncio.Queue] = set()
_ws_subscribers: Set[WebSocket] = set()

# Initialize SmallWebRTC Request Handler
# Uses Google public STUN server for robust NAT traversal
ice_servers = [
    IceServer(urls=["stun:stun.l.google.com:19302", "stun:stun1.l.google.com:19302"])
]
small_webrtc_handler = SmallWebRTCRequestHandler(ice_servers=ice_servers)


async def broadcast_live_event(event_payload: Dict[str, Any]):
    """Broadcast an event to all connected SSE and WebSocket clients."""
    # 1. Deliver to SSE queues
    dead_queues = set()
    for queue in _sse_subscribers:
        try:
            queue.put_nowait(event_payload)
        except asyncio.QueueFull:
            dead_queues.add(queue)
        except Exception:
            dead_queues.add(queue)

    for dead in dead_queues:
        _sse_subscribers.discard(dead)

    # 2. Deliver to WebSockets
    dead_ws = set()
    msg_text = json.dumps(event_payload)
    for ws in list(_ws_subscribers):
        try:
            await ws.send_text(msg_text)
        except Exception:
            dead_ws.add(ws)

    for dead in dead_ws:
        _ws_subscribers.discard(dead)


# Register our broadcast function with tools.py event emitter
tools.register_event_listener(broadcast_live_event)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown management."""
    print("=================================================================")
    print("  Apollo Healthcare Voice AI Receptionist - Backend Server")
    print("=================================================================")
    db.init_db(reset=False)
    print("  SQLite database initialized.")
    print("  Ready to accept WebRTC calls on /api/offer and SSE on /api/events")
    print("=================================================================")
    yield
    print("  Shutting down SmallWebRTC handler...")
    await small_webrtc_handler.close()


app = FastAPI(
    title="Apollo Voice Receptionist API",
    description="Backend API powering the Voice AI Doctor Appointment Assistant",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for local Vite dev server and browser clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==============================================================================
# WebRTC Signaling Endpoints
# ==============================================================================

@app.post("/api/offer")
async def handle_webrtc_offer(request: Request):
    """
    Handle initial WebRTC offer from browser SmallWebRTC client.
    Initializes peer connection, starts Pipecat bot task, and returns SDP answer.
    """
    try:
        body = await request.json()
        webrtc_request = SmallWebRTCRequest(
            sdp=body["sdp"],
            type=body["type"],
            pc_id=body.get("pc_id"),
            restart_pc=body.get("restart_pc"),
            request_data=body.get("request_data") or body.get("requestData")
        )

        async def connection_callback(connection: SmallWebRTCConnection):
            # Launch bot pipeline task in background
            print(f"[server.py] Starting bot task for peer: {connection.pc_id}")
            asyncio.create_task(run_bot_pipeline(connection))

        answer = await small_webrtc_handler.handle_web_request(
            webrtc_request,
            connection_callback
        )
        return answer
    except Exception as e:
        print(f"[server.py] Error processing WebRTC offer: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/api/offer")
async def handle_webrtc_patch(request: Request):
    """Handle trickled ICE candidates from browser client."""
    try:
        body = await request.json()
        patch_request = SmallWebRTCPatchRequest(
            pc_id=body["pc_id"],
            candidates=[IceCandidate(**c) for c in body.get("candidates", [])]
        )
        await small_webrtc_handler.handle_patch_request(patch_request)
        return {"status": "success"}
    except Exception as e:
        print(f"[server.py] Error processing ICE patch: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==============================================================================
# REST API Endpoints for Dashboard
# ==============================================================================

@app.get("/api/doctors")
def get_doctors():
    """Return all doctors with their availability map for the next 7 days."""
    doctors = db.get_doctors_with_slots(days_ahead=7)
    return {"doctors": doctors}


@app.get("/api/appointments")
def get_appointments():
    """Return all booked appointments sorted by newest first."""
    appointments = db.get_all_appointments()
    return {"appointments": appointments}


@app.post("/api/reset")
def reset_database():
    """Reset database to fresh mock doctors and sample appointments."""
    db.init_db(reset=True)
    # Broadcast reset event so dashboard refreshes automatically
    asyncio.create_task(broadcast_live_event({
        "event": "database_reset",
        "data": {},
        "timestamp": ""
    }))
    return {
        "status": "success",
        "message": "Database successfully reset with seed doctors and appointments."
    }


@app.get("/api/health")
def health_check():
    """Server health status check."""
    return {
        "status": "healthy",
        "service": "Voice AI Receptionist",
        "active_sse_subscribers": len(_sse_subscribers),
        "active_ws_subscribers": len(_ws_subscribers)
    }


# ==============================================================================
# Real-Time Event Streams (SSE & WebSocket)
# ==============================================================================

@app.get("/api/events")
async def sse_event_stream(request: Request):
    """
    Server-Sent Events (SSE) endpoint.
    Streams live appointment updates, cancellation events, call status, and live transcripts.
    """
    queue: asyncio.Queue = asyncio.Queue(maxsize=100)
    _sse_subscribers.add(queue)

    async def event_generator():
        try:
            # Send initial ping so client knows connection is alive
            yield f"event: connected\ndata: {json.dumps({'message': 'SSE connected'})}\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    payload = await asyncio.wait_for(queue.get(), timeout=15.0)
                    evt_name = payload.get("event", "message")
                    data_json = json.dumps(payload)
                    yield f"event: {evt_name}\ndata: {data_json}\n\n"
                except asyncio.TimeoutError:
                    # Keep-alive heartbeat ping
                    yield ": keep-alive\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            _sse_subscribers.discard(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.websocket("/ws")
async def websocket_event_stream(websocket: WebSocket):
    """
    WebSocket endpoint for real-time dashboard events and transcripts.
    """
    await websocket.accept()
    _ws_subscribers.add(websocket)
    try:
        await websocket.send_text(json.dumps({"event": "connected", "message": "WebSocket connected"}))
        while True:
            # Listen for any client message or disconnect
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text(json.dumps({"event": "pong"}))
    except (WebSocketDisconnect, asyncio.CancelledError):
        pass
    finally:
        _ws_subscribers.discard(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.server:app", host="0.0.0.0", port=8000, reload=True)
