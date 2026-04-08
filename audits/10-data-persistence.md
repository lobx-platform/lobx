# Audit 10 -- Data Persistence & Storage

**Date:** 2026-04-08
**Scope:** How experiment data is stored, retrieved, and analyzed; integrity and scalability concerns.
**Files reviewed:** `back/utils/logfiles_analysis.py`, `back/utils/calculate_metrics.py`, `back/core/parameter_logger.py`, `back/api/routes/questionnaire.py`, `back/api/routes/data.py`, `back/core/data_models.py`, `back/core/handlers.py`, `back/utils/utils.py`, `docker-compose.yml`, `config/app.yaml`, `back/logs/` directory.

---

## 1. Current Storage Architecture

The platform uses **no database**. All persistent data is stored as flat files on disk, spread across several formats and locations under `back/logs/`:

| Data Type | Format | Location | Write Mechanism |
|---|---|---|---|
| **Trading activity** (orders, matches, cancellations) | `.log` (Python `logging.FileHandler`) | `logs/SESSION_*_MARKET_*.log` | `setup_trading_logger()` in `utils/utils.py` |
| **Parameter history** | Single JSON file (append-by-key) | `logs/parameters/parameter_history.json` | `ParameterLogger._save_history()` -- full rewrite on each entry |
| **Questionnaire responses** | Per-trader JSON files | `logs/questionnaire/{trader_id}.json` | Full rewrite with `json.dump()` on each interaction |
| **Consent records** | Single CSV (append mode) | `logs/consent/consent_data.csv` | `csv.DictWriter` append |
| **LLM monitor decisions** | Per-market JSON files | `logs/monitor/SESSION_*_MONITORED_*.json` | JSON dump per market |
| **Agentic trader logs** | Per-market JSON files | `logs/agentic/SESSION_*_MARKET_*.json` | JSON dump per market |

**Current scale:**
- 4,488 files totaling **4.9 GB** in `back/logs/`
- 4,476 `.log` files at the top level alone, of which **1,499 are empty** (33% -- failed/aborted markets)
- 55 monitor logs, 1,026 agentic logs

**Notable:** `config/app.yaml` references MongoDB (host, port, collection name) and Parquet data files, but **no MongoDB client is imported or used anywhere in the backend code**. These appear to be vestigial references from an earlier architecture that was never fully implemented or was abandoned.

---

## 2. Is File-Based Storage Appropriate?

### What works

- **Trading logs (`.log` files) are a reasonable choice for their specific purpose.** Each market gets its own file. Python's `logging` module handles buffered writes efficiently. The append-only nature matches the event stream semantics of order flow data. One file per market means no contention between concurrent markets.
- **The format is human-readable**, which helps during debugging and development.
- **No external dependencies** -- no database server to install, configure, or maintain. For a research platform with a small team, this is a genuine advantage.

### What does not work

1. **No queryability.** To answer "how many trades did user X make across all sessions?" requires scanning hundreds of log files and parsing each one line by line. The analysis code in `logfiles_analysis.py` (637 lines) is essentially a hand-written log parser with multiple fallback paths for malformed data.

2. **No relational integrity.** There is no systematic link between a trading log, its parameter configuration, the questionnaire responses from participants in that market, and their consent records. Joining these datasets for analysis requires manual cross-referencing by session ID patterns embedded in filenames.

3. **The parameter history file is a scalability bottleneck.** `ParameterLogger._save_history()` loads the entire JSON file into memory, adds one entry, then rewrites the entire file. After thousands of parameter changes, this file will grow large and every write will become slower.

4. **One-third of log files are empty.** 1,499 out of 4,476 log files are 0 bytes -- artifacts of markets that were created but never ran. There is no cleanup mechanism and no way to distinguish "empty because it failed" from "empty because it hasn't started yet" without checking external state.

5. **Questionnaire data uses per-file JSON** that is entirely rewritten on each interaction. For a platform supporting many concurrent users, this means frequent full-file rewrites.

---

## 3. Should They Add a Database?

### Recommendation: Yes, but scoped carefully

The platform would benefit from a **lightweight relational database for metadata and results**, while **keeping the existing log files for raw trading data**. This is a hybrid approach.

#### SQLite: the right fit here

| Factor | SQLite | PostgreSQL |
|---|---|---|
| Deployment complexity | Zero -- single file, no server | Requires server process, Docker service |
| Concurrent writes | Limited (one writer at a time with WAL mode) | Excellent |
| Data volume | Handles GB-scale well | Designed for TB-scale |
| Query capability | Full SQL | Full SQL + advanced extensions |
| Portability | Copy one file to share the entire dataset | Requires export/import |
| Team size | Small teams (perfect for 5-person research group) | Larger teams with ops support |

