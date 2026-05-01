"""Ollama-backed AI service for health chat and document analysis."""

import re

import requests

import config


INVALID_TEMP_MSG = "That temperature is not possible for the human body. Please check and confirm the correct value."


class AIService:
    """Wraps all Ollama interactions with safe fallbacks and guardrails."""

    def __init__(self, model=None, generate_url=None):
        self.model = model or config.OLLAMA_MODEL
        self.generate_url = generate_url or config.OLLAMA_URL
        self.tags_url = "http://localhost:11434/api/tags"

    def is_available(self):
        try:
            resp = requests.get(self.tags_url, timeout=3)
            return resp.status_code == 200
        except Exception:
            return False

    def _extract_celsius(self, text):
        lower = (text or "").lower()
        c_match = re.search(r"(\d{2,3}(?:\.\d+)?)\s*°?\s*c", lower)
        if c_match:
            return float(c_match.group(1))
        return None

    def _is_greeting(self, text):
        cleaned = re.sub(r"[^a-z\s]", "", (text or "").strip().lower())
        return cleaned in {"hi", "hello", "hey", "good morning", "good afternoon", "good evening"}

    def _build_history_block(self, history):
        if not history:
            return "No prior messages."
        lines = []
        for row in history[-10:]:
            role = "User" if row.get("role") == "user" else "Assistant"
            lines.append(f"{role}: {row.get('content', '')}")
        return "\n".join(lines)

    def _fallback_chat(self, message):
        msg = (message or "").lower()
        if self._is_greeting(msg):
            return "Hi! I'm Memoria, your health assistant. How are you feeling today? Tell me about any symptoms or health questions you have."

        # Conversational responses
        conversational = {
            "how are you": "I'm here and ready to help! Tell me what's on your mind — any symptoms, health questions, or concerns?",
            "thank": "You're welcome! Let me know if there's anything else I can help with.",
            "thanks": "You're welcome! Let me know if there's anything else I can help with.",
            "who are you": "I'm Memoria, your AI health assistant. I can help you understand symptoms, medications, and general health questions. How can I help?",
            "what can you do": "I can help with understanding symptoms, basic health guidance, medication questions, and tracking your health. What would you like to know?",
            "help": "Of course! You can tell me about any symptoms you're experiencing, ask about medications, or discuss health concerns. What's going on?",
            "ok": "Let me know if you have any health questions or symptoms you'd like to discuss!",
            "bye": "Take care! Remember to stay hydrated and get enough rest. Come back anytime you need health guidance.",
            "good": "Glad to hear that! Let me know if you have any health questions.",
        }
        for key, response in conversational.items():
            if key in msg:
                return response

        # Symptom-based responses
        symptom_responses = {
            "fever": "Fever often indicates your body is fighting an infection. Here's what you can do:\n\n• Take paracetamol (as directed) to manage temperature\n• Stay well hydrated — water, clear broths, oral rehydration solution\n• Rest as much as possible\n• Use a cool compress on your forehead\n\nIf your fever is above 103°F (39.4°C), persists more than 3 days, or comes with severe symptoms, please see a doctor. Do you have any other symptoms alongside the fever?",
            "headache": "Headaches can have many causes. Here are some things to consider:\n\n• Stay hydrated — dehydration is a very common cause\n• Rest in a quiet, dark room if possible\n• Mild OTC pain relief like paracetamol can help\n• Check if you've been straining your eyes or under stress\n\nIs the headache sudden and severe, or has it been gradual? Any other symptoms like nausea, vision changes, or stiff neck?",
            "cough": "Coughing is your body's way of clearing irritants. Here's what may help:\n\n• Stay hydrated with warm fluids — tea with honey works well\n• Use a humidifier or steam inhalation\n• Avoid smoke and strong irritants\n• Rest your voice when possible\n\nIs the cough dry or producing phlegm? How long have you had it? If you notice blood, difficulty breathing, or it persists beyond 2 weeks, please see a doctor.",
            "cold": "Common cold symptoms usually resolve on their own. To feel better sooner:\n\n• Rest and get plenty of sleep\n• Stay hydrated with warm liquids\n• Saline nasal spray can help with congestion\n• Honey and warm water can soothe a sore throat\n\nMost colds improve within 7-10 days. See a doctor if symptoms worsen or you develop high fever.",
            "stomach": "Stomach issues can range from minor to serious. Some general advice:\n\n• Start with clear liquids and bland foods (BRAT diet: bananas, rice, applesauce, toast)\n• Stay hydrated with small, frequent sips\n• Avoid spicy, fatty, or dairy foods temporarily\n• Rest and monitor your symptoms\n\nCan you tell me more? Is it pain, nausea, or something else?",
            "nausea": "Nausea can be uncomfortable. Here are some tips:\n\n• Sip ginger tea or clear fluids slowly\n• Eat small, bland meals\n• Avoid strong smells and greasy food\n• Rest in a semi-upright position\n\nHow long have you been feeling nauseous? Any vomiting, dizziness, or other symptoms?",
            "dizzi": "Dizziness can have several causes including dehydration, low blood sugar, or inner ear issues.\n\n• Sit or lie down immediately to prevent falls\n• Drink water slowly\n• Eat something if you haven't recently\n• Avoid sudden position changes\n\nIs the room spinning, or do you feel lightheaded? Any hearing changes or nausea with it?",
            "chest pain": "⚠️ Chest pain can be serious. If you're experiencing severe chest pain, pressure, or tightness — especially with shortness of breath, arm pain, or jaw pain — please call emergency services immediately.\n\nIf the pain is mild, it could be muscular, acid reflux, or anxiety-related. Can you describe the pain — is it sharp, dull, burning, or pressure-like?",
            "breath": "Difficulty breathing needs attention.\n\n• If severe or sudden, seek emergency medical care immediately\n• Sit upright to help open your airways\n• Try to stay calm and breathe slowly\n\nIs this new or have you experienced it before? Any wheezing, chest tightness, or recent illness?",
            "allerg": "For mild allergic reactions:\n\n• An antihistamine like cetirizine can help with itching, sneezing, and hives\n• Avoid the suspected allergen\n• Cool compresses can soothe itchy skin\n\n⚠️ If you notice swelling of lips/tongue/throat, difficulty breathing, or feel faint, seek emergency care immediately. What are your symptoms?",
            "sleep": "Good sleep is crucial for health. Some tips:\n\n• Keep a consistent sleep schedule\n• Avoid screens 1 hour before bed\n• Keep your room cool and dark\n• Limit caffeine after noon\n• Try relaxation techniques like deep breathing\n\nWhat specific sleep issues are you having?",
            "stress": "Stress management is important for overall health:\n\n• Practice deep breathing or meditation\n• Regular physical activity helps significantly\n• Maintain social connections\n• Set boundaries and prioritize tasks\n• Consider journaling your thoughts\n\nWould you like to talk about what's causing your stress?",
            "pain": "I'd like to help with your pain. Can you tell me:\n\n• Where exactly is the pain?\n• How would you describe it — sharp, dull, throbbing, burning?\n• How long have you had it?\n• Does anything make it better or worse?\n\nThis will help me give you more specific guidance.",
            "tired": "Persistent fatigue can have many causes:\n\n• Ensure you're getting 7-9 hours of quality sleep\n• Stay hydrated and eat balanced meals\n• Regular moderate exercise can boost energy\n• Check if any medications might cause drowsiness\n\nHow long have you been feeling tired? Any other symptoms like fever, weight changes, or mood changes?",
            "sore throat": "Sore throats are common and usually heal on their own:\n\n• Gargle with warm salt water\n• Drink warm liquids with honey\n• Use throat lozenges for temporary relief\n• Rest your voice\n\nIf it persists beyond a week, comes with high fever, or you have difficulty swallowing, please see a doctor.",
            "back": "Back pain is very common. Here's what may help:\n\n• Apply ice (first 48 hours) or heat to the area\n• Gentle stretching and movement is usually better than bed rest\n• OTC pain relief like ibuprofen can help\n• Maintain good posture\n\nIs the pain in your upper or lower back? Any numbness, tingling, or leg weakness?",
            "anxiet": "I'm glad you're reaching out about anxiety. Some helpful strategies:\n\n• Deep breathing: inhale 4 seconds, hold 4, exhale 4\n• Grounding techniques: notice 5 things you can see, 4 you can touch, etc.\n• Regular exercise and sleep hygiene help long-term\n• Limit caffeine and alcohol\n\nIf anxiety is significantly affecting your daily life, please consider speaking with a mental health professional.",
            "blood pressure": "For blood pressure concerns:\n\n• Normal range is around 120/80 mmHg\n• Reduce sodium intake and eat more fruits, vegetables, and whole grains\n• Regular exercise (30 min most days) helps\n• Manage stress and limit alcohol\n\nDo you know your recent readings? Are you currently on any blood pressure medication?",
            "skin": "Skin concerns can vary widely. To help you better:\n\n• Is it a rash, bump, discoloration, or something else?\n• Is it itchy, painful, or burning?\n• How long has it been present?\n• Any new products, foods, or medications recently?\n\nThis will help me provide more specific guidance.",
            "medication": "I can help with medication questions! What would you like to know?\n\n• Side effects of a specific medication\n• General usage guidelines\n• Interactions with other medications\n\nPlease note that for specific dosage or prescription changes, always consult your doctor or pharmacist.",
        }

        for keyword, response in symptom_responses.items():
            if keyword in msg:
                return response

        # Default catch-all — conversational and helpful
        return (
            "Thanks for sharing that. I want to make sure I understand correctly and give you the best guidance.\n\n"
            "Could you tell me a bit more about what you're experiencing? "
            "For example:\n"
            "• What symptoms are you having?\n"
            "• How long have they been present?\n"
            "• Is there anything that makes it better or worse?\n\n"
            "The more details you share, the better I can help!"
        )

    def _call_ollama(self, prompt):
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }
        resp = requests.post(self.generate_url, json=payload, timeout=30)
        data = resp.json()
        return (data.get("response") or "").strip()

    def _allergy_warnings(self, response_text, profile):
        allergies = [a.lower() for a in (profile.get("allergies") or []) if isinstance(a, str)]
        meds_mentioned = []
        for med in ["paracetamol", "ibuprofen", "aspirin", "amoxicillin", "cetirizine"]:
            if med in (response_text or "").lower():
                meds_mentioned.append(med)

        warnings = []
        for med in meds_mentioned:
            if any(med in a or a in med for a in allergies):
                warnings.append(f"Allergy warning: possible conflict with {med} based on your allergy list.")
        return warnings

    def chat(self, message, profile, chat_history):
        if self._is_greeting(message):
            return {"response": "Hi! How can I help you today?", "source": "rule"}

        temp_c = self._extract_celsius(message)
        if temp_c is not None and temp_c > 45:
            return {"response": INVALID_TEMP_MSG, "source": "rule"}

        prompt = (
            "You are Memoria, a smart and calm AI health assistant. "
            "Use a natural doctor-like tone. Keep it short and clear. "
            "Do not invent symptoms, duration, or history not present in user input or provided profile. "
            "Basic advice is allowed (paracetamol, hydration, rest) when appropriate. "
            "If severe red-flag symptoms are present, strongly advise immediate medical care.\n\n"
            f"Patient profile: {profile}\n"
            f"Recent chat memory (last 10):\n{self._build_history_block(chat_history)}\n\n"
            f"User message: {message}\n"
            "Assistant reply:"
        )

        if not self.is_available():
            return {"response": self._fallback_chat(message), "source": "fallback"}

        try:
            text = self._call_ollama(prompt)
            if not text:
                text = self._fallback_chat(message)
            warnings = self._allergy_warnings(text, profile)
            if warnings:
                text = text + "\n\n" + " ".join(warnings)
            return {"response": text, "source": "ollama"}
        except Exception:
            return {"response": self._fallback_chat(message), "source": "fallback"}

    def analyze_document(self, document_text, profile):
        prompt = (
            "Analyze the following medical document and return concise sections exactly as:\n"
            "1. Patient condition\n"
            "2. Medicines\n"
            "3. What each medicine does\n"
            "4. Instructions\n\n"
            "Do not hallucinate details not in the document.\n"
            f"Patient profile: {profile}\n\n"
            f"Document content:\n{document_text}\n"
        )

        if not self.is_available():
            return {
                "analysis": (
                    "1. Patient condition: Could not run AI analysis right now.\n"
                    "2. Medicines: Not available\n"
                    "3. What each medicine does: Not available\n"
                    "4. Instructions: Please retry when Ollama is available"
                ),
                "source": "fallback",
            }

        try:
            text = self._call_ollama(prompt)
            if not text:
                raise ValueError("empty AI output")
            return {"analysis": text, "source": "ollama"}
        except Exception:
            return {
                "analysis": (
                    "1. Patient condition: AI analysis failed.\n"
                    "2. Medicines: Not available\n"
                    "3. What each medicine does: Not available\n"
                    "4. Instructions: Please try again later"
                ),
                "source": "fallback",
            }

    def quick_action(self, action):
        action = (action or "").lower()
        if action == "fever":
            return {
                "advice": "For mild fever: rest, hydration, and paracetamol if needed. If fever is very high or persistent, seek medical care."
            }
        if action == "cough":
            return {
                "advice": "For cough: stay hydrated, rest, and monitor for breathing trouble or high fever. Seek care if symptoms worsen."
            }
        return {"advice": "Quick action not available."}
