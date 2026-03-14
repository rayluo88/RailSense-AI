# RailSense-AI Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a full-stack railway anomaly detection pipeline with LLM reasoning, deployed as a Docker-compose stack with FastAPI, Streamlit, and PostgreSQL.

**Architecture:** Three-layer system — data ingestion (LTA API + synthetic sensors), detection engine (Z-score, Isolation Forest, STL, Prophet with ensemble scoring), and AI reasoning agent (pluggable LLM provider). FastAPI serves the backend API, Streamlit renders the dashboard, PostgreSQL stores everything.

**Tech Stack:** Python 3.11, FastAPI, Streamlit, PostgreSQL, SQLAlchemy, scikit-learn, statsmodels, prophet, httpx, Prefect, Docker

---

## Task 1: Project Skeleton & Docker Infrastructure

**Files:**
- Create: `railsense-ai/pyproject.toml`
- Create: `railsense-ai/docker-compose.yml`
- Create: `railsense-ai/Dockerfile`
- Create: `railsense-ai/.env.example`
- Create: `railsense-ai/src/__init__.py`
- Create: `railsense-ai/src/api/__init__.py`
- Create: `railsense-ai/src/api/main.py`
- Create: `railsense-ai/src/dashboard/__init__.py`
- Create: `railsense-ai/src/dashboard/app.py`
- Create: `railsense-ai/tests/__init__.py`

**Step 1: Create `pyproject.toml` with all dependencies**

```toml
[project]
name = "railsense-ai"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.34",
    "sqlalchemy>=2.0",
    "psycopg2-binary>=2.9",
    "alembic>=1.14",
    "httpx>=0.28",
    "scikit-learn>=1.6",
    "statsmodels>=0.14",
    "prophet>=1.1",
    "streamlit>=1.41",
    "pandas>=2.2",
    "numpy>=2.0",
    "prefect>=3.0",
    "pydantic>=2.0",
    "pydantic-settings>=2.0",
    "anthropic>=0.43",
    "openai>=1.60",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "pytest-asyncio>=0.24", "pytest-cov>=6.0", "httpx"]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
```

**Step 2: Create `docker-compose.yml`**

```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_DB: railsense
      POSTGRES_USER: railsense
      POSTGRES_PASSWORD: railsense_dev
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  api:
    build: .
    command: uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
    ports:
      - "8000:8000"
    env_file: .env
    depends_on:
      - db
    volumes:
      - .:/app

  dashboard:
    build: .
    command: streamlit run src/dashboard/app.py --server.port 8501 --server.address 0.0.0.0
    ports:
      - "8501:8501"
    env_file: .env
    depends_on:
      - api
    volumes:
      - .:/app

volumes:
  pgdata:
```

**Step 3: Create `Dockerfile`**

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml .
RUN pip install -e ".[dev]"
COPY . .
```

**Step 4: Create `.env.example`**

```
DATABASE_URL=postgresql://railsense:railsense_dev@db:5432/railsense
LLM_PROVIDER=claude
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
LTA_API_KEY=
```

**Step 5: Create FastAPI skeleton `src/api/main.py`**

```python
from fastapi import FastAPI

app = FastAPI(title="RailSense-AI", version="0.1.0")


@app.get("/health")
async def health():
    return {"status": "ok"}
```

**Step 6: Create Streamlit skeleton `src/dashboard/app.py`**

```python
import streamlit as st

st.set_page_config(page_title="RailSense-AI", layout="wide")
st.title("RailSense-AI")
st.write("Railway Anomaly Detection & Reasoning Platform")
```

**Step 7: Create `__init__.py` files**

Empty files for: `src/__init__.py`, `src/api/__init__.py`, `src/dashboard/__init__.py`, `tests/__init__.py`

**Step 8: Verify Docker stack starts**

```bash
cd railsense-ai
cp .env.example .env
docker compose up --build -d
# Wait for services to start
curl http://localhost:8000/health
# Expected: {"status":"ok"}
# Visit http://localhost:8501 — should see Streamlit page
docker compose down
```

**Step 9: Commit**

```bash
git init
git add .
git commit -m "feat: project skeleton with Docker, FastAPI, Streamlit, PostgreSQL"
```

---

## Task 2: Database Schema & Configuration

**Files:**
- Create: `railsense-ai/src/config.py`
- Create: `railsense-ai/src/db/__init__.py`
- Create: `railsense-ai/src/db/models.py`
- Create: `railsense-ai/src/db/session.py`
- Create: `railsense-ai/alembic.ini`
- Create: `railsense-ai/alembic/env.py`
- Test: `railsense-ai/tests/test_db.py`

**Step 1: Create `src/config.py`** — Pydantic settings loading from env

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://railsense:railsense_dev@localhost:5432/railsense"
    llm_provider: str = "claude"
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    lta_api_key: str = ""

    model_config = {"env_file": ".env"}


settings = Settings()
```

**Step 2: Create `src/db/session.py`** — SQLAlchemy engine and session factory

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from src.config import settings

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

**Step 3: Create `src/db/models.py`** — All four tables from the design doc

```python
import enum
from datetime import datetime

from sqlalchemy import (
    Column, DateTime, Enum, Float, ForeignKey, Index, Integer, String, Text,
)
from sqlalchemy.orm import relationship

from src.db.session import Base


class SensorType(str, enum.Enum):
    VIBRATION = "vibration"
    TEMPERATURE = "temperature"
    DOOR_CYCLE = "door_cycle"
    CURRENT_DRAW = "current_draw"


class Severity(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class SensorReading(Base):
    __tablename__ = "sensor_readings"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    train_id = Column(String(20), nullable=False, index=True)
    sensor_type = Column(Enum(SensorType), nullable=False)
    value = Column(Float, nullable=False)
    line_id = Column(String(10), nullable=False)
    station_id = Column(String(20), nullable=False)

    __table_args__ = (
        Index("ix_sensor_readings_train_time", "train_id", "timestamp"),
    )


class AnomalyEvent(Base):
    __tablename__ = "anomaly_events"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    train_id = Column(String(20), nullable=False)
    sensor_type = Column(Enum(SensorType), nullable=False)
    detection_method = Column(String(30), nullable=False)
    anomaly_score = Column(Float, nullable=False)
    severity = Column(Enum(Severity), nullable=False)
    value = Column(Float, nullable=False)
    line_id = Column(String(10), nullable=False)
    station_id = Column(String(20), nullable=False)

    assessments = relationship("AgentAssessment", back_populates="anomaly_event")


class AgentAssessment(Base):
    __tablename__ = "agent_assessments"

    id = Column(Integer, primary_key=True)
    anomaly_event_id = Column(Integer, ForeignKey("anomaly_events.id"), nullable=False)
    llm_provider = Column(String(20), nullable=False)
    root_cause = Column(Text, nullable=False)
    severity_override = Column(Enum(Severity))
    recommended_action = Column(Text, nullable=False)
    reasoning = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    anomaly_event = relationship("AnomalyEvent", back_populates="assessments")


class LtaDisruption(Base):
    __tablename__ = "lta_disruptions"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    line_id = Column(String(10), nullable=False)
    station_id = Column(String(20))
    message = Column(Text, nullable=False)
    direction = Column(String(50))
```

**Step 4: Set up Alembic**

```bash
cd railsense-ai
pip install -e ".[dev]"
alembic init alembic
```

Edit `alembic/env.py` to import `Base` and `models`:

```python
# At top of alembic/env.py, add:
from src.db.session import Base
from src.db import models  # noqa: F401 — registers models with Base

target_metadata = Base.metadata
```

Edit `alembic.ini`: set `sqlalchemy.url = postgresql://railsense:railsense_dev@localhost:5432/railsense`

**Step 5: Generate and run initial migration**

```bash
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
```

**Step 6: Write test `tests/test_db.py`**

```python
from src.db.models import SensorType, Severity, SensorReading, AnomalyEvent


def test_sensor_type_enum():
    assert SensorType.VIBRATION.value == "vibration"
    assert len(SensorType) == 4


def test_severity_enum():
    assert Severity.CRITICAL.value == "critical"
    assert len(Severity) == 3


def test_sensor_reading_columns():
    cols = {c.name for c in SensorReading.__table__.columns}
    assert cols == {"id", "timestamp", "train_id", "sensor_type", "value", "line_id", "station_id"}


def test_anomaly_event_columns():
    cols = {c.name for c in AnomalyEvent.__table__.columns}
    assert "anomaly_score" in cols
    assert "detection_method" in cols
```

**Step 7: Run tests**

```bash
pytest tests/test_db.py -v
```

Expected: 4 PASS

**Step 8: Commit**

```bash
git add .
git commit -m "feat: database schema with SQLAlchemy models and Alembic migrations"
```

---

## Task 3: Synthetic Sensor Data Generator

**Files:**
- Create: `railsense-ai/src/ingestion/__init__.py`
- Create: `railsense-ai/src/ingestion/synthetic_gen.py`
- Test: `railsense-ai/tests/test_synthetic_gen.py`

**Step 1: Write failing tests `tests/test_synthetic_gen.py`**

