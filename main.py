from fastapi import FastAPI

app = FastAPI(title="Firasah API")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/auth/tiktok/callback")
def tiktok_callback(code: str | None = None, state: str | None = None):
    """Placeholder for TikTok's OAuth redirect during Sandbox setup.

    Just needs to exist and respond so TikTok accepts it as a Redirect URI —
    real token-exchange logic gets added once past Sandbox. Deliberately does
    NOT echo the authorization code back in the response: it is a credential
    (single-use, short-lived, but still one), and it is already visible in
    the browser's address bar for the one-off manual exchange anyway.
    """
    return {"status": "received"}
