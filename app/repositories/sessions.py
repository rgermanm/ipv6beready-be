from pymongo.collection import Collection

from app.db import get_db
from app.models.session import LabSessionStatus

COLLECTION = "lab_sessions"


def _collection() -> Collection:
    return get_db()[COLLECTION]


def get_session(lab_id: str) -> LabSessionStatus | None:
    doc = _collection().find_one({"_id": lab_id})
    if not doc:
        return None
    doc.pop("_id", None)
    return LabSessionStatus.model_validate(doc)


def save_session(session: LabSessionStatus) -> None:
    doc = session.model_dump()
    _collection().update_one(
        {"_id": session.lab_id},
        {"$set": doc},
        upsert=True,
    )


def delete_session(lab_id: str) -> bool:
    result = _collection().delete_one({"_id": lab_id})
    return result.deleted_count > 0
