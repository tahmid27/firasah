"""Response models; every endpoint declares one as its `response_model`."""

from pydantic import BaseModel


class MeResponse(BaseModel):
    user_id: str
    org_id: str
    role: str
