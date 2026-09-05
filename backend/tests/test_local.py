"""Local unit tests for the PathFinder lambda handler.

Runs without AWS credentials by stubbing ``boto3``. Usage:
    python -m pytest tests/test_local.py
    # or
    python tests/test_local.py
"""

import json
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "lambda"))

import recommender  # noqa: E402

_retrieve_payload = {"output": {"text": "Bedrock KB answer"}}
_converse_payload = {
    "output": {"message": {"content": [{"text": '{"primary_track": "AI & Machine Learning", "core_courses": ["x"], "starter_projects": ["y"], "career_paths": ["z"], "alternative_tracks": [], "top_tracks": [], "recommended": true}'}]}}
}
_fake_calls = []


class _FakeClient:
    def retrieve_and_generate(self, **kwargs):
        _fake_calls.append(kwargs)
        return _retrieve_payload

    def converse(self, **kwargs):
        _fake_calls.append(kwargs)
        return _converse_payload


class _FakeSession:
    def client(self, *args, **kwargs):
        return _FakeClient()


_fake_boto3 = types.SimpleNamespace(client=lambda *a, **k: _FakeClient())
sys.modules["boto3"] = _fake_boto3

import lambda_handler  # noqa: E402


class TestRecommender(unittest.TestCase):
    def setUp(self):
        _fake_calls.clear()
        lambda_handler.KNOWLEDGE_BASE_ID = ""
        lambda_handler.bedrock_runtime = None
        lambda_handler.bedrock_agent_runtime = _FakeClient()

    def test_no_kb_returns_roadmap(self):
        lambda_handler.KNOWLEDGE_BASE_ID = ""
        event = {
            "body": json.dumps(
                {
                    "interests": ["AI", "machine learning"],
                    "strengths": ["mathematics", "logic"],
                    "ambitions": ["Data Scientist"],
                }
            )
        }
        response = lambda_handler.lambda_handler(event, {})
        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(response["headers"]["Access-Control-Allow-Origin"], "*")
        body = json.loads(response["body"])
        rec = body["recommendation"]
        self.assertEqual(rec["source"], "built-in-recommender")
        self.assertEqual(rec["roadmap"]["primary_track"], "AI & Machine Learning")
        self.assertTrue(rec["roadmap"]["core_courses"])
        self.assertTrue(rec["roadmap"]["starter_projects"])

    def test_kb_path_calls_bedrock(self):
        lambda_handler.KNOWLEDGE_BASE_ID = "kb-123"
        event = {"body": json.dumps({"prompt": "hello"})}
        response = lambda_handler.lambda_handler(event, {})
        self.assertTrue(_fake_calls, "retrieve_and_generate should be called")
        self.assertEqual(
            _fake_calls[0]["retrieveAndGenerateConfiguration"]["knowledgeBaseConfiguration"][
                "knowledgeBaseId"
            ],
            "kb-123",
        )
        body = json.loads(response["body"])
        self.assertEqual(body["recommendation"], "Bedrock KB answer")

    def test_empty_body_defaults(self):
        lambda_handler.KNOWLEDGE_BASE_ID = ""
        response = lambda_handler.lambda_handler({"body": "{}"}, {})
        body = json.loads(response["body"])
        self.assertFalse(body["recommendation"]["roadmap"]["recommended"])

    def test_model_path_uses_converse(self):
        lambda_handler.KNOWLEDGE_BASE_ID = ""
        lambda_handler._has_aws_credentials = lambda: True
        lambda_handler.bedrock_runtime = _FakeClient()
        event = {
            "body": json.dumps(
                {
                    "interests": ["AI"],
                    "strengths": ["mathematics"],
                    "ambitions": ["AI Researcher"],
                }
            )
        }
        response = lambda_handler.lambda_handler(event, {})
        converse_calls = [c for c in _fake_calls if "modelId" in c]
        self.assertTrue(converse_calls, "converse should be called")
        body = json.loads(response["body"])
        self.assertTrue(body["recommendation"]["source"].startswith("bedrock:"))
        self.assertEqual(
            body["recommendation"]["roadmap"]["primary_track"], "AI & Machine Learning"
        )

    def test_model_fallback_to_next_bedrock_model(self):
        class _FlakyClient(_FakeClient):
            def __init__(self):
                self.attempts = 0

            def converse(self, **kwargs):
                self.attempts += 1
                if self.attempts == 1:
                    raise RuntimeError("model-not-available")
                return _converse_payload

        lambda_handler.KNOWLEDGE_BASE_ID = ""
        lambda_handler._has_aws_credentials = lambda: True
        client = _FlakyClient()
        lambda_handler.bedrock_runtime = client
        event = {
            "body": json.dumps(
                {
                    "interests": ["AI"],
                    "strengths": ["mathematics"],
                    "ambitions": ["AI Researcher"],
                }
            )
        }
        response = lambda_handler.lambda_handler(event, {})
        self.assertEqual(client.attempts, 2, "should try primary then fallback model")
        body = json.loads(response["body"])
        self.assertTrue(body["recommendation"]["source"].startswith("bedrock:"))
        self.assertEqual(
            body["recommendation"]["roadmap"]["primary_track"], "AI & Machine Learning"
        )

    def test_all_models_fail_falls_back_to_recommender(self):
        class _FailingClient(_FakeClient):
            def converse(self, **kwargs):
                raise RuntimeError("all-models-down")

        lambda_handler.KNOWLEDGE_BASE_ID = ""
        lambda_handler._has_aws_credentials = lambda: True
        lambda_handler.bedrock_runtime = _FailingClient()
        event = {
            "body": json.dumps(
                {
                    "interests": ["AI"],
                    "strengths": ["mathematics"],
                    "ambitions": ["AI Researcher"],
                }
            )
        }
        response = lambda_handler.lambda_handler(event, {})
        body = json.loads(response["body"])
        self.assertEqual(body["recommendation"]["source"], "built-in-recommender")
        self.assertIn("all-models-down", body["recommendation"]["model_error"])
        self.assertEqual(
            body["recommendation"]["roadmap"]["primary_track"], "AI & Machine Learning"
        )

    def test_model_path_non_json_text(self):
        lambda_handler.KNOWLEDGE_BASE_ID = ""
        lambda_handler._has_aws_credentials = lambda: True
        client = _FakeClient()
        client.converse = lambda **kw: {
            "output": {"message": {"content": [{"text": "Some prose answer"}]}}
        }
        lambda_handler.bedrock_runtime = client
        event = {"body": json.dumps({"interests": ["web development"]})}
        response = lambda_handler.lambda_handler(event, {})
        body = json.loads(response["body"])
        self.assertEqual(body["recommendation"]["roadmap"], "Some prose answer")

    def test_cybersecurity_scoring(self):
        roadmap = recommender.build_roadmap(
            ["cybersecurity", "networking"],
            ["logic", "systems"],
            ["Security Engineer"],
        )
        self.assertEqual(roadmap["primary_track"], "Cybersecurity & Networking")


if __name__ == "__main__":
    unittest.main(verbosity=2)
