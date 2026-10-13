"""Persist ranking snapshots and collect protected, blind human judgments."""

import json
import os
import secrets
import sqlite3
from contextlib import closing, contextmanager
from pathlib import Path
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field, StrictInt

from api.core.monitoring import enqueue_scores
from .metrics import ranking_metrics


@contextmanager
def evaluation_db():
    # ponytail: local SQLite for one API deployment; use shared PostgreSQL before scaling replicas.
    path = Path(os.getenv("REMY_EVALUATION_DB", "target/evaluations.sqlite3"))
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path, timeout=5)) as db:
        db.execute("""CREATE TABLE IF NOT EXISTS ranking_evaluations (
            id TEXT PRIMARY KEY, trace_id TEXT, snapshot TEXT NOT NULL,
            grades TEXT, metrics TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )""")
        with db:
            yield db


def save_evaluation(trace_id, plan_id, request, recipes):
    if not os.getenv("REMY_EVALUATION_TOKEN"):
        return None
    evaluation_id = str(uuid4())
    snapshot = {
        "plan_id": plan_id,
        "request": request.model_dump(mode="json"),
        "ranking_version": "nutrient-deviation-v1",
        "data_version": os.getenv("REMY_DATA_VERSION", "unspecified"),
        "candidates": [{
            "recipe_id": recipe.recipe_id, "title": recipe.title,
            "nutrients": recipe.nutrients, "instructions": recipe.instructions,
            "ingredients": [ingredient.cleaned_text or ingredient.raw_text or ingredient.text
                            or ingredient.description or ingredient.canonical_key
                            for ingredient in recipe.ingredients],
        } for recipe in recipes],
    }
    with evaluation_db() as db:
        db.execute("INSERT INTO ranking_evaluations (id, trace_id, snapshot) VALUES (?, ?, ?)",
                   (evaluation_id, trace_id, json.dumps(snapshot, allow_nan=False)))
    return evaluation_id


security = HTTPBearer(auto_error=False)


def require_reviewer(credentials: HTTPAuthorizationCredentials | None = Depends(security)):
    token = os.getenv("REMY_EVALUATION_TOKEN")
    if not token:
        raise HTTPException(503, "Ranking evaluation is disabled")
    if credentials is None or not secrets.compare_digest(credentials.credentials.encode(), token.encode()):
        raise HTTPException(401, "Invalid reviewer token", headers={"WWW-Authenticate": "Bearer"})


class HumanGrades(BaseModel):
    model_config = ConfigDict(extra="forbid")
    grades: dict[Annotated[str, Field(min_length=1, max_length=128)],
                 Annotated[StrictInt, Field(ge=0, le=3)]] = Field(min_length=1, max_length=300)


router = APIRouter(dependencies=[Depends(require_reviewer)])


def read_record(db, evaluation_id):
    row = db.execute("SELECT trace_id, snapshot, grades, metrics FROM ranking_evaluations WHERE id = ?",
                     (str(evaluation_id),)).fetchone()
    if row is None:
        raise HTTPException(404, "Unknown evaluation")
    return row


@router.get("/{evaluation_id}")
def blind_candidates(evaluation_id: UUID):
    with evaluation_db() as db:
        _, raw, _, _ = read_record(db, evaluation_id)
    snapshot = json.loads(raw)
    candidates = snapshot["candidates"]
    secrets.SystemRandom().shuffle(candidates)
    # No original ranking, algorithm scores, trace link, plan order, or previous grades.
    return {"evaluation_id": str(evaluation_id), "request": snapshot["request"],
            "candidates": candidates, "grade_range": [0, 3], "relevant_min_grade": 2}


@router.post("/{evaluation_id}/grades")
def submit_grades(evaluation_id: UUID, body: HumanGrades):
    with evaluation_db() as db:
        db.execute("BEGIN IMMEDIATE")
        trace_id, raw, previous, _ = read_record(db, evaluation_id)
        if previous is not None and json.loads(previous) != body.grades:
            raise HTTPException(409, "Grades are immutable; retry with the same grades")
        ranked_ids = [candidate["recipe_id"] for candidate in json.loads(raw)["candidates"]]
        try:
            metrics = ranking_metrics(ranked_ids, body.grades)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        # Commit before enqueueing. A network failure never loses the judgments.
        db.execute("UPDATE ranking_evaluations SET grades = ?, metrics = ? WHERE id = ?",
                   (json.dumps(body.grades), json.dumps(metrics), str(evaluation_id)))
    queued = enqueue_scores(str(evaluation_id), trace_id, metrics)
    return {"evaluation_id": str(evaluation_id), "trace_id": trace_id, "metrics": metrics,
            "langfuse_scores_queued": queued}
