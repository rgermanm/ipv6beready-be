from fastapi import APIRouter, HTTPException

from app.models.roadmap import RoadmapDefinition, RoadmapSummary
from app.repositories import roadmaps as roadmap_repo

router = APIRouter(prefix="/roadmaps", tags=["roadmaps"])


@router.get("")
def get_roadmaps() -> list[RoadmapSummary]:
    """List learning paths that form the IPv6 course graph."""
    return roadmap_repo.list_roadmaps()


@router.get("/{slug}")
def get_roadmap(slug: str) -> RoadmapDefinition:
    """Full path: modules, skill graph and labs hydrated from the catalog."""
    roadmap = roadmap_repo.get_roadmap(slug)
    if not roadmap:
        raise HTTPException(status_code=404, detail="Roadmap not found")
    return roadmap
