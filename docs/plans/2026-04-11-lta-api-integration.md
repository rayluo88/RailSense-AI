# Plan: Integrate Real LTA DataMall APIs into RailSense-AI

## Context

The RailSense-AI project has a dormant `LtaClient` that points at real LTA DataMall endpoints but is never called from the pipeline. The `PCDRealTime` method is also broken — it parses crowd density data as train arrivals. Meanwhile the entire pipeline runs on synthetic sensor data only.

Integrating real LTA data (disruptions, crowd density, facilities maintenance) adds significant credibility to the portfolio project. The real data serves as **operational context enrichment** — the AI agent can correlate synthetic sensor anomalies with real-world events. LTA does not expose equipment telemetry publicly, so synthetic sensors remain the core detection pipeline.

---

## Phase 1: Database & Client (foundation)

### 1.1 Add new DB models — `src/db/models.py`

**New table: `lta_crowd_density`**
| Column | Type | Notes |
|--------|------|-------|
| id | Integer PK | |
| timestamp | DateTime, indexed | StartTime from API |
| end_time | DateTime | |
| station_code | String(10), indexed | e.g. EW13 |
| train_line | String(10), indexed | e.g. EWL |
| crowd_level | String(5) | l, m, h, NA |
| source | String(10) | "realtime" or "forecast" |
| fetched_at | DateTime | when we polled |

Composite index: `(train_line, station_code, timestamp)`

**New table: `lta_facilities_maintenance`**
| Column | Type | Notes |
|--------|------|-------|
| id | Integer PK | |
| station_code | String(10), indexed | |
| station_name | String(100) | |
| train_line | String(10) | |
| equipment_type | String(20) | "Lift" for now |
| equipment_id | String(50) | LiftID |
| description | Text | LiftDesc |
| fetched_at | DateTime, indexed | |

**Extend existing `lta_disruptions` table** — add nullable columns:
- `status` String(10) — "1" (minor) or "2" (major)
- `affected_stations` Text — raw station range
- `free_bus` Text
- `free_shuttle` Text
- `fetched_at` DateTime

### 1.2 Alembic migration

```bash
alembic revision --autogenerate -m "add_lta_crowd_facilities_tables"
alembic upgrade head
```

### 1.3 Fix and extend `src/ingestion/lta_client.py`

**Fix:** Remove broken `get_train_arrivals` and `parse_train_arrival` (PCDRealTime returns crowd density, not arrivals).

**Fix:** `get_disruptions()` — the `CreateDate` field doesn't exist in AffectedSegments. Use current timestamp. Also capture top-level `Status` field and per-segment `Stations`, `FreePublicBus`, `FreeMRTShuttle`.

**Add methods:**

```python
async def get_crowd_density_realtime(self, train_line: str) -> list[dict]:
    # GET /PCDRealTime?TrainLine={train_line}
    # Parse: Station, StartTime, EndTime, CrowdLevel

async def get_crowd_density_forecast(self, train_line: str) -> list[dict]:
    # GET /PCDForecast?TrainLine={train_line}
    # Parse: Date, Station, Start, CrowdLevel

async def get_facilities_maintenance(self) -> list[dict]:
    # GET /v2/FacilitiesMaintenance
    # Parse: Line, StationCode, StationName, LiftID, LiftDesc
```

### 1.4 Update tests — `tests/test_lta_client.py`

Add parse tests for each new method with mocked httpx responses.

---

## Phase 2: Ingestion Tasks — `src/tasks.py`

### 2.1 Add LTA ingestion tasks

```python
@task
async def ingest_lta_disruptions():
    # Poll TrainServiceAlerts, upsert to lta_disruptions
    # Deduplicate on (line_id, message_hash, timestamp rounded to 5min)

@task
async def ingest_lta_crowd_density():
    # Iterate all 11 lines: CCL, CEL, CGL, DTL, EWL, NEL, NSL, BPL, SLRT, PLRT, TEL
    # Call get_crowd_density_realtime(line) for each
    # Bulk insert to lta_crowd_density with source="realtime"
    # Add 0.5s delay between lines to avoid rate limiting

@task
async def ingest_lta_facilities():
    # Call get_facilities_maintenance()
    # Upsert to lta_facilities_maintenance (dedupe on station_code + equipment_id)
```

### 2.2 Wire into flow

Add the three tasks to `ingestion_detection_flow()` after the existing synthetic pipeline. They run independently and don't block detection.

---

## Phase 3: Agent Context Enrichment