```python
import pandas as pd

from src.ingestion.synthetic_gen import SyntheticGenerator, AnomalyScenario


def test_generator_produces_dataframe():
    gen = SyntheticGenerator(seed=42)
    df = gen.generate(train_id="T001", hours=24)
    assert isinstance(df, pd.DataFrame)
    assert len(df) > 0


def test_generator_has_all_sensor_types():
    gen = SyntheticGenerator(seed=42)
    df = gen.generate(train_id="T001", hours=24)
    expected = {"vibration", "temperature", "door_cycle", "current_draw"}
    assert set(df["sensor_type"].unique()) == expected


def test_generator_follows_daily_pattern():
    """Peak hours should have higher baseline values than off-peak."""
    gen = SyntheticGenerator(seed=42)
    df = gen.generate(train_id="T001", hours=24)
    temp = df[df["sensor_type"] == "temperature"]
    peak = temp[(temp["timestamp"].dt.hour >= 7) & (temp["timestamp"].dt.hour <= 9)]
    offpeak = temp[(temp["timestamp"].dt.hour >= 1) & (temp["timestamp"].dt.hour <= 4)]
    assert peak["value"].mean() > offpeak["value"].mean()


def test_anomaly_injection():
    gen = SyntheticGenerator(seed=42)
    scenario = AnomalyScenario(
        sensor_types=["vibration", "temperature"],
        start_hour=12,
        duration_hours=2,
        magnitude=3.0,
    )
    df = gen.generate(train_id="T001", hours=24, anomalies=[scenario])
    assert "is_anomaly" in df.columns
    assert df["is_anomaly"].sum() > 0


def test_correlated_anomaly():
    """Bearing failure should show in both vibration AND temperature."""
    gen = SyntheticGenerator(seed=42)
    scenario = AnomalyScenario(
        sensor_types=["vibration", "temperature"],
        start_hour=12,
        duration_hours=2,
        magnitude=3.0,
    )
    df = gen.generate(train_id="T001", hours=24, anomalies=[scenario])
    anomaly_window = df[df["is_anomaly"]]
    anomaly_sensors = anomaly_window["sensor_type"].unique()
    assert "vibration" in anomaly_sensors
    assert "temperature" in anomaly_sensors


def test_gradual_degradation():
    gen = SyntheticGenerator(seed=42)
    scenario = AnomalyScenario(
        sensor_types=["door_cycle"],
        start_hour=0,
        duration_hours=24,
        magnitude=2.0,
        gradual=True,
    )
    df = gen.generate(train_id="T001", hours=24, anomalies=[scenario])
    door = df[df["sensor_type"] == "door_cycle"].sort_values("timestamp")
    first_quarter = door.head(len(door) // 4)["value"].mean()
    last_quarter = door.tail(len(door) // 4)["value"].mean()
    assert last_quarter > first_quarter
```

**Step 2: Run tests to verify they fail**

```bash
pytest tests/test_synthetic_gen.py -v
```

Expected: FAIL — `ModuleNotFoundError`

**Step 3: Implement `src/ingestion/synthetic_gen.py`**

```python
from dataclasses import dataclass, field

import numpy as np
import pandas as pd


@dataclass
class AnomalyScenario:
    sensor_types: list[str]
    start_hour: int
    duration_hours: int
    magnitude: float = 3.0
    gradual: bool = False


SENSOR_BASELINES = {
    "vibration": {"mean": 0.3, "std": 0.05, "unit": "g"},
    "temperature": {"mean": 35.0, "std": 2.0, "unit": "°C"},
    "door_cycle": {"mean": 2500, "std": 100, "unit": "ms"},
    "current_draw": {"mean": 150, "std": 15, "unit": "A"},
}

# Peak hour multipliers — higher load during rush hours
PEAK_HOURS = {7, 8, 9, 17, 18, 19}
PEAK_MULTIPLIER = {
    "vibration": 1.15,
    "temperature": 1.20,
    "door_cycle": 1.05,
    "current_draw": 1.25,
}


class SyntheticGenerator:
    def __init__(self, seed: int = 42, interval_minutes: int = 5):
        self.rng = np.random.default_rng(seed)
        self.interval_minutes = interval_minutes

    def generate(
        self,
        train_id: str,
        hours: int,
        line_id: str = "NSL",
        station_id: str = "NS1",
        anomalies: list[AnomalyScenario] | None = None,
    ) -> pd.DataFrame:
        anomalies = anomalies or []
        n_points = (hours * 60) // self.interval_minutes
        start = pd.Timestamp("2026-03-01")
        timestamps = pd.date_range(start, periods=n_points, freq=f"{self.interval_minutes}min")

        rows = []
        for sensor_type, baseline in SENSOR_BASELINES.items():
            values = self.rng.normal(baseline["mean"], baseline["std"], n_points)

            # Apply daily ridership pattern
            for i, ts in enumerate(timestamps):
                if ts.hour in PEAK_HOURS:
                    values[i] *= PEAK_MULTIPLIER[sensor_type]

            # Mark anomalies
            is_anomaly = np.zeros(n_points, dtype=bool)

            for scenario in anomalies:
                if sensor_type not in scenario.sensor_types:
                    continue
                start_idx = (scenario.start_hour * 60) // self.interval_minutes
                end_idx = start_idx + (scenario.duration_hours * 60) // self.interval_minutes
                end_idx = min(end_idx, n_points)

                for i in range(start_idx, end_idx):
                    if scenario.gradual:
                        progress = (i - start_idx) / max(end_idx - start_idx, 1)
                        values[i] += baseline["std"] * scenario.magnitude * progress
                    else:
                        values[i] += baseline["std"] * scenario.magnitude
                    is_anomaly[i] = True

            for i in range(n_points):
                rows.append({
                    "timestamp": timestamps[i],
                    "train_id": train_id,
                    "sensor_type": sensor_type,
                    "value": float(values[i]),
                    "line_id": line_id,
                    "station_id": station_id,
                    "is_anomaly": bool(is_anomaly[i]),
                })

        return pd.DataFrame(rows)
```

**Step 4: Run tests to verify they pass**

```bash
pytest tests/test_synthetic_gen.py -v
```

Expected: 6 PASS

**Step 5: Commit**

```bash
git add .
git commit -m "feat: synthetic sensor data generator with anomaly injection"
```

---

## Task 4: Seed Script & Ingestion API

**Files:**
- Create: `railsense-ai/scripts/seed_data.py`
- Modify: `railsense-ai/src/api/main.py`
- Create: `railsense-ai/src/api/schemas.py`
- Test: `railsense-ai/tests/test_api.py`

**Step 1: Create `src/api/schemas.py`** — Pydantic response models

```python
from datetime import datetime

from pydantic import BaseModel


class SensorReadingOut(BaseModel):
    id: int
    timestamp: datetime
    train_id: str
    sensor_type: str
    value: float
    line_id: str
    station_id: str

    model_config = {"from_attributes": True}


class AnomalyEventOut(BaseModel):
    id: int
    timestamp: datetime
    train_id: str
    sensor_type: str
    detection_method: str
    anomaly_score: float
    severity: str
    value: float
    line_id: str
    station_id: str

    model_config = {"from_attributes": True}


class AgentAssessmentOut(BaseModel):
    id: int
    anomaly_event_id: int
    llm_provider: str
    root_cause: str
    severity_override: str | None
    recommended_action: str
    reasoning: str
    created_at: datetime

    model_config = {"from_attributes": True}
```

**Step 2: Expand `src/api/main.py`** with sensor reading and anomaly endpoints

```python
from datetime import datetime

from fastapi import Depends, FastAPI, Query
from sqlalchemy.orm import Session

from src.api.schemas import AnomalyEventOut, SensorReadingOut
from src.db.models import AnomalyEvent, SensorReading
from src.db.session import get_db

app = FastAPI(title="RailSense-AI", version="0.1.0")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/sensors", response_model=list[SensorReadingOut])
def get_sensor_readings(
    train_id: str | None = None,
    sensor_type: str | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int = Query(default=100, le=1000),
    db: Session = Depends(get_db),
):
    q = db.query(SensorReading)
    if train_id:
        q = q.filter(SensorReading.train_id == train_id)
    if sensor_type:
        q = q.filter(SensorReading.sensor_type == sensor_type)
    if start:
        q = q.filter(SensorReading.timestamp >= start)
    if end:
        q = q.filter(SensorReading.timestamp <= end)
    return q.order_by(SensorReading.timestamp.desc()).limit(limit).all()


@app.get("/api/anomalies", response_model=list[AnomalyEventOut])
def get_anomalies(
    severity: str | None = None,
    train_id: str | None = None,
    limit: int = Query(default=50, le=500),
    db: Session = Depends(get_db),
):
    q = db.query(AnomalyEvent)
    if severity:
        q = q.filter(AnomalyEvent.severity == severity)
    if train_id:
        q = q.filter(AnomalyEvent.train_id == train_id)
    return q.order_by(AnomalyEvent.timestamp.desc()).limit(limit).all()
```

**Step 3: Write failing test `tests/test_api.py`**

```python
from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_get_sensors_empty():
    r = client.get("/api/sensors")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_get_anomalies_empty():
    r = client.get("/api/anomalies")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
```

**Step 4: Run tests**

```bash
pytest tests/test_api.py -v
```

Expected: 3 PASS (using test DB or SQLite override — may need a conftest.py with test DB setup)

