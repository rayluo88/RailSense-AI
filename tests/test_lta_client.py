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
