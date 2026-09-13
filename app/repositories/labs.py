import logging

from bson import ObjectId
from bson.errors import InvalidId
from pymongo.collection import Collection
from pydantic import ValidationError

from app.data.labs import LABS
from app.db import get_db, is_connected
from app.models.lab import LabDefinition, LabSummary

logger = logging.getLogger(__name__)

COLLECTION = "labs"


def _collection() -> Collection:
    return get_db()[COLLECTION]


def ensure_indexes() -> None:
    collection = _collection()
    collection.create_index("path", unique=True, name="labs_path_unique")
    collection.create_index(
        "slug",
        unique=True,
        name="labs_slug_unique",
        partialFilterExpression={"slug": {"$type": "string"}},
    )
    collection.create_index("title", name="labs_title")


def seed_labs() -> None:
    """Create the labs collection and upsert catalog documents.

    Every lab document must include at least ``path`` and ``description``.
    """
    if not is_connected():
        return

    collection = _collection()
    ensure_indexes()

    for lab in LABS.values():
        if not lab.path or not lab.description:
            raise ValueError(f"Lab {lab.id} requires path and description")

        doc = lab.model_dump()
        doc.pop("id", None)
        doc["slug"] = lab.slug or lab.id
        # Display numbers are 1-based list order, independent of leftover guide ids
        for index, exercise in enumerate(doc.get("exercises") or [], start=1):
            exercise["number"] = index
            exercise["id"] = f"step-{index}"
        # Keep clab.path aligned with the top-level lab path
        if doc.get("formula", {}).get("clab"):
            doc["formula"]["clab"]["path"] = lab.path

        collection.update_one(
            {"slug": doc["slug"]},
            {"$set": doc},
            upsert=True,
        )


def _public_id(doc: dict, raw_id) -> str:
    slug = doc.get("slug")
    if slug:
        return str(slug)
    return str(raw_id) if raw_id is not None else ""


def _catalog_summaries() -> list[LabSummary]:
    return [
        LabSummary.model_validate(
            lab.model_dump(exclude={"formula", "exercises"})
        )
        for lab in LABS.values()
    ]


def list_labs() -> list[LabSummary]:
    if not is_connected():
        return _catalog_summaries()

    docs = _collection().find(
        {"title": {"$exists": True}},
        {"formula": 0},
    )
    labs: list[LabSummary] = []
    for doc in docs:
        raw_id = doc.pop("_id", doc.get("id"))
        exercises = doc.pop("exercises", None) or []
        doc["id"] = _public_id(doc, raw_id)
        doc.setdefault("slug", doc["id"])
        doc.setdefault("description", "")
        doc.setdefault("category", "routing")
        doc.setdefault("difficulty", "medium")
        doc.setdefault("duration_minutes", 60)
        doc.setdefault("tags", [])
        doc.setdefault("path", "")
        doc.setdefault("enabled", True)
        doc.setdefault(
            "exercise_count",
            len(exercises) if isinstance(exercises, list) else 0,
        )
        if not doc.get("enabled", True):
            continue
        try:
            labs.append(LabSummary.model_validate(doc))
        except ValidationError as exc:
            logger.warning("Skipping lab %s from collection: %s", raw_id, exc)
    return labs


def _find_lab_doc(lab_id: str) -> dict | None:
    collection = _collection()
    doc = collection.find_one({"slug": lab_id})
    if doc:
        return doc
    try:
        doc = collection.find_one({"_id": ObjectId(lab_id)})
        if doc:
            return doc
    except (InvalidId, TypeError):
        pass
    return collection.find_one({"_id": lab_id})


def get_lab(lab_id: str) -> LabDefinition | None:
    if not is_connected():
        return LABS.get(lab_id)

    doc = _find_lab_doc(lab_id)
    if not doc:
        return LABS.get(lab_id)
    raw_id = doc.pop("_id", lab_id)
    doc["id"] = _public_id(doc, raw_id)
    doc.setdefault("slug", doc["id"])
    try:
        return LabDefinition.model_validate(doc)
    except ValidationError:
        return LABS.get(lab_id)
