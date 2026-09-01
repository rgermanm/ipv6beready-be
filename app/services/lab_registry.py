from app.models.lab import LabDefinition, LabSummary
from app.repositories import labs as lab_repo


def list_labs() -> list[LabSummary]:
    return lab_repo.list_labs()


def get_lab(lab_id: str) -> LabDefinition | None:
    return lab_repo.get_lab(lab_id)
