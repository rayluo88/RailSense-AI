"""Tests for src/ingestion/writers.py — shared DB write helpers."""

from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.db.models import LtaCrowdDensity, LtaDisruption, LtaFacilitiesMaintenance
from src.db.session import Base
from src.ingestion.writers import write_crowd_density, write_disruptions, write_facilities


def _make_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_write_disruptions_inserts():
    db = _make_db()
    disruptions = [
        {
            "line_id": "EWL",
            "direction": "Pasir Ris",
            "affected_stations": "EW1,EW2,EW3",
            "timestamp": datetime(2026, 4, 16, 10, 0),
            "status": "2",
            "free_bus": "EW1",
            "free_shuttle": "",
        }
    ]
    count = write_disruptions(db, disruptions)
    assert count == 1
    assert db.query(LtaDisruption).count() == 1


def test_write_disruptions_deduplicates():
    db = _make_db()
    disruption = {
        "line_id": "NSL",
        "direction": "Marina South Pier",
        "affected_stations": "NS1,NS2",
        "timestamp": datetime(2026, 4, 16, 10, 0),
        "status": "2",
        "free_bus": "",
        "free_shuttle": "",
    }
    write_disruptions(db, [disruption])
    count = write_disruptions(db, [disruption])
    assert count == 0  # Second insert is deduplicated
    assert db.query(LtaDisruption).count() == 1


def test_write_disruptions_empty():
    db = _make_db()
    assert write_disruptions(db, []) == 0


def test_write_crowd_density_inserts():
    db = _make_db()
    records = [
        {
            "station_code": "EW13",
            "train_line": "EWL",
            "timestamp": datetime(2026, 4, 16, 10, 0),
            "end_time": datetime(2026, 4, 16, 10, 10),
            "crowd_level": "h",
            "source": "realtime",
        },
        {
            "station_code": "EW14",
            "train_line": "EWL",
            "timestamp": datetime(2026, 4, 16, 10, 0),
            "end_time": datetime(2026, 4, 16, 10, 10),
            "crowd_level": "l",
            "source": "realtime",
        },
    ]
    count = write_crowd_density(db, records)
    assert count == 2
    assert db.query(LtaCrowdDensity).count() == 2


def test_write_crowd_density_skips_empty_station():
    db = _make_db()
    records = [
        {
            "station_code": "",
            "train_line": "EWL",
            "timestamp": datetime(2026, 4, 16, 10, 0),
            "end_time": None,
            "crowd_level": "NA",
            "source": "realtime",
        },
        {
            "station_code": "EW1",
            "train_line": "EWL",
            "timestamp": datetime(2026, 4, 16, 10, 0),
            "end_time": None,
            "crowd_level": "l",
            "source": "realtime",
        },
    ]
    count = write_crowd_density(db, records)
    assert count == 1


def test_write_crowd_density_empty():
    db = _make_db()
    assert write_crowd_density(db, []) == 0


def test_write_facilities_replaces_snapshot():
    db = _make_db()
    batch1 = [
        {
            "station_code": "DT20",
            "station_name": "Fort Canning",
            "train_line": "DTL",
            "equipment_type": "Lift",
            "equipment_id": "B1L02",
            "description": "EXIT B",
        }
    ]
    write_facilities(db, batch1)
    assert db.query(LtaFacilitiesMaintenance).count() == 1

    batch2 = [
        {
            "station_code": "NS1",
            "station_name": "Jurong East",
            "train_line": "NSL",
            "equipment_type": "Lift",
            "equipment_id": "A1L01",
            "description": "EXIT A",
        },
        {
            "station_code": "NS2",
            "station_name": "Bukit Batok",
            "train_line": "NSL",
            "equipment_type": "Lift",
            "equipment_id": "A1L02",
            "description": "EXIT B",
        },
    ]
    count = write_facilities(db, batch2)
    assert count == 2
    # Old records replaced
    assert db.query(LtaFacilitiesMaintenance).count() == 2
    codes = {r.station_code for r in db.query(LtaFacilitiesMaintenance).all()}
    assert codes == {"NS1", "NS2"}


def test_write_facilities_skips_empty_station():
    db = _make_db()
    facilities = [
        {
            "station_code": "",
            "station_name": "",
            "train_line": "EWL",
            "equipment_type": "Lift",
            "equipment_id": "X",
            "description": "test",
        }
    ]
    count = write_facilities(db, facilities)
    assert count == 0


def test_write_facilities_empty():
    db = _make_db()
    assert write_facilities(db, []) == 0
