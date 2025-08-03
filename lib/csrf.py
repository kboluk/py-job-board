from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from fastapi.responses import JSONResponse
from fastapi import status

class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method in ("POST", "PUT", "DELETE"):
            session_id = request.cookies.get("session_id")
            if not session_id:
                return JSONResponse(
                    {"detail": "Missing session"},
                    status_code=status.HTTP_403_FORBIDDEN,
                )

            # You’d use your own session store here
            from lib.sessions import getSession
            try:
                session = getSession(session_id=session_id)
            except:
                return JSONResponse(
                    {"detail": "Invalid session"},
                    status_code=status.HTTP_403_FORBIDDEN,
                )

            expected_token = session.csrfToken

            # Determine where the token is supplied
            content_type = request.headers.get("content-type", "")
            if content_type.startswith("application/json"):
                actual_token = request.headers.get("x-csrf-token")
            elif content_type.startswith("application/x-www-form-urlencoded"):
                form = await request.form()
                actual_token = form.get("_csrf")
            else:
                actual_token = None

            if actual_token != expected_token:
                return JSONResponse(
                    {"detail": "CSRF token invalid or missing"},
                    status_code=status.HTTP_403_FORBIDDEN,
                )

        return await call_next(request)
