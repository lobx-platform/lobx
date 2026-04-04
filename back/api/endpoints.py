"""
LOBX Platform - Router aggregator.

All endpoint logic lives in api/routes/*.py.
This file wires them together and configures middleware.
"""

import asyncio

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from .routes import auth, trading, admin, questionnaire, data, test
from .shared import base_settings

# --- App ---

app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*", "Authorization"],
    expose_headers=["Content-Disposition"],
    max_age=3600,
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin-allow-popups"
    response.headers["Cross-Origin-Embedder-Policy"] = "require-corp"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    return response


# --- Include all route modules ---

app.include_router(auth.router)
app.include_router(trading.router)
app.include_router(admin.router)
app.include_router(questionnaire.router)
app.include_router(data.router)
app.include_router(test.router)


# --- Startup ---

@app.on_event("startup")
async def startup_event():
    from core.parameter_logger import ParameterLogger
    logger = ParameterLogger()
    logger.log_parameter_state(current_state=base_settings, source='system_startup')
