from src.agent.provider import get_provider


def test_get_deepseek_provider():
    p = get_provider("deepseek")
    assert type(p).__name__ == "DeepSeekProvider"


def test_get_claude_provider():
    p = get_provider("claude")
    assert type(p).__name__ == "ClaudeProvider"


def test_get_openai_provider():
    p = get_provider("openai")
    assert type(p).__name__ == "OpenAIProvider"


def test_get_ollama_provider():
    p = get_provider("ollama")
    assert type(p).__name__ == "OllamaProvider"
