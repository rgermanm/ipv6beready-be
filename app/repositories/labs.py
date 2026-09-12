from pymongo.collection import Collection
from pydantic import ValidationError

from app.data.labs import LABS
from app.db import get_db, is_connected
from app.models.lab import LabDefinition, LabSummary

COLLECTION = "labs"


def _collection() -> Collection:
    return get_db()[COLLECTION]


def ensure_indexes() -> None:
    collection = _collection()
    collection.create_index("path", unique=True, name="labs_path_unique")
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
        # Display numbers are 1-based list order, independent of leftover guide ids
        for index, exercise in enumerate(doc.get("exercises") or [], start=1):
            exercise["number"] = index
            exercise["id"] = f"step-{index}"
        # Keep clab.path aligned with the top-level lab path
        if doc.get("formula", {}).get("clab"):
            doc["formula"]["clab"]["path"] = lab.path

        collection.update_one(
            {"_id": lab.id},
            {"$set": doc},
            upsert=True,
        )


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
        {"title": {"$exists": True}, "path": {"$exists": True}},
        {"formula": 0, "exercises": 0},
    )
    labs: list[LabSummary] = []
    for doc in docs:
        raw_id = doc.pop("_id", doc.get("id"))
        doc["id"] = str(raw_id) if raw_id is not None else None
        try:
            labs.append(LabSummary.model_validate(doc))
        except ValidationError:
            continue
    return labs or _catalog_summaries()


def get_lab(lab_id: str) -> LabDefinition | None:
    if not is_connected():
        return LABS.get(lab_id)

    doc = _collection().find_one({"_id": lab_id})
    if not doc:
        return LABS.get(lab_id)
    raw_id = doc.pop("_id", lab_id)
    doc["id"] = str(raw_id)
    try:
        return LabDefinition.model_validate(doc)
    except ValidationError:
        return LABS.get(lab_id)
