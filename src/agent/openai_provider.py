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
