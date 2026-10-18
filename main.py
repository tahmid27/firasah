from fastapi import FastAPI

from api.routes import appeals, email, fundraising, overview, social
from api.schemas import MeResponse
from api.tenancy import CurrentOrg

app = FastAPI(title="Firasah API")
app.include_router(overview.router)
app.include_router(fundraising.router)
app.include_router(social.router)
app.include_router(email.router)
app.include_router(appeals.router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/me", response_model=MeResponse)
def me(ctx: CurrentOrg):
    """The caller's user ID, organisation and role."""
    return MeResponse(
        user_id=ctx.user_id, org_id=ctx.org_id, org_name=ctx.org_name, role=ctx.role
    )


@app.get("/auth/tiktok/callback")
def tiktok_callback(code: str | None = None, state: str | None = None):
    """Placeholder TikTok OAuth redirect (Sandbox). Public: TikTok calls it.
    Must check `state` once it exchanges tokens. Doesn't echo the code."""
    return {"status": "received"}
