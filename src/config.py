from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://railsense:railsense_dev@localhost:5432/railsense"
    llm_provider: str = "deepseek"
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    deepseek_api_key: str = ""
    lta_api_key: str = ""
    enable_scheduler: bool = True
    scheduler_start_hour: int = 9   # SGT (0900)
    scheduler_end_hour: int = 22    # SGT (2200)

    model_config = {"env_file": ".env"}


settings = Settings()
