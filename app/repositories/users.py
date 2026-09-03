from bson import ObjectId
from bson.errors import InvalidId
from pymongo.collection import Collection
from pymongo.errors import DuplicateKeyError

from app.db import get_db
from app.models.user import User

COLLECTION = "users"


def _collection() -> Collection:
    return get_db()[COLLECTION]


def ensure_indexes() -> None:
    collection = _collection()
    collection.create_index("email", unique=True, name="users_email_unique")
    collection.create_index(
        "google_id",
        unique=True,
        sparse=True,
        name="users_google_id_unique",
    )


def _doc_to_user(doc: dict) -> User:
    return User(
        id=str(doc["_id"]),
        email=doc["email"],
        name=doc["name"],
        hashed_password=doc.get("hashed_password"),
        google_id=doc.get("google_id"),
        avatar=doc.get("avatar"),
        is_active=doc.get("is_active", True),
        is_superuser=doc.get("is_superuser", False),
    )


def get_user_by_email(email: str) -> User | None:
    doc = _collection().find_one({"email": email})
    return _doc_to_user(doc) if doc else None


def get_user_by_google_id(google_id: str) -> User | None:
    doc = _collection().find_one({"google_id": google_id})
    return _doc_to_user(doc) if doc else None


def get_user_by_id(user_id: str) -> User | None:
    try:
        oid = ObjectId(user_id)
    except (InvalidId, TypeError):
        return None
    doc = _collection().find_one({"_id": oid})
    return _doc_to_user(doc) if doc else None


def insert_user(user: User) -> User:
    doc = {
        "email": str(user.email),
        "name": user.name,
        "hashed_password": user.hashed_password,
        "is_active": user.is_active,
        "is_superuser": user.is_superuser,
    }
    if user.google_id is not None:
        doc["google_id"] = user.google_id
    if user.avatar is not None:
        doc["avatar"] = user.avatar
    result = _collection().insert_one(doc)
    user.id = str(result.inserted_id)
    return user


def save_user(user: User) -> User:
    try:
        oid = ObjectId(user.id)
    except (InvalidId, TypeError) as exc:
        raise ValueError("Invalid user id") from exc
    _collection().update_one(
        {"_id": oid},
        {
            "$set": {
                "email": str(user.email),
                "name": user.name,
                "hashed_password": user.hashed_password,
                "google_id": user.google_id,
                "avatar": user.avatar,
                "is_active": user.is_active,
                "is_superuser": user.is_superuser,
            }
        },
    )
    return user


def delete_user(user: User) -> None:
    try:
        oid = ObjectId(user.id)
    except (InvalidId, TypeError):
        return
    _collection().delete_one({"_id": oid})


class EmailAlreadyExistsError(Exception):
    pass


def create_user_or_raise(user: User) -> User:
    try:
        return insert_user(user)
    except DuplicateKeyError as exc:
        raise EmailAlreadyExistsError from exc
