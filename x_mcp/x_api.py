import httpx
from x_mcp.config import X_API_BASE

async def search_recent_request(access_token: str, params: dict) -> dict:
    url = f"{X_API_BASE}/2/tweets/search/recent"
    headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url, params=params, headers=headers)
    return {"status_code": resp.status_code, "json": resp.json() if resp.content else {}, "text": resp.text}


async def create_post_request(access_token: str, payload: dict) -> dict:
    url = f"{X_API_BASE}/2/tweets"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, json=payload, headers=headers)
    return {"status_code": resp.status_code, "json": resp.json() if resp.content else {}, "text": resp.text}

async def get_user_by_username_request(
    access_token: str,
    username: str,
    user_fields: str | None = None,
    expansions: str | None = None,
    tweet_fields: str | None = None,
) -> dict:
    """
    GET /2/users/by/username/{username}
    """
    url = f"{X_API_BASE}/2/users/by/username/{username}"

    params: dict[str, str] = {}
    if user_fields:
        params["user.fields"] = user_fields
    if expansions:
        params["expansions"] = expansions
    if tweet_fields:
        params["tweet.fields"] = tweet_fields

    headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url, params=params, headers=headers)

    return {
        "status_code": resp.status_code,
        "json": resp.json() if resp.content else {},
        "text": resp.text,
    }


async def get_user_posts_request(
    access_token: str,
    user_id: str,
    params: dict | None = None,
) -> dict:
    """
    GET /2/users/{id}/tweets
    Retrieves posts authored by a specific user id.
    """
    url = f"{X_API_BASE}/2/users/{user_id}/tweets"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }

    qparams = params or {}

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url, params=qparams, headers=headers)

    return {
        "status_code": resp.status_code,
        "json": resp.json() if resp.content else {},
        "text": resp.text,
    }