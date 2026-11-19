"""Small SQLite JSON repository with atomic task and result writes."""

import json
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException
from pydantic import BaseModel

from ..models.review import Task


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex}"


def now() -> datetime:
    return datetime.now(UTC)


class Store:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS records (
                    kind TEXT NOT NULL, id TEXT NOT NULL, parent TEXT NOT NULL,
                    payload TEXT NOT NULL, PRIMARY KEY(kind, id)
                );
                CREATE TABLE IF NOT EXISTS review_tasks (
                    id TEXT PRIMARY KEY, kind TEXT NOT NULL, resource TEXT NOT NULL,
                    payload TEXT NOT NULL, UNIQUE(kind, resource)
                );
            """)

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def write(db, kind: str, identifier: str, parent: str, value: BaseModel):
        db.execute("INSERT INTO records VALUES (?, ?, ?, ?)", (kind, identifier, parent, value.model_dump_json()))

    def add(self, kind: str, identifier: str, parent: str, value: BaseModel):
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            if kind in {"asset", "review", "project_context", "meeting", "report_addendum", "review_decision"}:
                if db.execute("SELECT 1 FROM records WHERE kind='project' AND id=?", (parent,)).fetchone() is None:
                    raise HTTPException(404, "项目已删除，请重新选择项目。")
            self.write(db, kind, identifier, parent, value)

    def delete_project(self, project_id: str) -> list[str]:
        """Delete project-owned data atomically, retaining shared persona libraries."""
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT 1 FROM records WHERE kind='project' AND id=?", (project_id,)).fetchone() is None:
                raise HTTPException(404, "项目不存在或已删除。")
            rows = db.execute("SELECT kind,id,payload FROM records WHERE parent=?", (project_id,)).fetchall()
            asset_ids = {r["id"] for r in rows if r["kind"] == "asset"}
            review_ids = {r["id"] for r in rows if r["kind"] == "review"}
            tasks = [r for r in db.execute("SELECT id,kind,resource,payload FROM review_tasks").fetchall()
                     if (r["kind"] == "review" and r["resource"] in asset_ids)
                     or (r["kind"] == "rewrite" and r["resource"].split("/", 1)[0] in review_ids)]
            if any(json.loads(r["payload"])["status"] in {"queued", "running"} for r in tasks) or any(
                r["kind"] == "meeting" and json.loads(r["payload"])["status"] == "generating" for r in rows
            ):
                raise HTTPException(409, "项目正在处理审核或生成内容，请等待完成后再删除。")
            files = [json.loads(r["payload"]).get("storage_name", "") for r in rows if r["kind"] == "asset"]
            db.executemany("DELETE FROM review_tasks WHERE id=?", [(r["id"],) for r in tasks])
            db.executemany("DELETE FROM records WHERE kind='rewrite' AND parent=?", [(r,) for r in review_ids])
            db.execute("DELETE FROM records WHERE parent=? AND kind!='persona'", (project_id,))
            db.execute("DELETE FROM records WHERE kind='project' AND id=?", (project_id,))
        return [name for name in files if name]

    def get(self, kind: str, identifier: str, schema):
        with self.connection() as db:
            row = db.execute("SELECT payload FROM records WHERE kind=? AND id=?", (kind, identifier)).fetchone()
        if row is None:
            raise HTTPException(404, "记录不存在，请重新选择项目或素材。")
        return schema.model_validate_json(row["payload"])

    def list(self, kind: str, schema, parent: str | None = None):
        with self.connection() as db:
            if parent is None:
                rows = db.execute("SELECT payload FROM records WHERE kind=? ORDER BY rowid DESC", (kind,)).fetchall()
            else:
                rows = db.execute("SELECT payload FROM records WHERE kind=? AND parent=? ORDER BY rowid DESC", (kind, parent)).fetchall()
        return [schema.model_validate_json(row["payload"]) for row in rows]

    def task(self, identifier: str) -> Task:
        with self.connection() as db:
            row = db.execute("SELECT payload FROM review_tasks WHERE id=?", (identifier,)).fetchone()
        if row is None:
            raise HTTPException(404, "任务不存在。")
        return Task.model_validate_json(row["payload"])

    def start_task(self, kind, resource, mode, model) -> tuple[Task, bool]:
        task = Task(task_id=new_id("task"), kind=kind, resource_id=resource, mode=mode, model=model,
                    status="queued", stage="queued", created_at=now())
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            owner_kind = "asset" if kind == "review" else "review"
            owner_id = resource if kind == "review" else resource.split("/", 1)[0]
            if db.execute("SELECT 1 FROM records WHERE kind=? AND id=?", (owner_kind, owner_id)).fetchone() is None:
                raise HTTPException(404, "素材或审核已删除，请重新选择项目。")
            inserted = db.execute("INSERT INTO review_tasks VALUES (?, ?, ?, ?) ON CONFLICT(kind, resource) DO NOTHING",
                                 (task.task_id, kind, resource, task.model_dump_json())).rowcount
            row = db.execute("SELECT payload FROM review_tasks WHERE kind=? AND resource=?", (kind, resource)).fetchone()
        return Task.model_validate_json(row["payload"]), bool(inserted)

    def save_task(self, task: Task):
        with self.connection() as db:
            db.execute("UPDATE review_tasks SET payload=? WHERE id=?", (task.model_dump_json(), task.task_id))

    def retry(self, identifier, mode, model):
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT payload FROM review_tasks WHERE id=?", (identifier,)).fetchone()
            if row is None:
                raise HTTPException(404, "任务不存在。")
            task = Task.model_validate_json(row["payload"])
            if task.status not in ("failed", "interrupted"):
                raise HTTPException(409, "仅失败或中断的任务可以重试。")
            if (mode, model) != (task.mode, task.model):
                raise HTTPException(409, "请使用创建任务时的模式和模型重试。")
            task.status, task.error = "queued", None
            task.error_code, task.retryable = None, False
            db.execute("UPDATE review_tasks SET payload=? WHERE id=?", (task.model_dump_json(), identifier))
        return task

    def recover(self):
        with self.connection() as db:
            for row in db.execute("SELECT id,payload FROM review_tasks").fetchall():
                task = Task.model_validate_json(row["payload"])
                if task.status in ("queued", "running"):
                    task.status = "interrupted"
                    task.error = "服务已重启，已完成步骤保留，请重试继续。"
                    task.error_code, task.retryable = "service_restarted", True
                    db.execute("UPDATE review_tasks SET payload=? WHERE id=?", (task.model_dump_json(), row["id"]))

    def finish(self, task: Task, records):
        with self.connection() as db:
            for kind, identifier, parent, value in records:
                self.write(db, kind, identifier, parent, value)
            task.status, task.stage, task.error = "completed", "completed", None
            task.error_code, task.retryable = None, False
            task.events.append("completed")
            db.execute("UPDATE review_tasks SET payload=? WHERE id=?", (task.model_dump_json(), task.task_id))
