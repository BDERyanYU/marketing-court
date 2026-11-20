import sqlite3
from contextlib import closing
from pathlib import Path
from typing import TypeVar
from uuid import UUID

from pydantic import BaseModel

from .models import Comparison, Exposure, Panel


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

    def panels_with_report_names(self) -> list[tuple[Panel, str | None]]:
        with closing(self.connect()) as db:
            rows = db.execute(
                """
                SELECT panel.body, json_extract(report.body, '$.filename')
                FROM jury_records AS panel
                LEFT JOIN jury_records AS report
                    ON report.kind = 'report' AND report.id = json_extract(panel.body, '$.report_id')
                WHERE panel.kind = 'panel'
                ORDER BY panel.rowid DESC
                """
            ).fetchall()
        return [(Panel.model_validate_json(body), filename) for body, filename in rows]

    def append_exposure(self, comparison_id: UUID, exposure: Exposure) -> None:
        with closing(self.connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT body FROM jury_records WHERE kind = 'comparison' AND id = ?",
                (str(comparison_id),),
            ).fetchone()
            if row is None:
                raise LookupError("Comparison record disappeared.")
            comparison = Comparison.model_validate_json(row[0])
            key = (exposure.member_id, exposure.variant)
            if any((item.member_id, item.variant) == key for item in comparison.exposures):
                return
            comparison.exposures.append(exposure)
            db.execute(
                """
                UPDATE jury_records
                SET body = ?, revision = revision + 1
                WHERE kind = 'comparison' AND id = ?
                """,
                (comparison.model_dump_json(), str(comparison_id)),
            )
