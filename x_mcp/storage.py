import json
from pathlib import Path

STATE_DIR = Path.home() / ".x-mcp"
STATE_DIR.mkdir(parents=True, exist_ok=True)

PENDING_STATES_PATH = STATE_DIR / "pending_states.json"
AUTH_PATH = STATE_DIR / "auth.json"


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2))


def load_pending_states() -> dict:
    return read_json(PENDING_STATES_PATH)


def save_pending_states(states: dict) -> None:
    write_json(PENDING_STATES_PATH, states)


def load_tokens() -> dict | None:
    if not AUTH_PATH.exists():
        return None
    return read_json(AUTH_PATH)


def save_tokens(tokens: dict) -> None:
    write_json(AUTH_PATH, tokens)
