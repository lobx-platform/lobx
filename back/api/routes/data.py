"""Data routes: /files, /files/grouped, /files/{path}, /files/download-all"""

import io
import re
import zipfile
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import FileResponse, StreamingResponse

from ..auth import get_current_admin_user
from ..shared import ROOT_DIR

router = APIRouter()


@router.get("/files")
async def list_files(path: str = Query("", description="Relative path to browse"), _=Depends(get_current_admin_user)):
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
async def list_files_grouped(_=Depends(get_current_admin_user)):
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
async def download_all_logs(pattern: str = Query("", description="Filter by filename pattern"), _=Depends(get_current_admin_user)):
    """Download log files as a zip archive. Use ?pattern=T0_ to filter."""

    def create_zip(pattern_filter):
        buf = io.BytesIO()
        count = 0
        try:
            with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as zf:  # STORED is faster than DEFLATED for streaming
                # Add log files
                for item in ROOT_DIR.iterdir():
                    if not item.is_file() or not item.name.endswith(".log"):
                        continue
                    if pattern_filter and pattern_filter not in item.name:
                        continue
                    zf.write(item, item.name)
                    count += 1
                # Include questionnaire data if exists
                q_dir = ROOT_DIR / "questionnaire"
                if q_dir.is_dir():
                    for item in q_dir.iterdir():
                        if item.is_file():
                            zf.write(item, f"questionnaire/{item.name}")
                            count += 1
            if count == 0:
                raise ValueError("No log files found")
            buf.seek(0)
            return buf, count
        except Exception as e:
            raise

    try:
        # Run zip creation in thread pool to avoid blocking event loop
        executor = ThreadPoolExecutor(max_workers=1)
        loop = __import__('asyncio').get_event_loop()
        buf, count = await loop.run_in_executor(executor, create_zip, pattern)
        return StreamingResponse(
            buf,
            media_type="application/zip",
            headers={"Content-Disposition": "attachment; filename=lobx_logs.zip"},
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating zip: {str(e)}")


@router.get("/files/{file_path:path}")
async def get_file(file_path: str, _=Depends(get_current_admin_user)):
    try:
        full_path = (ROOT_DIR / file_path).resolve()

        if not full_path.is_relative_to(ROOT_DIR):
            raise HTTPException(status_code=403, detail="Access denied")

        if not full_path.is_file():
            raise HTTPException(status_code=404, detail="File not found")

        return FileResponse(full_path)
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")