**Step 5: Create `scripts/seed_data.py`**

```python
"""Seed the database with synthetic sensor data for demo purposes."""

from src.db.models import SensorReading
from src.db.session import SessionLocal, engine, Base
from src.ingestion.synthetic_gen import AnomalyScenario, SyntheticGenerator

TRAIN_UNITS = ["T001", "T002", "T003", "T004", "T005"]
LINES = {"T001": "NSL", "T002": "NSL", "T003": "EWL", "T004": "EWL", "T005": "CCL"}
STATIONS = {"T001": "NS1", "T002": "NS9", "T003": "EW4", "T004": "EW12", "T005": "CC3"}

SCENARIOS = {
    "T002": [
        AnomalyScenario(sensor_types=["vibration", "temperature"], start_hour=36, duration_hours=4, magnitude=3.5),
    ],
    "T004": [
        AnomalyScenario(sensor_types=["door_cycle"], start_hour=0, duration_hours=72, magnitude=2.5, gradual=True),
    ],
    "T005": [
        AnomalyScenario(sensor_types=["current_draw"], start_hour=48, duration_hours=1, magnitude=5.0),
    ],
}


def seed():
    Base.metadata.create_all(engine)
    db = SessionLocal()

    # Clear existing data
    db.query(SensorReading).delete()
    db.commit()

    gen = SyntheticGenerator(seed=42)

    for train_id in TRAIN_UNITS:
        print(f"Generating data for {train_id}...")
        df = gen.generate(
            train_id=train_id,
            hours=72,
            line_id=LINES[train_id],
            station_id=STATIONS[train_id],
            anomalies=SCENARIOS.get(train_id, []),
        )

        readings = [
            SensorReading(
                timestamp=row["timestamp"],
                train_id=row["train_id"],
                sensor_type=row["sensor_type"],
                value=row["value"],
                line_id=row["line_id"],
                station_id=row["station_id"],
            )
            for _, row in df.iterrows()
        ]
        db.bulk_save_objects(readings)
        db.commit()
        print(f"  Inserted {len(readings)} readings")

    db.close()
    print("Seed complete.")


if __name__ == "__main__":
    seed()
```

**Step 6: Run seed script against Docker PostgreSQL**

```bash
docker compose up db -d
python scripts/seed_data.py
```

Expected: prints insertion counts for 5 train units

**Step 7: Commit**

```bash
git add .
git commit -m "feat: API endpoints for sensors/anomalies and seed data script"
```

---

## Task 5: Z-Score Detector

**Files:**
- Create: `railsense-ai/src/detection/__init__.py`
- Create: `railsense-ai/src/detection/base.py`
- Create: `railsense-ai/src/detection/zscore.py`
- Test: `railsense-ai/tests/test_zscore.py`

**Step 1: Write failing tests `tests/test_zscore.py`**

```python
import numpy as np
import pandas as pd

from src.detection.zscore import ZScoreDetector


def _make_series(n=1000, spike_at=500, spike_magnitude=5.0):
    """Normal series with one spike."""
    rng = np.random.default_rng(42)
    values = rng.normal(0.3, 0.05, n)
    timestamps = pd.date_range("2026-03-01", periods=n, freq="5min")
    if spike_at is not None:
        values[spike_at] = 0.3 + 0.05 * spike_magnitude
    return pd.DataFrame({"timestamp": timestamps, "value": values})


def test_no_anomalies_in_clean_data():
    df = _make_series(spike_at=None)
    detector = ZScoreDetector(window=100, threshold_warn=2.0, threshold_crit=3.0)
    results = detector.detect(df)
    # Very few false positives expected in normal data
    assert results["severity"].isna().sum() > len(results) * 0.95


def test_detects_spike():
    df = _make_series(spike_at=500, spike_magnitude=6.0)
    detector = ZScoreDetector(window=100, threshold_warn=2.0, threshold_crit=3.0)
    results = detector.detect(df)
    spike_row = results.iloc[500]
    assert spike_row["severity"] == "critical"
    assert 0.0 <= spike_row["anomaly_score"] <= 1.0


def test_score_normalized():
    df = _make_series(spike_at=500, spike_magnitude=4.0)
    detector = ZScoreDetector(window=100, threshold_warn=2.0, threshold_crit=3.0)
    results = detector.detect(df)
    scores = results["anomaly_score"].dropna()
    assert scores.min() >= 0.0
    assert scores.max() <= 1.0
```

**Step 2: Run tests to verify they fail**

```bash
pytest tests/test_zscore.py -v
```

Expected: FAIL — `ModuleNotFoundError`

**Step 3: Create `src/detection/base.py`** — base protocol

```python
from typing import Protocol

import pandas as pd


class Detector(Protocol):
    def detect(self, df: pd.DataFrame) -> pd.DataFrame:
        """Input: DataFrame with 'timestamp' and 'value' columns.
        Output: Same DataFrame with added 'anomaly_score' and 'severity' columns.
        """
        ...
```

**Step 4: Implement `src/detection/zscore.py`**

```python
import numpy as np
import pandas as pd


class ZScoreDetector:
    def __init__(self, window: int = 288, threshold_warn: float = 2.0, threshold_crit: float = 3.0):
        self.window = window
        self.threshold_warn = threshold_warn
        self.threshold_crit = threshold_crit

    def detect(self, df: pd.DataFrame) -> pd.DataFrame:
        result = df.copy()
        values = result["value"].values.astype(float)

        rolling_mean = pd.Series(values).rolling(self.window, min_periods=1).mean().values
        rolling_std = pd.Series(values).rolling(self.window, min_periods=1).std().values
        rolling_std = np.where(rolling_std == 0, 1e-10, rolling_std)

        z_scores = np.abs((values - rolling_mean) / rolling_std)

        # Normalize score to 0-1 using sigmoid-like mapping
        max_z = max(self.threshold_crit * 2, z_scores.max()) if len(z_scores) > 0 else 1
        scores = np.clip(z_scores / max_z, 0.0, 1.0)

        severity = pd.array([None] * len(df), dtype=object)
        severity[z_scores >= self.threshold_crit] = "critical"
        severity[(z_scores >= self.threshold_warn) & (z_scores < self.threshold_crit)] = "warning"

        result["anomaly_score"] = scores
        result["severity"] = severity
        result["detection_method"] = "zscore"
        return result
```

**Step 5: Run tests**

```bash
pytest tests/test_zscore.py -v
```

Expected: 3 PASS

**Step 6: Commit**

```bash
git add .
git commit -m "feat: Z-score anomaly detector with rolling baseline"
```

---

## Task 6: Isolation Forest Detector

**Files:**
- Create: `railsense-ai/src/detection/isolation_forest.py`
- Test: `railsense-ai/tests/test_isolation_forest.py`

**Step 1: Write failing tests `tests/test_isolation_forest.py`**

```python
import numpy as np
import pandas as pd

from src.detection.isolation_forest import IsolationForestDetector


def _make_multivariate(n=500):
    """4-sensor data with one multivariate outlier at row 250."""
    rng = np.random.default_rng(42)
    data = {
        "timestamp": pd.date_range("2026-03-01", periods=n, freq="5min"),
        "vibration": rng.normal(0.3, 0.05, n),
        "temperature": rng.normal(35, 2, n),
        "door_cycle": rng.normal(2500, 100, n),
        "current_draw": rng.normal(150, 15, n),
    }
    # Inject correlated anomaly
    data["vibration"][250] = 0.8
    data["temperature"][250] = 55.0
    return pd.DataFrame(data)


def test_detects_multivariate_outlier():
    df = _make_multivariate()
    detector = IsolationForestDetector(contamination=0.02)
    results = detector.detect(df)
    assert results.iloc[250]["anomaly_score"] > 0.5


def test_output_has_required_columns():
    df = _make_multivariate()
    detector = IsolationForestDetector()
    results = detector.detect(df)
    assert "anomaly_score" in results.columns
    assert "severity" in results.columns
    assert "detection_method" in results.columns


def test_scores_normalized():
    df = _make_multivariate()
    detector = IsolationForestDetector()
    results = detector.detect(df)
    assert results["anomaly_score"].min() >= 0.0
    assert results["anomaly_score"].max() <= 1.0
```

**Step 2: Run tests to verify they fail**

```bash
pytest tests/test_isolation_forest.py -v
```

**Step 3: Implement `src/detection/isolation_forest.py`**

```python
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest


SENSOR_COLS = ["vibration", "temperature", "door_cycle", "current_draw"]


class IsolationForestDetector:
    def __init__(self, contamination: float = 0.05, random_state: int = 42):
        self.contamination = contamination
        self.random_state = random_state

    def detect(self, df: pd.DataFrame) -> pd.DataFrame:
        result = df.copy()
        X = result[SENSOR_COLS].values

        model = IsolationForest(
            contamination=self.contamination,
            random_state=self.random_state,
            n_estimators=200,
        )
        model.fit(X)

        raw_scores = model.decision_function(X)
        # decision_function: lower = more anomalous. Invert and normalize to 0-1.
        scores = 1 - (raw_scores - raw_scores.min()) / (raw_scores.max() - raw_scores.min() + 1e-10)

        severity = pd.array([None] * len(df), dtype=object)
        severity[scores >= 0.8] = "critical"
        severity[(scores >= 0.6) & (scores < 0.8)] = "warning"

        result["anomaly_score"] = scores
        result["severity"] = severity
        result["detection_method"] = "isolation_forest"
        return result
```

