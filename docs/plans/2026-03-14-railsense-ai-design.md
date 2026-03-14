# RailSense-AI: Intelligent Railway Anomaly Detection & Reasoning Platform

## Overview

A full-stack data pipeline and dashboard that detects anomalies in railway time-series sensor data and uses LLM-based reasoning to classify, prioritize, and recommend actions. Built to demonstrate skills aligned with LTA's Railway Common Data Platform (CDP) Senior Data Scientist role.

Deployed as a Docker-compose stack with FastAPI backend, Streamlit frontend, and PostgreSQL storage.

## Architecture

Three layers:

1. **Data Ingestion Layer** — Pulls real LTA data (train arrivals, disruption alerts) from DataMall API on a schedule, and generates synthetic sensor streams (vibration, temperature, door cycles, current draw) that correlate with real operational patterns. Stored in PostgreSQL with time-series optimized schema.

2. **Detection & Analysis Layer** — Multiple anomaly detection models run against incoming sensor data: statistical baselines (Z-score, rolling statistics), Isolation Forest for multivariate anomalies, and forecast-based detection (STL decomposition vs Prophet comparison) that flags deviations from expected patterns. Detected anomalies are enriched with contextual metadata.

3. **AI Reasoning Layer** — An LLM agent receives enriched anomaly events and performs root cause hypothesis, severity classification, and recommended action generation. Uses function-calling to query historical patterns.

**Data flow:** LTA API + Synthetic Generator → FastAPI ingestion endpoints → PostgreSQL → Detection engine (scheduled) → Anomaly events → LLM Agent → Classified alerts → Streamlit dashboard

## Data Layer

### Real data from LTA DataMall API

- Train arrival times — derive delay patterns per line/station
- Platform crowd density — correlates with operational stress
- Train disruption alerts — ground truth for anomaly validation (when a real disruption happened, did our sensors flag it?)

### Synthetic sensor streams (per train unit)

| Sensor | Baseline | Anomaly Pattern |
|---|---|---|
| Vibration (g-force) | ~0.3g with noise | Bearing wear, wheel flats |
| Temperature (°C) | Ambient + load curve | Motor overheating |
| Door cycle time (ms) | ~2.5s per open/close | Gradual degradation |
| Current draw (A) | Traction motor baseline | Electrical fault spikes |

The synthetic generator produces realistic data: follows daily ridership patterns (peak hours = higher load = higher baseline temps), injects gradual degradation trends (not just random spikes), and plants correlated multi-sensor anomalies (e.g., bearing failure shows in both vibration AND temperature simultaneously).

### PostgreSQL schema (key tables)

- `sensor_readings` — timescale-partitioned by day: timestamp, train_id, sensor_type, value, line_id, station_id
- `anomaly_events` — detected anomalies with detection method, severity, raw scores
- `agent_assessments` — LLM agent outputs: classification, reasoning, recommended action
- `lta_disruptions` — real disruption data for validation

## Detection Engine

Three complementary detection methods:

### 1. Statistical Baseline (Z-score + rolling thresholds)

- Per sensor per train unit, maintain 7-day rolling mean and standard deviation
- Flag readings beyond 3σ as anomalies, 2σ as warnings
- Fast, interpretable, good for sudden spikes

### 2. Isolation Forest (multivariate)

- Trained on feature vectors combining all four sensor types per train unit
- Catches anomalies visible only in sensor relationships (e.g., vibration normal alone but abnormal given current temperature)
- Retrained weekly on latest clean data window

### 3. Forecast-based detection (STL vs Prophet comparison)

Both methods run on the same sensor streams for empirical comparison:

- **STL decomposition** — Decompose into trend + seasonal + residual, flag residuals exceeding thresholds. Lighter, more principled for sensor data.
- **Prophet** — Forecast incorporating daily/weekly seasonality and ridership-driven trends. Anomaly = significant deviation from forecast.
- Evaluate on: detection accuracy against planted anomalies, false positive rate, computation time, interpretability
- Whichever wins becomes default; the other remains available

### Ensemble scoring

- Each method produces a normalized anomaly score (0–1)
- Weighted combination with agreement between methods boosting confidence
- Thresholds: info (0.4–0.6), warning (0.6–0.8), critical (0.8+)
- Only warning+ events forwarded to LLM agent (reduces noise and API cost)

## AI Reasoning Agent

### Context packet sent to agent

