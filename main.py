from fastapi import FastAPI

from api.schemas import MeResponse
from api.tenancy import CurrentOrg

app = FastAPI(title="Firasah API")


@app.get("/health")
def health():
    """Public by design: lets a load balancer check the process is up."""
    return {"status": "ok"}


@app.get("/me", response_model=MeResponse)
def me(ctx: CurrentOrg):
    """Who the caller is and which charity they act for — resolved from
    their verified token and a server-side membership lookup."""
    return MeResponse(user_id=ctx.user_id, org_id=ctx.org_id, role=ctx.role)


@app.get("/auth/tiktok/callback")
def tiktok_callback(code: str | None = None, state: str | None = None):
    """Placeholder for TikTok's OAuth redirect during Sandbox setup.

    Public by necessity (TikTok's servers call it). Just needs to exist and
    respond so TikTok accepts it as a Redirect URI — real token-exchange
    logic gets added once past Sandbox, and must then check `state` to tie
    the callback to the charity that started connecting. Deliberately does
    NOT echo the authorization code back in the response: it is a credential
    (single-use, short-lived, but still one), and it is already visible in
    the browser's address bar for the one-off manual exchange anyway.
    """
    return {"status": "received"}
