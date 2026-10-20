"""Offline eval: judge every stored plan with the Jev judge and report the ranking metrics.

    make eval-jev            (runs inside the API container, needs JEV_API_KEY)

No human grades are used. For each stored plan the judge grades the candidates in the
plan's ranked order, then nDCG@3, Precision@3 and pairwise_accuracy are computed.
Results are pushed to each plan's Langfuse trace (--no-push to skip), and a report is
written to --out. Judge calls are cached in the evaluation database.
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from api.core.jev import JevClient, JevConfigError, JevError, require_jev_key
from api.core.monitoring import enqueue_trace_scores
from api.features.plan.eval.evaluation import evaluation_db
from api.features.plan.judge.judge import JUDGE_VERSION, judge_grades, judge_one
from api.features.plan.jev_ranking import ranking_version
from api.features.plan.eval.metrics import ranking_metrics

METRIC_KEYS = ("nDCG@3", "Precision@3", "pairwise_accuracy")


def ensure_judge_table(db):
    db.execute("""CREATE TABLE IF NOT EXISTS jev_judgments (
        evaluation_id TEXT NOT NULL, recipe_id TEXT NOT NULL, judge_version TEXT NOT NULL,
        score REAL NOT NULL, probabilities TEXT NOT NULL, model TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (evaluation_id, recipe_id, judge_version)
    )""")


def judge_snapshot(db, client: JevClient, evaluation_id: str, snapshot: dict) -> dict[str, dict]:
    """Return {recipe_id: {score, probabilities, model}} for every candidate, using the cache."""
    results = {}
    for candidate in snapshot["candidates"]:
        row = db.execute("SELECT score, probabilities, model FROM jev_judgments "
                         "WHERE evaluation_id = ? AND recipe_id = ? AND judge_version = ?",
                         (evaluation_id, candidate["recipe_id"], JUDGE_VERSION)).fetchone()
        if row is None:
            judged = judge_one(client, snapshot["request"], candidate)
            db.execute("INSERT INTO jev_judgments (evaluation_id, recipe_id, judge_version, score, probabilities, model) "
                       "VALUES (?, ?, ?, ?, ?, ?)",
                       (evaluation_id, candidate["recipe_id"], JUDGE_VERSION, judged["score"],
                        json.dumps(judged["probabilities"]), judged["model"]))
            results[candidate["recipe_id"]] = judged
        else:
            results[candidate["recipe_id"]] = {"score": row[0], "probabilities": json.loads(row[1]), "model": row[2]}
    return results


def mean_of(rows: list[dict], key: str):
    values = [row[key] for row in rows if row[key] is not None]
    return sum(values) / len(values) if values else None


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=Path("target/eval/jev_report.json"))
    parser.add_argument("--no-push", action="store_true", help="do not write scores to Langfuse")
    parser.add_argument("--limit", type=int, default=25,
                        help="number of most recent plans to judge")
    args = parser.parse_args(argv)

    try:
        key = require_jev_key()
    except JevConfigError as exc:
        print(f"error: {exc}. The Jev eval needs JEV_API_KEY.", file=sys.stderr)
        return 2

    client = JevClient(key)
    plans, pushed = [], 0
    try:
        with evaluation_db() as db:
            ensure_judge_table(db)
            rows = db.execute(
                "SELECT id, trace_id, snapshot FROM ranking_evaluations "
                "ORDER BY created_at DESC LIMIT ?", (args.limit,)
            ).fetchall()
            for evaluation_id, trace_id, raw in rows:
                snapshot = json.loads(raw)
                if not snapshot["candidates"]:
                    continue
                judged = judge_snapshot(db, client, evaluation_id, snapshot)
                ordered = [candidate["recipe_id"] for candidate in snapshot["candidates"]]
                dupes = {rid: n for rid, n in Counter(ordered).items() if n > 1}
                if dupes:
                    print(f"skip {evaluation_id} for {trace_id}: duplicate recipe_ids {dupes}",
                          file=sys.stderr)
                    continue

                # 1. Pool metrics (Ranker)
                grades = judge_grades(judged)
                metrics = ranking_metrics(ordered, grades)

                # 2. Output metrics (Solver)
                selected_ids = snapshot.get("selected_ids", [])
                output_metrics = {}
                if selected_ids:
                    selected_grades = [grades[r] for r in selected_ids if r in grades]
                    if selected_grades:
                        output_metrics = {
                            "plan_mean_grade": sum(selected_grades) / len(selected_grades),
                            "plan_share_good": sum(g >= 2 for g in selected_grades) / len(selected_grades),
                            "plan_repeat_rate": 1 - len(set(selected_ids)) / len(selected_ids),
                        }

                diag = {
                    "pool_size": len(grades),
                    "good_in_pool": sum(g >= 2 for g in grades.values()),
                    "best_grade_in_pool": max(grades.values()) if grades else 0,
                }

                # Eyeball the pool
                for rank, rid in enumerate(ordered[:10], 1):
                    print(rank, grades.get(rid, "N/A"), rid)

                plans.append({
                    "evaluation_id": evaluation_id,
                    "trace_id": trace_id,
                    "candidates": len(ordered),
                    **metrics,
                    "output_metrics": output_metrics,
                    "diagnostics": diag
                })

                # 3. Push BOTH pool and output metrics to Langfuse
                if not args.no_push:
                    pushed_pool = enqueue_trace_scores(
                        trace_id, metrics, source="jev-judge-pool",
                        comment="LLM judge (Jev) grades of the ranked pool",
                        metadata={"judge_version": JUDGE_VERSION}
                    )
                    pushed_output = False
                    if output_metrics:
                        pushed_output = enqueue_trace_scores(
                            trace_id, output_metrics, source="jev-judge-output",
                            comment="LLM judge (Jev) grades of the final selected meals",
                            metadata={"judge_version": JUDGE_VERSION}
                        )
                    if pushed_pool or pushed_output:
                        pushed += 1
    except JevError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    finally:
        client.close()

    report = {
        "judge_version": JUDGE_VERSION,
        "plans": len(plans),
        "averages": {key: mean_of(plans, key) for key in METRIC_KEYS},
        "scores_pushed_to_langfuse": pushed,
        "per_plan": plans,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, allow_nan=False))
    print(json.dumps({k: report[k] for k in ("plans", "averages", "scores_pushed_to_langfuse")}, indent=2))
    print(f"report written to {args.out}")

    print("Waiting 5 seconds for Langfuse background flush...")
    import time
    time.sleep(5)

    print("Langfuse background flush complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
