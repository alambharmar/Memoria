"""Integration tests for Memoria medical hub APIs."""

from io import BytesIO
import json
import os
import sys
import tempfile
import unittest

from docx import Document

# Ensure project root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config

# Use isolated test data dir
_TEST_DIR = tempfile.mkdtemp()
config.DATA_DIR = _TEST_DIR

from app import create_app
import routes.api_routes as api_routes


class TestMedicalHub(unittest.TestCase):
    """Test required medical hub features end-to-end."""

    def setUp(self):
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

        # Stub AI for deterministic tests.
        api_routes.ai_service.chat = lambda message, profile, chat_history: {
            "response": "Test AI reply with paracetamol advice.",
            "source": "test",
        }
        api_routes.ai_service.analyze_document = lambda document_text, profile: {
            "analysis": (
                "1. Patient condition: Mild respiratory infection\n"
                "2. Medicines: Paracetamol\n"
                "3. What each medicine does: Reduces fever\n"
                "4. Instructions: Use as directed"
            ),
            "source": "test",
        }

        self._login()

    def _login(self):
        resp = self.client.post(
            "/login",
            json={
                "username": config.DEFAULT_USER["username"],
                "password": config.DEFAULT_USER["password"],
            },
        )
        self.assertEqual(resp.status_code, 200)

    def test_profile_update(self):
        resp = self.client.post(
            "/profile/update",
            json={
                "name": "Alice",
                "age": "31",
                "allergies": ["aspirin"],
                "conditions": ["asthma"],
                "medications": [{"name": "Vitamin D"}],
                "notes": "Seasonal issues",
            },
        )
        self.assertEqual(resp.status_code, 200)
        payload = resp.get_json()
        self.assertEqual(payload["profile"]["name"], "Alice")
        self.assertIn("aspirin", payload["profile"]["allergies"])

        get_resp = self.client.get("/profile")
        self.assertEqual(get_resp.status_code, 200)
        self.assertEqual(get_resp.get_json()["name"], "Alice")

    def test_symptom_logging_and_history(self):
        add = self.client.post(
            "/symptoms/add",
            json={
                "date": "2026-04-07",
                "symptoms": ["fever", "cough"],
                "severity": "high",
            },
        )
        self.assertEqual(add.status_code, 200)

        add2 = self.client.post(
            "/symptoms/add",
            json={
                "date": "2026-04-08",
                "symptoms": ["fever"],
                "severity": "high",
            },
        )
        self.assertEqual(add2.status_code, 200)
        self.assertTrue(add2.get_json()["alerts"])

        hist = self.client.get("/symptoms/history")
        self.assertEqual(hist.status_code, 200)
        self.assertGreaterEqual(len(hist.get_json()["history"]), 2)

    def test_chat_with_memory(self):
        for i in range(12):
            resp = self.client.post("/chat", json={"message": f"msg {i}"})
            self.assertEqual(resp.status_code, 200)

        data = resp.get_json()
        self.assertIn("response", data)
        self.assertLessEqual(len(data.get("history", [])), 10)

    def test_document_upload_docx(self):
        doc = Document()
        doc.add_paragraph("Patient has mild fever. Prescribed paracetamol.")
        buf = BytesIO()
        doc.save(buf)
        buf.seek(0)

        resp = self.client.post(
            "/upload",
            data={"file": (buf, "report.docx")},
            content_type="multipart/form-data",
        )
        self.assertEqual(resp.status_code, 200)
        payload = resp.get_json()
        self.assertIn("document", payload)
        self.assertIn("Patient condition", payload["document"]["analysis"])

    def test_timeline_endpoint(self):
        self.client.post("/chat", json={"message": "I have cough"})
        self.client.post(
            "/symptoms/add",
            json={"symptoms": ["cough"], "severity": "low"},
        )

        tl = self.client.get("/timeline")
        self.assertEqual(tl.status_code, 200)
        self.assertIn("timeline", tl.get_json())


if __name__ == "__main__":
    unittest.main()