### 3.1 Extend `AnomalyContext` — `src/agent/provider.py`

Add three new optional fields:
```python
active_disruptions: list[dict] = field(default_factory=list)
crowd_levels: list[dict] = field(default_factory=list)
facilities_issues: list[dict] = field(default_factory=list)
```

### 3.2 Update prompts — `src/agent/prompts.py`

**System prompt addition:** Instruct the agent to use LTA operational data — correlate sensor anomalies with disruptions, crowd levels, and maintenance events.

**User template addition:**
```
Active Disruptions on {line_id}: {active_disruptions}
Current Crowd Density: {crowd_levels}
Facilities Under Maintenance: {facilities_issues}
```

### 3.3 Enrich assess endpoint — `src/api/main.py`

In `assess_anomaly()`, after fetching the anomaly event, query:
1. `lta_disruptions` matching `event.line_id` from last 24h
2. `lta_crowd_density` matching `event.line_id` from last hour
3. `lta_facilities_maintenance` matching `event.line_id` (latest fetch)

Pass all three into `AnomalyContext`.

---

## Phase 4: API & Dashboard

### 4.1 New API endpoints — `src/api/main.py` + `src/api/schemas.py`

```
GET /api/disruptions?line_id=NSL&limit=50
GET /api/crowd-density?train_line=NSL&limit=100
GET /api/facilities?train_line=NSL
```

Add corresponding Pydantic response schemas.

### 4.2 Dashboard queries — `src/dashboard/queries.py`

```python
def get_operations_overview(db) -> dict:
    # Aggregate: active disruptions, current crowd by line, facilities under maintenance

def get_crowd_density_data(db, train_line=None) -> dict:
    # Latest crowd snapshot per station, grouped by line

def get_facilities_data(db, train_line=None) -> dict:
    # Active maintenance events
```

### 4.3 New dashboard page — `src/templates/lta_operations.html`

- **Service Alerts** — table of active disruptions with status badge (minor/major), line, direction, affected stations
- **Station Crowd Density** — color-coded table by line (green=low, yellow=moderate, red=high)
- **Facilities Maintenance** — table of lifts under maintenance

### 4.4 Update overview — `src/templates/overview.html`

Add a "Service Disruptions" card showing active disruption count with line badges.

### 4.5 Navigation — `src/templates/base.html`

Add "LTA Operations" nav item → `/operations`

---

## Phase 5: Config & .env

### 5.1 Set API key in `.env`
```
LTA_API_KEY=<key>
```

### 5.2 Optional: add polling intervals to `src/config.py`
```python
lta_crowd_interval_minutes: int = 10
lta_disruptions_interval_minutes: int = 5
```

---

## Verification

1. **Client unit tests** — mock httpx, verify parsing for all 4 endpoints
2. **Live API smoke test** — run each client method once, confirm real data returns
3. **DB integration** — run flow, verify rows in `lta_crowd_density`, `lta_disruptions`, `lta_facilities_maintenance`
4. **Agent enrichment** — trigger `POST /api/assess/{id}`, verify LLM response references crowd/disruption context
5. **Dashboard** — visit `/operations`, confirm all three panels render
6. **Idempotency** — run flow twice rapidly, verify no duplicate disruption/facilities rows

---

## Files to Modify/Create

| File | Action |
|------|--------|
| `src/db/models.py` | Add CrowdDensity, FacilitiesMaintenance models; extend LtaDisruption |
| `alembic/versions/xxx_add_lta_tables.py` | New migration (auto-generated) |
| `src/ingestion/lta_client.py` | Fix PCDRealTime parsing, add 3 new methods, fix disruptions |
| `src/tasks.py` | Add 3 LTA ingestion tasks, wire into flow |
| `src/agent/provider.py` | Extend AnomalyContext with 3 new fields |
| `src/agent/prompts.py` | Add operational context to system + user prompts |
| `src/api/main.py` | Enrich assess endpoint, add 3 new API routes |
| `src/api/schemas.py` | Add DisruptionOut, CrowdDensityOut, FacilitiesOut schemas |
| `src/dashboard/queries.py` | Add operations query functions |
| `src/dashboard/routes.py` | Add /operations route |
| `src/templates/lta_operations.html` | New page (create) |
| `src/templates/overview.html` | Add disruptions card |
| `src/templates/base.html` | Add nav item |
| `src/config.py` | Add optional polling intervals |
| `.env` | Set LTA_API_KEY |
| `tests/test_lta_client.py` | Update tests for fixed/new methods |
