from fastapi import APIRouter, Depends, HTTPException

from app.models.instance import LabInstance, LabInstancePublic
from app.models.lab import LabDefinition
from app.models.user import User
from app.security import get_current_active_user
from app.services.container_manager import container_manager
from app.services.lab_registry import get_lab

router = APIRouter(prefix="/labs", tags=["lab-instances"])


def _to_public(instance: LabInstance, lab: LabDefinition) -> LabInstancePublic:
    creds = None
    if lab.formula.clab:
        creds = lab.formula.clab.node_credentials.model_dump()
    elif lab.formula.credentials:
        creds = lab.formula.credentials.model_dump()
    return LabInstancePublic(
        sessionId=instance.session_id,
        instanceId=instance.id,
        roomSlug=instance.lab_id,
        userId=instance.user_id,
        clabName=instance.clab_name,
        status=instance.status,
        endpoint=instance.endpoint,
        protocol=instance.protocol,
        port=instance.port or lab.formula.port,
        credentials=creds,
        expiresAt=instance.expires_at.isoformat(),
        ttlSeconds=instance.ttl_seconds,
        message=instance.message,
        inspect=instance.inspect,
        nodes=instance.nodes,
    )


@router.post("/{lab_id}")
def create_lab(
    lab_id: str,
    current_user: User = Depends(get_current_active_user),
) -> LabInstancePublic:
    """Deploy a per-user containerlab instance for this lab."""
    lab = get_lab(lab_id)
    if not lab:
        raise HTTPException(status_code=404, detail="Lab not found")

    instance = container_manager.create_instance(lab, user_id=current_user.id)
    if instance.status == "error":
        raise HTTPException(status_code=500, detail=instance.message or "Deploy failed")
    return _to_public(instance, lab)


@router.get("/{lab_id}/session")
@router.get("/{lab_id}/instance")
def get_lab_instance(
    lab_id: str,
    current_user: User = Depends(get_current_active_user),
) -> LabInstancePublic:
    """Get the current user's running instance for a lab."""
    lab = get_lab(lab_id)
    if not lab:
        raise HTTPException(status_code=404, detail="Lab not found")

    instance = container_manager.get_instance(lab_id, current_user.id)
    if not instance:
        raise HTTPException(status_code=404, detail="No active lab instance")

    return _to_public(instance, lab)


@router.delete("/{lab_id}")
def stop_lab(
    lab_id: str,
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """Destroy the current user's containerlab instance."""
    if not container_manager.stop_instance(lab_id, current_user.id):
        raise HTTPException(status_code=404, detail="No active lab instance")

    return {"message": "Lab terminated"}
