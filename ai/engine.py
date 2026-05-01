"""AI Engine for Memoria using local Ollama."""

import json
import re
import requests

import config
from ai.health_prompt import build_context_prompt
from ai.memory import ConversationMemory
from ai.symptom_checker import check_symptoms
from models.health_data import HealthProfile, SymptomTracker, VitalsTracker


SAFETY_DISCLAIMER = "This is not medical advice. Please consult a healthcare professional."
URGENT_RESPONSE = "⚠️ URGENT: Seek immediate medical attention"
TRAINING_DATA_PATH = f"{config.BASE_DIR}/data/training_data.json"


class _OllamaAdapter:
    """Small adapter to provide ollama.generate-like interface via HTTP API."""

    def __init__(self, base_url):
        self.base_url = base_url

    def generate(self, model, prompt):
        resp = requests.post(
            self.base_url,
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=30,
        )
        data = resp.json()
        return {"response": data.get("response", "")}


ollama = _OllamaAdapter(config.OLLAMA_URL)


def load_examples():
    """Load synthetic prompt-training examples from disk."""
    try:
        with open(TRAINING_DATA_PATH, "r") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
    except Exception:
        pass
    return []


import math
from collections import Counter

class BM25:
    """Lightweight BM25 Okapi implementation for fast in-memory example retrieval."""
    def __init__(self, corpus):
        self.corpus_size = len(corpus)
        self.avgdl = sum(len(doc) for doc in corpus) / self.corpus_size if self.corpus_size else 0
        self.doc_freqs = []
        self.idf = {}
        self.doc_len = []
        
        df = {}
        for doc in corpus:
            self.doc_len.append(len(doc))
            frequencies = Counter(doc)
            self.doc_freqs.append(frequencies)
            for word in frequencies.keys():
                df[word] = df.get(word, 0) + 1
                
        for word, freq in df.items():
            self.idf[word] = math.log(1 + (self.corpus_size - freq + 0.5) / (freq + 0.5))
            
    def get_scores(self, query):
        scores = [0] * self.corpus_size
        for q in query:
            if q not in self.idf:
                continue
            idf = self.idf[q]
            for i, doc_freq in enumerate(self.doc_freqs):
                freq = doc_freq.get(q, 0)
                if freq == 0:
                    continue
                # k1=1.5, b=0.75 are standard BM25 defaults
                numerator = freq * (1.5 + 1)
                denominator = freq + 1.5 * (1 - 0.75 + 0.75 * (self.doc_len[i] / (self.avgdl or 1)))
                scores[i] += idf * (numerator / denominator)
        return scores

def _tokenize(text):
    return [t for t in re.findall(r"[a-z0-9]+", (text or "").lower())]

_cached_examples = None
_cached_bm25 = None

def get_relevant_examples(user_input, top_n=5):
    """Select top examples using BM25 scoring."""
    global _cached_examples, _cached_bm25
    
    if _cached_examples is None:
        _cached_examples = load_examples()
        corpus = [_tokenize(ex.get("input", "")) for ex in _cached_examples]
        if corpus:
            _cached_bm25 = BM25(corpus)
            
    if not _cached_examples or not _cached_bm25:
        return []
        
    query_tokens = _tokenize(user_input)
    if not query_tokens:
        return _cached_examples[:top_n]
        
    scores = _cached_bm25.get_scores(query_tokens)
    scored = [(scores[i], ex) for i, ex in enumerate(_cached_examples) if scores[i] > 0]
    scored.sort(key=lambda x: x[0], reverse=True)
    
    top = [ex for _, ex in scored[:top_n]]
    
    # Fill remaining if needed
    if len(top) < top_n:
        used_ids = {id(e) for e in top}
        for ex in _cached_examples:
            if id(ex) not in used_ids:
                top.append(ex)
            if len(top) == top_n:
                break
                
    return top


def build_prompt(user_input):
    """Build few-shot prompt using selected synthetic examples."""
    selected = get_relevant_examples(user_input)
    parts = [
        "--- TRAINING EXAMPLES FOR STYLE GUIDANCE ---",
    ]
    for ex in selected:
        parts.append(f"User: {ex.get('input', '')}")
        parts.append(f"AI: {ex.get('output', '')}\n")
    return "\n".join(parts)


