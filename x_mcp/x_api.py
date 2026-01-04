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

async def get_liked_posts(
    access_token: str,
    user_id: str,
    max_results: int = 10,
    pagination_token: str | None = None,
) -> dict:
    # X requires 5 <= max_results <= 100 for this endpoint
    if max_results < 5:
        max_results = 5
    if max_results > 100:
        max_results = 100

    url = f"{X_API_BASE}/2/users/{user_id}/liked_tweets"
    params: dict[str, str | int] = {
        "max_results": max_results,
        "tweet.fields": "created_at,author_id,lang,public_metrics,conversation_id",
        "expansions": "author_id",
        "user.fields": "name,username,verified,profile_image_url",
    }
    if pagination_token:
        params["pagination_token"] = pagination_token

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url, params=params, headers=headers)

    if resp.status_code != 200:
        return {"ok": False, "status_code": resp.status_code, "error": resp.text}

    data = resp.json()
    return {
        "ok": True,
        "user_id": user_id,
        "tweets": data.get("data", []),
        "includes": data.get("includes", {}),
        "meta": data.get("meta", {}),
    }