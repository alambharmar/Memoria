"""Tests for the Memoria AI engine and health data models."""

import json
import os
import sys
import tempfile
import unittest

# Ensure the project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Override DATA_DIR before importing modules that use it
import config

_test_dir = tempfile.mkdtemp()
config.DATA_DIR = _test_dir


from ai.engine import AIEngine
from ai.health_prompt import SYSTEM_PROMPT, build_context_prompt
from ai.memory import ConversationMemory
from models.health_data import HealthProfile, SymptomTracker, VitalsTracker


class TestHealthPrompt(unittest.TestCase):
    """Test health prompt generation."""

    def test_system_prompt_exists(self):
        self.assertIn("Memoria", SYSTEM_PROMPT)
        self.assertIn("NOT a doctor", SYSTEM_PROMPT)

    def test_build_context_prompt_empty(self):
        prompt = build_context_prompt({}, [])
        self.assertIn("Memoria", prompt)

    def test_build_context_prompt_with_profile(self):
        profile = {
            "name": "Test User",
            "age": 30,
            "conditions": ["Asthma"],
            "medications": [{"name": "Inhaler", "dosage": "2 puffs"}],
            "allergies": ["Peanuts"],
        }
        prompt = build_context_prompt(profile, [])
        self.assertIn("Test User", prompt)
        self.assertIn("Asthma", prompt)
        self.assertIn("Inhaler", prompt)
        self.assertIn("Peanuts", prompt)

    def test_build_context_prompt_with_memories(self):
        memories = ["User mentioned headaches", "User takes aspirin"]
        prompt = build_context_prompt({}, memories)
        self.assertIn("headaches", prompt)
        self.assertIn("aspirin", prompt)


class TestConversationMemory(unittest.TestCase):
    """Test conversation memory management."""

    def setUp(self):
        self.memory = ConversationMemory("test_memory")

    def tearDown(self):
        if os.path.exists(self.memory.memory_file):
            os.remove(self.memory.memory_file)

    def test_add_and_get_messages(self):
        self.memory.add_message("user", "Hello")
        self.memory.add_message("assistant", "Hi there!")
        messages = self.memory.get_recent_messages()
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["role"], "user")
        self.assertEqual(messages[1]["role"], "assistant")

    def test_conversation_for_ollama(self):
        self.memory.add_message("user", "Test message")
        ollama_msgs = self.memory.get_conversation_for_ollama()
        self.assertEqual(len(ollama_msgs), 1)
        self.assertEqual(ollama_msgs[0]["role"], "user")
        self.assertEqual(ollama_msgs[0]["content"], "Test message")

    def test_health_insights(self):
        self.memory.add_health_insight("User has headaches")
        insights = self.memory.get_recent_insights()
        self.assertEqual(len(insights), 1)
        self.assertIn("headaches", insights[0])

    def test_clear(self):
        self.memory.add_message("user", "Hello")
        self.memory.add_health_insight("Test")
        self.memory.clear()
        self.assertEqual(len(self.memory.conversations), 0)
        self.assertEqual(len(self.memory.health_insights), 0)

    def test_persistence(self):
        self.memory.add_message("user", "Persistent message")
        # Create a new instance to test loading from disk
        memory2 = ConversationMemory("test_memory")
        messages = memory2.get_recent_messages()
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["content"], "Persistent message")


