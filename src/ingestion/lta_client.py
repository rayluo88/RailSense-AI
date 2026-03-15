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
