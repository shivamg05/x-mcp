import os
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

X_API_BASE = "https://api.x.com"
X_OAUTH_AUTHORIZE_URL = "https://x.com/i/oauth2/authorize"
X_OAUTH_TOKEN_URL = "https://api.x.com/2/oauth2/token"

X_SCOPES = [
    "tweet.read",
    "tweet.write",
    "users.read",
    "like.read",
    "offline.access",
]

X_CLIENT_ID = os.getenv("X_CLIENT_ID")
X_CLIENT_SECRET = os.getenv("X_CLIENT_SECRET")
X_REDIRECT_URI = os.getenv("X_REDIRECT_URI")

if not X_CLIENT_ID or not X_CLIENT_SECRET or not X_REDIRECT_URI:
    raise RuntimeError(
        "Missing required X OAuth env vars. Please set "
        "X_CLIENT_ID, X_CLIENT_SECRET, and X_REDIRECT_URI"
    )
