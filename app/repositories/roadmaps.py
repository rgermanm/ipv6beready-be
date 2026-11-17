import logging

from pydantic import ValidationError
from pymongo.collection import Collection

from app.data.roadmaps import ROADMAPS
from app.db import get_db, is_connected
from app.models.lab import LabSummary
from app.models.roadmap import RoadmapDefinition, RoadmapSummary
from app.repositories import labs as lab_repo

logger = logging.getLogger(__name__)

COLLECTION = "roadmaps"


def _collection() -> Collection:
    return get_db()[COLLECTION]


def ensure_indexes() -> None:
    collection = _collection()
    collection.create_index(
        "slug",
        unique=True,
        name="roadmaps_slug_unique",
        partialFilterExpression={"slug": {"$type": "string"}},
    )
    collection.create_index("stage_order", name="roadmaps_stage_order")


def seed_roadmaps() -> None:
    if not is_connected():
        return

    collection = _collection()
    ensure_indexes()
    for roadmap in ROADMAPS.values():
        doc = roadmap.model_dump()
        doc.pop("id", None)
        collection.update_one(
            {"slug": doc["slug"]},
            {"$set": doc},
            upsert=True,
        )


def _labs_by_slug() -> dict[str, LabSummary]:
    indexed: dict[str, LabSummary] = {}
    for lab in lab_repo.list_labs():
        indexed[lab.slug or lab.id] = lab
        indexed[lab.id] = lab
    return indexed


def _hydrate(roadmap: RoadmapDefinition, labs: dict[str, LabSummary]) -> RoadmapDefinition:
    lab_count = 0
    available_lab_count = 0
    for node in roadmap.nodes:
        if not node.lab_slug:
            continue
        lab_count += 1
        lab = labs.get(node.lab_slug)
        if not lab:
            node.available = False
            continue
        node.available = lab.enabled
        node.title = node.title or lab.title
        node.description = node.description or lab.description
        node.difficulty = lab.difficulty
        node.exercise_count = lab.exercise_count
        node.duration_minutes = lab.duration_minutes
        if node.available:
            available_lab_count += 1
    roadmap.lab_count = lab_count
    roadmap.available_lab_count = available_lab_count
    roadmap.module_count = len(roadmap.modules)
    roadmap.lab_slugs = [
        node.lab_slug for node in roadmap.nodes if node.lab_slug
    ]
    return roadmap


def _to_definition(doc: dict) -> RoadmapDefinition | None:
    raw_id = doc.pop("_id", None)
    slug = doc.get("slug") or str(raw_id or "")
    doc["id"] = slug
    doc["slug"] = slug
    try:
        return RoadmapDefinition.model_validate(doc)
    except ValidationError as exc:
        logger.warning("Skipping roadmap %s: %s", slug, exc)
        return None


def _catalog() -> list[RoadmapDefinition]:
    labs = _labs_by_slug()
    return [_hydrate(item.model_copy(deep=True), labs) for item in ROADMAPS.values()]


def list_roadmaps() -> list[RoadmapSummary]:
    definitions = _list_definitions()
    return [
        RoadmapSummary.model_validate(
            item.model_dump(exclude={"modules", "nodes", "edges"})
        )
        for item in definitions
        if item.enabled
    ]


def _list_definitions() -> list[RoadmapDefinition]:
    if not is_connected():
        return _catalog()

    labs = _labs_by_slug()
    roadmaps: list[RoadmapDefinition] = []
    for stub in _collection().find({}).sort("stage_order", 1):
        definition = _to_definition(stub)
        if not definition:
            continue
        roadmaps.append(_hydrate(definition, labs))
    return roadmaps or _catalog()


def get_roadmap(slug: str) -> RoadmapDefinition | None:
    if not is_connected():
        catalog = {item.slug: item for item in _catalog()}
        return catalog.get(slug)

    doc = _collection().find_one({"slug": slug})
    if not doc:
        catalog = {item.slug: item for item in _catalog()}
        return catalog.get(slug)
    definition = _to_definition(doc)
    if not definition:
        return None
    return _hydrate(definition, _labs_by_slug())
