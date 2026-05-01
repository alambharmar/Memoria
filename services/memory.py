"""Persistent storage and memory utilities for Memoria medical hub."""

import json
import os
from datetime import datetime, timezone
from threading import Lock

import config


USERS_FILE = os.path.join(config.DATA_DIR, "users.json")
RECORDS_FILE = os.path.join(config.DATA_DIR, "medical_records.json")


DEFAULT_PROFILE = {
    "name": "",
    "age": "",
    "allergies": [],
    "conditions": [],
    "medications": [],
    "notes": "",
}


class MemoryStore:
    """Simple JSON-backed storage with per-user medical records."""

    def __init__(self):
        self._lock = Lock()
        self._ensure_files()

    def _ensure_files(self):
        os.makedirs(config.DATA_DIR, exist_ok=True)
        if not os.path.exists(USERS_FILE):
            with open(USERS_FILE, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        config.DEFAULT_USER["username"]: {
                            "password": config.DEFAULT_USER["password"],
                            "profile": dict(DEFAULT_PROFILE),
                        }
                    },
                    f,
                    indent=2,
                )
        if not os.path.exists(RECORDS_FILE):
            with open(RECORDS_FILE, "w", encoding="utf-8") as f:
                json.dump({}, f, indent=2)

    def _read_json(self, path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}

    def _write_json(self, path, data):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def _now(self):
        return datetime.now(timezone.utc).isoformat()

    def _default_record(self):
        return {
            "symptoms": [],
            "chat_history": [],
            "documents": [],
            "chat_summaries": [],
            "alerts": [],
        }

    def ensure_user(self, username):
        with self._lock:
            users = self._read_json(USERS_FILE)
            if username not in users:
                users[username] = {
                    "password": "",
                    "profile": dict(DEFAULT_PROFILE),
                }
                self._write_json(USERS_FILE, users)

            records = self._read_json(RECORDS_FILE)
            if username not in records:
                records[username] = self._default_record()
                self._write_json(RECORDS_FILE, records)

    def verify_user(self, username, password):
        users = self._read_json(USERS_FILE)
        row = users.get(username)
        return bool(row and row.get("password") == password)

    def get_profile(self, username):
        self.ensure_user(username)
        users = self._read_json(USERS_FILE)
        row = users.get(username, {})
        profile = row.get("profile", {})
        merged = dict(DEFAULT_PROFILE)
        merged.update(profile)
        return merged

    def update_profile(self, username, payload):
        self.ensure_user(username)
        with self._lock:
            users = self._read_json(USERS_FILE)
            profile = users[username].get("profile", dict(DEFAULT_PROFILE))
            for key in DEFAULT_PROFILE:
                if key in payload:
                    profile[key] = payload[key]
            users[username]["profile"] = profile
            self._write_json(USERS_FILE, users)
            return profile

    def add_medication(self, username, medication):
        profile = self.get_profile(username)
        meds = profile.get("medications", [])
        meds.append(medication)
        profile["medications"] = meds
        return self.update_profile(username, {"medications": meds})

    def add_symptom(self, username, symptom_entry):
        self.ensure_user(username)
        if "date" not in symptom_entry or not symptom_entry["date"]:
            symptom_entry["date"] = self._now()

        with self._lock:
            records = self._read_json(RECORDS_FILE)
            records[username]["symptoms"].append(symptom_entry)
            if len(records[username]["symptoms"]) > 200:
                records[username]["symptoms"] = records[username]["symptoms"][-200:]
            self._write_json(RECORDS_FILE, records)

        if self._needs_smart_alert(username):
            self._add_alert(username, "You should consult a doctor")

    def symptom_history(self, username):
        self.ensure_user(username)
        records = self._read_json(RECORDS_FILE)
        return records.get(username, {}).get("symptoms", [])

    def add_chat_message(self, username, role, content):
        self.ensure_user(username)
        msg = {
            "role": role,
            "content": content,
            "timestamp": self._now(),
        }
        with self._lock:
            records = self._read_json(RECORDS_FILE)
            history = records[username]["chat_history"]
            history.append(msg)
            records[username]["chat_history"] = history[-10:]

            if role == "assistant":
                records[username]["chat_summaries"].append(
                    {
                        "date": msg["timestamp"],
                        "summary": content[:180],
                    }
                )
                records[username]["chat_summaries"] = records[username]["chat_summaries"][-25:]

            self._write_json(RECORDS_FILE, records)

    def chat_history(self, username):
        self.ensure_user(username)
        records = self._read_json(RECORDS_FILE)
        return records.get(username, {}).get("chat_history", [])

    def clear_chat_history(self, username):
        self.ensure_user(username)
        with self._lock:
            records = self._read_json(RECORDS_FILE)
            records[username]["chat_history"] = []
            records[username]["chat_summaries"] = []
            self._write_json(RECORDS_FILE, records)

    def add_document_analysis(self, username, analysis_row):
        self.ensure_user(username)
        row = dict(analysis_row)
        row.setdefault("date", self._now())
        with self._lock:
            records = self._read_json(RECORDS_FILE)
            records[username]["documents"].append(row)
            records[username]["documents"] = records[username]["documents"][-50:]
            self._write_json(RECORDS_FILE, records)

    def get_documents(self, username):
        self.ensure_user(username)
        records = self._read_json(RECORDS_FILE)
        return records.get(username, {}).get("documents", [])

    def _needs_smart_alert(self, username):
        history = self.symptom_history(username)
        if len(history) < 2:
            return False
        last = history[-5:]
        high_count = sum(1 for item in last if (item.get("severity") or "").lower() == "high")
        return high_count >= 2

    def _add_alert(self, username, message):
        with self._lock:
            records = self._read_json(RECORDS_FILE)
            alerts = records[username].get("alerts", [])
            if alerts and alerts[-1].get("message") == message:
                return
            alerts.append({"date": self._now(), "message": message})
            records[username]["alerts"] = alerts[-20:]
            self._write_json(RECORDS_FILE, records)

    def get_alerts(self, username):
        self.ensure_user(username)
        records = self._read_json(RECORDS_FILE)
        return records.get(username, {}).get("alerts", [])

    def timeline(self, username):
        self.ensure_user(username)
        records = self._read_json(RECORDS_FILE).get(username, self._default_record())
        timeline_rows = []

        for s in records.get("symptoms", []):
            timeline_rows.append(
                {
                    "type": "symptom",
                    "date": s.get("date", ""),
                    "data": s,
                }
            )

        for d in records.get("documents", []):
            timeline_rows.append(
                {
                    "type": "document",
                    "date": d.get("date", ""),
                    "data": d,
                }
            )

        for c in records.get("chat_summaries", []):
            timeline_rows.append(
                {
                    "type": "chat_summary",
                    "date": c.get("date", ""),
                    "data": c,
                }
            )

        timeline_rows.sort(key=lambda x: x.get("date", ""), reverse=True)
        return timeline_rows[:100]
