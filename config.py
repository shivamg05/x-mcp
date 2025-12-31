import os
from dotenv import load_dotenv

# Load local .env if present (development only)
load_dotenv()

def get_env(name: str, required: bool = True) -> str | None:
    value = os.getenv(name)
    if required and not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value