from pathlib import Path
from pydantic_settings import BaseSettings

# Look for .env at the project root (one level above backend/)
_ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"


class Settings(BaseSettings):
    google_distance_matrix_api_key: str = ""

    model_config = {"env_file": str(_ENV_FILE)}


settings = Settings()
