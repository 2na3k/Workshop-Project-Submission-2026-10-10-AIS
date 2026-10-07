"""Run: uv run --package remy-api python -m unittest discover -s remy/api/tests -p test_monitoring.py"""

import json
import math
import os
import tempfile
import unittest
from contextlib import contextmanager
from unittest.mock import patch

from fastapi.testclient import TestClient

from api.core import monitoring
from api.features.plan.evaluation import evaluation_db
from api.features.plan.metrics import ranking_metrics
from api.features.plan.models import Ingredient, Recipe
from api.features.plan.dependencies import get_plan_service
from api.features.plan.schemas import PlanRequest
from api.features.plan.service import PlanService


class RecordingClient:
    def __init__(self):
        self.spans, self.scores = [], []

    @contextmanager
    def start_as_current_observation(self, **kwargs):
        span = RecordingSpan(kwargs)
        self.spans.append(span)
        yield span

    def create_score(self, **kwargs):
        self.scores.append(kwargs)


class RecordingSpan:
    trace_id = "1234567890abcdef1234567890abcdef"

    def __init__(self, kwargs):
        self.kwargs, self.updates = kwargs, []

    def update(self, **kwargs):
        self.updates.append(kwargs)


class MetricsTests(unittest.TestCase):
    def test_metrics_and_edge_cases(self):
        ranked = ["a", "b", "c", "d"]
        perfect = ranking_metrics(ranked, dict(zip(ranked, [3, 2, 1, 0])))
        self.assertEqual(perfect, {"nDCG@3": 1.0, "Precision@3": 2 / 3, "pairwise_accuracy": 1.0})
        reversed_grades = ranking_metrics(ranked, dict(zip(ranked, [0, 1, 2, 3])))
        self.assertAlmostEqual(reversed_grades["nDCG@3"],
                               (1 / math.log2(3) + 3 / 2) / (7 + 3 / math.log2(3) + 1 / 2))
        self.assertEqual(reversed_grades["Precision@3"], 1 / 3)
        self.assertEqual(reversed_grades["pairwise_accuracy"], 0)
        self.assertEqual(ranking_metrics(["a", "b", "c"], {"a": 3, "b": 3, "c": 1})["pairwise_accuracy"], 1)
        zero = ranking_metrics(["a"], {"a": 0})
        self.assertEqual(zero, {"nDCG@3": 0.0, "Precision@3": 0.0, "pairwise_accuracy": None})
        self.assertEqual(ranking_metrics(["a"], {"a": 3})["Precision@3"], 1 / 3)
        for ranked, grades in [([], {}), (["a", "a"], {"a": 3}), (["a", "b"], {"a": 3}),
                               (["a"], {"a": 3, "b": 0}), (["a"], {"a": True}),
                               (["a"], {"a": 2.5}), (["a"], {"a": 4}), (["a"], {"a": -1})]:
            with self.assertRaises(ValueError):
                ranking_metrics(ranked, grades)


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {
            "LANGFUSE_TRACING_ENABLED": "false", "REMY_EVALUATION_TOKEN": "reviewer-test-token",
            "REMY_EVALUATION_DB": self.temp.name + "/evaluations.sqlite3",
        })
        self.env.start()
        monitoring.get_client.cache_clear()
        self.addCleanup(self.temp.cleanup)
        self.addCleanup(self.env.stop)
        self.addCleanup(monitoring.get_client.cache_clear)
        self.recording = RecordingClient()
        self.client_patch = patch("api.core.monitoring.get_client", return_value=self.recording)
        self.client_patch.start()
        self.addCleanup(self.client_patch.stop)
        self.request = PlanRequest(horizon_days=1, meals_per_day=1,
                                   nutrients=[{"code": "calories", "unit": "kcal", "goal": {"value": 300}}])
        outer = self

        class Repository:
            def fetch_candidates(self):
                return [Recipe(recipe_id=key, title="Recipe " + key, ingredients=[Ingredient(
                    quantity=100, unit="g", text="food", nutrients={"calories": kcal},
                    nutrition_basis="per 100 g")]) for key, kcal in [("a", 200), ("b", 300), ("c", 100), ("d", 400)]]

        self.service = PlanService(Repository())
        from api.main import app

        previous_overrides = app.dependency_overrides.copy()
        self.addCleanup(setattr, app, "dependency_overrides", previous_overrides)
        app.dependency_overrides[get_plan_service] = lambda: outer.service
        self.http = TestClient(app)
        self.addCleanup(self.http.close)
        self.headers = {"Authorization": "Bearer reviewer-test-token"}

    def create(self):
        response = self.http.post("/api/v1/plan", json=self.request.model_dump())
        self.assertEqual(response.status_code, 200, response.text)
        for block in response.text.split("\n\n"):
            if block.startswith("event: plan\n"):
                return json.loads(block.split("data: ", 1)[1])
        self.fail("Stream ended without a plan event: " + response.text)

    def test_plan_blind_grading_persistence_and_idempotent_scores(self):
        result = self.create()
        self.assertEqual(result["trace_id"], RecordingSpan.trace_id)
        evaluation_id = result["evaluation_id"]
        route = "/api/v1/evaluations/" + evaluation_id
        unauthorized = self.http.get(route)
        self.assertEqual(unauthorized.status_code, 401)
        self.assertEqual(unauthorized.json()["error"]["code"], "HTTP_401")
        self.assertEqual(unauthorized.headers["WWW-Authenticate"], "Bearer")
        self.assertEqual(self.http.get(route, headers={"Authorization": "Bearer wrong"}).status_code, 401)
        with patch("api.features.plan.evaluation.secrets.SystemRandom.shuffle",
                   side_effect=lambda candidates: candidates.reverse()):
            blind = self.http.get(route, headers=self.headers).json()
        self.assertNotIn("trace_id", blind)
        self.assertNotIn("plan_id", blind)
        self.assertEqual([item["recipe_id"] for item in blind["candidates"]], ["c", "d", "a", "b"])
        self.assertTrue(all("score" not in item for item in blind["candidates"]))
        self.assertEqual(blind["request"], self.request.model_dump())
        grades = {"grades": {"b": 3, "a": 2, "d": 1, "c": 0}}
        response = self.http.post(route + "/grades", headers=self.headers, json=grades)
        self.assertEqual(response.status_code, 200, response.text)
        scored = response.json()
        self.assertEqual(scored["metrics"]["nDCG@3"], 1.0)
        self.assertEqual(scored["metrics"]["Precision@3"], 2 / 3)
        self.assertEqual(scored["metrics"]["pairwise_accuracy"], 1.0)
        self.assertTrue(scored["langfuse_scores_queued"])
        self.assertEqual({score["name"] for score in self.recording.scores}, set(scored["metrics"]))
        self.assertTrue(all(score["trace_id"] == result["trace_id"] for score in self.recording.scores))
        ids = [score["score_id"] for score in self.recording.scores]
        self.assertEqual(self.http.post(route + "/grades", headers=self.headers, json=grades).status_code, 200)
        self.assertEqual(ids, [score["score_id"] for score in self.recording.scores[3:]])
        with evaluation_db() as db:
            raw = db.execute("SELECT grades, metrics FROM ranking_evaluations WHERE id = ?", (evaluation_id,)).fetchone()
        self.assertEqual(json.loads(raw[0]), grades["grades"])
        self.assertEqual(json.loads(raw[1]), scored["metrics"])
        self.assertEqual([span.kwargs["name"] for span in self.recording.spans],
                         ["meal-plan", "retrieve-candidates", "filter-candidates", "rank-candidates", "solve-plan", "generate-response"])
        self.assertNotIn("allergies", self.recording.spans[0].kwargs["metadata"])
        self.assertNotIn("input", self.recording.spans[0].kwargs)
        changed = {"grades": {"b": 0, "a": 2, "d": 1, "c": 0}}
        self.assertEqual(self.http.post(route + "/grades", headers=self.headers, json=changed).status_code, 409)

    def test_grading_validation(self):
        route = "/api/v1/evaluations/" + self.create()["evaluation_id"] + "/grades"
        for body in [{"grades": {"b": 3}}, {"grades": {"b": 3, "a": 2, "d": 1, "c": 0, "unknown": 3}},
                     {"grades": {"b": True}}, {"grades": {"b": 4}}, {"grades": {"b": 1.0}},
                     {"grades": {"b": 3}, "trace_id": RecordingSpan.trace_id}, {"grades": {}}]:
            self.assertEqual(self.http.post(route, headers=self.headers, json=body).status_code, 422)
        self.assertEqual(self.http.get("/api/v1/evaluations/00000000-0000-0000-0000-000000000000",
                                       headers=self.headers).status_code, 404)

    def test_disabled_and_snapshot_failure_do_not_change_plan(self):
        with patch("api.core.monitoring.get_client", return_value=None), patch.dict(os.environ, {"REMY_EVALUATION_TOKEN": ""}):
            result = self.create()
            self.assertIsNone(result["trace_id"])
            self.assertIsNone(result["evaluation_id"])
            self.assertEqual(result["status"], "complete")
            self.assertEqual(self.http.get("/api/v1/evaluations/00000000-0000-0000-0000-000000000000").status_code, 503)
        with patch("api.features.plan.service.save_evaluation", side_effect=OSError("disk unavailable")):
            result = self.create()
            self.assertIsNone(result["evaluation_id"])
            self.assertEqual(result["status"], "complete")

    def test_sdk_failure_preserves_plan_and_local_grades(self):
        with patch.object(self.recording, "start_as_current_observation", side_effect=RuntimeError("offline")):
            result = self.create()
            self.assertIsNone(result["trace_id"])
            self.assertEqual(result["status"], "complete")
        result = self.create()
        route = "/api/v1/evaluations/" + result["evaluation_id"] + "/grades"
        grades = {"grades": {"a": 0, "b": 0, "c": 0, "d": 0}}
        with patch.object(self.recording, "create_score", side_effect=RuntimeError("offline")):
            response = self.http.post(route, headers=self.headers, json=grades).json()
        self.assertFalse(response["langfuse_scores_queued"])
        self.assertIsNone(response["metrics"]["pairwise_accuracy"])
        response = self.http.post(route, headers=self.headers, json=grades).json()
        self.assertTrue(response["langfuse_scores_queued"])
        self.assertEqual({score["name"] for score in self.recording.scores}, {"nDCG@3", "Precision@3"})

    def test_real_sdk_parentage_and_score_ingestion_without_network(self):
        import httpx
        from langfuse import Langfuse
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import SimpleSpanProcessor
        from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

        exporter, provider, batches = InMemorySpanExporter(), TracerProvider(), []

        def ingest(request):
            batch = json.loads(request.content)["batch"]
            batches.extend(batch)
            return httpx.Response(200, json={"successes": [{"id": event["id"], "status": 201}
                                                         for event in batch], "errors": []})

        transport_client = httpx.Client(transport=httpx.MockTransport(ingest))
        self.addCleanup(transport_client.close)
        with patch("langfuse._client.resource_manager.LangfuseSpanProcessor",
                   return_value=SimpleSpanProcessor(exporter)), patch.dict(os.environ, {
                       "LANGFUSE_MEDIA_UPLOAD_ENABLED": "false", "LANGFUSE_TRACING_ENABLED": "true"}):
            sdk = Langfuse(public_key="pk-lf-offline-test", secret_key="sk-lf-offline-test",
                          httpx_client=transport_client, tracer_provider=provider, flush_at=1,
                          flush_interval=0.01)
        self.addCleanup(sdk.shutdown)
        with patch("api.core.monitoring.get_client", return_value=sdk):
            result = self.create()
            route = "/api/v1/evaluations/" + result["evaluation_id"] + "/grades"
            response = self.http.post(route, headers=self.headers,
                                      json={"grades": {"a": 2, "b": 3, "c": 0, "d": 1}})
            self.assertEqual(response.status_code, 200, response.text)
            sdk.flush()
            with patch.object(self.service.repository, "fetch_candidates", side_effect=RuntimeError("private database URI")):
                with self.assertRaises(RuntimeError):
                    self.service.generate(self.request)
        spans = exporter.get_finished_spans()
        root = next(span for span in spans if span.name == "meal-plan")
        children = [span for span in spans if span.parent and span.parent.span_id == root.context.span_id]
        self.assertEqual(len(children), 5)
        self.assertEqual(result["trace_id"], format(root.context.trace_id, "032x"))
        self.assertTrue(all(span.context.trace_id == root.context.trace_id for span in children))
        self.assertNotIn("private database URI", repr([(span.attributes, span.events) for span in spans]))
        self.assertEqual({event["body"]["name"] for event in batches}, {"nDCG@3", "Precision@3", "pairwise_accuracy"})
        self.assertTrue(all(event["body"]["traceId"] == result["trace_id"] for event in batches))

    def test_business_failure_is_not_swallowed_or_sent_raw(self):
        with patch.object(self.service.repository, "fetch_candidates", side_effect=RuntimeError("private database URI")):
            with self.assertRaisesRegex(RuntimeError, "private database URI"):
                self.service.generate(self.request)
        self.assertTrue(all(span.updates[-1] == {"level": "ERROR", "status_message": "RuntimeError"}
                            for span in self.recording.spans))
        self.assertNotIn("private database URI", repr([span.updates for span in self.recording.spans]))

    def test_telemetry_update_and_close_failures_are_isolated(self):
        @contextmanager
        def broken_context(**kwargs):
            span = RecordingSpan(kwargs)
            span.update = lambda **updates: (_ for _ in ()).throw(RuntimeError("update failed"))
            yield span
            raise RuntimeError("close failed")
        with patch.object(self.recording, "start_as_current_observation", side_effect=broken_context):
            self.assertEqual(self.create()["status"], "complete")


if __name__ == "__main__":
    unittest.main()