**Step 4: Run tests**

```bash
pytest tests/test_isolation_forest.py -v
```

Expected: 3 PASS

**Step 5: Commit**

```bash
git add .
git commit -m "feat: Isolation Forest multivariate anomaly detector"
```

---

## Task 7: STL Decomposition Detector

**Files:**
- Create: `railsense-ai/src/detection/stl_detector.py`
- Test: `railsense-ai/tests/test_stl_detector.py`

**Step 1: Write failing tests `tests/test_stl_detector.py`**

```python
import numpy as np
import pandas as pd

from src.detection.stl_detector import STLDetector


def _make_seasonal_series(n=576, anomaly_at=400):
    """2 days of data (5-min intervals) with daily seasonality and one anomaly."""
    rng = np.random.default_rng(42)
    timestamps = pd.date_range("2026-03-01", periods=n, freq="5min")
    # Daily seasonal pattern
    seasonal = 5.0 * np.sin(2 * np.pi * np.arange(n) / 288)
    noise = rng.normal(0, 0.5, n)
    values = 35.0 + seasonal + noise
    if anomaly_at is not None:
        values[anomaly_at] += 15.0
    return pd.DataFrame({"timestamp": timestamps, "value": values})


def test_detects_anomaly_in_seasonal_data():
    df = _make_seasonal_series(anomaly_at=400)
    detector = STLDetector(period=288, threshold_warn=2.0, threshold_crit=3.0)
    results = detector.detect(df)
    assert results.iloc[400]["severity"] in ("warning", "critical")


def test_clean_seasonal_data_few_false_positives():
    df = _make_seasonal_series(anomaly_at=None)
    detector = STLDetector(period=288, threshold_warn=2.0, threshold_crit=3.0)
    results = detector.detect(df)
    flagged = results["severity"].dropna()
    assert len(flagged) < len(results) * 0.05


def test_output_columns():
    df = _make_seasonal_series()
    detector = STLDetector(period=288)
    results = detector.detect(df)
    assert "anomaly_score" in results.columns
    assert "detection_method" in results.columns
    assert (results["detection_method"] == "stl").all()
```

**Step 2: Run tests to verify they fail**

```bash
pytest tests/test_stl_detector.py -v
```

**Step 3: Implement `src/detection/stl_detector.py`**

```python
import numpy as np
import pandas as pd
from statsmodels.tsa.seasonal import STL


class STLDetector:
    def __init__(self, period: int = 288, threshold_warn: float = 2.0, threshold_crit: float = 3.0):
        self.period = period
        self.threshold_warn = threshold_warn
        self.threshold_crit = threshold_crit

    def detect(self, df: pd.DataFrame) -> pd.DataFrame:
        result = df.copy()
        series = pd.Series(result["value"].values, index=result["timestamp"])

        stl = STL(series, period=self.period, robust=True)
        decomposition = stl.fit()
        residuals = decomposition.resid.values

        resid_std = np.std(residuals)
        resid_std = max(resid_std, 1e-10)
        z_scores = np.abs(residuals / resid_std)

        max_z = max(self.threshold_crit * 2, z_scores.max())
        scores = np.clip(z_scores / max_z, 0.0, 1.0)

        severity = pd.array([None] * len(df), dtype=object)
        severity[z_scores >= self.threshold_crit] = "critical"
        severity[(z_scores >= self.threshold_warn) & (z_scores < self.threshold_crit)] = "warning"

        result["anomaly_score"] = scores
        result["severity"] = severity
        result["detection_method"] = "stl"
        return result
```

**Step 4: Run tests**

```bash
pytest tests/test_stl_detector.py -v
```

Expected: 3 PASS

**Step 5: Commit**

```bash
git add .
git commit -m "feat: STL decomposition anomaly detector"
```

---

## Task 8: Prophet Detector

**Files:**
- Create: `railsense-ai/src/detection/prophet_detector.py`
- Test: `railsense-ai/tests/test_prophet_detector.py`

**Step 1: Write failing tests `tests/test_prophet_detector.py`**

```python
import numpy as np
import pandas as pd

from src.detection.prophet_detector import ProphetDetector


def _make_seasonal_series(n=576, anomaly_at=400):
    rng = np.random.default_rng(42)
    timestamps = pd.date_range("2026-03-01", periods=n, freq="5min")
    seasonal = 5.0 * np.sin(2 * np.pi * np.arange(n) / 288)
    noise = rng.normal(0, 0.5, n)
    values = 35.0 + seasonal + noise
    if anomaly_at is not None:
        values[anomaly_at] += 15.0
    return pd.DataFrame({"timestamp": timestamps, "value": values})


def test_detects_anomaly():
    df = _make_seasonal_series(anomaly_at=400)
    detector = ProphetDetector(threshold_warn=2.0, threshold_crit=3.0)
    results = detector.detect(df)
    assert results.iloc[400]["severity"] in ("warning", "critical")


def test_output_columns():
    df = _make_seasonal_series()
    detector = ProphetDetector()
    results = detector.detect(df)
    assert "anomaly_score" in results.columns
    assert (results["detection_method"] == "prophet").all()


def test_scores_normalized():
    df = _make_seasonal_series()
    detector = ProphetDetector()
    results = detector.detect(df)
    assert results["anomaly_score"].min() >= 0.0
    assert results["anomaly_score"].max() <= 1.0
```

**Step 2: Run tests to verify they fail**

```bash
pytest tests/test_prophet_detector.py -v
```

**Step 3: Implement `src/detection/prophet_detector.py`**

```python
import numpy as np
import pandas as pd
from prophet import Prophet


class ProphetDetector:
    def __init__(self, threshold_warn: float = 2.0, threshold_crit: float = 3.0, interval_width: float = 0.95):
        self.threshold_warn = threshold_warn
        self.threshold_crit = threshold_crit
        self.interval_width = interval_width

    def detect(self, df: pd.DataFrame) -> pd.DataFrame:
        result = df.copy()
        prophet_df = pd.DataFrame({"ds": df["timestamp"], "y": df["value"]})

        model = Prophet(
            interval_width=self.interval_width,
            daily_seasonality=True,
            weekly_seasonality=False,
            yearly_seasonality=False,
        )
        model.fit(prophet_df)
        forecast = model.predict(prophet_df)

        residuals = (df["value"].values - forecast["yhat"].values)
        resid_std = np.std(residuals)
        resid_std = max(resid_std, 1e-10)
        z_scores = np.abs(residuals / resid_std)

        max_z = max(self.threshold_crit * 2, z_scores.max())
        scores = np.clip(z_scores / max_z, 0.0, 1.0)

        severity = pd.array([None] * len(df), dtype=object)
        severity[z_scores >= self.threshold_crit] = "critical"
        severity[(z_scores >= self.threshold_warn) & (z_scores < self.threshold_crit)] = "warning"

        result["anomaly_score"] = scores
        result["severity"] = severity
        result["detection_method"] = "prophet"
        return result
```

**Step 4: Run tests**

```bash
pytest tests/test_prophet_detector.py -v
```

Expected: 3 PASS (Prophet is slow — these tests may take 10-30s)

**Step 5: Commit**

```bash
git add .
git commit -m "feat: Prophet forecast-based anomaly detector"
```

---

## Task 9: Ensemble Scoring

**Files:**
- Create: `railsense-ai/src/detection/ensemble.py`
- Test: `railsense-ai/tests/test_ensemble.py`

**Step 1: Write failing tests `tests/test_ensemble.py`**

```python
import pandas as pd

from src.detection.ensemble import EnsembleScorer


def test_combines_scores():
    results = [
        pd.DataFrame({"anomaly_score": [0.3, 0.9, 0.1], "severity": [None, "critical", None]}),
        pd.DataFrame({"anomaly_score": [0.2, 0.8, 0.1], "severity": [None, "critical", None]}),
        pd.DataFrame({"anomaly_score": [0.4, 0.7, 0.2], "severity": [None, "warning", None]}),
    ]
    scorer = EnsembleScorer()
    combined = scorer.combine(results)
    assert combined.iloc[1]["ensemble_score"] > combined.iloc[0]["ensemble_score"]


def test_agreement_boost():
    """When multiple methods agree on anomaly, score should be higher than any individual."""
    all_agree = [
        pd.DataFrame({"anomaly_score": [0.7], "severity": ["warning"]}),
        pd.DataFrame({"anomaly_score": [0.7], "severity": ["warning"]}),
        pd.DataFrame({"anomaly_score": [0.7], "severity": ["warning"]}),
    ]
    scorer = EnsembleScorer()
    combined = scorer.combine(all_agree)
    assert combined.iloc[0]["ensemble_score"] >= 0.7


def test_severity_thresholds():
    results = [
        pd.DataFrame({"anomaly_score": [0.9, 0.5, 0.1], "severity": ["critical", "warning", None]}),
    ]
    scorer = EnsembleScorer()
    combined = scorer.combine(results)
    assert combined.iloc[0]["ensemble_severity"] == "critical"
    assert combined.iloc[1]["ensemble_severity"] == "warning"
    assert combined.iloc[2]["ensemble_severity"] == "info"
```

