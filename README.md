# 🧠 Memoria

**AI Powered Health Companion App**

Memoria is a local-first AI health assistant that runs entirely on your Mac. It uses [Ollama](https://ollama.ai) to run a large language model locally — no external APIs, no cloud services, complete privacy.

## Features

- **💬 AI Health Chat** — Conversational AI assistant with health-focused knowledge and memory
- **👤 Health Profile** — Track your conditions, medications, allergies, and personal info
- **🩺 Symptom Tracker** — Log symptoms with severity ratings and notes
- **❤️ Vitals Tracker** — Record blood pressure, heart rate, temperature, and more
- **🧠 Memory** — AI remembers your health history across conversations
- **🔒 100% Local** — All data and AI inference stays on your machine

## Quick Start

### 1. Install Ollama (for AI features)

```bash
brew install ollama
ollama serve
ollama pull llama3.2
```

### 2. Install & Run Memoria

```bash
pip install -r requirements.txt
python app.py
```

### 3. Open in browser

Navigate to **http://127.0.0.1:5000** and log in with:
- Username: `admin`
- Password: `memoria123`

## Configuration

Environment variables (all optional):

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `llama3.2` | Model to use for chat |
| `SECRET_KEY` | (built-in) | Flask session secret key |
| `FLASK_DEBUG` | `1` | Enable debug mode |

## Project Structure

```
Memoria/
├── app.py                    # Flask web application
├── config.py                 # Configuration
├── requirements.txt          # Python dependencies
├── ai/
│   ├── engine.py             # AI engine (Ollama integration)
│   ├── health_prompt.py      # Health-focused system prompts
│   └── memory.py             # Conversation memory
├── models/
│   └── health_data.py        # Health profile, symptoms, vitals models
├── static/
│   ├── css/style.css         # Styles
│   └── js/app.js             # Frontend utilities
├── templates/                # HTML templates
│   ├── base.html
│   ├── login.html
│   ├── dashboard.html
│   ├── chat.html
│   ├── profile.html
│   ├── symptoms.html
│   └── vitals.html
├── data/                     # Local data storage (gitignored)
└── tests/
    └── test_app.py           # Tests
```

## Running Tests

```bash
python -m pytest tests/ -v
```

## Notes

- Memoria works in **limited mode** without Ollama — you can still track health data
- When Ollama is running, you get full conversational AI capabilities
- All data is stored locally in the `data/` directory as JSON files
- The AI always reminds users to consult healthcare professionals for medical advice
