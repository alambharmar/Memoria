"""Health data models for Memoria - manages user health information locally."""

import json
import os
from datetime import datetime

from config import DATA_DIR


class HealthProfile:
    """Manages a user's health profile data."""

    def __init__(self, user_id="default"):
        self.user_id = user_id
        self.profile_file = os.path.join(DATA_DIR, f"profile_{user_id}.json")
        self.data = {
            "name": "",
            "age": None,
            "gender": "",
            "height": "",
            "weight": "",
            "blood_type": "",
            "conditions": [],
            "allergies": [],
            "medications": [],
            "emergency_contact": "",
        }
        self._load()

    def _load(self):
        if os.path.exists(self.profile_file):
            with open(self.profile_file, "r") as f:
                stored = json.load(f)
                self.data.update(stored)

    def _save(self):
        with open(self.profile_file, "w") as f:
            json.dump(self.data, f, indent=2, default=str)

    def update(self, **kwargs):
        """Update profile fields."""
        for key, value in kwargs.items():
            if key in self.data:
                self.data[key] = value
        self._save()

    def add_medication(self, name, dosage="", frequency="", notes=""):
        """Add a medication to the profile."""
        med = {
            "name": name,
            "dosage": dosage,
            "frequency": frequency,
            "notes": notes,
            "added": datetime.now().isoformat(),
        }
        self.data["medications"].append(med)
        self._save()
        return med

    def remove_medication(self, name):
        """Remove a medication by name."""
        self.data["medications"] = [
            m for m in self.data["medications"] if m["name"] != name
        ]
        self._save()

    def add_condition(self, condition):
        """Add a health condition."""
        if condition not in self.data["conditions"]:
            self.data["conditions"].append(condition)
            self._save()

    def remove_condition(self, condition):
        """Remove a health condition."""
        self.data["conditions"] = [
            c for c in self.data["conditions"] if c != condition
        ]
        self._save()

    def add_allergy(self, allergy):
        """Add an allergy."""
        if allergy not in self.data["allergies"]:
            self.data["allergies"].append(allergy)
            self._save()

    def remove_allergy(self, allergy):
        """Remove an allergy."""
        self.data["allergies"] = [a for a in self.data["allergies"] if a != allergy]
        self._save()

    def to_dict(self):
        return dict(self.data)


class SymptomTracker:
    """Tracks symptoms over time."""

    def __init__(self, user_id="default"):
        self.user_id = user_id
        self.symptoms_file = os.path.join(DATA_DIR, f"symptoms_{user_id}.json")
        self.entries = []
        self._load()

    def _load(self):
        if os.path.exists(self.symptoms_file):
            with open(self.symptoms_file, "r") as f:
                self.entries = json.load(f)

    def _save(self):
        with open(self.symptoms_file, "w") as f:
            json.dump(self.entries, f, indent=2, default=str)

    def log_symptom(self, symptom, severity=5, notes=""):
        """Log a symptom entry (severity 1-10)."""
        entry = {
            "symptom": symptom,
            "severity": max(1, min(10, severity)),
            "notes": notes,
            "timestamp": datetime.now().isoformat(),
        }
        self.entries.append(entry)
        self._save()
        return entry

    def get_entries(self, limit=50):
        """Get recent symptom entries."""
        return self.entries[-limit:]

    def get_by_symptom(self, symptom):
        """Get entries for a specific symptom."""
        return [e for e in self.entries if e["symptom"].lower() == symptom.lower()]

    def delete_entry(self, index):
        """Delete a symptom entry by index."""
        if 0 <= index < len(self.entries):
            self.entries.pop(index)
            self._save()
            return True
        return False


class VitalsTracker:
    """Tracks vitals like blood pressure, heart rate, temperature, etc."""

    def __init__(self, user_id="default"):
        self.user_id = user_id
        self.vitals_file = os.path.join(DATA_DIR, f"vitals_{user_id}.json")
        self.entries = []
        self._load()

    def _load(self):
        if os.path.exists(self.vitals_file):
            with open(self.vitals_file, "r") as f:
                self.entries = json.load(f)

    def _save(self):
        with open(self.vitals_file, "w") as f:
            json.dump(self.entries, f, indent=2, default=str)

    def log_vitals(self, vital_type, value, unit="", notes=""):
        """Log a vitals reading."""
        entry = {
            "type": vital_type,
            "value": value,
            "unit": unit,
            "notes": notes,
            "timestamp": datetime.now().isoformat(),
        }
        self.entries.append(entry)
        self._save()
        return entry

    def get_entries(self, vital_type=None, limit=50):
        """Get recent vitals, optionally filtered by type."""
        if vital_type:
            filtered = [
                e for e in self.entries if e["type"].lower() == vital_type.lower()
            ]
            return filtered[-limit:]
        return self.entries[-limit:]

    def delete_entry(self, index):
        """Delete a vitals entry by index."""
        if 0 <= index < len(self.entries):
            self.entries.pop(index)
            self._save()
            return True
        return False
