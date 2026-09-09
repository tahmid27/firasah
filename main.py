from fastapi import FastAPI

app = FastAPI(title="Firasah API")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/auth/tiktok/callback")
def tiktok_callback(code: str | None = None, state: str | None = None):
    """Placeholder for TikTok's OAuth redirect during Sandbox setup.

    Just needs to exist and respond so TikTok accepts it as a Redirect URI —
    real token-exchange logic gets added once past Sandbox.
    """
    return {"status": "received", "code": code, "state": state}
