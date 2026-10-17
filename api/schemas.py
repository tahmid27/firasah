"""Response shapes. Every endpoint declares one of these as its
`response_model`, and FastAPI drops any field not declared here — so even if
a credential or an internal column ended up in the data by mistake, it could
not be serialised into a response."""

from pydantic import BaseModel


class MeResponse(BaseModel):
    user_id: str
    org_id: str
    role: str
