"""Create a participant-to-market lookup without changing existing analysis outputs.

Run independently with: python participant_market_map.py

For each .log file, match its filename stem exactly to the market_id in
Logfiles/parameters/parameter_history.json. A market with several participants
produces one row per participant. Conflicting metadata is flagged, not guessed.

Output: Daystatistics/participant_market_<DATE>.csv
"""

import csv
import json
from collections import defaultdict
from pathlib import Path

from settings import BASE_DIR, DATE, DAYSTATS_SUBFOLDER, FOLDERS, LOGFILES_SUBFOLDER


def read_market_participants(history_path):
    """Return market ID -> distinct participant sets from market-start records."""
    with history_path.open(encoding="utf-8") as f:
        history = json.load(f)
    if not isinstance(history, dict):
        raise ValueError(f"Expected a JSON object in {history_path}")

    assignments = defaultdict(set)
    for entry in history.values():
        if not isinstance(entry, dict) or entry.get("source") != "market_start":
            continue
        market_id = entry.get("market_id")
        if not isinstance(market_id, str) or not market_id:
            continue
        participants = entry.get("participants")
        if not isinstance(participants, list) or any(
            not isinstance(p, str) or not p for p in participants
        ):
            assignment = None  # Invalid participant data: do not guess.
        else:
            assignment = frozenset(participants)
        assignments[market_id].add(assignment)
    return assignments


def build_rows():
    """Associate every available logfile with metadata, without analysing trades."""
    rows = []
    for folder in FOLDERS:
        logs_dir = Path(BASE_DIR) / folder / LOGFILES_SUBFOLDER
        if not logs_dir.is_dir():
            raise FileNotFoundError(f"Logfiles directory not found: {logs_dir}")

        history_path = logs_dir / "parameters" / "parameter_history.json"
        assignments = (read_market_participants(history_path)
                       if history_path.is_file() else None)

        for log_path in sorted(logs_dir.glob("*.log")):
            market_id = log_path.stem  # Preserve the exact logfile market ID.
            status = None
            if assignments is None:
                status = "history_file_missing"
            else:
                candidates = assignments.get(market_id)
                if not candidates:
                    status = "not_in_history"
                elif len(candidates) != 1 or None in candidates:
                    status = "ambiguous_metadata"
                else:
                    participants = next(iter(candidates))
                    if not participants:
                        status = "no_participants"
                    else:
                        for participant in sorted(participants):
                            rows.append({"Folder": folder, "Market": market_id,
                                         "Participant": participant, "Status": "matched"})
            if status:
                rows.append({"Folder": folder, "Market": market_id,
                             "Participant": "", "Status": status})
    return rows


def main():
    if not FOLDERS:
        raise ValueError("FOLDERS in settings.py must not be empty")
    output_dir = Path(BASE_DIR) / FOLDERS[0] / DAYSTATS_SUBFOLDER
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"participant_market_{DATE}.csv"

    rows = build_rows()
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["Folder", "Market", "Participant", "Status"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} participant-market rows to {output_path}")


if __name__ == "__main__":
    main()