**Step 2: Run tests to verify they fail**

```bash
pytest tests/test_ensemble.py -v
```

**Step 3: Implement `src/detection/ensemble.py`**

```python
import numpy as np
import pandas as pd


class EnsembleScorer:
    def __init__(
        self,
        weights: list[float] | None = None,
        threshold_info: float = 0.4,
        threshold_warn: float = 0.6,
        threshold_crit: float = 0.8,
    ):
        self.weights = weights
        self.threshold_info = threshold_info
        self.threshold_warn = threshold_warn
        self.threshold_crit = threshold_crit

    def combine(self, results: list[pd.DataFrame]) -> pd.DataFrame:
        n = len(results)
        weights = self.weights or [1.0 / n] * n
        scores = np.stack([r["anomaly_score"].values for r in results])

        weighted_avg = np.average(scores, axis=0, weights=weights)

        # Agreement boost: if multiple methods flag the same point, boost score
        flagged = (scores >= 0.5).sum(axis=0)
        agreement_factor = 1.0 + 0.1 * (flagged - 1)
        ensemble_score = np.clip(weighted_avg * agreement_factor, 0.0, 1.0)

        severity = []
        for s in ensemble_score:
            if s >= self.threshold_crit:
                severity.append("critical")
            elif s >= self.threshold_warn:
                severity.append("warning")
            elif s >= self.threshold_info:
                severity.append("info")
            else:
                severity.append("info")

        return pd.DataFrame({
            "ensemble_score": ensemble_score,
            "ensemble_severity": severity,
            "methods_agreed": flagged,
        })
```

**Step 4: Run tests**

```bash
pytest tests/test_ensemble.py -v
```

Expected: 3 PASS

**Step 5: Commit**

```bash
git add .
git commit -m "feat: ensemble scorer combining multiple detection methods"
```

---

## Task 10: LLM Provider Abstraction & Claude Implementation

**Files:**
- Create: `railsense-ai/src/agent/__init__.py`
- Create: `railsense-ai/src/agent/provider.py`
- Create: `railsense-ai/src/agent/prompts.py`
- Create: `railsense-ai/src/agent/claude_provider.py`
- Test: `railsense-ai/tests/test_agent.py`

**Step 1: Create `src/agent/provider.py`** — protocol + data models

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass
class AnomalyContext:
    timestamp: datetime
    train_id: str
    line_id: str
    station_id: str
    sensor_type: str
    value: float
    anomaly_score: float
    detection_methods: list[str]
    is_peak_hour: bool
    recent_history: list[dict]
    correlated_sensors: list[dict]


@dataclass
class AgentAssessment:
    root_cause: str
    severity: str  # critical, warning, monitor
    recommended_action: str
    reasoning: str


class LLMProvider(Protocol):
    async def analyze_anomaly(self, context: AnomalyContext) -> AgentAssessment: ...


def get_provider(provider_name: str) -> LLMProvider:
    if provider_name == "claude":
        from src.agent.claude_provider import ClaudeProvider
        return ClaudeProvider()
    elif provider_name == "openai":
        from src.agent.openai_provider import OpenAIProvider
        return OpenAIProvider()
    elif provider_name == "ollama":
        from src.agent.ollama_provider import OllamaProvider
        return OllamaProvider()
    else:
        raise ValueError(f"Unknown LLM provider: {provider_name}")
```

**Step 2: Create `src/agent/prompts.py`**

```python
SYSTEM_PROMPT = """You are a railway maintenance analyst for Singapore's MRT system.
You analyze sensor anomalies detected on train units and provide actionable assessments.

For each anomaly, you must provide:
1. Root cause hypothesis - what is likely causing this anomaly
2. Severity classification - critical, warning, or monitor
3. Recommended action - what should maintenance teams do

Consider:
- Time of day (peak hours mean higher impact)
- Whether multiple sensors on the same unit are abnormal (correlated failures)
- Recent history (trending vs. one-off spike)
- The specific sensor type and what it indicates about equipment health

Be concise and specific. Maintenance teams need clear, actionable guidance."""

USER_PROMPT_TEMPLATE = """Analyze this sensor anomaly:

Train Unit: {train_id} (Line: {line_id}, Station: {station_id})
Timestamp: {timestamp}
Sensor: {sensor_type}
Value: {value}
Anomaly Score: {anomaly_score:.2f}
Detection Methods Triggered: {detection_methods}
Peak Hour: {is_peak_hour}

Recent History (last 5 readings for this sensor):
{recent_history}

Other Sensors on Same Unit Currently:
{correlated_sensors}

Respond in this exact JSON format:
{{"root_cause": "...", "severity": "critical|warning|monitor", "recommended_action": "...", "reasoning": "..."}}"""
```

**Step 3: Create `src/agent/claude_provider.py`**

```python
import json

import anthropic

from src.agent.prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from src.agent.provider import AgentAssessment, AnomalyContext
from src.config import settings


class ClaudeProvider:
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    async def analyze_anomaly(self, context: AnomalyContext) -> AgentAssessment:
        prompt = USER_PROMPT_TEMPLATE.format(
            train_id=context.train_id,
            line_id=context.line_id,
            station_id=context.station_id,
            timestamp=context.timestamp.isoformat(),
            sensor_type=context.sensor_type,
            value=context.value,
            anomaly_score=context.anomaly_score,
            detection_methods=", ".join(context.detection_methods),
            is_peak_hour=context.is_peak_hour,
            recent_history=json.dumps(context.recent_history, indent=2, default=str),
            correlated_sensors=json.dumps(context.correlated_sensors, indent=2, default=str),
        )

        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )

        result = json.loads(response.content[0].text)
        return AgentAssessment(
            root_cause=result["root_cause"],
            severity=result["severity"],
            recommended_action=result["recommended_action"],
            reasoning=result["reasoning"],
        )
```

**Step 4: Write tests `tests/test_agent.py`**

```python
from datetime import datetime

from src.agent.provider import AnomalyContext, AgentAssessment, get_provider
from src.agent.prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE


def test_anomaly_context_creation():
    ctx = AnomalyContext(
        timestamp=datetime(2026, 3, 14, 8, 30),
        train_id="T001",
        line_id="NSL",
        station_id="NS1",
        sensor_type="vibration",
        value=0.8,
        anomaly_score=0.92,
        detection_methods=["zscore", "isolation_forest"],
        is_peak_hour=True,
        recent_history=[],
        correlated_sensors=[],
    )
    assert ctx.is_peak_hour is True
    assert ctx.anomaly_score == 0.92


def test_agent_assessment_creation():
    assessment = AgentAssessment(
        root_cause="Bearing wear",
        severity="critical",
        recommended_action="Immediate inspection",
        reasoning="High vibration during peak hours",
    )
    assert assessment.severity == "critical"


def test_get_provider_claude():
    provider = get_provider("claude")
    assert hasattr(provider, "analyze_anomaly")


def test_get_provider_unknown():
    try:
        get_provider("unknown")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def test_prompt_template_formats():
    ctx = AnomalyContext(
        timestamp=datetime(2026, 3, 14, 8, 30),
        train_id="T001", line_id="NSL", station_id="NS1",
        sensor_type="vibration", value=0.8, anomaly_score=0.92,
        detection_methods=["zscore"], is_peak_hour=True,
        recent_history=[], correlated_sensors=[],
    )
    prompt = USER_PROMPT_TEMPLATE.format(
        train_id=ctx.train_id, line_id=ctx.line_id, station_id=ctx.station_id,
        timestamp=ctx.timestamp.isoformat(), sensor_type=ctx.sensor_type,
        value=ctx.value, anomaly_score=ctx.anomaly_score,
        detection_methods=", ".join(ctx.detection_methods),
        is_peak_hour=ctx.is_peak_hour, recent_history="[]", correlated_sensors="[]",
    )
    assert "T001" in prompt
    assert "vibration" in prompt
    assert SYSTEM_PROMPT.startswith("You are a railway")
```

**Step 5: Run tests**

```bash
pytest tests/test_agent.py -v
```

Expected: 5 PASS

**Step 6: Commit**

```bash
git add .
git commit -m "feat: LLM provider abstraction with Claude implementation and prompts"
```

---

## Task 11: OpenAI & Ollama Providers

**Files:**
- Create: `railsense-ai/src/agent/openai_provider.py`
- Create: `railsense-ai/src/agent/ollama_provider.py`
- Test: `railsense-ai/tests/test_providers.py`

**Step 1: Implement `src/agent/openai_provider.py`**

```python
import json

import openai

from src.agent.prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from src.agent.provider import AgentAssessment, AnomalyContext
from src.config import settings