class TestHealthProfile(unittest.TestCase):
    """Test health profile model."""

    def setUp(self):
        self.profile = HealthProfile("test_profile")

    def tearDown(self):
        if os.path.exists(self.profile.profile_file):
            os.remove(self.profile.profile_file)

    def test_default_profile(self):
        data = self.profile.to_dict()
        self.assertEqual(data["name"], "")
        self.assertIsNone(data["age"])
        self.assertEqual(data["conditions"], [])

    def test_update_profile(self):
        self.profile.update(name="John", age=35)
        self.assertEqual(self.profile.data["name"], "John")
        self.assertEqual(self.profile.data["age"], 35)

    def test_medications(self):
        med = self.profile.add_medication("Aspirin", dosage="100mg", frequency="Daily")
        self.assertEqual(med["name"], "Aspirin")
        self.assertEqual(len(self.profile.data["medications"]), 1)

        self.profile.remove_medication("Aspirin")
        self.assertEqual(len(self.profile.data["medications"]), 0)

    def test_conditions(self):
        self.profile.add_condition("Diabetes")
        self.assertIn("Diabetes", self.profile.data["conditions"])

        # No duplicates
        self.profile.add_condition("Diabetes")
        self.assertEqual(self.profile.data["conditions"].count("Diabetes"), 1)

        self.profile.remove_condition("Diabetes")
        self.assertNotIn("Diabetes", self.profile.data["conditions"])

    def test_allergies(self):
        self.profile.add_allergy("Penicillin")
        self.assertIn("Penicillin", self.profile.data["allergies"])

        self.profile.remove_allergy("Penicillin")
        self.assertNotIn("Penicillin", self.profile.data["allergies"])

    def test_persistence(self):
        self.profile.update(name="Persist Test")
        profile2 = HealthProfile("test_profile")
        self.assertEqual(profile2.data["name"], "Persist Test")


class TestSymptomTracker(unittest.TestCase):
    """Test symptom tracking."""

    def setUp(self):
        self.tracker = SymptomTracker("test_symptoms")

    def tearDown(self):
        if os.path.exists(self.tracker.symptoms_file):
            os.remove(self.tracker.symptoms_file)

    def test_log_symptom(self):
        entry = self.tracker.log_symptom("Headache", severity=7, notes="After work")
        self.assertEqual(entry["symptom"], "Headache")
        self.assertEqual(entry["severity"], 7)

    def test_severity_clamping(self):
        entry = self.tracker.log_symptom("Test", severity=15)
        self.assertEqual(entry["severity"], 10)

        entry = self.tracker.log_symptom("Test", severity=-5)
        self.assertEqual(entry["severity"], 1)

    def test_get_entries(self):
        self.tracker.log_symptom("Headache")
        self.tracker.log_symptom("Nausea")
        entries = self.tracker.get_entries()
        self.assertEqual(len(entries), 2)

    def test_get_by_symptom(self):
        self.tracker.log_symptom("Headache")
        self.tracker.log_symptom("Nausea")
        self.tracker.log_symptom("Headache")
        results = self.tracker.get_by_symptom("Headache")
        self.assertEqual(len(results), 2)

    def test_delete_entry(self):
        self.tracker.log_symptom("Headache")
        self.assertTrue(self.tracker.delete_entry(0))
        self.assertEqual(len(self.tracker.entries), 0)

    def test_delete_invalid_index(self):
        self.assertFalse(self.tracker.delete_entry(999))


class TestVitalsTracker(unittest.TestCase):
    """Test vitals tracking."""

    def setUp(self):
        self.tracker = VitalsTracker("test_vitals")

    def tearDown(self):
        if os.path.exists(self.tracker.vitals_file):
            os.remove(self.tracker.vitals_file)

    def test_log_vitals(self):
        entry = self.tracker.log_vitals("Blood Pressure", "120/80", unit="mmHg")
        self.assertEqual(entry["type"], "Blood Pressure")
        self.assertEqual(entry["value"], "120/80")

    def test_filter_by_type(self):
        self.tracker.log_vitals("Blood Pressure", "120/80")
        self.tracker.log_vitals("Heart Rate", "72")
        self.tracker.log_vitals("Blood Pressure", "118/75")

        bp = self.tracker.get_entries(vital_type="Blood Pressure")
        self.assertEqual(len(bp), 2)

        hr = self.tracker.get_entries(vital_type="Heart Rate")
        self.assertEqual(len(hr), 1)

    def test_delete_entry(self):
        self.tracker.log_vitals("Heart Rate", "72")
        self.assertTrue(self.tracker.delete_entry(0))
        self.assertEqual(len(self.tracker.entries), 0)


