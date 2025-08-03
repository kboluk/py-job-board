from fastapi import FastAPI, Request, Response, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader, select_autoescape
from typing import Optional, List, Union
import asyncio
import json
from lib.jobs import tags as available_tags, filter_jobs
from lib.sessions import createSession, updateFilter, getSession, Filter, lifespan, touch_session
from lib.csrf import CSRFMiddleware

app = FastAPI(lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.add_middleware(CSRFMiddleware)

templates = Environment(
    loader=FileSystemLoader("templates"),
    autoescape=select_autoescape(["html", "xml"])
)

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    session_id = request.cookies.get("session_id")
    if not session_id:
        session_id = createSession()
    else:
        touch_session(session_id=session_id)
    session = getSession(session_id=session_id)
    template = templates.get_template("index.html")
    html = template.render(
        request=request,
        jobs=filter_jobs(
            keyword=session.filter.query,
            selectedTags=session.filter.selected_tags
        ),
        query="",
        tags=available_tags,
        selectedTags=session.filter.selected_tags,
        csrfToken=session.csrfToken
    )
    response = HTMLResponse(content=html)
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        samesite="strict",
        max_age=3600
    )
    return response

@app.post("/search")
async def search(
    request: Request,
    q: Optional[str] = Form(None),
    tag: Union[str, List[str], None] = Form(None)
):
    content_type = request.headers.get("content-type", "")
    session_id = request.cookies.get("session_id")
    if content_type.startswith("application/json"):
        data = await request.json()
        query = data.get("q", "")
        selected_tags = data.get("tag", [])
        updateFilter(session_id=session_id, filter=Filter(query=query, selected_tags=selected_tags))
        return Response(status_code=204)
    elif content_type.startswith("application/x-www-form-urlencoded"):
        # Use parsed form values from args
        query = q or ""
        if isinstance(tag, str):
            selected_tags = [tag]
        elif isinstance(tag, list):
            selected_tags = tag
        else:
            selected_tags = []
    else:
        return JSONResponse({"error": "Unsupported Content-Type"}, status_code=415)
    
    session = getSession(session_id=session_id)
    updateFilter(session_id=session_id, filter=Filter(query=query, selected_tags=selected_tags))
    filtered_jobs = filter_jobs(keyword=query, selectedTags=selected_tags)
    template = templates.get_template("index.html")
    html = template.render(
        request=request,
        jobs=filtered_jobs,
        query=query,
        tags=available_tags,
        selectedTags=selected_tags,
        csrfToken=session.csrfToken
    )
    return HTMLResponse(content=html)


@app.get("/events")
async def events(request: Request):
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="Missing session ID")
    touch_session(session_id=session_id)
    session = getSession(session_id=session_id)
    queue = session.stream

    def push_results():
        query  = session.filter.query
        selected_tags = session.filter.selected_tags
        subset = filter_jobs(keyword=query, selectedTags=selected_tags)
        template = templates.get_template("results.html")
        payload = {
            "html": template.render(jobs=subset),
            "count": len(subset)
        }
        session.stream.put_nowait(f"event: results\ndata: {json.dumps(payload)}\n\n")


    async def event_stream():
        # Initial ping (helps avoid connection timeout)
        yield "event: ping\ndata: connected\n\n"

        while True:
            try:
                message = await queue.get()
                yield message
                # Exit early if client disconnected
                if await request.is_disconnected():
                    session.bus.off("update", push_results)
                    break

            except asyncio.CancelledError:
                session.bus.off("update", push_results)

    session.bus.on("update", push_results)

    return StreamingResponse(event_stream(), media_type="text/event-stream")
