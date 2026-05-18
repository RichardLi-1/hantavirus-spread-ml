from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    version: str


class ModelsStatusResponse(BaseModel):
    ready: bool
    has_metrics: bool
    has_forecasts: bool


class RetrainResponse(BaseModel):
    ok: bool
    metrics: dict
