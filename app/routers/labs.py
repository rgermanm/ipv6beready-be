from fastapi import APIRouter, HTTPException

from app.models.lab import Exercise, LabDefinition
from app.services.lab_registry import get_lab, list_labs

router = APIRouter(prefix="/labs", tags=["labs"])


@router.get("")
def get_labs() -> list[dict]:
    """List all available labs (summary without formula details)."""
    return [lab.model_dump() for lab in list_labs()]


@router.get("/{lab_id}")
def get_lab_by_id(lab_id: str) -> LabDefinition:
    """Get a lab definition including its exercise list and container formula."""
    lab = get_lab(lab_id)
    if not lab:
        raise HTTPException(status_code=404, detail="Lab not found")
    return lab


@router.get("/{lab_id}/exercises")
def get_lab_exercises(lab_id: str) -> list[Exercise]:
    """Get the exercise list for a specific lab."""
    lab = get_lab(lab_id)
    if not lab:
        raise HTTPException(status_code=404, detail="Lab not found")
    return lab.exercises