class OpenAIProvider:
    def __init__(self):
        self.client = openai.OpenAI(api_key=settings.openai_api_key)

    async def analyze_anomaly(self, context: AnomalyContext) -> AgentAssessment:
        prompt = USER_PROMPT_TEMPLATE.format(
            train_id=context.train_id, line_id=context.line_id,
            station_id=context.station_id, timestamp=context.timestamp.isoformat(),
            sensor_type=context.sensor_type, value=context.value,
            anomaly_score=context.anomaly_score,
            detection_methods=", ".join(context.detection_methods),
            is_peak_hour=context.is_peak_hour,
            recent_history=json.dumps(context.recent_history, default=str),
            correlated_sensors=json.dumps(context.correlated_sensors, default=str),
        )

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            max_tokens=500,
            response_format={"type": "json_object"},
        )

        result = json.loads(response.choices[0].message.content)
        return AgentAssessment(
            root_cause=result["root_cause"],
            severity=result["severity"],
            recommended_action=result["recommended_action"],
            reasoning=result["reasoning"],
        )
```

**Step 2: Implement `src/agent/ollama_provider.py`**

```python
import json

import httpx

from src.agent.prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from src.agent.provider import AgentAssessment, AnomalyContext


class OllamaProvider:
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3"):
        self.base_url = base_url
        self.model = model

    async def analyze_anomaly(self, context: AnomalyContext) -> AgentAssessment:
        prompt = USER_PROMPT_TEMPLATE.format(
            train_id=context.train_id, line_id=context.line_id,
            station_id=context.station_id, timestamp=context.timestamp.isoformat(),
            sensor_type=context.sensor_type, value=context.value,
            anomaly_score=context.anomaly_score,
            detection_methods=", ".join(context.detection_methods),
            is_peak_hour=context.is_peak_hour,
            recent_history=json.dumps(context.recent_history, default=str),
            correlated_sensors=json.dumps(context.correlated_sensors, default=str),
        )

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json={"model": self.model, "prompt": f"{SYSTEM_PROMPT}\n\n{prompt}", "stream": False, "format": "json"},
                timeout=60.0,
            )
            response.raise_for_status()
            result = json.loads(response.json()["response"])

        return AgentAssessment(
            root_cause=result["root_cause"],
            severity=result["severity"],
            recommended_action=result["recommended_action"],
            reasoning=result["reasoning"],
        )
```

**Step 3: Write test `tests/test_providers.py`**

```python
from src.agent.provider import get_provider


def test_get_claude_provider():
    p = get_provider("claude")
    assert type(p).__name__ == "ClaudeProvider"


def test_get_openai_provider():
    p = get_provider("openai")
    assert type(p).__name__ == "OpenAIProvider"


def test_get_ollama_provider():
    p = get_provider("ollama")
    assert type(p).__name__ == "OllamaProvider"
```

**Step 4: Run tests**

```bash
pytest tests/test_providers.py -v
```

Expected: 3 PASS

**Step 5: Commit**

```bash
git add .
git commit -m "feat: OpenAI and Ollama LLM provider implementations"
```

---

## Task 12: Agent Assessment API Endpoint

**Files:**
- Modify: `railsense-ai/src/api/main.py`
- Modify: `railsense-ai/src/api/schemas.py`
- Test: `railsense-ai/tests/test_api.py`

**Step 1: Add assessment endpoint to `src/api/main.py`**

Add these imports and endpoint after the existing code:

```python
from src.agent.provider import AnomalyContext, get_provider
from src.config import settings
from src.db.models import AgentAssessment as AgentAssessmentModel, AnomalyEvent

@app.post("/api/assess/{anomaly_event_id}", response_model=AgentAssessmentOut)
async def assess_anomaly(anomaly_event_id: int, db: Session = Depends(get_db)):
    event = db.query(AnomalyEvent).filter(AnomalyEvent.id == anomaly_event_id).first()
    if not event:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Anomaly event not found")

    # Build context from event + related data
    recent = (
        db.query(SensorReading)
        .filter(SensorReading.train_id == event.train_id, SensorReading.sensor_type == event.sensor_type)
        .filter(SensorReading.timestamp <= event.timestamp)
        .order_by(SensorReading.timestamp.desc())
        .limit(5)
        .all()
    )

    context = AnomalyContext(
        timestamp=event.timestamp,
        train_id=event.train_id,
        line_id=event.line_id,
        station_id=event.station_id,
        sensor_type=event.sensor_type.value,
        value=event.value,
        anomaly_score=event.anomaly_score,
        detection_methods=[event.detection_method],
        is_peak_hour=event.timestamp.hour in {7, 8, 9, 17, 18, 19},
        recent_history=[{"timestamp": str(r.timestamp), "value": r.value} for r in recent],
        correlated_sensors=[],
    )

    provider = get_provider(settings.llm_provider)
    assessment = await provider.analyze_anomaly(context)

    db_assessment = AgentAssessmentModel(
        anomaly_event_id=event.id,
        llm_provider=settings.llm_provider,
        root_cause=assessment.root_cause,
        severity_override=assessment.severity,
        recommended_action=assessment.recommended_action,
        reasoning=assessment.reasoning,
    )
    db.add(db_assessment)
    db.commit()
    db.refresh(db_assessment)
    return db_assessment
```

**Step 2: Add test for 404 case**

```python
# Add to tests/test_api.py
def test_assess_nonexistent_anomaly():
    r = client.post("/api/assess/99999")
    assert r.status_code == 404
```

**Step 3: Run tests**

```bash
pytest tests/test_api.py -v
```

Expected: 4 PASS

**Step 4: Commit**

```bash
git add .
git commit -m "feat: anomaly assessment API endpoint with LLM agent integration"
```

---

## Task 13: LTA DataMall API Client

**Files:**
- Create: `railsense-ai/src/ingestion/lta_client.py`
- Test: `railsense-ai/tests/test_lta_client.py`

**Step 1: Write failing tests `tests/test_lta_client.py`**

```python
from src.ingestion.lta_client import LtaClient


def test_client_init():
    client = LtaClient(api_key="test-key")
    assert client.api_key == "test-key"
    assert "datamall2.mytransport.sg" in client.base_url


def test_parse_disruption():
    raw = {
        "Status": "2",
        "AffectedLine": "NSL",
        "Direction": "Jurong East - Marina South Pier",
        "Stations": "NS1-NS5",
        "FreeText": "Train service disruption on NSL",
        "CreateDate": "2026-03-14T08:30:00",
    }
    parsed = LtaClient.parse_disruption(raw)
    assert parsed["line_id"] == "NSL"
    assert "disruption" in parsed["message"].lower()


def test_parse_train_arrival():
    raw = {
        "StationCode": "NS1",
        "StationName": "Jurong East",
        "Destination": "Marina South Pier",
        "EstimatedArrival": "2026-03-14T08:35:00",
    }
    parsed = LtaClient.parse_train_arrival(raw)
    assert parsed["station_id"] == "NS1"
```

**Step 2: Run tests to verify they fail**

```bash
pytest tests/test_lta_client.py -v
```

**Step 3: Implement `src/ingestion/lta_client.py`**

```python
from datetime import datetime

import httpx

from src.config import settings


class LtaClient:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.lta_api_key
        self.base_url = "https://datamall2.mytransport.sg/ltaodataservice"
        self.headers = {"AccountKey": self.api_key, "accept": "application/json"}

    async def get_train_arrivals(self, station_code: str) -> list[dict]:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{self.base_url}/PCDRealTime",
                params={"TrainLine": station_code[:2]},
                headers=self.headers,
                timeout=10.0,
            )
            r.raise_for_status()
            return [self.parse_train_arrival(item) for item in r.json().get("value", [])]

    async def get_disruptions(self) -> list[dict]:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{self.base_url}/TrainServiceAlerts",
                headers=self.headers,
                timeout=10.0,
            )
            r.raise_for_status()
            return [
                self.parse_disruption(item)
                for item in r.json().get("value", {}).get("AffectedSegments", [])
            ]

    @staticmethod
    def parse_disruption(raw: dict) -> dict:
        return {
            "line_id": raw.get("AffectedLine", ""),
            "station_id": raw.get("Stations", "").split("-")[0] if raw.get("Stations") else None,
            "direction": raw.get("Direction", ""),
            "message": raw.get("FreeText", ""),
            "timestamp": datetime.fromisoformat(raw["CreateDate"]) if raw.get("CreateDate") else datetime.utcnow(),
        }

    @staticmethod
    def parse_train_arrival(raw: dict) -> dict:
        return {
            "station_id": raw.get("StationCode", ""),
            "station_name": raw.get("StationName", ""),
            "destination": raw.get("Destination", ""),
            "estimated_arrival": datetime.fromisoformat(raw["EstimatedArrival"]) if raw.get("EstimatedArrival") else None,
        }
```

**Step 4: Run tests**

```bash
pytest tests/test_lta_client.py -v
```

Expected: 3 PASS

**Step 5: Commit**

```bash
git add .
git commit -m "feat: LTA DataMall API client for train arrivals and disruptions"
```

---

## Task 14: Detection Pipeline Runner

**Files:**
- Create: `railsense-ai/src/detection/pipeline.py`
- Test: `railsense-ai/tests/test_pipeline.py`

**Step 1: Write failing tests `tests/test_pipeline.py`**

```python
import pandas as pd
import numpy as np

from src.detection.pipeline import DetectionPipeline


def _make_test_data(n=576):
    rng = np.random.default_rng(42)
    timestamps = pd.date_range("2026-03-01", periods=n, freq="5min")
    return pd.DataFrame({
        "timestamp": timestamps,
        "train_id": "T001",
        "sensor_type": "vibration",
        "value": rng.normal(0.3, 0.05, n),
        "line_id": "NSL",
        "station_id": "NS1",
    })


