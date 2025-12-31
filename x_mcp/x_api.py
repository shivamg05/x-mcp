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
