from datetime import datetime

from src.ingestion.lta_client import ALL_TRAIN_LINES, LtaClient


def test_client_init():
    client = LtaClient(api_key="test-key")
    assert client.api_key == "test-key"
    assert "datamall2.mytransport.sg" in client.base_url


def test_all_train_lines_defined():
    assert "EWL" in ALL_TRAIN_LINES
    assert "NSL" in ALL_TRAIN_LINES
    assert "TEL" in ALL_TRAIN_LINES
    assert len(ALL_TRAIN_LINES) == 11


def test_parse_crowd_realtime():
    raw = {
        "Station": "EW13",
        "StartTime": "2026-04-11T09:40:00+08:00",
        "EndTime": "2026-04-11T09:50:00+08:00",
        "CrowdLevel": "h",
    }
    parsed = LtaClient._parse_crowd_realtime(raw, "EWL")
    assert parsed["station_code"] == "EW13"
    assert parsed["train_line"] == "EWL"
    assert parsed["crowd_level"] == "h"
    assert parsed["source"] == "realtime"
    assert parsed["end_time"] is not None


def test_parse_crowd_realtime_missing_times():
    raw = {"Station": "NS1", "StartTime": None, "EndTime": None, "CrowdLevel": "NA"}
    parsed = LtaClient._parse_crowd_realtime(raw, "NSL")
    assert parsed["crowd_level"] == "NA"
    assert parsed["end_time"] is None
    # Falls back to utcnow when StartTime is None
    assert isinstance(parsed["timestamp"], datetime)


def test_parse_crowd_forecast():
    raw = {
        "Station": "NS1",
        "Start": "2026-04-11T08:00:00+08:00",
        "CrowdLevel": "m",
    }
    parsed = LtaClient._parse_crowd_forecast(raw, "NSL")
    assert parsed["station_code"] == "NS1"
    assert parsed["crowd_level"] == "m"
    assert parsed["source"] == "forecast"
    assert parsed["end_time"] is None


def test_parse_disruption():
    raw = {
        "Line": "NEL",
        "Direction": "Punggol",
        "Stations": "NE1,NE3,NE4,NE5",
        "FreePublicBus": "NE1,NE3",
        "FreeMRTShuttle": "NE1|CC15",
    }
    fetched_at = datetime(2026, 4, 11, 10, 0, 0)
    parsed = LtaClient._parse_disruption(raw, "2", fetched_at)
    assert parsed["line_id"] == "NEL"
    assert parsed["direction"] == "Punggol"
    assert parsed["affected_stations"] == "NE1,NE3,NE4,NE5"
    assert parsed["free_bus"] == "NE1,NE3"
    assert parsed["free_shuttle"] == "NE1|CC15"
    assert parsed["status"] == "2"
    assert parsed["timestamp"] == fetched_at


def test_parse_disruption_empty_segment():
    raw = {"Line": "EWL", "Direction": "", "Stations": "", "FreePublicBus": "", "FreeMRTShuttle": ""}
    parsed = LtaClient._parse_disruption(raw, "1", datetime.utcnow())
    assert parsed["line_id"] == "EWL"
    assert parsed["status"] == "1"


def test_parse_facility():
    raw = {
        "Line": "DTL",
        "StationCode": "DT20",
        "StationName": "Fort Canning",
        "LiftID": "B1L02",
        "LiftDesc": "EXIT B STREET LEVEL - CONCOURSE",
    }
    parsed = LtaClient._parse_facility(raw)
    assert parsed["train_line"] == "DTL"
    assert parsed["station_code"] == "DT20"
    assert parsed["station_name"] == "Fort Canning"
    assert parsed["equipment_type"] == "Lift"
    assert parsed["equipment_id"] == "B1L02"
    assert "CONCOURSE" in parsed["description"]


def test_parse_facility_missing_lift_id():
    raw = {"Line": "NSL", "StationCode": "NS1", "StationName": "Jurong East", "LiftID": "", "LiftDesc": ""}
    parsed = LtaClient._parse_facility(raw)
    assert parsed["station_code"] == "NS1"
    assert parsed["equipment_id"] == ""
