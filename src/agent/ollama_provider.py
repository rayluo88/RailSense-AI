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
            active_disruptions=json.dumps(context.active_disruptions, default=str) or "None",
            crowd_levels=json.dumps(context.crowd_levels, default=str) or "None",
            facilities_issues=json.dumps(context.facilities_issues, default=str) or "None",
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
