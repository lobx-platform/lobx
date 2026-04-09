"""Questionnaire routes: /save_questionnaire_response, /questionnaire/status, /consent/*, /save_premarket_interaction"""

import asyncio
import csv
import io
import json
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel

from ..auth import get_current_admin_user
from ..shared import ROOT_DIR, _trader_locks
from utils.api_responses import success

router = APIRouter()


# --- Models ---

class QuestionnaireResponse(BaseModel):
    trader_id: str
    responses: List[str]
    market_number: Optional[int] = None


class PremarketInteraction(BaseModel):
    trader_id: str
    question_index: int
    question_text: str
    selected_answer: str
    is_correct: bool


class ConsentData(BaseModel):
    trader_id: str = ''
    user_id: str = ''
    user_type: str = ''
    prolific_id: str = ''
    consent_given: bool = True
    consent_timestamp: str = ''


# --- Helpers ---

def _get_questionnaire_dir():
    d = ROOT_DIR / "questionnaire"
    d.mkdir(exist_ok=True)
    return d


def _get_trader_json_path(trader_id: str) -> Path:
    return _get_questionnaire_dir() / f"{trader_id}.json"


def _read_trader_data(trader_id: str) -> dict:
    path = _get_trader_json_path(trader_id)
    if path.exists():
        with open(path, 'r') as f:
            return json.load(f)
    return {"trader_id": trader_id, "premarket_interactions": [], "postmarket_responses": None}


def _write_trader_data(trader_id: str, data: dict):
    path = _get_trader_json_path(trader_id)
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)


async def _get_lock(trader_id: str) -> asyncio.Lock:
    if trader_id not in _trader_locks:
        _trader_locks[trader_id] = asyncio.Lock()
    return _trader_locks[trader_id]


# --- Endpoints ---

@router.post("/save_premarket_interaction")
async def save_premarket_interaction(interaction: PremarketInteraction):
    try:
        lock = await _get_lock(interaction.trader_id)
        async with lock:
            data = _read_trader_data(interaction.trader_id)
            data["premarket_interactions"].append({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "question_index": interaction.question_index,
                "question_text": interaction.question_text,
                "selected_answer": interaction.selected_answer,
                "is_correct": interaction.is_correct,
            })
            _write_trader_data(interaction.trader_id, data)
        return success(message="Pre-market interaction saved")
    except Exception as e:
        return {"status": "error", "message": f"Failed to save pre-market interaction: {str(e)}"}


@router.get("/questionnaire/status")
async def questionnaire_status(trader_id: str = Query(...)):
    try:
        data = _read_trader_data(trader_id)
        completed = data.get("postmarket_responses") is not None
        return success(data={"completed": completed})
    except Exception:
        return success(data={"completed": False})


@router.post("/save_questionnaire_response")
async def save_questionnaire_response(response: QuestionnaireResponse):
    try:
        lock = await _get_lock(response.trader_id)
        async with lock:
            data = _read_trader_data(response.trader_id)

            if response.market_number is not None:
                if "per_market_responses" not in data:
                    data["per_market_responses"] = {}
                data["per_market_responses"][str(response.market_number)] = {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "market_description": response.responses[0] if len(response.responses) > 0 else None,
                    "imbalance_reason": response.responses[1] if len(response.responses) > 1 else None,
                }
            else:
                data["postmarket_responses"] = {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "q1": response.responses[0] if len(response.responses) > 0 else None,
                    "q2": response.responses[1] if len(response.responses) > 1 else None,
                    "q3": response.responses[2] if len(response.responses) > 2 else None,
                    "q4": response.responses[3] if len(response.responses) > 3 else None,
                    "market_description": response.responses[4] if len(response.responses) > 4 else None,
                    "imbalance_reason": response.responses[5] if len(response.responses) > 5 else None,
                }

            _write_trader_data(response.trader_id, data)
        return success(message="Questionnaire response saved successfully")
    except Exception as e:
        return {"status": "error", "message": f"Failed to save questionnaire response: {str(e)}"}


@router.get("/admin/download_questionnaire_data")
async def download_questionnaire_data(current_user: dict = Depends(get_current_admin_user)):
    try:
        questionnaire_dir = _get_questionnaire_dir()
        json_files = list(questionnaire_dir.glob("*.json"))

        if not json_files:
            return Response(content="No questionnaire data found", media_type="text/plain")

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
            for f in json_files:
                zf.write(f, f.name)
        buf.seek(0)

        return StreamingResponse(
            buf, media_type="application/zip",
            headers={"Content-Disposition": "attachment; filename=questionnaire_data.zip"}
        )
    except Exception as e:
        return Response(content=f"Error downloading questionnaire data: {str(e)}", media_type="text/plain", status_code=500)


@router.post("/consent/save")
async def save_consent_data(consent: ConsentData):
    consent_dir = Path("logs/consent")
    consent_dir.mkdir(parents=True, exist_ok=True)
    consent_file = consent_dir / "consent_data.csv"
    file_exists = consent_file.exists()
    timestamp = datetime.now().isoformat()
    user_id = consent.user_id or consent.prolific_id
    user_type = consent.user_type or ("prolific" if consent.prolific_id else None)
    with open(consent_file, mode='a', newline='') as file:
        fieldnames = ['trader_id', 'user_id', 'user_type', 'consent_given', 'consent_timestamp']
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        trader_id = consent.trader_id or user_id
        writer.writerow({
            'trader_id': trader_id, 'user_id': user_id, 'user_type': user_type,
            'consent_given': str(consent.consent_given), 'consent_timestamp': timestamp
        })
    return success(message="Consent data saved successfully", timestamp=timestamp)


@router.post("/consent/debug")
async def debug_consent(data: dict):
    return success(received=data)


@router.get("/admin/download-consent-data")
async def download_consent_data(current_user: dict = Depends(get_current_admin_user)):
    consent_file = ROOT_DIR.parent / "logs/consent/consent_data.csv"
    if not consent_file.exists():
        return JSONResponse(status_code=404, content={"status": "error", "message": "Consent data file not found"})
    return FileResponse(path=consent_file, filename="consent_data.csv", media_type="text/csv")
