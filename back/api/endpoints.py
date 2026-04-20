"""
LOBX Platform - Router aggregator.

All endpoint logic lives in api/routes/*.py.
This file wires them together and configures middleware.

The exported ``app`` is a Socket.IO ASGIApp that wraps the FastAPI instance,
so both HTTP/REST routes and Socket.IO events are served on the same port.
"""

import asyncio

import socketio
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from .routes import auth, trading, admin, questionnaire, data, test
from .shared import base_settings

# --- FastAPI app (handles REST + legacy WS) ---

_fastapi_app = FastAPI()

_fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*", "Authorization"],
    expose_headers=["Content-Disposition"],
    max_age=3600,
)


@_fastapi_app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin-allow-popups"
    response.headers["Cross-Origin-Embedder-Policy"] = "require-corp"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    return response


# --- Include all route modules ---

_fastapi_app.include_router(auth.router)
_fastapi_app.include_router(trading.router)
_fastapi_app.include_router(admin.router)
_fastapi_app.include_router(questionnaire.router)
_fastapi_app.include_router(data.router)
_fastapi_app.include_router(test.router)


# --- Startup ---

@_fastapi_app.on_event("startup")
async def startup_event():
    from core.parameter_logger import ParameterLogger
    logger = ParameterLogger()
    logger.log_parameter_state(current_state=base_settings, source='system_startup')


# --- Socket.IO ASGI wrapper ---
# Import the shared sio instance (event handlers registered at module level)
from .socketio_server import sio  # noqa: E402

app = socketio.ASGIApp(sio, other_asgi_app=_fastapi_app)
