import sqlite3
from contextlib import closing
from pathlib import Path
from typing import TypeVar
from uuid import UUID

from pydantic import BaseModel

from .models import Comparison


Record = TypeVar("Record", bound=BaseModel)


class JuryRepository:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self.connect()) as db, db:
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS jury_records (
                    kind TEXT NOT NULL,
                    id TEXT NOT NULL,
                    body TEXT NOT NULL,
                    revision INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (kind, id)
                )
                """
            )

    def connect(self):
        return sqlite3.connect(self.path, timeout=5)

    def create(self, kind: str, record_id: UUID, record: BaseModel) -> None:
        with closing(self.connect()) as db, db:
            db.execute(
                "INSERT INTO jury_records (kind, id, body) VALUES (?, ?, ?)",
                (kind, str(record_id), record.model_dump_json()),
            )

    def get(self, kind: str, record_id: UUID, model: type[Record]) -> Record | None:
        with closing(self.connect()) as db:
            row = db.execute(
                "SELECT body FROM jury_records WHERE kind = ? AND id = ?", (kind, str(record_id)),
            ).fetchone()
        return model.model_validate_json(row[0]) if row is not None else None

    def advance(self, comparison: Comparison, expected_index: int) -> bool:
        with closing(self.connect()) as db, db:
            updated = db.execute(
                """
                UPDATE jury_records
                SET body = ?, revision = revision + 1
                WHERE kind = 'comparison' AND id = ? AND revision = ?
                """,
                (comparison.model_dump_json(), str(comparison.comparison_id), expected_index),
            )
        return updated.rowcount == 1
