import os

from dotenv import load_dotenv

load_dotenv()


def get_env(
    key: str,
    default: str | None = None,
    required: bool = False,
) -> str:
    value = os.getenv(key, default)

    if required and not value:
        raise RuntimeError(
            f"Missing required environment variable: {key}"
        )

    return value


# ---------------------------------------------------------------------------
# Request Settings
# ---------------------------------------------------------------------------

REQUEST_TIMEOUT_SECONDS = int(
    get_env("REQUEST_TIMEOUT_SECONDS", "20")
)


# ---------------------------------------------------------------------------
# Base URLs
# ---------------------------------------------------------------------------

WEB_BASE = get_env(
    "WEB_BASE",
    "https://hipsbook.gbydigitaltech.co.th",
)

STREAM_API_BASE = get_env(
    "STREAM_API_BASE",
    "https://hips-stream.com",
)


# ---------------------------------------------------------------------------
# Live Test Target
# ---------------------------------------------------------------------------

LIVE_ID = get_env(
    "LIVE_ID",
    required=True,
)


# ---------------------------------------------------------------------------
# Stream API Key
# ---------------------------------------------------------------------------
# Do not hardcode this value.
# Keep the real value in .env only.
# ---------------------------------------------------------------------------

STREAM_API_KEY = get_env(
    "STREAM_API_KEY",
    required=True,
)


# ---------------------------------------------------------------------------
# Derived URLs
# ---------------------------------------------------------------------------

LIVE_PATH = f"/live/{LIVE_ID}"
LIVE_PAGE_URL = f"{WEB_BASE}{LIVE_PATH}"

LIVE_DETAIL_API_URL = f"{STREAM_API_BASE}/api/livestream/{LIVE_ID}"
