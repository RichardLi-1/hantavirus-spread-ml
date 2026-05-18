from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    version: str


class RetrainResponse(BaseModel):
    ok: bool
    metrics: dict
