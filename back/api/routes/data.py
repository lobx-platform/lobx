"""Data routes: /files, /files/grouped, /files/{path}, /files/download-all"""

import asyncio
import re
import tempfile
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from ..auth import get_current_admin_user
from ..shared import ROOT_DIR

router = APIRouter()


@router.get("/files")
async def list_files(path: str = Query("", description="Relative path to browse")):
    try:
        full_path = (ROOT_DIR / path).resolve()

        if not full_path.is_relative_to(ROOT_DIR):
            raise HTTPException(status_code=403, detail="Access denied")

        if not full_path.exists():
            raise HTTPException(status_code=404, detail="Path not found")

        if full_path.is_file():
            return {"type": "file", "name": full_path.name}

        files = []
        directories = []

        for item in full_path.iterdir():
            mod_time = datetime.fromtimestamp(item.stat().st_mtime)
            if item.is_file():
                files.append({"type": "file", "name": item.name, "modified": mod_time})
            elif item.is_dir():
                directories.append({"type": "directory", "name": item.name, "modified": mod_time})

        files.sort(key=lambda x: x["modified"], reverse=True)
        directories.sort(key=lambda x: x["modified"], reverse=True)

        files = [{"type": f["type"], "name": f["name"]} for f in files]
        directories = [{"type": d["type"], "name": d["name"]} for d in directories]

        return {
            "current_path": str(full_path.relative_to(ROOT_DIR)),
            "parent_path": str(full_path.parent.relative_to(ROOT_DIR)) if full_path != ROOT_DIR else None,
            "directories": directories,
            "files": files
        }
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/files/grouped")
async def list_files_grouped():
    """Returns log files grouped by session for heatmap display."""
    try:
        multi_market_pattern = re.compile(r'^(?:COHORT\d+_)?SESSION_(\d+_[a-f0-9]+)_MARKET_(\d+)\.log$', re.IGNORECASE)
        single_market_pattern = re.compile(r'^(?:COHORT\d+_)?SESSION_(\d+_[a-f0-9]+)_trading\.log$', re.IGNORECASE)
        cohort_market_pattern = re.compile(r'^COHORT\d+_SESSION_(\d+_[a-f0-9]+)_trading_market(\d+)\.log$', re.IGNORECASE)
        # New format: T{treatment}_M{market}_{timestamp}.log
        new_format_pattern = re.compile(r'^T(\d+)_M(\d+)_(\d+)\.log$')

        sessions = {}
        ungrouped = []
        max_market = 0

        for item in ROOT_DIR.iterdir():
            if not item.is_file() or not item.name.endswith('.log'):
                continue
            filename = item.name
            session_id = None
            market_num = None
            match = new_format_pattern.match(filename)
            if match:
                # T0_M0_1775690467.log → session_id="T0", market_num=0
                session_id = f"T{match.group(1)}"
                market_num = int(match.group(2))
            else:
                match = multi_market_pattern.match(filename)
                if match:
                    session_id = match.group(1)
                    market_num = int(match.group(2))
                else:
                    match = cohort_market_pattern.match(filename)
                    if match:
                        session_id = match.group(1)
                        market_num = int(match.group(2))
                    else:
                        match = single_market_pattern.match(filename)
                        if match:
                            session_id = match.group(1)
                            market_num = 1
            if session_id is not None:
                max_market = max(max_market, market_num)
                if session_id not in sessions:
                    sessions[session_id] = {'markets': {}}
                sessions[session_id]['markets'][market_num] = filename
            else:
                ungrouped.append(filename)

        session_list = []
        for session_id, data in sorted(sessions.items(), key=lambda x: x[0], reverse=True):
            session_list.append({'session_id': session_id, 'markets': data['markets']})

        return {'sessions': session_list, 'max_market': max_market, 'ungrouped': ungrouped}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/files/download-all")
async def download_all_logs(_=Depends(get_current_admin_user)):
    """Download all experiment data (logs, parameters, questionnaire, consent) as a single zip."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"experiment_data_{ts}.zip"
    out = Path(tempfile.gettempdir()) / filename

    proc = await asyncio.create_subprocess_exec(
        "zip", "-r0q", str(out), ".",
        "-x", "*.gz", "*.tar", "*.zip",
        cwd=str(ROOT_DIR),
    )
    rc = await proc.wait()
    if rc != 0:
        raise HTTPException(status_code=500, detail="Failed to build archive")

    return FileResponse(out, media_type="application/zip", filename=filename)


@router.get("/files/{file_path:path}")
async def get_file(file_path: str):
    try:
        full_path = (ROOT_DIR / file_path).resolve()

        if not full_path.is_relative_to(ROOT_DIR):
            raise HTTPException(status_code=403, detail="Access denied")

        if not full_path.is_file():
            raise HTTPException(status_code=404, detail="File not found")

        return FileResponse(full_path)
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")
