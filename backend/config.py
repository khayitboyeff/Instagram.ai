
from pathlib import Path
import os
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
ENV_FILE = ROOT / ".env"


import re

def _repair_joined_env_lines() -> None:
    """Repair a common .env typo where SESSION_SECRET was appended to the image model."""
    if not ENV_FILE.exists():
        return
    try:
        content = ENV_FILE.read_text(encoding="utf-8-sig")
        # Example of the malformed line:
        # GEMINI_IMAGE_MODEL=gemini-nano-banana-2.1SESSION_SECRET=...
        pattern = re.compile(
            r"(?m)^(\s*GEMINI_IMAGE_MODEL\s*=\s*[^\r\n]*?)(SESSION_SECRET\s*=.*)$",
            re.IGNORECASE,
        )
        repaired, count = pattern.subn(lambda m: m.group(1).rstrip() + "\n" + m.group(2).lstrip(), content)
        if count:
            ENV_FILE.write_text(repaired, encoding="utf-8")
    except OSError:
        # Do not prevent the app from starting if the environment file is read-only.
        pass


_repair_joined_env_lines()
load_dotenv(ENV_FILE)

APP_NAME = os.getenv("APP_NAME", "Insta AI Studio")
APP_VERSION = "1.1.0"

HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8001"))

# Render domenini avtomatik aniqlash.
APP_BASE_URL = (
    os.getenv("APP_BASE_URL", "").strip().rstrip("/")
    or os.getenv("RENDER_EXTERNAL_URL", "").strip().rstrip("/")
    or f"http://127.0.0.1:{PORT}"
)

FRONTEND_URL = os.getenv(
    "FRONTEND_URL",
    "http://localhost:8888"
).rstrip("/")

ACCESS_TOKEN_TTL_HOURS = int(
    os.getenv("ACCESS_TOKEN_TTL_HOURS", "168")
)

STORAGE_ROOT = Path(
    os.getenv("STORAGE_ROOT", str(ROOT / "storage"))
).resolve()

SESSION_SECRET = os.getenv("SESSION_SECRET", "")
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "")


def _first_env(*names: str) -> str:
    for name in names:
        value = os.getenv(name, "").strip()
        if value:
            return value
    return ""


# Instagram sozlamalari
IG_ACCESS_TOKEN = _first_env(
    "IG_ACCESS_TOKEN",
    "INSTAGRAM_ACCESS_TOKEN",
    "META_ACCESS_TOKEN",
)

IG_USER_ID = _first_env(
    "IG_USER_ID",
    "INSTAGRAM_USER_ID",
)

IG_USERNAME = _first_env(
    "IG_USERNAME",
    "INSTAGRAM_USERNAME",
).lstrip("@")

IG_GRAPH_VERSION = os.getenv(
    "IG_GRAPH_VERSION",
    "v26.0",
).strip()


# Gemini sozlamalari
GEMINI_API_KEY = os.getenv(
    "GEMINI_API_KEY",
    "",
).strip()

GEMINI_VIDEO_MODEL = os.getenv(
    "GEMINI_VIDEO_MODEL",
    os.getenv("GEMINI_TEXT_MODEL", "gemini-3.8-flash"),
).strip()

GEMINI_CONTENT_MODEL = os.getenv(
    "GEMINI_CONTENT_MODEL",
    "gemini-3.5-flash-lite",
).strip()

GEMINI_IMAGE_MODEL = os.getenv(
    "GEMINI_IMAGE_MODEL",
    "gemini-nano-banana-2.1",
).strip()
# Defensive cleanup: never pass a pasted SESSION_SECRET assignment as part of a model ID.
GEMINI_IMAGE_MODEL = re.split(
    r"SESSION_SECRET\s*=", GEMINI_IMAGE_MODEL, maxsplit=1, flags=re.IGNORECASE
)[0].strip() or "gemini-nano-banana-2.1"


# Video yuklash
MAX_UPLOAD_MB = int(
    os.getenv("MAX_UPLOAD_MB", "300")
)

DATABASE_PATH = STORAGE_ROOT / "insta_studio.db"
UPLOAD_DIR = STORAGE_ROOT / "uploads"
COVER_DIR = STORAGE_ROOT / "covers"
TOKEN_KEY_PATH = STORAGE_ROOT / "token.key"


# Kerakli papkalarni yaratish
for folder in (
    ROOT / "storage",
    STORAGE_ROOT,
    UPLOAD_DIR,
    COVER_DIR,
):
    folder.mkdir(parents=True, exist_ok=True)
