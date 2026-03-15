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
    if provider_name == "deepseek":
        from src.agent.deepseek_provider import DeepSeekProvider
        return DeepSeekProvider()
    elif provider_name == "claude":
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