def test_ai():
    """Quick console test for pseudo-training prompt behavior."""
    engine = AIEngine("test_runner")
    test_inputs = [
        "I have mild fever and cough",
        "I have 104 fever",
        "I have 95C fever",
        "my friend is having heart attack",
        "what medicine should I take?",
    ]
    for text in test_inputs:
        result = engine.chat(text)
        print(f"INPUT: {text}")
        print(f"OUTPUT: {result.get('response', '')}")
        print("-" * 40)


class AIEngine:
    """Core AI engine that communicates with local Ollama."""

    def __init__(self, user_id="default"):
        self.user_id = user_id
        self.model = config.OLLAMA_MODEL
        self.ollama_url = config.OLLAMA_URL
        self.memory = ConversationMemory(user_id)
        self._health_profile = {}
        self._last_assessment = None

    def check_ollama_status(self):
        """Check if local Ollama server is reachable."""
        try:
            resp = requests.get("http://localhost:11434/api/tags", timeout=3)
            return resp.status_code == 200
        except Exception:
            return False

    # Backward-compatible naming used by templates and routes.
    def check_ai_status(self):
        return self.check_ollama_status()

    def list_models(self):
        """List available local Ollama models."""
        if not self.check_ollama_status():
            return []
        try:
            resp = requests.get("http://localhost:11434/api/tags", timeout=3)
            data = resp.json()
            return [m.get("name", "") for m in data.get("models", [])]
        except Exception:
            return []

    def set_health_profile(self, profile):
        """Set the user's health profile for context."""
        self._health_profile = profile

    def fallback_response(self, message):
        """Guaranteed non-empty fallback response."""
        msg = (message or "").lower()
        if self._is_greeting(msg):
            return "Hi! How can I help you today?"
        if "fever" in msg:
            return "This is usually a mild infection. You can take paracetamol, stay hydrated, and rest. Let me know if you also have cough or body aches."
        if "headache" in msg:
            return "Is the headache severe or mild? Are you hydrated?"
        return "Tell me what you are feeling and I will help you step by step."

    def _is_greeting(self, message):
        text = re.sub(r"[^a-z\s]", "", (message or "").strip().lower())
        return text in {
            "hi",
            "hello",
            "hey",
            "good morning",
            "good afternoon",
            "good evening",
        }

    def _non_repeated_questions(self, questions):
        """Return at most one follow-up question that was not asked before."""
        asked_history = " ".join(
            [m.get("content", "").lower() for m in self.memory.get_recent_messages(20) if m.get("role") == "assistant"]
        )
        for q in questions:
            if q.lower() not in asked_history:
                return [q]
        return []

    def _build_natural_response(self, user_message, symptom_assessment):
        """Build a natural, doctor-like response without rigid section labels."""
        symptom = symptom_assessment.get("symptom") or "symptoms"
        severity = symptom_assessment.get("severity", "low")
        urgent = symptom_assessment.get("urgent", False)
        high_fever_case = symptom_assessment.get("high_fever_case", False)
        invalid_temperature = symptom_assessment.get("invalid_temperature", False)
        subject = symptom_assessment.get("subject", "you")
        possible_cause = symptom_assessment.get(
            "possible_causes",
            "possible causes include common non-specific conditions.",
        )
        followups = self._non_repeated_questions(
            symptom_assessment.get("follow_up_questions", [])
        )

        variant = sum(ord(c) for c in (user_message or "")) % 3

        if invalid_temperature:
            text = (
                "That temperature is not possible for the human body. "
                "Please check and confirm the correct value."
            )
            if followups:
                text += f" {followups[0]}"
            return text

        if high_fever_case:
            text = (
                "That is a very high fever and you should not ignore it. "
                "This is a high fever and can be dangerous, and possible causes include a strong infection or significant inflammation.\n\n"
                "Please take paracetamol, drink plenty of fluids, rest, and monitor your temperature closely. "
                "You can also use a cool compress to help reduce temperature.\n\n"
                "Please seek medical attention immediately."
            )
            if followups:
                text += f" If you can, tell me: {followups[0]}"
            return text
        else:
            home_steps = symptom_assessment.get("home_care_steps") or []
            if home_steps:
                care_advice = ", ".join(home_steps) + "."
            else:
                care_advice = symptom_assessment.get("advice", "Monitor your symptoms and rest.")

            if urgent:
                doctor_timing = "⚠️ URGENT: Please seek urgent medical care now."
            elif severity == "high":
                doctor_timing = "You should see a doctor as soon as possible today."
            elif severity == "medium":
                doctor_timing = "If this is not improving, arrange a doctor review within 24 hours."
            else:
                doctor_timing = "See a doctor if symptoms worsen or persist."

            if subject == "friend":
                starters = [
                    "Thanks for sharing this about your friend.",
                    "From what you described about your friend,",
                    "Based on what you told me about your friend,",
                ]
            elif symptom == "symptoms":
                starters = [
                    "Thanks for sharing that.",
                    "Got it, thanks for the details.",
                    "I hear you, and this is helpful context.",
                ]
            else:
                starters = [
                    f"From what you described, this sounds like {symptom}.",
                    f"Given your symptoms, {symptom} seems to be the main issue right now.",
                    f"This likely relates to {symptom} based on what you shared.",
                ]

            bridges = [
                f"Possible causes include {possible_cause}",
                f"A likely explanation is that {possible_cause}",
                f"This may happen because {possible_cause}",
            ]

            closers = [
                f"For now, {care_advice} {doctor_timing}",
                f"Right now, {care_advice} {doctor_timing}",
                f"At this stage, {care_advice} {doctor_timing}",
            ]

            text = f"{starters[variant]} {bridges[variant]}\n\n{closers[variant]}"
            if followups:
                text += f" If needed, could you tell me: {followups[0]}"
            return text

    def generate_response(self, message, system_prompt, recent_messages):
        """Generate a non-streaming response from local Ollama."""
        if not (message or "").strip():
            return self.fallback_response(message)

        # Safety pre-check: impossible Celsius values are handled before model call.
        direct_temp = check_symptoms(message)
        if direct_temp.get("invalid_temperature"):
            return "That temperature is not possible for the human body. Please check and confirm the correct value."

        training_prompt = build_prompt(message)
        
        history_parts = ["--- REAL CONVERSATION HISTORY ---"]
        if recent_messages:
            for msg in recent_messages[-10:]:
                role = "User" if msg["role"] == "user" else "AI"
                history_parts.append(f"{role}: {msg['content']}")
                
        history_parts.append(f"User: {message}")
        history_parts.append("AI:")
        
        real_history_str = "\n".join(history_parts)
        full_prompt = f"{system_prompt}\n\n{training_prompt}\n\n{real_history_str}"

        if not self.check_ollama_status():
            return ""

        try:
            response = ollama.generate(
                model="llama3",
                prompt=full_prompt,
            )
            text = (response.get("response", "") or "").strip()
            if not text:
                return self.fallback_response(message)
            return self._dedupe_repeated_sentences(text)
        except Exception:
            return self.fallback_response(message)

    def _dedupe_repeated_sentences(self, text):
        """Remove exact repeated sentences to reduce repetitive responses."""
        if not text:
            return ""
        parts = re.split(r"(?<=[.!?])\s+", text.strip())
        seen = set()
        kept = []
        for s in parts:
            key = s.strip().lower()
            if not key or key in seen:
                continue
            seen.add(key)
            kept.append(s.strip())
        return " ".join(kept)

    def _ensure_disclaimer(self, text):
        if not text:
            return SAFETY_DISCLAIMER
        if SAFETY_DISCLAIMER in text:
            return text
        return f"{text}\n\n{SAFETY_DISCLAIMER}"

    def _should_add_disclaimer(self, response_text, symptom_assessment):
        if symptom_assessment.get("urgent") or symptom_assessment.get("high_fever_case"):
            return True
        if symptom_assessment.get("invalid_temperature"):
            return False
        lower = (response_text or "").lower()
        med_markers = ["paracetamol", "ibuprofen", "medicine", "medication", "tablet", "dose"]
        return any(marker in lower for marker in med_markers)

    def chat(self, user_message):
        """Send a message and return JSON-ready response payload."""
        if not (user_message or "").strip():
            text = "Please tell me what symptoms you have right now."
            return {
                "response": text,
                "status": "fallback",
                "model": self.model,
                "severity": "low",
                "symptom": None,
                "urgent": False,
            }

        if self._is_greeting(user_message):
            greeting = "Hi! How can I help you today?"
            self.memory.add_message("user", user_message)
            self.memory.add_message("assistant", greeting)
            return {
                "response": greeting,
                "status": "ok" if self.check_ollama_status() else "fallback",
                "model": self.model,
                "severity": "low",
                "symptom": None,
                "urgent": False,
            }

        self.memory.add_message("user", user_message)

        symptom_assessment = check_symptoms(user_message)
        self._last_assessment = symptom_assessment

        similar_note = self.memory.find_recent_similar_symptom(
            symptom_assessment.get("symptom")
        )
        symptom_assessment["past_similar_note"] = similar_note

        if symptom_assessment.get("symptom"):
            details = []
            if symptom_assessment.get("temperature_c") is not None:
                details.append(f"temp {symptom_assessment['temperature_c']:.1f}C")
            if symptom_assessment.get("duration_days") is not None:
                details.append(f"{symptom_assessment['duration_days']} days")
            self.memory.add_symptom_entry(
                symptom_assessment.get("symptom"),
                symptom_assessment.get("severity"),
                ", ".join(details),
            )

        if symptom_assessment.get("urgent"):
            urgent_text = self._build_natural_response(user_message, symptom_assessment)
            if self._should_add_disclaimer(urgent_text, symptom_assessment):
                urgent_text = self._ensure_disclaimer(urgent_text)
            self.memory.add_message("assistant", urgent_text)
            return {
                "response": urgent_text,
                "status": "urgent",
                "severity": "high",
                "symptom": symptom_assessment.get("symptom"),
                "urgent": True,
            }

        recent_insights = self.memory.get_recent_insights()
        
        # Hydrate dynamic health data
        fresh_profile = HealthProfile(self.user_id).to_dict()
        fresh_profile["tracked_symptoms"] = SymptomTracker(self.user_id).get_entries(limit=5)
        fresh_profile["tracked_vitals"] = VitalsTracker(self.user_id).get_entries(limit=5)
        
        system_prompt = build_context_prompt(
            fresh_profile,
            recent_insights,
            symptom_assessment,
        )
        # Use few-shot prompt generation; fall back to local reasoning if model output is empty.
        # Keep deterministic guidance for critical validation/emergency scenarios.
        if symptom_assessment.get("invalid_temperature") or symptom_assessment.get("high_fever_case"):
            response_text = self._build_natural_response(user_message, symptom_assessment)
        else:
            recent_messages = self.memory.get_recent_messages()
            model_response = self.generate_response(user_message, system_prompt, recent_messages)
            response_text = model_response.strip() if model_response else ""
            if not response_text:
                response_text = self._build_natural_response(user_message, symptom_assessment)
        if self._should_add_disclaimer(response_text, symptom_assessment):
            response_text = self._ensure_disclaimer(response_text)

        self.memory.add_message("assistant", response_text)
        return {
            "response": response_text,
            "status": "ok" if self.check_ollama_status() else "fallback",
            "model": self.model,
            "severity": symptom_assessment.get("severity", "low"),
            "symptom": symptom_assessment.get("symptom"),
            "urgent": symptom_assessment.get("urgent", False),
        }

    def stream_chat(self, user_message):
        """Compatibility generator: yields a single full response chunk."""
        result = self.chat(user_message)
        yield result.get("response", self.fallback_response(user_message))

    def get_last_assessment(self):
        return self._last_assessment or {}
