"""AI Engine for Memoria - integrates with Ollama for local LLM inference."""

import json
import requests

import config
from ai.health_prompt import build_context_prompt
from ai.memory import ConversationMemory


class AIEngine:
    """Core AI engine that communicates with the local Ollama instance."""

    def __init__(self, user_id="default"):
        self.ollama_host = config.OLLAMA_HOST
        self.model = config.OLLAMA_MODEL
        self.memory = ConversationMemory(user_id)
        self._health_profile = {}
        self._ollama_available = None

    def check_ollama_status(self):
        """Check if Ollama is running and accessible."""
        if self._ollama_available is not None:
            return self._ollama_available
        try:
            resp = requests.get(f"{self.ollama_host}/api/tags", timeout=5)
            self._ollama_available = resp.status_code == 200
            return self._ollama_available
        except requests.ConnectionError:
            self._ollama_available = False
            return False

    def list_models(self):
        """List available Ollama models."""
        try:
            resp = requests.get(f"{self.ollama_host}/api/tags", timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                return [m["name"] for m in data.get("models", [])]
        except requests.ConnectionError:
            pass
        return []

    def set_health_profile(self, profile):
        """Set the user's health profile for context."""
        self._health_profile = profile

    def chat(self, user_message):
        """Send a message to the AI and get a response.

        Returns a dict with 'response' and 'status' keys.
        """
        # Store the user message in memory
        self.memory.add_message("user", user_message)

        # Build context-aware system prompt
        recent_insights = self.memory.get_recent_insights()
        system_prompt = build_context_prompt(self._health_profile, recent_insights)

        # Build message history for the API
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(self.memory.get_conversation_for_ollama(count=10))

        # Try Ollama first
        if self.check_ollama_status():
            response = self._call_ollama(messages)
        else:
            response = self._fallback_response(user_message)

        # Store the assistant response
        self.memory.add_message("assistant", response["response"])

        return response

    def _call_ollama(self, messages):
        """Call the Ollama API for chat completion."""
        try:
            resp = requests.post(
                f"{self.ollama_host}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9,
                    },
                },
                timeout=120,
            )
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "response": data.get("message", {}).get("content", ""),
                    "status": "ok",
                    "model": self.model,
                }
            return {
                "response": f"Model returned status {resp.status_code}. "
                "Please ensure the model is pulled: "
                f"`ollama pull {self.model}`",
                "status": "error",
            }
        except requests.Timeout:
            return {
                "response": "The AI model took too long to respond. "
                "Please try a shorter question or a smaller model.",
                "status": "timeout",
            }
        except requests.ConnectionError:
            self._ollama_available = False
            return self._fallback_response(messages[-1]["content"])

    def _fallback_response(self, user_message):
        """Provide a helpful fallback when Ollama is not available."""
        msg_lower = user_message.lower()

        if any(w in msg_lower for w in ["emergency", "911", "dying", "heart attack"]):
            return {
                "response": "⚠️ **If this is a medical emergency, please call 911 "
                "(or your local emergency number) immediately.** "
                "Do not wait for AI assistance in an emergency situation.",
                "status": "fallback",
            }

        if any(w in msg_lower for w in ["headache", "pain", "ache", "sore"]):
            return {
                "response": "I understand you're experiencing discomfort. While I can't "
                "provide a diagnosis without Ollama running, here are some "
                "general tips:\n\n"
                "• Stay hydrated and rest\n"
                "• Track when the pain started and any triggers\n"
                "• Note the severity on a scale of 1-10\n"
                "• If pain is severe or persistent, consult a healthcare "
                "professional\n\n"
                "💡 **To enable full AI capabilities**, please install and "
                "start Ollama: `brew install ollama && ollama serve`",
                "status": "fallback",
            }

        if any(w in msg_lower for w in ["medication", "medicine", "drug", "pill"]):
            return {
                "response": "I can help you track medications! You can add your "
                "medications in the Health Profile section. Always take "
                "medications as prescribed by your doctor.\n\n"
                "💡 **To enable full AI capabilities**, please install and "
                "start Ollama: `brew install ollama && ollama serve`",
                "status": "fallback",
            }

        if any(w in msg_lower for w in ["hello", "hi", "hey", "good"]):
            return {
                "response": "Hello! I'm Memoria, your AI health assistant. 👋\n\n"
                "I can help you with:\n"
                "• 💬 Health questions and wellness advice\n"
                "• 📊 Tracking symptoms and vitals\n"
                "• 💊 Medication management\n"
                "• 🧠 Remembering your health history\n\n"
                "**Note:** I'm currently running in limited mode. For full AI "
                "capabilities, please install and start Ollama:\n"
                "`brew install ollama && ollama serve`\n"
                f"Then pull a model: `ollama pull {self.model}`",
                "status": "fallback",
            }

        return {
            "response": "I'm Memoria, your health assistant. I'm currently running "
            "in limited mode because Ollama is not available.\n\n"
            "**To enable full AI capabilities:**\n"
            "1. Install Ollama: `brew install ollama`\n"
            "2. Start the server: `ollama serve`\n"
            f"3. Pull a model: `ollama pull {self.model}`\n\n"
            "In the meantime, you can still:\n"
            "• Track your symptoms and vitals in the dashboard\n"
            "• Manage your medications\n"
            "• Log your health data\n\n"
            "How can I help you today?",
            "status": "fallback",
        }

    def stream_chat(self, user_message):
        """Stream a chat response from Ollama (generator).

        Yields chunks of the response text.
        """
        self.memory.add_message("user", user_message)

        recent_insights = self.memory.get_recent_insights()
        system_prompt = build_context_prompt(self._health_profile, recent_insights)

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(self.memory.get_conversation_for_ollama(count=10))

        if not self.check_ollama_status():
            fallback = self._fallback_response(user_message)
            self.memory.add_message("assistant", fallback["response"])
            yield fallback["response"]
            return

        full_response = ""
        try:
            resp = requests.post(
                f"{self.ollama_host}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": True,
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9,
                    },
                },
                timeout=120,
                stream=True,
            )
            for line in resp.iter_lines():
                if line:
                    data = json.loads(line)
                    chunk = data.get("message", {}).get("content", "")
                    if chunk:
                        full_response += chunk
                        yield chunk
                    if data.get("done"):
                        break
        except (requests.ConnectionError, requests.Timeout):
            if not full_response:
                fallback = self._fallback_response(user_message)
                full_response = fallback["response"]
                yield full_response

        self.memory.add_message("assistant", full_response)