class TestAIEngine(unittest.TestCase):
    """Test AI engine (without actual Ollama connection)."""

    def setUp(self):
        self.engine = AIEngine("test_engine")
        self.engine._ollama_available = False  # Force fallback mode

    def tearDown(self):
        mem_file = self.engine.memory.memory_file
        if os.path.exists(mem_file):
            os.remove(mem_file)

    def test_fallback_greeting(self):
        result = self.engine.chat("Hello!")
        self.assertIn("response", result)
        self.assertEqual(result["status"], "fallback")
        self.assertIn("Memoria", result["response"])

    def test_fallback_emergency(self):
        result = self.engine.chat("I think I'm having a heart attack")
        self.assertIn("911", result["response"])

    def test_fallback_pain(self):
        result = self.engine.chat("I have a bad headache")
        self.assertIn("hydrated", result["response"])

    def test_fallback_medication(self):
        result = self.engine.chat("What about my medication?")
        self.assertIn("medication", result["response"].lower())

    def test_set_health_profile(self):
        self.engine.set_health_profile({"name": "Test", "conditions": ["Asthma"]})
        self.assertEqual(self.engine._health_profile["name"], "Test")

    def test_conversation_memory_stored(self):
        self.engine.chat("Hello")
        messages = self.engine.memory.get_recent_messages()
        # Should have user message + assistant response
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["role"], "user")
        self.assertEqual(messages[1]["role"], "assistant")


class TestFlaskApp(unittest.TestCase):
    """Test Flask application routes."""

    def setUp(self):
        from app import app
        app.config["TESTING"] = True
        self.client = app.test_client()
        # Login
        self.client.post("/login", data={
            "username": "admin",
            "password": "memoria123",
        })

    def test_login_page(self):
        # Fresh client without login
        from app import app
        client = app.test_client()
        resp = client.get("/login")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Memoria", resp.data)

    def test_login_success(self):
        from app import app
        client = app.test_client()
        resp = client.post("/login", data={
            "username": "admin",
            "password": "memoria123",
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

    def test_login_failure(self):
        from app import app
        client = app.test_client()
        resp = client.post("/login", data={
            "username": "wrong",
            "password": "wrong",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Invalid", resp.data)

    def test_dashboard_requires_login(self):
        from app import app
        client = app.test_client()
        resp = client.get("/")
        self.assertEqual(resp.status_code, 302)

    def test_dashboard(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)

    def test_chat_page(self):
        resp = self.client.get("/chat")
        self.assertEqual(resp.status_code, 200)

    def test_profile_page(self):
        resp = self.client.get("/profile")
        self.assertEqual(resp.status_code, 200)

    def test_symptoms_page(self):
        resp = self.client.get("/symptoms")
        self.assertEqual(resp.status_code, 200)

    def test_vitals_page(self):
        resp = self.client.get("/vitals")
        self.assertEqual(resp.status_code, 200)

    def test_api_chat(self):
        resp = self.client.post("/api/chat", json={"message": "Hello"})
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("response", data)

    def test_api_chat_empty(self):
        resp = self.client.post("/api/chat", json={"message": ""})
        self.assertEqual(resp.status_code, 400)

    def test_api_status(self):
        resp = self.client.get("/api/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("ollama_available", data)

    def test_api_profile(self):
        # GET
        resp = self.client.get("/api/profile")
        self.assertEqual(resp.status_code, 200)

        # POST
        resp = self.client.post("/api/profile", json={"name": "Test User"})
        self.assertEqual(resp.status_code, 200)

    def test_api_symptoms_crud(self):
        # POST
        resp = self.client.post("/api/symptoms", json={
            "symptom": "Headache",
            "severity": 7,
        })
        self.assertEqual(resp.status_code, 200)

        # GET
        resp = self.client.get("/api/symptoms")
        self.assertEqual(resp.status_code, 200)

    def test_api_vitals_crud(self):
        # POST
        resp = self.client.post("/api/vitals", json={
            "type": "Heart Rate",
            "value": "72",
            "unit": "bpm",
        })
        self.assertEqual(resp.status_code, 200)

        # GET
        resp = self.client.get("/api/vitals")
        self.assertEqual(resp.status_code, 200)

    def test_api_clear_memory(self):
        resp = self.client.post("/api/memory/clear")
        self.assertEqual(resp.status_code, 200)

    def test_logout(self):
        resp = self.client.get("/logout", follow_redirects=True)
        self.assertEqual(resp.status_code, 200)


if __name__ == "__main__":
    unittest.main()
