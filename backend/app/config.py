"""
Centralized settings, loaded from environment variables / .env file.
Import `settings` anywhere you need a config value — never read os.environ directly
elsewhere in the app.
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Hugging Face / LLM
    hf_model_repo: str = "MohamedShata/tariikhna-llama-3.1-8b-lora"
    hf_token: str = ""
    llm_mode: str = "remote"        # "local" or "remote"
    llm_remote_url: str = ""

    # fal.ai
    fal_key: str = ""

    # Database
    database_url: str = "sqlite:///./tariikhna.db"

    # Static media (illustrations) served by the backend under /media.
    # Relative to the directory uvicorn is launched from (backend/).
    media_dir: str = "media"

    class Config:
        env_file = ".env"


settings = Settings()