from __future__ import annotations

import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
STATIC_DIR = BASE_DIR / "static"
REPORTS_DIR = BASE_DIR / "reports"


def _load_dotenv() -> None:
    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        value = value.strip().strip("'").strip('"')
        os.environ.setdefault(key.strip(), value)


_load_dotenv()

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct:free")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

CALCOM_API_KEY = os.getenv("CALCOM_API_KEY", "")
CALCOM_EVENT_TYPE_ID = os.getenv("CALCOM_EVENT_TYPE_ID", "")
CALCOM_TIMEZONE = os.getenv("CALCOM_TIMEZONE", "Asia/Kolkata")
CALCOM_API_VERSION = os.getenv("CALCOM_API_VERSION", "2024-09-04")

GOOGLE_ACCESS_TOKEN = os.getenv("GOOGLE_ACCESS_TOKEN", "")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REFRESH_TOKEN = os.getenv("GOOGLE_REFRESH_TOKEN", "")
GOOGLE_CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID", "primary")
GOOGLE_TIMEZONE = os.getenv("GOOGLE_TIMEZONE", "Asia/Kolkata")
CALENDLY_URL = os.getenv(
    "CALENDLY_URL",
    "https://calendly.com/adarshsinghtomar7909043383/new-meeting",
)

PERSONA_NAME = os.getenv("PERSONA_NAME", "Adarsh Singh Tomar")
PERSONA_ROLE = os.getenv("PERSONA_ROLE", "AI representative for Adarsh Singh Tomar")
