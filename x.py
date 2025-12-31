from typing import Any, Dict
from fastmcp import FastMCP
from config import get_env
from urllib.parse import urlencode
from dotenv import load_dotenv
import logging
import httpx
import os
import secrets
from fastapi import FastAPI, HTTPException, Query
import threading
import uvicorn
import json
from pathlib import Path
import base64
import hashlib
import time

STATE_DIR = Path.home() / ".x-mcp"
STATE_DIR.mkdir(parents=True, exist_ok=True)

PENDING_STATES_PATH = STATE_DIR / "pending_states.json"
AUTH_PATH = STATE_DIR / "auth.json"

def _load_pending_states() -> dict:
    if not PENDING_STATES_PATH.exists():
        return {}
    try:
        return json.loads(PENDING_STATES_PATH.read_text())
    except Exception:
        return {}


def _save_pending_states(states: dict) -> None:
    PENDING_STATES_PATH.write_text(json.dumps(states))


def pkce_verifier() -> None:
    v = secrets.token_urlsafe(64)
    return v[:128]


def pkce_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")


def add_pending_state(state: str, verifier: str) -> None:
    states = _load_pending_states()
    states[state] = {"verifier": verifier, "created_at": int(time.time())}
    _save_pending_states(states)


def consume_pending_state(state: str) -> str | None:
    states = _load_pending_states()
    entry = states.get(state)
    if not entry:
        return None
    verifier = entry.get("verifier")
    del states[state]
    _save_pending_states(states)
    return verifier

TOKEN_REFRESH_SKEW_SECONDS = 60  # refresh 1 min early

def load_tokens() -> dict | None:
    if not AUTH_PATH.exists():
        return None
    return json.loads(AUTH_PATH.read_text())


def save_tokens(token_json: dict) -> None:
    AUTH_PATH.write_text(json.dumps(token_json, indent=2))


def is_token_expired(tokens: dict) -> bool:
    obtained_at = int(tokens.get("obtained_at", 0))
    expires_in = int(tokens.get("expires_in", 0))
    # refresh slightly early to avoid edge races
    return time.time() >= (obtained_at + expires_in - TOKEN_REFRESH_SKEW_SECONDS)

async def refresh_access_token(refresh_token: str) -> dict:
    basic = base64.b64encode(f"{X_CLIENT_ID}:{X_CLIENT_SECRET}".encode()).decode()

    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {basic}",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(X_OAUTH_TOKEN_URL, data=data, headers=headers)
        if resp.status_code >= 400:
            logging.error("Token refresh failed: %s %s", resp.status_code, resp.text)
            raise RuntimeError("Token refresh failed")

        return resp.json()

async def get_valid_access_token() -> str:
    tokens = load_tokens()
    if not tokens:
        raise RuntimeError("Not logged in. Run login_to_x first.")

    if not is_token_expired(tokens):
        return tokens["access_token"]

    logging.info("Access token expired/expiring; refreshing…")

    refreshed = await refresh_access_token(tokens["refresh_token"])

    # Some providers rotate refresh_token; keep old if none returned
    new_tokens = {
        "obtained_at": int(time.time()),
        "token_type": refreshed.get("token_type", tokens.get("token_type")),
        "expires_in": refreshed.get("expires_in", tokens.get("expires_in")),
        "access_token": refreshed["access_token"],
        "scope": refreshed.get("scope", tokens.get("scope")),
        "refresh_token": refreshed.get("refresh_token", tokens.get("refresh_token")),
    }

    save_tokens(new_tokens)
    return new_tokens["access_token"]

logging.basicConfig(level=logging.INFO)

load_dotenv()

X_API_BASE = "https://api.x.com"
X_CLIENT_ID = os.getenv("X_CLIENT_ID")
X_CLIENT_SECRET = os.getenv("X_CLIENT_SECRET")
X_REDIRECT_URI = os.getenv("X_REDIRECT_URI")

if not X_CLIENT_ID or not X_CLIENT_SECRET or not X_REDIRECT_URI:
    raise RuntimeError(
        "Missing required X OAuth env vars. Please set "
        "X_CLIENT_ID, X_CLIENT_SECRET, and X_REDIRECT_URI"
    )

# Initialize FastMCP server
mcp = FastMCP("x-mcp")

X_OAUTH_AUTHORIZE_URL = "https://x.com/i/oauth2/authorize"
X_OAUTH_TOKEN_URL = "https://api.x.com/2/oauth2/token"

X_SCOPES = [
    "tweet.read",
    "tweet.write",
    "users.read",
    "offline.access",
]

