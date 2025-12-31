## 🛠 X API Setup

To use this project, each user must create their **own X Developer App** and supply their credentials locally. This keeps credentials secure and avoids shared-account risks.

---

### 1. Create an X Developer Account

Sign up here:https://developer.x.com/en

Once approved, go to:

> **Developer Portal → Projects & Apps → Add App**

---

### 2. Configure App Authentication

Under **User authentication settings**, enable OAuth and configure the following:

#### App Permissions

Select **Read and Write**

#### Type of App

Select **Web App, Automated App or Bot**

#### Callback / Redirect URL

Add `http://localhost:8000/callback` 

#### Website URL

You may use any valid URL, for example `https://example.com`

This field is required by X but is not used in the local OAuth flow

---

Leave the remaining fields blank, click save!

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