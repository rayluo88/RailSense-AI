from datetime import datetime

import httpx

from src.config import settings

ALL_TRAIN_LINES = ["CCL", "CEL", "CGL", "DTL", "EWL", "NEL", "NSL", "BPL", "SLRT", "PLRT", "TEL"]


class LtaClient:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.lta_api_key
        self.base_url = "https://datamall2.mytransport.sg/ltaodataservice"
        self.headers = {"AccountKey": self.api_key, "accept": "application/json"}

    async def get_crowd_density_realtime(self, train_line: str) -> list[dict]:
        """Real-time MRT/LRT station crowdedness level for a train line. Updates every 10 min."""
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{self.base_url}/PCDRealTime",
                params={"TrainLine": train_line},
                headers=self.headers,
                timeout=10.0,
            )
            r.raise_for_status()
            return [self._parse_crowd_realtime(item, train_line) for item in r.json().get("value", [])]

    async def get_crowd_density_forecast(self, train_line: str) -> list[dict]:
        """Forecasted MRT/LRT station crowdedness at 30-minute intervals. Updates every 24 hrs."""
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{self.base_url}/PCDForecast",
                params={"TrainLine": train_line},
                headers=self.headers,
                timeout=10.0,
            )
            r.raise_for_status()
            return [self._parse_crowd_forecast(item, train_line) for item in r.json().get("value", [])]

    async def get_disruptions(self) -> list[dict]:
        """Active train service disruptions. Updates ad hoc."""
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{self.base_url}/TrainServiceAlerts",
                headers=self.headers,
                timeout=10.0,
            )
            r.raise_for_status()
            payload = r.json().get("value", {})
            overall_status = str(payload.get("Status", "1"))
            segments = payload.get("AffectedSegments", [])
            now = datetime.utcnow()
            return [self._parse_disruption(seg, overall_status, now) for seg in segments]

    async def get_facilities_maintenance(self) -> list[dict]:
        """Adhoc lift maintenance events at MRT stations."""
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{self.base_url}/v2/FacilitiesMaintenance",
                headers=self.headers,
                timeout=10.0,
            )
            r.raise_for_status()
            return [self._parse_facility(item) for item in r.json().get("value", [])]

    @staticmethod
    def _parse_crowd_realtime(raw: dict, train_line: str) -> dict:
        def _parse_dt(s: str | None) -> datetime | None:
            if not s:
                return None
            try:
                return datetime.fromisoformat(s)
            except ValueError:
                return None

        return {
            "station_code": raw.get("Station", ""),
            "train_line": train_line,
            "timestamp": _parse_dt(raw.get("StartTime")) or datetime.utcnow(),
            "end_time": _parse_dt(raw.get("EndTime")),
            "crowd_level": raw.get("CrowdLevel", "NA"),
            "source": "realtime",
        }

    @staticmethod
    def _parse_crowd_forecast(raw: dict, train_line: str) -> dict:
        def _parse_dt(s: str | None) -> datetime | None:
            if not s:
                return None
            try:
                return datetime.fromisoformat(s)
            except ValueError:
                return None

        return {
            "station_code": raw.get("Station", ""),
            "train_line": train_line,
            "timestamp": _parse_dt(raw.get("Start")) or datetime.utcnow(),
            "end_time": None,
            "crowd_level": raw.get("CrowdLevel", "NA"),
            "source": "forecast",
        }

    @staticmethod
    def _parse_disruption(raw: dict, overall_status: str, fetched_at: datetime) -> dict:
        return {
            "line_id": raw.get("Line", ""),
            "direction": raw.get("Direction", ""),
            "affected_stations": raw.get("Stations", ""),
            "free_bus": raw.get("FreePublicBus", ""),
            "free_shuttle": raw.get("FreeMRTShuttle", ""),
            "message": raw.get("Direction", "") or f"Service disruption on {raw.get('Line', 'unknown')} line",
            "status": overall_status,
            "timestamp": fetched_at,
        }

    @staticmethod
    def _parse_facility(raw: dict) -> dict:
        return {
            "train_line": raw.get("Line", ""),
            "station_code": raw.get("StationCode", ""),
            "station_name": raw.get("StationName", ""),
            "equipment_type": "Lift",
            "equipment_id": raw.get("LiftID", ""),
            "description": raw.get("LiftDesc", ""),
        }