**SQLite is the right choice** because:
- The platform runs as a **single backend process** (one `uvicorn` instance). There is no multi-process write contention.
- The data volume is modest (4.9 GB accumulated over months).
- The team values **portability** -- SQLite databases can be attached directly to analysis notebooks.
- PostgreSQL would add operational burden (Docker service, connection management, migrations) that is disproportionate for a research platform of this scale.
- SQLite's WAL mode handles the platform's concurrency pattern well: many reads (analysis, admin panel) and sequential writes (the asyncio event loop is single-threaded, and orders are processed under an `asyncio.Lock`).

#### What to put in the database

| Table | Source of Data | Purpose |
|---|---|---|
| `sessions` | Session manager | Session ID, start time, treatment config, status |
| `markets` | Market orchestrator | Market ID, session FK, parameters snapshot, start/end time, log file path |
| `participants` | Session manager | Username, session FK, market FK, role, goal, treatment group |
| `trades` | Matched order events | Timestamp, market FK, buyer, seller, price, amount |
| `questionnaire_responses` | Questionnaire routes | Participant FK, market number, question, answer, timestamp |
| `consent` | Consent routes | Participant ID, timestamp, consent given |
| `parameter_changes` | Parameter logger | Timestamp, parameter name, old value, new value, source |

#### What to keep as files

- **Raw trading logs (`.log`)**: These are the ground truth, append-only event streams. Keep them as-is. They are the equivalent of write-ahead logs -- immutable, ordered records of everything that happened.
- **Agentic/monitor JSON logs**: These are debugging artifacts for LLM behavior. File-based storage is appropriate.

---

## 4. Post-Hoc Analysis Pipeline

There are **two separate log analysis implementations** that partially overlap:

### `logfiles_analysis.py` (pandas-based, 637 lines)
- `logfile_to_message()`: Parses `.log` files line by line using string splitting (`line.split(" - ", 2)`), then `ast.literal_eval` with extensive fallback string parsing.
- `process_logfile()`: Reconstructs the order book from the parsed events, replaying every ADD_ORDER and CANCEL_ORDER to track bids/asks, midprices, and per-trader PnL.
- `calculate_trader_specific_metrics()`: Computes VWAP, slippage, penalized VWAP, and reward for goal-based traders.

### `calculate_metrics.py` (polars-based, 111 lines)
- `parse_log_line()`: Uses regex to parse log lines, then `ast.literal_eval`.
- `process_log_file()`: Reconstructs order book state at each message, producing a LOBSTER-format-compatible output.
- `write_to_csv()`: Exports to CSV for further analysis.

### Problems with the analysis pipeline

1. **Two parsers for the same data.** Both parse the same `.log` files but with different approaches (pandas vs. polars), different output formats, and different error handling. This is a maintenance risk -- a change to the log format could break one parser but not the other.

2. **Brittle log parsing.** The log format includes Python `repr()` output of enum values (`<OrderType.BID: 1>`) and `datetime.datetime(...)` constructors. Both parsers have extensive workarounds (string replacement, regex substitution) to handle these non-standard representations. This is fragile -- any change to the `Order` model's `__repr__` will silently break parsing.

3. **No schema validation.** Parsed data is never validated against an expected schema. Malformed entries are silently skipped with a `print()` warning (not even logged).

4. **Full replay required for every analysis.** To compute any metric for a market, the entire order book must be reconstructed from scratch by replaying every event. There is no pre-computed summary or intermediate state.

5. **The `__main__` block references a hardcoded local path** (`/Users/marioljonuzaj/Documents/...`), confirming this is used as a standalone script rather than an integrated pipeline.

---

## 5. Data Integrity Concerns

### Concurrent write safety

| Data Type | Concurrency Control | Risk Level |
|---|---|---|
| Trading logs | Python `logging.FileHandler` (thread-safe, but one handler per market) | **Low** -- each market has its own log file and logger instance |
| Parameter history | None -- full JSON rewrite with no locking | **Medium** -- if two admin actions overlap, last write wins (data loss) |
| Questionnaire | `asyncio.Lock` per trader ID | **Low** -- properly serialized within the async event loop |
| Consent CSV | `open(file, mode='a')` -- append mode, no locking | **Medium** -- concurrent appends could interleave on some OS/filesystem combinations, though unlikely with single-process asyncio |

### Crash recovery

- **Trading logs:** Python's `logging.FileHandler` does not call `fsync()`. On crash, the OS write buffer may lose the last few log entries. For a 3-minute trading day, this could mean losing the final seconds of a market.
- **Parameter history:** A crash during `_save_history()` (which does a full JSON rewrite) could produce a truncated/corrupted JSON file, losing the entire parameter history. There is no atomic write pattern (write-to-temp-then-rename).
- **Questionnaire data:** Same risk as parameter history -- full JSON rewrite without atomic write.
- **No checksums or integrity verification** on any stored data.

