import logging
import uvicorn
from fastapi import FastAPI, HTTPException, Query

from x_mcp.oauth import consume_pending_state, exchange_code_for_tokens

app = FastAPI()

@app.get("/oauth/callback")
async def oauth_callback(code: str = Query(...), state: str = Query(...)):
    verifier = consume_pending_state(state)
    if not verifier:
        raise HTTPException(status_code=400, detail="Invalid or expired state")

    try:
        await exchange_code_for_tokens(code, verifier)
    except Exception as e:
        logging.exception("Token exchange failed")
        raise HTTPException(status_code=500, detail="Token exchange failed") from e

    return {
        "message": "Login successful. Tokens stored. You can return to Claude now.",
        "tokens_saved": True,
    }

def run_http_server():
    uvicorn.run(app, host="127.0.0.1", port=3000, log_level="info")
