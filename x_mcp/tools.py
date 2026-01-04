import secrets
from typing import Any

from x_mcp.oauth import (
    pkce_verifier, pkce_challenge, add_pending_state,
    build_authorization_url, get_valid_access_token,
)
from x_mcp.x_api import search_recent_request, create_post_request, get_user_by_username_request, get_user_posts_request

MAX_STANDARD_POST_CHARS = 280

def register_tools(mcp: Any) -> None:
    @mcp.tool()
    def login_to_x() -> dict:
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
        if not query or not query.strip():
            raise RuntimeError("query must be a non-empty string")

        max_results = max(10, min(100, max_results))
        if sort_order not in ("recency", "relevancy"):
            raise RuntimeError("sort_order must be 'recency' or 'relevancy'")

        token = await get_valid_access_token()

        params: dict[str, str | int] = {
            "query": query,
            "max_results": max_results,
            "sort_order": sort_order,
            "tweet.fields": "created_at,author_id,lang,public_metrics,conversation_id",
            "expansions": "author_id",
            "user.fields": "name,username,verified,profile_image_url",
        }
        if start_time: params["start_time"] = start_time
        if end_time: params["end_time"] = end_time
        if since_id: params["since_id"] = since_id
        if until_id: params["until_id"] = until_id
        if next_token: params["next_token"] = next_token

        resp = await search_recent_request(token, params)
        if resp["status_code"] != 200:
            return {"ok": False, "status_code": resp["status_code"], "error": resp["text"]}
        data = resp["json"]
        return {"ok": True, "query": query, "tweets": data.get("data", []), "includes": data.get("includes", {}), "meta": data.get("meta", {})}


    @mcp.tool()
    async def create_post(
        text: str,
        reply_to_post_id: str | None = None,
        quote_post_id: str | None = None,
    ) -> dict:
        if not text or not text.strip():
            raise RuntimeError("text must be a non-empty string")

        if len(text) > MAX_STANDARD_POST_CHARS:
            return {
                "ok": False,
                "error": f"Post is {len(text)} characters. Standard X posts are limited to {MAX_STANDARD_POST_CHARS}.",
            }

        token = await get_valid_access_token()

        payload: dict = {"text": text}
        if reply_to_post_id:
            payload["reply"] = {"in_reply_to_tweet_id": reply_to_post_id}
        if quote_post_id:
            payload["quote_tweet_id"] = quote_post_id

        resp = await create_post_request(token, payload)
        if resp["status_code"] not in (200, 201):
            return {"ok": False, "status_code": resp["status_code"], "error": resp["text"]}
        data = resp["json"]
        return {"ok": True, "data": data.get("data", data)}

    
    @mcp.tool()
    async def get_user_from_username(username: str) -> dict:
        """
        Retrieve X user info from a single username.

        Args:
            username: e.g. "karpathy" (without @)
        """
        if not username or not username.strip():
            raise RuntimeError("username must be a non-empty string")

        username_clean = username.strip().lstrip("@")

        access_token = await get_valid_access_token()

        # Keep your existing defaults (these are good)
        user_fields = (
            "created_at,description,profile_image_url,protected,public_metrics,"
            "verified,pinned_tweet_id"
        )
        expansions = "pinned_tweet_id"
        tweet_fields = "created_at,author_id"

        resp = await get_user_by_username_request(
            access_token=access_token,
            username=username_clean,
            user_fields=user_fields,
            expansions=expansions,
            tweet_fields=tweet_fields,
        )

        if resp["status_code"] != 200:
            return {"ok": False, "status_code": resp["status_code"], "error": resp["text"]}

        data = resp["json"]
        return {
            "ok": True,
            "username": username_clean,
            "user": data.get("data"),
            "includes": data.get("includes", {}),
            "errors": data.get("errors", []),
        }


    @mcp.tool()
    async def get_user_posts(
        user_id: str,
        max_results: int = 10,
        pagination_token: str | None = None,
        since_id: str | None = None,
        until_id: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        exclude_replies: bool = False,
        exclude_retweets: bool = False,
    ) -> dict:
        """
        Retrieve posts authored by a specific user (by user_id).

        Args:
            user_id: Numeric user id (string), e.g. "2244994945"
            max_results: 5-100
            pagination_token: Token for next page
            since_id: Minimum post id (newer than)
            until_id: Maximum post id (older than)
            start_time: ISO8601 UTC timestamp (YYYY-MM-DDTHH:mm:ssZ)
            end_time: ISO8601 UTC timestamp (YYYY-MM-DDTHH:mm:ssZ)
            exclude_replies: Exclude replies from results
            exclude_retweets: Exclude retweets from results
        """
        if not user_id or not user_id.strip():
            raise RuntimeError("user_id must be a non-empty string")

        # X requires 5 <= max_results <= 100
        if max_results < 5:
            max_results = 5
        if max_results > 100:
            max_results = 100

        token = await get_valid_access_token()

        params: dict[str, str | int] = {
            "max_results": max_results,
            # good defaults for LLM usefulness without overfetching
            "tweet.fields": "created_at,author_id,lang,public_metrics,conversation_id,referenced_tweets",
        }

        # optional filters
        if pagination_token:
            params["pagination_token"] = pagination_token
        if since_id:
            params["since_id"] = since_id
        if until_id:
            params["until_id"] = until_id
        if start_time:
            params["start_time"] = start_time
        if end_time:
            params["end_time"] = end_time

        # exclude param is a list, but API accepts comma-separated in querystring
        excludes = []
        if exclude_replies:
            excludes.append("replies")
        if exclude_retweets:
            excludes.append("retweets")
        if excludes:
            params["exclude"] = ",".join(excludes)

        resp = await get_user_posts_request(token, user_id.strip(), params)

        if resp["status_code"] != 200:
            return {"ok": False, "status_code": resp["status_code"], "error": resp["text"]}

        data = resp["json"] or {}
        return {
            "ok": True,
            "user_id": user_id.strip(),
            "tweets": data.get("data", []),
            "includes": data.get("includes", {}),
            "meta": data.get("meta", {}),
            "errors": data.get("errors", []),
        }