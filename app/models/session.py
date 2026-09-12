from typing import Literal

from pydantic import BaseModel

from app.models.lab import LabCredentials


class LabSessionStatus(BaseModel):
    session_id: str
    lab_id: str
    status: Literal["starting", "running", "stopped", "expired", "error"]
    endpoint: str | None = None
    protocol: Literal["ssh", "http", "rdp"]
    port: int
    credentials: LabCredentials | None = None
    expires_at: str | None = None
    message: str | None = None
    container_id: str | None = None


class LabStartRequest(BaseModel):
    user_id: str | None = None