def test_pipeline_runs_zscore():
    df = _make_test_data()
    pipeline = DetectionPipeline(methods=["zscore"])
    results = pipeline.run(df)
    assert "anomaly_score" in results.columns
    assert "detection_method" in results.columns


def test_pipeline_runs_multiple_methods():
    df = _make_test_data()
    pipeline = DetectionPipeline(methods=["zscore", "stl"])
    results = pipeline.run(df)
    assert "ensemble_score" in results.columns
    assert "ensemble_severity" in results.columns


def test_pipeline_filters_warnings_and_above():
    df = _make_test_data()
    pipeline = DetectionPipeline(methods=["zscore"])
    anomalies = pipeline.get_anomaly_events(df)
    assert isinstance(anomalies, list)
    for event in anomalies:
        assert event["severity"] in ("warning", "critical")
```

**Step 2: Run tests to verify they fail**

```bash
pytest tests/test_pipeline.py -v
```

**Step 3: Implement `src/detection/pipeline.py`**

```python
import pandas as pd

from src.detection.ensemble import EnsembleScorer
from src.detection.isolation_forest import IsolationForestDetector
from src.detection.prophet_detector import ProphetDetector
from src.detection.stl_detector import STLDetector
from src.detection.zscore import ZScoreDetector

DETECTOR_MAP = {
    "zscore": lambda: ZScoreDetector(),
    "isolation_forest": lambda: IsolationForestDetector(),
    "stl": lambda: STLDetector(),
    "prophet": lambda: ProphetDetector(),
}


class DetectionPipeline:
    def __init__(self, methods: list[str] | None = None):
        self.methods = methods or ["zscore", "stl", "isolation_forest"]
        self.scorer = EnsembleScorer()

    def run(self, df: pd.DataFrame) -> pd.DataFrame:
        if len(self.methods) == 1:
            detector = DETECTOR_MAP[self.methods[0]]()
            return detector.detect(df)

        results = []
        for method_name in self.methods:
            if method_name == "isolation_forest":
                continue  # handled separately — needs multivariate input
            detector = DETECTOR_MAP[method_name]()
            results.append(detector.detect(df))

        if len(results) == 0:
            return df

        if len(results) == 1:
            return results[0]

        combined = self.scorer.combine(results)
        output = df.copy()
        output["ensemble_score"] = combined["ensemble_score"]
        output["ensemble_severity"] = combined["ensemble_severity"]
        output["methods_agreed"] = combined["methods_agreed"]
        return output

    def get_anomaly_events(self, df: pd.DataFrame) -> list[dict]:
        result = self.run(df)

        score_col = "ensemble_score" if "ensemble_score" in result.columns else "anomaly_score"
        severity_col = "ensemble_severity" if "ensemble_severity" in result.columns else "severity"

        events = []
        for _, row in result.iterrows():
            sev = row.get(severity_col)
            if sev in ("warning", "critical"):
                events.append({
                    "timestamp": row["timestamp"],
                    "train_id": row.get("train_id", ""),
                    "sensor_type": row.get("sensor_type", ""),
                    "anomaly_score": float(row[score_col]),
                    "severity": sev,
                    "value": float(row["value"]),
                    "line_id": row.get("line_id", ""),
                    "station_id": row.get("station_id", ""),
                    "detection_method": ",".join(self.methods),
                })
        return events
```

**Step 4: Run tests**

```bash
pytest tests/test_pipeline.py -v
```

Expected: 3 PASS

**Step 5: Commit**

```bash
git add .
git commit -m "feat: detection pipeline runner with ensemble integration"
```

---

## Task 15: Streamlit Dashboard — Live Overview

**Files:**
- Modify: `railsense-ai/src/dashboard/app.py`

**Step 1: Implement the Live Overview page**

```python
import httpx
import pandas as pd
import streamlit as st

API_BASE = "http://localhost:8000"

st.set_page_config(page_title="RailSense-AI", layout="wide")

page = st.sidebar.selectbox("Navigation", ["Live Overview", "Sensor Explorer", "Alert Feed", "Model Comparison"])


def fetch(endpoint: str, params: dict | None = None) -> list[dict]:
    try:
        r = httpx.get(f"{API_BASE}{endpoint}", params=params, timeout=10.0)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"API error: {e}")
        return []


if page == "Live Overview":
    st.title("RailSense-AI — Live Overview")

    col1, col2, col3, col4 = st.columns(4)
    anomalies = fetch("/api/anomalies", {"limit": 500})

    with col1:
        critical = [a for a in anomalies if a["severity"] == "critical"]
        st.metric("Critical Alerts", len(critical))
    with col2:
        warning = [a for a in anomalies if a["severity"] == "warning"]
        st.metric("Warnings", len(warning))
    with col3:
        trains = set(a["train_id"] for a in anomalies)
        st.metric("Affected Trains", len(trains))
    with col4:
        total = len(anomalies)
        health = max(0, 100 - total)
        st.metric("System Health", f"{health}%")

    if anomalies:
        st.subheader("Recent Anomalies by Line")
        df = pd.DataFrame(anomalies)
        st.dataframe(df[["timestamp", "train_id", "line_id", "sensor_type", "severity", "anomaly_score"]], use_container_width=True)


elif page == "Sensor Explorer":
    st.title("Sensor Explorer")
    st.info("Select a train unit to view sensor data.")
    # Implemented in Task 16


elif page == "Alert Feed":
    st.title("Alert Feed")
    st.info("LLM agent assessments will appear here.")
    # Implemented in Task 17


elif page == "Model Comparison":
    st.title("Model Comparison — STL vs Prophet")
    st.info("Detection method comparison will appear here.")
    # Implemented in Task 18
```

**Step 2: Verify manually**

```bash
docker compose up -d
# Visit http://localhost:8501
```

Expected: Dashboard loads with 4 metric cards and anomaly table

**Step 3: Commit**

```bash
git add .
git commit -m "feat: Streamlit dashboard with Live Overview page"
```

---

## Task 16: Streamlit Dashboard — Sensor Explorer

**Files:**
- Modify: `railsense-ai/src/dashboard/app.py`

**Step 1: Replace the Sensor Explorer placeholder** with:

```python
elif page == "Sensor Explorer":
    st.title("Sensor Explorer")

    train_id = st.selectbox("Train Unit", ["T001", "T002", "T003", "T004", "T005"])
    sensor_type = st.selectbox("Sensor", ["vibration", "temperature", "door_cycle", "current_draw"])

    readings = fetch("/api/sensors", {"train_id": train_id, "sensor_type": sensor_type, "limit": 1000})

    if readings:
        df = pd.DataFrame(readings)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp")

        # Plot sensor values
        st.subheader(f"{sensor_type} — {train_id}")
        st.line_chart(df.set_index("timestamp")["value"])

        # Overlay anomalies if any
        anomalies = fetch("/api/anomalies", {"train_id": train_id, "limit": 200})
        if anomalies:
            anom_df = pd.DataFrame(anomalies)
            anom_df = anom_df[anom_df["sensor_type"] == sensor_type]
            if not anom_df.empty:
                st.subheader("Detected Anomalies")
                st.dataframe(anom_df[["timestamp", "anomaly_score", "severity", "detection_method"]], use_container_width=True)
    else:
        st.warning("No sensor data found. Run the seed script first.")
```

**Step 2: Verify manually**

```bash
# Visit http://localhost:8501, select "Sensor Explorer"
```

**Step 3: Commit**

```bash
git add .
git commit -m "feat: Sensor Explorer page with anomaly overlay"
```

---

## Task 17: Streamlit Dashboard — Alert Feed

**Files:**
- Modify: `railsense-ai/src/dashboard/app.py`
- Modify: `railsense-ai/src/api/main.py` (add assessments GET endpoint)

**Step 1: Add GET assessments endpoint to `src/api/main.py`**

```python
from src.db.models import AgentAssessment as AgentAssessmentModel

@app.get("/api/assessments", response_model=list[AgentAssessmentOut])
def get_assessments(
    limit: int = Query(default=50, le=200),
    db: Session = Depends(get_db),
):
    return (
        db.query(AgentAssessmentModel)
        .order_by(AgentAssessmentModel.created_at.desc())
        .limit(limit)
        .all()
    )
```

**Step 2: Replace Alert Feed placeholder** in dashboard:

```python
elif page == "Alert Feed":
    st.title("Alert Feed")

    severity_filter = st.multiselect("Filter by severity", ["critical", "warning"], default=["critical", "warning"])
    anomalies = fetch("/api/anomalies", {"limit": 200})

    if anomalies:
        df = pd.DataFrame(anomalies)
        df = df[df["severity"].isin(severity_filter)]

        for _, row in df.iterrows():
            severity_color = "🔴" if row["severity"] == "critical" else "🟡"
            with st.expander(f"{severity_color} {row['train_id']} — {row['sensor_type']} ({row['severity']}) — {row['timestamp']}"):
                st.write(f"**Score:** {row['anomaly_score']:.2f}")
                st.write(f"**Line:** {row['line_id']} | **Station:** {row['station_id']}")
                st.write(f"**Detection Method:** {row['detection_method']}")

                # Show agent assessment if available
                if st.button(f"Request AI Analysis", key=f"assess_{row['id']}"):
                    with st.spinner("Analyzing..."):
                        r = httpx.post(f"{API_BASE}/api/assess/{row['id']}", timeout=30.0)
                        if r.status_code == 200:
                            assessment = r.json()
                            st.success(f"**Root Cause:** {assessment['root_cause']}")
                            st.info(f"**Action:** {assessment['recommended_action']}")
                            st.caption(f"**Reasoning:** {assessment['reasoning']}")
                        else:
                            st.error("Analysis failed")
    else:
        st.info("No anomalies detected yet.")
