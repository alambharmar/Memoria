"""Conversation memory management for the Memoria AI."""

import json
import os
from datetime import datetime

from config import DATA_DIR


class ConversationMemory:
    """Manages conversation history and extracted health insights."""

    def __init__(self, user_id="default"):
        self.user_id = user_id
        self.memory_file = os.path.join(DATA_DIR, f"memory_{user_id}.json")
        self.conversations = []
        self.health_insights = []
        self.symptom_history = []
        self._load()

    def _load(self):
        """Load memory from disk."""
        if os.path.exists(self.memory_file):
            with open(self.memory_file, "r") as f:
                data = json.load(f)
                self.conversations = data.get("conversations", [])
                self.health_insights = data.get("health_insights", [])
                self.symptom_history = data.get("symptom_history", [])

    def _save(self):
        """Persist memory to disk."""
        data = {
            "conversations": self.conversations,
            "health_insights": self.health_insights,
            "symptom_history": self.symptom_history,
        }
        with open(self.memory_file, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def add_message(self, role, content):
        """Add a message to conversation history."""
        self.conversations.append(
            {"role": role, "content": content, "timestamp": datetime.now().isoformat()}
        )
        # Keep only last 100 messages to manage memory
        if len(self.conversations) > 100:
            self.conversations = self.conversations[-100:]
        self._save()

    def add_health_insight(self, insight):
        """Store an extracted health insight."""
        self.health_insights.append(
            {"insight": insight, "timestamp": datetime.now().isoformat()}
        )
        self._save()

    def add_symptom_entry(self, symptom, severity, details=None):
        """Store structured symptom history for future context reuse."""
        if not symptom:
            return
        self.symptom_history.append(
            {
                "symptom": symptom,
                "severity": severity,
                "details": details or "",
                "timestamp": datetime.now().isoformat(),
            }
        )
        if len(self.symptom_history) > 50:
            self.symptom_history = self.symptom_history[-50:]
        self._save()

    def find_recent_similar_symptom(self, symptom):
        """Return a short natural-language note for similar recent symptom history."""
        if not symptom:
            return None
        for entry in reversed(self.symptom_history):
            if entry.get("symptom") == symptom:
                try:
                    ts = datetime.fromisoformat(entry["timestamp"])
                    days_ago = max((datetime.now() - ts).days, 0)
                except Exception:
                    days_ago = None

                if days_ago is None:
                    return f"You mentioned similar {symptom} previously."
                if days_ago == 0:
                    return f"You mentioned similar {symptom} earlier today."
                if days_ago == 1:
                    return f"You mentioned similar {symptom} yesterday."
                return f"You mentioned similar {symptom} about {days_ago} days ago."
        return None

    def get_recent_messages(self, count=20):
        """Get recent conversation messages for context."""
        return self.conversations[-count:]

    def get_recent_insights(self, count=10):
        """Get recent health insights."""
        return [i["insight"] for i in self.health_insights[-count:]]

    def get_conversation_messages(self, count=10):
        """Format recent conversation history for chat APIs."""
        messages = []
        for msg in self.conversations[-count:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
        return messages

    def clear(self):
        """Clear all conversation memory."""
        self.conversations = []
        self.health_insights = []
        self.symptom_history = []
        self._save()
