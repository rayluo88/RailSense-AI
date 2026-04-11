# RailSense-AI

**Real-time railway anomaly detection and AI-powered reasoning for Singapore's MRT network.**

A full-stack decision intelligence platform that ingests train sensor telemetry, applies an ensemble of statistical and ML-based anomaly detectors, and routes flagged anomalies to an LLM-powered reasoning agent for root-cause analysis, severity assessment, and maintenance recommendations.

> **Live demo:** [railsense-ai-production.up.railway.app](https://railsense-ai-production.up.railway.app/overview)

---

## Key Capabilities

- **Time-series anomaly detection** — Four methods (Z-Score, Isolation Forest, STL decomposition, Prophet) combined via weighted ensemble scoring with agreement boosting
- **AI reasoning agent** — Protocol-based LLM abstraction (DeepSeek, Claude, OpenAI, Ollama) that analyses flagged anomalies and returns structured root-cause hypotheses, severity classifications, and maintenance recommendations
- **Automated ML pipelines** — Prefect-orchestrated ingestion, detection, and alerting workflows with PostgreSQL persistence and 46 automated tests
- **Live LTA data integration** — Active LTA DataMall API client ingesting real-time station crowd density (all 11 MRT/LRT lines), live service disruption alerts, and facilities maintenance events; synthetic sensor generator covers equipment telemetry (bearing degradation, door wear, electrical faults) not exposed by the public API
- **Operations dashboard** — Server-rendered HTML dashboard (FastAPI + Jinja2) with live network overview, sensor drilldown, severity-filtered alerts with on-demand AI analysis, model comparison, and a dedicated LTA Operations page showing real crowd density, disruptions, and facilities maintenance

---

## Architecture

```mermaid
flowchart LR
    subgraph Ingestion["Data Ingestion"]
        SYN[Synthetic Sensor Generator]
        subgraph LTA["LTA DataMall API"]
            CROWD[Crowd Density<br/>10-min realtime]
            DIS[Service Disruptions<br/>ad hoc]
            FAC[Facilities Maintenance<br/>ad hoc]
        end
    end

    subgraph Detection["Detection Engine"]
        ZS[Z-Score]
        IF[Isolation Forest]
        STL[STL Decomposition]
        PR[Prophet]
        ENS[Ensemble Scorer]
    end

    subgraph Agent["AI Reasoning Agent"]
        CTX[Enriched Context<br/>sensor + LTA data]
        LLM["LLM Provider<br/>(DeepSeek / Claude / OpenAI / Ollama)"]
    end

    subgraph Interface["Interface Layer"]
        API[FastAPI REST API]
        DASH[HTML Dashboard<br/>Jinja2 + Plotly]
    end

    SYN --> Detection
    ZS --> ENS
    IF --> ENS
    STL --> ENS
    PR --> ENS
    ENS --> API
    CROWD --> CTX
    DIS --> CTX
    FAC --> CTX
    API --> CTX
    CTX --> LLM
    LLM --> API
    API --> DASH
```

---

## Quick Start

```bash
# Clone and start all services
docker compose up -d

# Seed with 30-day demo dataset (5 trains, 3 failure scenarios)
docker compose exec api python -m scripts.demo_seed

# Open the dashboard
open http://localhost:8000/overview
```

---

## Detection Methods

| Method | Type | Approach |
|---|---|---|
| **Z-Score** | Statistical | Rolling window baseline; flags readings beyond configurable sigma thresholds |
| **Isolation Forest** | ML (unsupervised) | Random feature splits across 4 sensor dimensions; captures multivariate correlations |
| **STL Decomposition** | Statistical | Seasonal-trend decomposition removes daily ridership patterns; MAD-based residual scoring |
| **Prophet** | Forecast-based | Daily seasonality model; residuals outside forecast interval are flagged |
| **Ensemble** | Meta-method | Weighted average of all detectors with agreement boosting for elevated precision |

---

## AI Reasoning Agent

The agent implements a **Protocol-based provider abstraction** (`LLMProvider` protocol) enabling hot-swappable LLM backends:

```
LLM_PROVIDER=deepseek  # or claude, openai, ollama
```

When an anomaly is flagged, the agent receives full operational context — sensor readings, detection methods triggered, peak hour status, recent history, correlated sensors, **active LTA service disruptions**, **real-time station crowd density**, and **facilities maintenance events on the same line** — and returns a structured assessment: **root cause hypothesis**, **severity classification** (critical / warning / monitor), and **recommended maintenance action** with chain-of-thought reasoning.

The enriched context allows the agent to correlate synthetic sensor anomalies with real-world events — for example, distinguishing whether elevated current draw is caused by equipment degradation or by abnormally high crowd density at peak hour.

---

## Dashboard

Five purpose-built views designed for railway operations teams:

| Page | Route | Description |
|---|---|---|
| **Live Overview** | `/overview` | Network-wide health metrics, MRT line status, real-time anomaly feed |
| **Sensor Explorer** | `/sensors` | Train sensor time-series with anomaly overlays and Plotly charts |
| **Alert Feed** | `/alerts` | Severity-filtered alert cards with expandable details and on-demand AI analysis |
| **Model Comparison** | `/models` | Side-by-side STL vs Prophet evaluation with precision, recall, F1, and prediction overlays |
| **LTA Operations** | `/operations` | Live LTA data: active service disruptions, per-station crowd density heatmap (all lines), facilities under maintenance |

---

## API

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Service health check |
| `GET` | `/api/sensors` | Query sensor readings (filter by train, type, time range) |
| `GET` | `/api/anomalies` | List detected anomaly events (filter by severity, train) |
| `POST` | `/api/assess/{id}` | Trigger AI agent assessment for a specific anomaly (enriched with live LTA context) |
| `GET` | `/api/assessments` | List all AI agent assessments |
| `GET` | `/api/compare` | Run STL vs Prophet comparison on synthetic data |
| `GET` | `/api/disruptions` | Live train service disruptions (filter by line) |
| `GET` | `/api/crowd-density` | Real-time station crowd density (filter by line) |
| `GET` | `/api/facilities` | Current facilities under maintenance (filter by line) |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11 |
| API | FastAPI + Uvicorn |
| Dashboard | Jinja2 + Plotly.js (server-rendered HTML) |
| Database | PostgreSQL 16 + SQLAlchemy 2.0 |
| ML / Statistics | scikit-learn, statsmodels, Prophet |
| Orchestration | Prefect |
| LLM Providers | DeepSeek, Anthropic Claude, OpenAI, Ollama |
| Infrastructure | Docker Compose, Railway |

---

## Project Structure

```
railsense-ai/
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
├── scripts/
│   ├── seed_data.py              # Basic seed script
│   └── demo_seed.py              # 30-day demo scenario generator
├── src/
│   ├── config.py                 # Pydantic settings
│   ├── tasks.py                  # Prefect flow definitions
│   ├── api/
│   │   ├── main.py               # FastAPI application
│   │   └── schemas.py            # Pydantic response models
│   ├── agent/
│   │   ├── provider.py           # LLMProvider protocol + factory
│   │   ├── prompts.py            # System/user prompt templates
│   │   ├── deepseek_provider.py
│   │   ├── claude_provider.py
│   │   ├── openai_provider.py
│   │   └── ollama_provider.py
│   ├── dashboard/
│   │   ├── routes.py             # Dashboard page routes (Jinja2)
│   │   └── queries.py            # DB query functions for dashboard
│   ├── templates/
│   │   ├── base.html             # Shared layout (sidebar, clock)
│   │   ├── overview.html         # Live Overview page
│   │   ├── sensor_explorer.html  # Sensor Explorer page
│   │   ├── alert_feed.html       # Alert Feed page
│   │   └── model_comparison.html # Model Comparison page
│   ├── static/
│   │   └── shared-styles.css     # Design system stylesheet
│   ├── db/
│   │   ├── models.py             # SQLAlchemy models
│   │   └── session.py            # Engine + session factory
│   ├── detection/
│   │   ├── base.py               # Detector Protocol
│   │   ├── zscore.py
│   │   ├── isolation_forest.py
│   │   ├── stl_detector.py
│   │   ├── prophet_detector.py
│   │   ├── ensemble.py           # Weighted ensemble scorer
│   │   ├── compare.py            # STL vs Prophet comparison
│   │   └── pipeline.py           # Detection pipeline orchestrator
│   └── ingestion/
│       ├── lta_client.py         # LTA DataMall API client (crowd density, disruptions, facilities)
│       └── synthetic_gen.py      # Synthetic sensor data generator
├── docs/
│   ├── DEPLOYMENT-RAILWAY.md     # Railway deployment guide
│   └── plans/                    # Architecture and implementation plans
├── designs/                      # HTML/CSS dashboard mockups
└── tests/                        # 54 tests, SQLite in-memory isolation
```

---

## Testing

```bash
uv run pytest --tb=short -q
# 54 passed
```

Full coverage across detection methods, API endpoints, database models, LLM provider factory, data pipeline, synthetic data generation, and LTA API client parsing (crowd density, disruptions, facilities). Tests use SQLite in-memory databases — no external services required.

---

## License

MIT