- Anomaly details: sensor type, value, score, detection method(s) that triggered
- Train unit context: line, current station, recent maintenance history
- Temporal context: time of day, peak/off-peak, day of week
- Historical patterns: has this train/sensor shown similar readings before?
- Correlated signals: are other sensors on the same unit also abnormal?

### Agent tasks (single prompt chain)

1. **Root cause hypothesis** — e.g., "Simultaneous vibration increase and temperature rise on bogie 2 suggests possible bearing degradation, consistent with 3-day upward trend"
2. **Severity classification** — critical / warning / monitor, with reasoning. Can override statistical severity based on context (e.g., moderate anomaly during peak hours on a line with no backup escalates)
3. **Recommended action** — immediate inspection, schedule maintenance within N days, continue monitoring, or suppress (false alarm with explanation)

### Implementation

LLM abstracted behind a provider protocol:

```python
class LLMProvider(Protocol):
    async def analyze_anomaly(self, context: AnomalyContext) -> AgentAssessment: ...
```

Concrete implementations: Claude (default), OpenAI, Ollama (local). Selected via `LLM_PROVIDER` environment variable. Prompt template shared across providers.

**Future enhancement:** Full agentic workflow where the agent autonomously creates work orders, escalates to supervisors, schedules predictive maintenance, or suppresses false alarms using tool-calling patterns.

## Dashboard (Streamlit)

### 1. Live Overview

Map of MRT lines with color-coded health status per segment. Summary cards: active alerts, trains monitored, anomalies detected today, system health score.

### 2. Sensor Explorer

Select a train unit → real-time sensor charts (vibration, temp, door, current) with anomaly regions highlighted. Toggle detection method overlays to see which method flagged what.

### 3. Alert Feed

Chronological anomaly events with LLM agent assessment inline: root cause, severity badge, recommended action. Click to expand full reasoning chain. Filter by line, severity, sensor type.

### 4. Model Comparison

STL vs Prophet side-by-side on the same data window. Metrics table: precision, recall, F1 against known planted anomalies, computation time. Visual overlay of predicted vs actual with residual bands.

## Project Structure

```
railsense-ai/
├── docker-compose.yml
├── src/
│   ├── ingestion/
│   │   ├── lta_client.py
│   │   └── synthetic_gen.py
│   ├── detection/
│   │   ├── zscore.py
│   │   ├── isolation_forest.py
│   │   ├── stl_detector.py
│   │   ├── prophet_detector.py
│   │   └── ensemble.py
│   ├── agent/
│   │   ├── provider.py
│   │   ├── claude_provider.py
│   │   ├── openai_provider.py
│   │   ├── ollama_provider.py
│   │   └── prompts.py
│   ├── api/
│   │   └── main.py
│   └── dashboard/
│       └── app.py
├── tests/
├── scripts/
│   └── seed_data.py
└── .env.example
```

### Key dependencies

- FastAPI + Uvicorn — API layer
- Streamlit — Dashboard
- SQLAlchemy + psycopg2 — PostgreSQL ORM
- scikit-learn — Isolation Forest
- statsmodels — STL decomposition
- prophet — Forecast comparison
- httpx — Async LTA API calls
- Prefect — Lightweight task scheduling

## Build Sequence

### Phase 1 — Foundation

- Docker-compose with PostgreSQL, FastAPI skeleton, Streamlit hello-world
- Database schema + migrations
- Synthetic sensor generator producing realistic time-series with planted anomalies
- Seed script to populate a few days of data

### Phase 2 — Detection Engine

- Z-score detector with rolling baselines
- Isolation Forest multivariate detector
- STL decomposition detector
- Prophet detector
- Ensemble scoring logic
- Unit tests validating detection against known planted anomalies

### Phase 3 — LTA Integration

- DataMall API client for train arrivals, crowd density, disruptions
- Correlation logic linking real disruption events to synthetic sensor anomalies
- Prefect scheduling for periodic ingestion + detection runs

### Phase 4 — AI Agent

- LLMProvider abstraction + Claude implementation
- Prompt engineering for root cause / severity / action output
- OpenAI and Ollama provider implementations
- Agent assessment storage and retrieval API

### Phase 5 — Dashboard

- Live Overview with line health map
- Sensor Explorer with anomaly highlighting
- Alert Feed with inline agent reasoning
- Model Comparison view (STL vs Prophet metrics)

### Phase 6 — Polish

- README with architecture diagram, setup instructions, screenshots
- Demo data script producing compelling 30-day dataset with realistic failure scenarios
- Performance tuning and edge case handling
