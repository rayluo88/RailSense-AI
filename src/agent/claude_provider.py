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
            active_disruptions=json.dumps(context.active_disruptions, default=str) or "None",
            crowd_levels=json.dumps(context.crowd_levels, default=str) or "None",
            facilities_issues=json.dumps(context.facilities_issues, default=str) or "None",
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