### Data loss scenarios

1. **Docker volume not mounted:** If `./back/logs:/app/logs:Z` is misconfigured or the volume is recreated, all data is lost. There is no backup mechanism.
2. **Disk full:** With 4.9 GB of logs and growing, a constrained deployment (e.g., small cloud VM) could hit disk limits. There is no monitoring or alerting for disk usage.
3. **Log rotation:** There is no log rotation configured for trading logs. Individual log files can grow to 2.5 MB each (observed), and with batch experiments generating thousands of markets, disk usage will grow linearly without bound.

---

## 6. Recommendations

### Priority 1: Protect existing data (immediate)

- **Add atomic writes to `ParameterLogger._save_history()` and `_write_trader_data()`**: Write to a temp file, then `os.rename()` to the final path. This is a 5-line change that prevents data corruption on crash.
- **Clean up empty log files**: Add a post-market cleanup step that removes `.log` files with 0 bytes, or better, don't create the log file until the first event is written.

### Priority 2: Add SQLite for structured data (next sprint)

- Create a `experiment.db` SQLite database with tables for sessions, markets, participants, trades, and questionnaire responses.
- Populate it from the existing orchestration code at the natural event points (market start, trade match, market end, questionnaire submission).
- Keep raw `.log` files as the immutable audit trail.
- This enables SQL-based analysis: `SELECT AVG(vwap) FROM trades WHERE treatment = 'high_informed' GROUP BY session_id` instead of replaying 4,000 log files.

### Priority 3: Unify the analysis pipeline (medium term)

- Choose one log parser (the polars-based `calculate_metrics.py` is cleaner and faster) and deprecate the other.
- Better yet, if trades are stored in SQLite at write time, most analysis can be done with SQL queries or direct DataFrame loads (`pd.read_sql()` / `pl.read_database()`), eliminating the need for log parsing entirely.
- Log files become a fallback for debugging and auditing, not the primary analysis input.

### Priority 4: Fix the log format (medium term)

- Log structured JSON instead of Python `repr()` output. Replace:
  ```
  ADD_ORDER: {'id': 'X', 'order_type': <OrderType.BID: 1>, 'timestamp': datetime.datetime(2026, 1, 29, ...)}
  ```
  with:
  ```json
  {"event": "ADD_ORDER", "id": "X", "order_type": 1, "timestamp": "2026-01-29T18:05:33.371Z"}
  ```
  This eliminates the need for the fragile `ast.literal_eval` + regex workarounds in both parsers.

### What NOT to do

- **Do not add PostgreSQL or MongoDB.** The operational overhead is not justified for a 5-person research team running experiments on a single server. SQLite covers the query needs without adding infrastructure complexity.
- **Do not replace log files with database writes for trading events.** The append-only log is a valuable audit trail and is the correct abstraction for high-frequency event streams. Write to both: log for auditability, database for queryability.
- **Do not build a custom ORM or migration framework.** Use SQLite directly with raw SQL or a lightweight library like `sqlite-utils`. The schema is simple enough that an ORM adds no value.

---

## Summary

The platform's file-based storage was a reasonable starting point but has outgrown its design. The core issue is not that files are used -- log files are appropriate for trading event streams -- but that **queryable, relational data** (sessions, participants, treatments, outcomes) is also stored as unstructured files, making cross-cutting analysis unnecessarily difficult. Adding a single SQLite database for structured metadata, while keeping log files for raw events, would resolve the main pain points with minimal architectural disruption.

---

## Sources

- [Best practices for data management in experimental research (APS)](https://journals.physiology.org/doi/full/10.1152/physrev.00043.2023)
- [Storing Market Data Efficiently (TimeStored)](https://www.timestored.com/data/store-market-tick-data)
- [How to store financial market data for backtesting (Medium)](https://medium.com/data-science/how-to-store-financial-market-data-for-backtesting-84b95fc016fc)
- [PostgreSQL vs SQLite: Which Wins in 2026? (SelectHub)](https://www.selecthub.com/relational-database-solutions/postgresql-vs-sqlite/)
- [SQLite vs PostgreSQL Performance Comparison 2026 (Medium)](https://medium.com/pythonic-af/sqlite-vs-postgresql-performance-comparison-46ba1d39c9c8)
- [SQLite vs PostgreSQL: A Detailed Comparison (DataCamp)](https://www.datacamp.com/blog/sqlite-vs-postgresql-detailed-comparison)
- [Cloud-based evaluation of databases for stock market data (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC9520093/)
