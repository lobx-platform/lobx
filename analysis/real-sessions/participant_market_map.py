"""Map each available market logfile to a single session/group identifier.

This script does not change existing outputs. Run it independently, or
add it before generate_statistics_by_folder.py in main.py later.

Input:
    <BASE_DIR>/<FOLDER>/Logfiles/*.log
    <BASE_DIR>/<FOLDER>/Logfiles/parameters/parameter_history.json

Output:
    <BASE_DIR>/<FOLDER>/Daystatistics/participant_market_<DATE>.csv
"""

import csv
import json
import re
from collections import defaultdict
from pathlib import Path

from settings import BASE_DIR, DATE, FOLDERS, LOGFILES_SUBFOLDER, DAYSTATS_SUBFOLDER


LAB_ID = re.compile(r"LAB_T(\d+)_P(\d+)")
COLUMNS = ["Folder", "Market", "Session_ID", "Status"]


def load_market_assignments(json_path):
    """Index market_start entries by exact market_id, retaining conflicting records."""
    with json_path.open(encoding="utf-8") as f:
        history = json.load(f)

    if not isinstance(history, dict):
        raise ValueError(f"Invalid parameter history (not a JSON object): {json_path}")

    assignments = defaultdict(set)
    for record in history.values():
        if not isinstance(record, dict) or record.get("source") != "market_start":
            continue
        market_id = record.get("market_id")
        if not isinstance(market_id, str) or not market_id:
            continue

        participants = record.get("participants")
        if not isinstance(participants, list) or any(
            not isinstance(p, str) or not p for p in participants
        ):
            assignments[market_id].add(None)
        else:
            assignments[market_id].add(frozenset(participants))
    return assignments


def identify_traders(market_id, assignments):
    """Return (session label, status) for one logfile market ID."""
    
    if market_id.startswith("SESSION_"):
        return "machine_" + market_id, "machine"

    candidates = assignments.get(market_id)
    if not candidates:
        return "Error_missing", "missing"
    if len(candidates) != 1 or None in candidates:
        return "Error_conflated", "conflated"

    participants = next(iter(candidates))
    if not participants:
        return "Error_missing", "missing"
    if len(participants) == 1:
        return next(iter(participants)), "matched"

    # For shared lab markets, build one stable group identifier.
    parsed = [LAB_ID.fullmatch(p) for p in participants]
    if any(match is None for match in parsed):
        return "Error_conflated", "conflated"
    treatments = {int(match.group(1)) for match in parsed}
    numbers = sorted({int(match.group(2)) for match in parsed})
    if len(treatments) != 1 or len(numbers) != len(participants):
        return "Error_conflated", "conflated"

    treatment = treatments.pop()
    return f"LAB_T{treatment}_P" + "_P".join(str(number) for number in numbers), "matched"


def build_rows():
    """Return exactly one mapping row per available .log file."""
    rows = []
    for folder in FOLDERS:
        logs_dir = Path(BASE_DIR) / folder / LOGFILES_SUBFOLDER
        if not logs_dir.is_dir():
            raise FileNotFoundError(f"Logfiles directory not found: {logs_dir}")

        json_path = logs_dir / "parameters" / "parameter_history.json"
        assignments = load_market_assignments(json_path) if json_path.is_file() else {}
        if not json_path.is_file():
            print(f"Warning: metadata file not found: {json_path}")

        for log_path in sorted(logs_dir.glob("*.log")):
            market_id = log_path.stem
            trader, status = identify_traders(market_id, assignments)
            rows.append({"Folder": folder, "Market": market_id,
                         "Session_ID": trader, "Status": status})
    return rows


def main():
    if not FOLDERS:
        raise ValueError("FOLDERS in settings.py must not be empty")

    rows = build_rows()
    output_dir = Path(BASE_DIR) / FOLDERS[0] / DAYSTATS_SUBFOLDER
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"participant_market_{DATE}.csv"

    with output_file.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Saved {len(rows)} market mappings to {output_file}")


if __name__ == "__main__":
    main()
