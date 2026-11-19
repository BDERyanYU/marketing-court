import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from ..models import COURT_STEPS, CourtCase, CourtInput, CourtStep, DebateTurn, Judgment, RunMode


class InputConflict(Exception):
    """The risk ID already identifies a different review snapshot."""


class CourtRepository:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS court_inputs (
                    risk_id TEXT PRIMARY KEY,
                    snapshot TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS court_cases (
                    case_id TEXT PRIMARY KEY,
                    snapshot TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    model TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    next_step TEXT
                );
                CREATE TABLE IF NOT EXISTS court_steps (
                    case_id TEXT NOT NULL REFERENCES court_cases(case_id),
                    step TEXT NOT NULL,
                    step_order INTEGER NOT NULL,
                    result TEXT NOT NULL,
                    PRIMARY KEY (case_id, step)
                );
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def register_input(self, snapshot: CourtInput, *, keep_existing: bool = False) -> None:
        with closing(self._connect()) as connection, connection:
            connection.execute(
                "INSERT INTO court_inputs VALUES (?, ?) ON CONFLICT(risk_id) DO NOTHING",
                (snapshot.risk_id, snapshot.model_dump_json()),
            )
            if keep_existing:
                return
            stored = connection.execute(
                "SELECT snapshot FROM court_inputs WHERE risk_id = ?",
                (snapshot.risk_id,),
            ).fetchone()
            if CourtInput.model_validate_json(stored["snapshot"]) != snapshot:
                raise InputConflict("This risk ID already identifies a different review. Use a new risk ID.")

    def get_input(self, risk_id: str) -> CourtInput | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT snapshot FROM court_inputs WHERE risk_id = ?",
                (risk_id,),
            ).fetchone()
        return CourtInput.model_validate_json(row["snapshot"]) if row is not None else None

    def create_case(self, snapshot: CourtInput, mode: RunMode, model: str) -> CourtCase:
        case = CourtCase(
            case_id=uuid4(),
            mode=mode,
            model=model,
            created_at=datetime.now(UTC),
            snapshot=snapshot,
            next_step=CourtStep.PROSECUTION_1,
        )
        with closing(self._connect()) as connection, connection:
            connection.execute(
                """
                INSERT INTO court_cases (case_id, snapshot, mode, model, created_at, next_step)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    str(case.case_id),
                    snapshot.model_dump_json(),
                    mode,
                    model,
                    case.created_at.isoformat(),
                    case.next_step,
                ),
            )
        return case

    def get_case(self, case_id: UUID) -> CourtCase | None:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT c.*, s.step, s.result
                FROM court_cases c LEFT JOIN court_steps s ON c.case_id = s.case_id
                WHERE c.case_id = ?
                ORDER BY s.step_order
                """,
                (str(case_id),),
            ).fetchall()
        if not rows:
            return None

        turns = []
        judgment = None
        for row in rows:
            if row["step"] == CourtStep.JUDGMENT:
                judgment = Judgment.model_validate_json(row["result"])
            elif row["step"] is not None:
                turns.append(DebateTurn.model_validate_json(row["result"]))

        case_row = rows[0]
        return CourtCase(
            case_id=case_id,
            mode=case_row["mode"],
            model=case_row["model"],
            created_at=datetime.fromisoformat(case_row["created_at"]),
            snapshot=CourtInput.model_validate_json(case_row["snapshot"]),
            next_step=case_row["next_step"],
            turns=turns,
            judgment=judgment,
        )

    def commit_step(
        self,
        case_id: UUID,
        step: CourtStep,
        next_step: CourtStep | None,
        result: DebateTurn | Judgment,
    ) -> None:
        with closing(self._connect()) as connection, connection:
            update = connection.execute(
                "UPDATE court_cases SET next_step = ? WHERE case_id = ? AND next_step = ?",
                (next_step, str(case_id), step),
            )
            if update.rowcount == 0:
                return
            connection.execute(
                "INSERT INTO court_steps VALUES (?, ?, ?, ?)",
                (str(case_id), step, COURT_STEPS.index(step), result.model_dump_json()),
            )