```

**Step 3: Verify manually**

**Step 4: Commit**

```bash
git add .
git commit -m "feat: Alert Feed page with inline LLM agent analysis"
```

---

## Task 18: Streamlit Dashboard — Model Comparison

**Files:**
- Modify: `railsense-ai/src/dashboard/app.py`
- Create: `railsense-ai/src/detection/compare.py`
- Test: `railsense-ai/tests/test_compare.py`

**Step 1: Write failing test `tests/test_compare.py`**

```python
import numpy as np
import pandas as pd

from src.detection.compare import compare_detectors


def test_compare_returns_metrics():
    rng = np.random.default_rng(42)
    n = 576
    df = pd.DataFrame({
        "timestamp": pd.date_range("2026-03-01", periods=n, freq="5min"),
        "value": rng.normal(35, 2, n),
    })
    is_anomaly = np.zeros(n, dtype=bool)
    is_anomaly[300] = True
    df["is_anomaly"] = is_anomaly
    df.loc[300, "value"] += 20

    metrics = compare_detectors(df)
    assert "stl" in metrics
    assert "prophet" in metrics
    for m in metrics.values():
        assert "precision" in m
        assert "recall" in m
        assert "f1" in m
        assert "time_seconds" in m
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_compare.py -v
```

**Step 3: Implement `src/detection/compare.py`**

```python
import time

import numpy as np
import pandas as pd
from sklearn.metrics import precision_score, recall_score, f1_score

from src.detection.stl_detector import STLDetector
from src.detection.prophet_detector import ProphetDetector


def compare_detectors(df: pd.DataFrame) -> dict:
    ground_truth = df["is_anomaly"].values.astype(int)
    results = {}

    for name, detector in [("stl", STLDetector()), ("prophet", ProphetDetector())]:
        start = time.time()
        detected = detector.detect(df)
        elapsed = time.time() - start

        predicted = np.where(detected["severity"].isna(), 0, 1)

        results[name] = {
            "precision": float(precision_score(ground_truth, predicted, zero_division=0)),
            "recall": float(recall_score(ground_truth, predicted, zero_division=0)),
            "f1": float(f1_score(ground_truth, predicted, zero_division=0)),
            "time_seconds": round(elapsed, 2),
            "total_flagged": int(predicted.sum()),
            "true_anomalies": int(ground_truth.sum()),
        }

    return results
```

**Step 4: Run test**

```bash
pytest tests/test_compare.py -v
```

Expected: 1 PASS

**Step 5: Replace Model Comparison placeholder** in dashboard:

```python
elif page == "Model Comparison":
    st.title("Model Comparison — STL vs Prophet")

    st.write("Comparing detection performance on synthetic data with known anomalies.")

    if st.button("Run Comparison"):
        with st.spinner("Running STL and Prophet detectors... (Prophet may take a minute)"):
            from src.ingestion.synthetic_gen import SyntheticGenerator, AnomalyScenario
            from src.detection.compare import compare_detectors

            gen = SyntheticGenerator(seed=99)
            scenario = AnomalyScenario(sensor_types=["temperature"], start_hour=12, duration_hours=2, magnitude=4.0)
            df = gen.generate(train_id="COMPARE", hours=48, anomalies=[scenario])
            temp_df = df[df["sensor_type"] == "temperature"].reset_index(drop=True)

            metrics = compare_detectors(temp_df)

            col1, col2 = st.columns(2)
            for col, (name, m) in zip([col1, col2], metrics.items()):
                with col:
                    st.subheader(name.upper())
                    st.metric("Precision", f"{m['precision']:.2%}")
                    st.metric("Recall", f"{m['recall']:.2%}")
                    st.metric("F1 Score", f"{m['f1']:.2%}")
                    st.metric("Computation Time", f"{m['time_seconds']}s")
                    st.metric("Total Flagged", m["total_flagged"])

            st.subheader("Sensor Data with Anomaly Window")
            st.line_chart(temp_df.set_index("timestamp")["value"])
```

**Step 6: Commit**

```bash
git add .
git commit -m "feat: Model Comparison page with STL vs Prophet metrics"
```

---

## Task 19: Prefect Scheduling

**Files:**
- Create: `railsense-ai/src/tasks.py`

**Step 1: Implement `src/tasks.py`**

```python
"""Prefect tasks for scheduled data ingestion and anomaly detection."""

from prefect import flow, task
from sqlalchemy.orm import Session

from src.db.models import AnomalyEvent, SensorReading
from src.db.session import SessionLocal
from src.detection.pipeline import DetectionPipeline
from src.ingestion.synthetic_gen import SyntheticGenerator
import pandas as pd


@task
def ingest_synthetic_data(train_id: str, hours: int = 1):
    gen = SyntheticGenerator()
    df = gen.generate(train_id=train_id, hours=hours)

    db = SessionLocal()
    readings = [
        SensorReading(
            timestamp=row["timestamp"], train_id=row["train_id"],
            sensor_type=row["sensor_type"], value=row["value"],
            line_id=row["line_id"], station_id=row["station_id"],
        )
        for _, row in df.iterrows()
    ]
    db.bulk_save_objects(readings)
    db.commit()
    db.close()
    return len(readings)


@task
def run_detection(train_id: str, sensor_type: str):
    db = SessionLocal()
    readings = (
        db.query(SensorReading)
        .filter(SensorReading.train_id == train_id, SensorReading.sensor_type == sensor_type)
        .order_by(SensorReading.timestamp.desc())
        .limit(288)  # last 24h at 5-min intervals
        .all()
    )

    if not readings:
        db.close()
        return 0

    df = pd.DataFrame([{
        "timestamp": r.timestamp, "train_id": r.train_id,
        "sensor_type": r.sensor_type.value, "value": r.value,
        "line_id": r.line_id, "station_id": r.station_id,
    } for r in readings])

    pipeline = DetectionPipeline(methods=["zscore", "stl"])
    events = pipeline.get_anomaly_events(df)

    for event in events:
        db.add(AnomalyEvent(
            timestamp=event["timestamp"], train_id=event["train_id"],
            sensor_type=event["sensor_type"], detection_method=event["detection_method"],
            anomaly_score=event["anomaly_score"], severity=event["severity"],
            value=event["value"], line_id=event["line_id"], station_id=event["station_id"],
        ))
    db.commit()
    db.close()
    return len(events)


@flow(name="railsense-ingestion-detection")
def ingestion_detection_flow():
    train_ids = ["T001", "T002", "T003", "T004", "T005"]
    sensor_types = ["vibration", "temperature", "door_cycle", "current_draw"]

    for train_id in train_ids:
        ingest_synthetic_data(train_id, hours=1)

    for train_id in train_ids:
        for sensor_type in sensor_types:
            run_detection(train_id, sensor_type)


if __name__ == "__main__":
    ingestion_detection_flow()
```

**Step 2: Verify**

```bash
python -m src.tasks
```

Expected: Prefect flow runs, ingests data, detects anomalies

**Step 3: Commit**

```bash
git add .
git commit -m "feat: Prefect flow for scheduled ingestion and detection"
```

---

## Task 20: Test Configuration & conftest

**Files:**
- Create: `railsense-ai/tests/conftest.py`

**Step 1: Create `tests/conftest.py`** — test database setup using SQLite

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.db.session import Base


@pytest.fixture(scope="session")
def test_engine():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def db_session(test_engine):
    Session = sessionmaker(bind=test_engine)
    session = Session()
    yield session
    session.rollback()
    session.close()
```

**Step 2: Run full test suite**

```bash
pytest tests/ -v --tb=short
```

Expected: All tests pass

**Step 3: Commit**

```bash
git add .
git commit -m "feat: test conftest with SQLite in-memory database"
```

---

## Task 21: README & Final Polish

**Files:**
- Create: `railsense-ai/README.md`

**Step 1: Write README** with:

- Project description and motivation (1 paragraph)
- Architecture diagram (ASCII or Mermaid)
- Quick start (docker compose up)
- Screenshots placeholder
- Tech stack table
- How detection methods work (brief)
- How the AI agent works (brief)
- API endpoints reference
- License

**Step 2: Create demo seed script** `scripts/demo_seed.py` that generates a compelling 30-day dataset with:

- 5 train units across 3 MRT lines
- 3 different failure scenarios (bearing degradation, door mechanism wear, electrical fault)
- Realistic temporal patterns

**Step 3: Final verification**

```bash
docker compose up --build -d
python scripts/demo_seed.py
python -m src.tasks
# Visit http://localhost:8501 and verify all 4 pages work
```

**Step 4: Commit**

```bash
git add .
git commit -m "docs: README with architecture, setup, and API reference"
```
