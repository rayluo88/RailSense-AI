import json

import openai

from src.agent.prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from src.agent.provider import AgentAssessment, AnomalyContext
from src.config import settings


class DeepSeekProvider:
    def __init__(self):
        self.client = openai.OpenAI(
            api_key=settings.deepseek_api_key,
            base_url="https://api.deepseek.com",
        )

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

        response = self.client.chat.completions.create(
            model="deepseek-chat",
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
