from pathlib import Path
from pydantic_settings import BaseSettings

# Look for .env at the project root (two levels above this file).
# In Docker / Cloud Run this path won't exist; env vars are injected directly.
_ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"


class Settings(BaseSettings):
    google_maps_api_key: str = ""

    model_config = {"env_file": str(_ENV_FILE)}


settings = Settings()
