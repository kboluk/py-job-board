import uuid
import asyncio
import time
import threading
from contextlib import asynccontextmanager
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
from lib.ee import EventEmitter

SESSION_TTL = 3600  # 1 hour
CLEANUP_INTERVAL = 300  # every 5 minutes

class Filter(BaseModel):
   query: str = ""
   selected_tags: list[str] = []

class Session(BaseModel):
    filter: Filter
    bus: EventEmitter
    csrfToken: str
    stream: asyncio.Queue[str]
    last_seen: int = 0
    model_config = {
        "arbitrary_types_allowed": True
    }


sessions: dict[str, Session] = {}

def createSession() -> str:
    session_id = str(uuid.uuid4())
    sessions[session_id] = Session(
      filter=Filter(),
      bus=EventEmitter(),
      csrfToken=uuid.uuid4().hex,
      stream=asyncio.Queue(),
      last_seen=int(time.time())
    )
    return session_id

def getSession(*, session_id: str) -> Session:
    if session_id not in sessions:
        raise HTTPException(status_code=400, detail="Invalid Session")
    return sessions[session_id]

def updateFilter(*, session_id: str, filter: Filter):
    session = sessions[session_id]
    touch_session(session_id=session_id)
    session.filter = filter
    session.bus.emit('update')

def touch_session(*, session_id: str):
    session = getSession(session_id=session_id)
    if session:
        session.last_seen = int(time.time())

def cleanup_sessions_loop():
    while True:
        now = time.time()
        expired = [
            sid for sid, session in sessions.items()
            if now - session.last_seen > SESSION_TTL
        ]
        for sid in expired:
            print(f"[Session Cleanup] Removing inactive session: {sid}")
            del sessions[sid]
        time.sleep(CLEANUP_INTERVAL)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    thread = threading.Thread(target=cleanup_sessions_loop, daemon=True)
    thread.start()
    print("[Startup] Session cleanup thread started")

    yield

    # Shutdown (optional cleanup)
    print("[Shutdown] Application shutting down")