def build_authorization_url(state: str, code_challenge: str) -> str:
    params = {
        "response_type": "code",
        "client_id": X_CLIENT_ID,
        "redirect_uri": X_REDIRECT_URI,
        "scope": " ".join(X_SCOPES),
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    return f"{X_OAUTH_AUTHORIZE_URL}?{urlencode(params)}"

# Track issued login states
pending_states: Dict[str, bool] = {}

@mcp.tool()
def login_to_x() -> dict:
    """
    Start the OAuth2.1 login flow for X (Twitter).
    Returns a URL the user should open in their browser to authenticate.
    """
    state = secrets.token_urlsafe(32)

    verifier = pkce_verifier()
    challenge = pkce_challenge(verifier)

    add_pending_state(state, verifier)

    url = build_authorization_url(state, challenge)

    return {
        "authorization_url": url,
        "message": "Please open the authorization_url in your browser and log in.",
    }

@mcp.tool()
async def search_recent(
    query: str,
    max_results: int = 10,
    sort_order: str = "recency",
    start_time: str | None = None,
    end_time: str | None = None,
    since_id: str | None = None,
    until_id: str | None = None,
    next_token: str | None = None,
) -> dict:
    """
    Search recent Posts (last ~7 days) matching a query.

    Args:
        query: X search query (e.g., "from:XDevelopers -is:retweet")
        max_results: 10-100 (X requires min 10). Defaults to 10.
        sort_order: "recency" or "relevancy". Defaults to "recency".
        start_time: ISO8601 UTC (YYYY-MM-DDTHH:mm:ssZ)
        end_time: ISO8601 UTC (YYYY-MM-DDTHH:mm:ssZ)
        since_id: return results newer than this Post ID
        until_id: return results older than this Post ID
        next_token: pagination token from prior response
    """
    if not query or not query.strip():
        raise RuntimeError("query must be a non-empty string")

    # X requires 10 <= max_results <= 100
    if max_results < 10:
        max_results = 10
    if max_results > 100:
        max_results = 100

    if sort_order not in ("recency", "relevancy"):
        raise RuntimeError("sort_order must be 'recency' or 'relevancy'")

    access_token = await get_valid_access_token()

    url = f"{X_API_BASE}/2/tweets/search/recent"
    params: dict[str, str | int] = {
        "query": query,
        "max_results": max_results,
        "sort_order": sort_order,
        # Good default fields so Claude has useful context without you overfetching
        "tweet.fields": "created_at,author_id,lang,public_metrics,conversation_id",
        "expansions": "author_id",
        "user.fields": "name,username,verified,profile_image_url",
    }

    # Optional params only if provided
    if start_time:
        params["start_time"] = start_time
    if end_time:
        params["end_time"] = end_time
    if since_id:
        params["since_id"] = since_id
    if until_id:
        params["until_id"] = until_id
    if next_token:
        # X uses next_token in meta; request param is next_token
        params["next_token"] = next_token

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url, params=params, headers=headers)

    if resp.status_code != 200:
        # Keep this error message usable in Claude
        logging.error("search_recent failed: %s %s", resp.status_code, resp.text)
        return {
            "ok": False,
            "status_code": resp.status_code,
            "error": resp.text,
        }

    data = resp.json()

    # Return a friendly, structured payload
    return {
        "ok": True,
        "query": query,
        "tweets": data.get("data", []),
        "includes": data.get("includes", {}),
        "meta": data.get("meta", {}),
    }


app = FastAPI()

@app.get("/oauth/callback")
async def oauth_callback(code: str = Query(...), state: str = Query(...)):
    verifier = consume_pending_state(state)
    if not verifier:
        raise HTTPException(status_code=400, detail="Invalid or expired state")

    # Confidential client: Basic base64(client_id:client_secret)
    basic = base64.b64encode(f"{X_CLIENT_ID}:{X_CLIENT_SECRET}".encode()).decode()

    data = {
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": X_REDIRECT_URI,
        "code_verifier": verifier,
    }

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {basic}",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(X_OAUTH_TOKEN_URL, data=data, headers=headers)
        if resp.status_code >= 400:
            logging.error("Token exchange failed: %s %s", resp.status_code, resp.text)
            raise HTTPException(status_code=500, detail="Token exchange failed")

        token_json = resp.json()

    # Persist tokens locally
    AUTH_PATH.write_text(
        json.dumps(
            {
                "obtained_at": int(time.time()),
                **token_json,
            },
            indent=2,
        )
    )

    logging.info("Saved tokens to %s", str(AUTH_PATH))

    return {
        "message": "Login successful. Tokens stored. You can return to Claude now.",
        "tokens_saved": True,
    }

def run_http_server():
    uvicorn.run(app, host="127.0.0.1", port=3000, log_level="info")

if __name__ == "__main__":
    threading.Thread(target=run_http_server, daemon=True).start()

    mcp.run()