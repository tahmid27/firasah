from fastapi import FastAPI

from api.schemas import MeResponse
from api.tenancy import CurrentOrg

app = FastAPI(title="Firasah API")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/me", response_model=MeResponse)
def me(ctx: CurrentOrg):
    """The caller's user ID, organisation and role."""
    return MeResponse(user_id=ctx.user_id, org_id=ctx.org_id, role=ctx.role)


@app.get("/auth/tiktok/callback")
def tiktok_callback(code: str | None = None, state: str | None = None):
    """Placeholder TikTok OAuth redirect (Sandbox). Public: TikTok calls it.
    Must check `state` once it exchanges tokens. Doesn't echo the code."""
    return {"status": "received"}
