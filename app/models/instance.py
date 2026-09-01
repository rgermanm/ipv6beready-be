from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


class InstanceNode(BaseModel):
    """Normalized containerlab node used by the frontend and SSH proxy."""

    name: str
    shortname: str
    ipv4: str | None = None
    ipv6: str | None = None
    state: str | None = None
    kind: str | None = None


class LabInstance(BaseModel):
    id: str
    session_id: str
    lab_id: str
    user_id: str
    clab_name: str
    path: str
    topology_file: str
    status: Literal["starting", "running", "stopped", "error"]
    ttl_seconds: int
    created_at: datetime
    expires_at: datetime
    inspect: Any = None
    nodes: list[InstanceNode] = Field(default_factory=list)
    message: str | None = None
    endpoint: str | None = None
    port: int | None = None
    protocol: Literal["ssh", "http", "rdp"] = "ssh"

    def is_expired(self, now: datetime | None = None) -> bool:
        moment = now or datetime.now(timezone.utc)
        expires = self.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        return moment >= expires


class LabInstancePublic(BaseModel):
    sessionId: str
    instanceId: str
    roomSlug: str
    userId: str
    clabName: str
    status: Literal["starting", "running", "stopped", "error"]
    endpoint: str | None = None
    protocol: Literal["ssh", "http", "rdp"] = "ssh"
    port: int
    credentials: dict | None = None
    expiresAt: str | None = None
    ttlSeconds: int
    message: str | None = None
    inspect: Any = None
    nodes: list[InstanceNode] = Field(default_factory=list)
