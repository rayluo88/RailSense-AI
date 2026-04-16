# Plan: Near-Realtime LTA Data Ingestion

## Context

The operations page (`/operations`) currently only displays data that was manually ingested via `python -m src.tasks`. There is no background scheduler — data goes stale immediately. The goal is to poll LTA DataMall APIs periodically so the dashboard stays current without manual intervention.

**Constraint:** Only poll during operating hours (0900–2200 SGT) to avoid wasting resources overnight.

## Deployment & Cost Impact

**Current setup:** Railway Hobby plan ($5/month, $5 credit included). Two services: FastAPI app + PostgreSQL. Estimated $2–4/month.

**Cost impact of adding background polling:**
- **CPU:** Minimal increase. Three lightweight HTTP calls every 5–30 min during 13 hours/day. Each poll takes <2 seconds. This adds maybe 1–2 minutes of CPU per day — negligible on Railway's usage-based billing.
- **Database:** Tiny increase in row inserts. Crowd density: ~11 lines × 6/hr × 13hrs = ~858 rows/day. Disruptions/facilities: a few rows. PostgreSQL on Railway is billed by storage + compute — this is well within the Hobby plan.
- **Memory:** No change — the asyncio tasks share the existing process memory.
- **Network:** ~200 small API calls/day to LTA. Free outbound on Railway.
- **Estimate:** Adds <$0.50/month. Total stays within the $5 credit.

## Approach: asyncio background tasks in FastAPI lifespan

**Why this over alternatives:**
- Prefect deployment needs a Prefect server/worker (overkill for 3 polling tasks)
- APScheduler adds a dependency for something asyncio does natively
- Separate Docker service adds operational complexity

An `asyncio.Task` in the FastAPI lifespan is zero new dependencies, idiomatic async Python, and demonstrates structured concurrency — good for a portfolio project.

## Poll Intervals

| Data type | LTA update freq | Our interval | Active hours |
|---|---|---|---|
| Disruptions | Ad-hoc | **5 min** | 0900–2200 SGT |
| Crowd density | Every 10 min | **10 min** | 0900–2200 SGT |
| Facilities | Ad-hoc (rare) | **30 min** | 0900–2200 SGT |

Outside 0900–2200 SGT, the scheduler sleeps and makes no API calls.

## Implementation Steps

### 1. Extract DB write helpers → `src/ingestion/writers.py` (new)

Extract the DB-write logic from `src/tasks.py` (lines ~77-199) into plain functions:
- `write_disruptions(db, disruptions) -> int`
- `write_crowd_density(db, records) -> int`
- `write_facilities(db, facilities) -> int`

Both `src/tasks.py` (Prefect) and the new scheduler will call these — no duplication.

### 2. Create `src/scheduler.py` (new)

- `_is_operating_hours() -> bool` — checks if current SGT time is between 0900–2200
- `_run_forever(name, interval, coro_fn)` — generic async loop with error handling; skips execution outside operating hours (sleeps 60s then rechecks)
- Three async ingestion coroutines calling `LtaClient` + writers
- `start_scheduler() -> list[asyncio.Task]` — launches all three, returns handles
- Module-level `_status` dict tracking last run time + record count per data type
- Guard: skip scheduling if `lta_api_key` is empty

### 3. Modify `src/config.py`

Add to `Settings`:
```python
enable_scheduler: bool = True
scheduler_start_hour: int = 9    # SGT
scheduler_end_hour: int = 22     # SGT
```

### 4. Modify `src/api/main.py`

- Import and call `start_scheduler()` in lifespan (guarded by `settings.enable_scheduler`)
- Cancel tasks on shutdown via `asyncio.gather(*tasks, return_exceptions=True)`
- Add `GET /api/scheduler/status` endpoint returning last run times + active/sleeping state

### 5. Modify `src/templates/lta_operations.html`

Add `<meta http-equiv="refresh" content="300">` for auto-refresh every 5 minutes.

### 6. Update `src/tasks.py`

Refactor to call the shared writers from step 1.

## Files

| File | Action |
|---|---|
| `src/ingestion/writers.py` | Create |
| `src/scheduler.py` | Create |
| `src/config.py` | Modify — add scheduler settings |
| `src/api/main.py` | Modify — lifespan + status endpoint |
| `src/templates/lta_operations.html` | Modify — meta refresh |
| `src/tasks.py` | Modify — use shared writers |

## Verification

1. `uv run python -c "from src.scheduler import start_scheduler"` — import check
2. `uv run pytest` — existing tests still pass
3. `docker compose up` → wait 5 min → check `/operations` shows fresh data
4. `curl localhost:8000/api/scheduler/status` → shows last run times and active/sleeping
5. Operations page auto-refreshes in browser
6. Verify scheduler sleeps outside 0900–2200 SGT (check logs)
