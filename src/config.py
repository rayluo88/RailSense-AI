from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://railsense:railsense_dev@localhost:5432/railsense"
    llm_provider: str = "deepseek"
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    deepseek_api_key: str = ""
    lta_api_key: str = ""

    model_config = {"env_file": ".env"}


settings = Settings()
