import logging

from bson import ObjectId
from bson.errors import InvalidId
from pymongo.collection import Collection
from pydantic import ValidationError

from app.data.labs import LABS
from app.db import get_db, is_connected
from app.models.lab import ClabConfig, LabDefinition, LabFormula, LabSummary

logger = logging.getLogger(__name__)

COLLECTION = "labs"
_DISABLED_STATUSES = {"disabled", "inactive", "archived", "off", "false", "0"}
_ENABLED_STATUSES = {"enabled", "active", "on", "true", "1"}


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


def _status_flag(value) -> bool | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower()
    if normalized in _DISABLED_STATUSES:
        return False
    if normalized in _ENABLED_STATUSES:
        return True
    return None


def _is_enabled(doc: dict) -> bool:
    status_enabled = _status_flag(doc.get("status"))
    if status_enabled is not None:
        return status_enabled
    enabled = doc.get("enabled")
    if isinstance(enabled, str):
        flagged = _status_flag(enabled)
        return True if flagged is None else flagged
    if enabled is None:
        return True
    return bool(enabled)


def _slug_from_doc(doc: dict, raw_id) -> str:
    for key in ("slug", "title"):
        value = doc.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    path = doc.get("path")
    if isinstance(path, str) and path.strip():
        return path.rstrip("/").split("/")[-1]
    return str(raw_id) if raw_id is not None else ""


def _normalize_lab_doc(doc: dict, *, include_body: bool = False) -> dict | None:
    raw_id = doc.pop("_id", doc.get("id"))
    exercises = doc.pop("exercises", None)
    exercise_list = exercises if isinstance(exercises, list) else []
    title = doc.get("title") if isinstance(doc.get("title"), str) else ""
    path = doc.get("path") if isinstance(doc.get("path"), str) else ""
    if not title.strip() and not path.strip():
        logger.warning("Skipping lab %s: missing title and path", raw_id)
        return None
    if not _is_enabled(doc):
        return None

    public_id = _slug_from_doc(doc, raw_id)
    doc["id"] = public_id
    doc["slug"] = public_id
    doc["title"] = title.strip() or public_id
    doc["description"] = doc.get("description") or ""
    doc["category"] = doc.get("category") or "routing"
    doc["path"] = path
    doc["enabled"] = True
    if not isinstance(doc.get("exercise_count"), int):
        doc["exercise_count"] = len(exercise_list)
    if include_body:
        doc["exercises"] = exercise_list
        if not doc.get("formula"):
            doc["formula"] = LabFormula(
                provider="clab",
                clab=ClabConfig(lab_name=public_id, path=path, topology_file=""),
            ).model_dump()
    return doc


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

    docs = _collection().find({}, {"formula": 0})
    labs: list[LabSummary] = []
    for doc in docs:
        raw_id = doc.get("_id")
        normalized = _normalize_lab_doc(doc)
        if not normalized:
            continue
        try:
            labs.append(LabSummary.model_validate(normalized))
        except ValidationError as exc:
            logger.warning("Skipping lab %s from collection: %s", raw_id, exc)
    return labs


def _find_lab_doc(lab_id: str) -> dict | None:
    collection = _collection()
    for query in ({"slug": lab_id}, {"title": lab_id}):
        doc = collection.find_one(query)
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
    normalized = _normalize_lab_doc(doc, include_body=True)
    if not normalized:
        return LABS.get(lab_id)
    try:
        return LabDefinition.model_validate(normalized)
    except ValidationError as exc:
        logger.warning("Invalid lab %s, retrying with defaults: %s", lab_id, exc)
        normalized["formula"] = LabFormula().model_dump()
        normalized["exercises"] = normalized.get("exercises") or []
        try:
            return LabDefinition.model_validate(normalized)
        except ValidationError:
            return LABS.get(lab_id)
