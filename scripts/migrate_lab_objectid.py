#!/usr/bin/env python3
"""Recreate labs._id='static-routing-lab-01' with an ObjectId and a slug field."""

from __future__ import annotations

import sys
from pathlib import Path

from bson import ObjectId

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db import close, connect, get_db  # noqa: E402

LEGACY_ID = "static-routing-lab-01"


def migrate() -> None:
    if not connect():
        raise SystemExit("MongoDB is not connected")

    collection = get_db()["labs"]
    try:
        collection.drop_index("labs_slug_unique")
    except Exception:
        pass
    existing = collection.find_one({"slug": LEGACY_ID, "_id": {"$type": "objectId"}})
    if existing:
        print(f"Already migrated: slug={LEGACY_ID} _id={existing['_id']}")
        return

    legacy = collection.find_one({"_id": LEGACY_ID})
    if not legacy:
        raise SystemExit(f"No lab document found with _id={LEGACY_ID!r}")

    new_doc = dict(legacy)
    new_doc.pop("_id", None)
    new_doc["slug"] = LEGACY_ID
    new_id = ObjectId()
    new_doc["_id"] = new_id

    original_path = new_doc.get("path")
    # Free the unique path index before inserting the replacement.
    if original_path:
        collection.update_one(
            {"_id": LEGACY_ID},
            {"$set": {"path": f"{original_path}.__migrating"}},
        )

    try:
        collection.insert_one(new_doc)
        collection.delete_one({"_id": LEGACY_ID})
    except Exception:
        if original_path:
            collection.update_one({"_id": LEGACY_ID}, {"$set": {"path": original_path}})
        raise

    inserted = collection.find_one({"_id": new_id})
    if not inserted:
        raise SystemExit("Insert reported success but the new document was not found")

    collection.create_index(
        "slug",
        unique=True,
        name="labs_slug_unique",
        partialFilterExpression={"slug": {"$type": "string"}},
    )

    print(
        "Migrated lab document:\n"
        f"  slug={inserted.get('slug')}\n"
        f"  _id={inserted['_id']} ({type(inserted['_id']).__name__})"
    )


if __name__ == "__main__":
    try:
        migrate()
    finally:
        close()
