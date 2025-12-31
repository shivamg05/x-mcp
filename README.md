# X MCP Server

This is an **MCP (Model Context Protocol) server** that allows MCP Clients (Claude Desktop, ChatGPT, Cursor, etc) to interact with the **X (Twitter) API**.

features:
- search recent posts on X
- create new posts on your behalf

Authentication is handled locally via OAuth2.1.  
Each user connects **their own X Developer App**, keeping credentials secure and isolated.

---

## What This MCP Server Enables

Once configured and connected to an MCP Client, the following tools are available:

### `search_recent`
Search posts from the last ~7 days using X’s **Recent Search API**.

Example use cases:
- Monitor discussion around a topic
- Track posts from a specific account
- Analyze reactions to breaking news


### `create_post`
Create a new post on X as the authenticated user.

Supports:
- Standard posts (≤ 280 characters)
- Replies
- Quote posts


### `login_to_x`
Starts the OAuth login flow.

Claude will return a URL that you open in your browser to authorize the app.  
Tokens are stored locally on your machine and automatically refreshed.

---

## Architecture Overview

- **MCP transport:** stdio (Claude Desktop ↔ server)
- **OAuth callback:** local FastAPI HTTP server (`localhost`)
- **Token storage:** `~/.x-mcp/auth.json`

---

## Installation

### 1. Clone the Repository

Clone this repository to your local machine:

```bash
git clone https://github.com/shivamg05/x-mcp.git
cd x-mcp
```

### 2. Install Dependencies

This project uses `uv` for dependency management.

If you don’t have `uv` installed:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

install dependencies and set up the virtual environment:

```bash
uv venv
source .venv/bin/activate
uv sync
```

---

## X API Setup

To use this project, each user must create their **own X Developer App** and supply their credentials locally. This keeps credentials secure and avoids shared-account risks.


### 1. Create an X Developer Account

Sign up here:https://developer.x.com/en

Once approved, go to:

> **Developer Portal → Projects & Apps → Add App**


### 2. Configure App Authentication

Under **User authentication settings**, enable OAuth and configure the following:

#### App Permissions

Select **Read and Write**

#### Type of App

Select **Web App, Automated App or Bot**

#### Callback / Redirect URL

Add `http://localhost:3000/oauth/callback` 

#### Website URL

You may use any valid URL, for example `https://example.com`

This field is required by X but is not used in the local OAuth flow

Leave the remaining fields blank, click save!

---

Copy:

- `Client ID`
- `Client Secret`

### 3. Store Credentials Securely

Create a `.env` file in the project root (make sure to add to `.gitignore!`):

```
X_CLIENT_ID=your_client_id_here
X_CLIENT_SECRET=your_client_secret_here
X_REDIRECT_URI=http://localhost:8000/callback
```

---

## Connecting the Server to Claude Desktop

Claude Desktop discovers MCP servers via a local configuration file.

### 1. Open Claude Desktop config

On macOS:

```bash
~/Library/Application\ Support/Claude/claude_desktop_config.json
```

Create the file if it does not already exist.

---

### 2. Add the MCP server entry

Update the file as follows (adjust paths if needed):

```json
{
  "mcpServers": {
    "x-mcp": {
      "command": "uv",
      "args": [
        "--directory",
        "/ABSOLUTE/PATH/TO/THIS/REPO",
        "run",
        "x.py"
      ]
    }
  }
}
```

---

## First-Time Login

Before using any X tools:

1. Ask Claude to log you in (e.g. “log me into X”)
2. Claude will call `login_to_x`
3. Open the returned authorization URL in your browser
4. Approve the app
5. You’ll see a confirmation page saying login succeeded

Tokens are now stored locally and will refresh automatically.

---

## Notes & Limitations

- Each user must use their **own X Developer App**
- Posts are limited to **280 characters** (standard X post length)
- Tokens are stored locally at `~/.x-mcp/`
---

## Security Model

- OAuth 2.1 with PKCE
- No shared credentials
- No secrets passed through Claude
- All sensitive data remains on the local machine