from bson import ObjectId
from bson.errors import InvalidId
from pymongo.collection import Collection

from app.db import get_db
from app.models.instance import LabInstance

COLLECTION = "instances"
ACTIVE_STATUSES = ("starting", "running")


def _collection() -> Collection:
    return get_db()[COLLECTION]


def ensure_indexes() -> None:
    collection = _collection()
    collection.create_index(
        [("user_id", 1), ("lab_id", 1), ("status", 1)],
        name="instances_user_lab_status",
    )
    collection.create_index("expires_at", name="instances_expires_at")
    collection.create_index("clab_name", name="instances_clab_name")


def _doc_to_instance(doc: dict) -> LabInstance:
    doc = dict(doc)
    doc["id"] = str(doc.pop("_id"))
    return LabInstance.model_validate(doc)


def _dump(instance: LabInstance) -> dict:
    doc = instance.model_dump(exclude={"id"})
    return doc


def insert_instance(instance: LabInstance) -> LabInstance:
    result = _collection().insert_one(_dump(instance))
    instance.id = str(result.inserted_id)
    return instance


def save_instance(instance: LabInstance) -> LabInstance:
    try:
        oid = ObjectId(instance.id)
    except (InvalidId, TypeError) as exc:
        raise ValueError("Invalid instance id") from exc
    _collection().update_one({"_id": oid}, {"$set": _dump(instance)})
    return instance


def get_instance(instance_id: str) -> LabInstance | None:
    try:
        oid = ObjectId(instance_id)
    except (InvalidId, TypeError):
        return None
    doc = _collection().find_one({"_id": oid})
    return _doc_to_instance(doc) if doc else None


def get_active_instance(user_id: str, lab_id: str) -> LabInstance | None:
    doc = _collection().find_one(
        {
            "user_id": user_id,
            "lab_id": lab_id,
            "status": {"$in": list(ACTIVE_STATUSES)},
        },
        sort=[("created_at", -1)],
    )
    return _doc_to_instance(doc) if doc else None


def get_latest_instance(user_id: str, lab_id: str) -> LabInstance | None:
    doc = _collection().find_one(
        {"user_id": user_id, "lab_id": lab_id},
        sort=[("created_at", -1)],
    )
    return _doc_to_instance(doc) if doc else None


def mark_stopped(instance: LabInstance, message: str | None = None) -> LabInstance:
    instance.status = "stopped"
    if message:
        instance.message = message
    return save_instance(instance)


def mark_expired(instance: LabInstance, message: str | None = None) -> LabInstance:
    instance.status = "expired"
    instance.message = message or "Lab instance expired"
    return save_instance(instance)
