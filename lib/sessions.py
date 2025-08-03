import uuid
import asyncio
from pydantic import BaseModel
from fastapi import HTTPException
from lib.ee import EventEmitter


class Filter(BaseModel):
   query: str = ""
   selected_tags: list[str] = []

class Session(BaseModel):
    filter: Filter
    bus: EventEmitter
    csrfToken: str
    stream: asyncio.Queue[str]
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
      stream=asyncio.Queue()
    )
    return session_id

def getSession(*, session_id: str) -> Session:
    if session_id not in sessions:
        raise HTTPException(status_code=400, detail="Invalid Session")
    return sessions[session_id]

def updateFilter(*, session_id: str, filter: Filter):
    session = sessions[session_id]
    if not session: return
    session.filter = filter
    session.bus.emit('update')