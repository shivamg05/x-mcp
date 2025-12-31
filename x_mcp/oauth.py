import base64
import hashlib
import secrets
import time
from urllib.parse import urlencode

import httpx

from x_mcp.config import (
    X_CLIENT_ID, X_CLIENT_SECRET, X_REDIRECT_URI,
    X_OAUTH_AUTHORIZE_URL, X_OAUTH_TOKEN_URL, X_SCOPES,
)
from x_mcp.storage import (
    load_pending_states, save_pending_states,
    load_tokens, save_tokens,
)

TOKEN_REFRESH_SKEW_SECONDS = 60


def pkce_verifier() -> str:
    v = secrets.token_urlsafe(64)
    return v[:128]


def pkce_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")


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


def add_pending_state(state: str, verifier: str) -> None:
    states = load_pending_states()
    states[state] = {"verifier": verifier, "created_at": int(time.time())}
    save_pending_states(states)


def consume_pending_state(state: str) -> str | None:
    states = load_pending_states()
    entry = states.get(state)
    if not entry:
        return None
    verifier = entry.get("verifier")
    del states[state]
    save_pending_states(states)
    return verifier


def is_token_expired(tokens: dict) -> bool:
    obtained_at = int(tokens.get("obtained_at", 0))
    expires_in = int(tokens.get("expires_in", 0))
    return time.time() >= (obtained_at + expires_in - TOKEN_REFRESH_SKEW_SECONDS)


async def exchange_code_for_tokens(code: str, verifier: str) -> dict:
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
        resp.raise_for_status()
        token_json = resp.json()

    tokens = {"obtained_at": int(time.time()), **token_json}
    save_tokens(tokens)
    return tokens


async def refresh_access_token(refresh_token: str) -> dict:
    basic = base64.b64encode(f"{X_CLIENT_ID}:{X_CLIENT_SECRET}".encode()).decode()
    data = {"grant_type": "refresh_token", "refresh_token": refresh_token}
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {basic}",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(X_OAUTH_TOKEN_URL, data=data, headers=headers)
        resp.raise_for_status()
        return resp.json()


async def get_valid_access_token() -> str:
    tokens = load_tokens()
    if not tokens:
        raise RuntimeError("Not logged in. Run login_to_x first.")

    if not is_token_expired(tokens):
        return tokens["access_token"]

    refreshed = await refresh_access_token(tokens["refresh_token"])
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
