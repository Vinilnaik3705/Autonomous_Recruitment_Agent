"""
WebSocket router - provides real-time updates for candidate screening and recruitment pipeline events.
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, List
import asyncio
import json
from backend.database import get_redis_client

router = APIRouter(prefix="/ws", tags=["websocket"])

class ConnectionManager:
  def __init__(self):

    self.active_connections: Dict[str, List[WebSocket]] = {}

  async def connect(self, job_id: str, websocket: WebSocket):
    await websocket.accept()
    if job_id not in self.active_connections:
      self.active_connections[job_id] = []
    self.active_connections[job_id].append(websocket)
    print(f"--> WS CONNECT: Client connected to job {job_id}. Active: {len(self.active_connections[job_id])}")

  def disconnect(self, job_id: str, websocket: WebSocket):
    if job_id in self.active_connections:
      if websocket in self.active_connections[job_id]:
        self.active_connections[job_id].remove(websocket)
      if not self.active_connections[job_id]:
        del self.active_connections[job_id]
    print(f"--> WS DISCONNECT: Client disconnected from job {job_id}")

  async def send_personal_message(self, message: str, websocket: WebSocket):
    await websocket.send_text(message)

  async def broadcast(self, job_id: str, message: dict):
    if job_id in self.active_connections:
      payload = json.dumps(message)
      for connection in self.active_connections[job_id]:
        try:
          await connection.send_text(payload)
        except Exception:

          pass

manager = ConnectionManager()

async def redis_listener(job_id: str, websocket: WebSocket):
  """Background listener for Redis Pub/Sub channel for a specific job."""
  redis_client = get_redis_client()
  if not redis_client:

    await websocket.send_text(json.dumps({"error": "Redis broker unavailable for real-time updates."}))
    return

  pubsub = redis_client.pubsub()
  channel_name = f"screening:{job_id}"
  pubsub.subscribe(channel_name)
  print(f"--> WS PUB/SUB: Subscribed to channel {channel_name}")

  try:
    while True:

      message = pubsub.get_message(ignore_subscribe_messages=True, timeout=0.1)
      if message and message["type"] == "message":
        data = message["data"]
        if isinstance(data, bytes):
          data = data.decode("utf-8")
        try:
          parsed_data = json.loads(data)
          await websocket.send_text(json.dumps(parsed_data))
        except Exception as e:
          print(f"--> WS PUB/SUB ERROR: Failed to forward message: {e}")

      await asyncio.sleep(0.2)
  except asyncio.CancelledError:
    print(f"--> WS PUB/SUB CANCELLED: Stopped listener for job {job_id}")
  finally:
    pubsub.unsubscribe(channel_name)
    pubsub.close()

@router.websocket("/screening/{job_id}")
async def websocket_screening_endpoint(websocket: WebSocket, job_id: str):
  await manager.connect(job_id, websocket)

  listener_task = asyncio.create_task(redis_listener(job_id, websocket))

  try:
    while True:

      data = await websocket.receive_text()
      try:
        payload = json.loads(data)
        if payload.get("type") == "ping":
          await websocket.send_text(json.dumps({"type": "pong"}))
      except json.JSONDecodeError:
        pass
  except WebSocketDisconnect:
    manager.disconnect(job_id, websocket)
  finally:

    listener_task.cancel()