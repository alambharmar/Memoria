# 🧠 Memoria

**AI Powered Health Companion App**

Memoria is a local-first AI health assistant that runs entirely on your machine. It uses [Ollama](https://ollama.ai) to run a large language model locally — no external APIs, no cloud services, complete privacy.

## Features

- **💬 AI Health Chat** — Conversational AI assistant with health-focused knowledge and memory
- **👤 Health Profile** — Track your conditions, medications, allergies, and personal info
- **🩺 Symptom Tracker** — Log symptoms with severity ratings and notes
- **❤️ Vitals Tracker** — Record blood pressure, heart rate, temperature, and more
- **🧠 Memory** — AI remembers your health history across conversations
- **🔒 100% Local** — All data and AI inference stays on your machine

---

## How to Run

### Prerequisites

| Requirement | How to check | Install |
|-------------|-------------|---------|
| **Python 3.10+** | `python3 --version` | [python.org/downloads](https://www.python.org/downloads/) or `brew install python` |
| **pip** (comes with Python) | `pip3 --version` | Included with Python |
| **Ollama** *(optional — for AI chat)* | `ollama --version` | [ollama.ai](https://ollama.ai) or `brew install ollama` |

### Quickest way (one command)

```bash
git clone https://github.com/alambharmar/Memoria.git
cd Memoria
./run.sh
```

`run.sh` creates a virtual environment, installs dependencies, and starts the server automatically.

### Manual setup (step by step)

```bash
# 1. Clone the repo
git clone https://github.com/alambharmar/Memoria.git
cd Memoria

# 2. Create & activate a virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate        # macOS / Linux
# venv\Scripts\activate         # Windows PowerShell

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Start the app
python app.py
```

### Open in your browser

Navigate to **http://127.0.0.1:5000** and log in with:

| | |
|-|-|
| **Username** | `admin` |
| **Password** | `memoria123` |

### Enable AI chat (optional but recommended)

Memoria works without Ollama (you can still track health data), but for the full AI chat experience:

```bash
# Install Ollama
brew install ollama          # macOS (or download from https://ollama.ai)

# Start the Ollama server (keep this running in a separate terminal)
ollama serve

# Pull a model (one-time download, ~2 GB)
ollama pull llama3.2
```

Then restart Memoria — the dashboard will show **AI Engine: Online**.

---

## Configuration

All settings are optional — the defaults work out of the box.

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `llama3.2` | Model to use for chat |
| `SECRET_KEY` | *(built-in)* | Flask session secret key |
| `FLASK_DEBUG` | `1` | Enable debug mode |

Example:

```bash
OLLAMA_MODEL=mistral python app.py
```

## Running Tests

```bash
pip install pytest            # one-time
python -m pytest tests/ -v
```

## Project Structure

```
Memoria/
├── app.py                    # Flask web application
├── config.py                 # Configuration
├── run.sh                    # One-command setup & run script
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

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `command not found: python3` | Install Python 3.10+ from [python.org](https://www.python.org/downloads/) |
| `No module named flask` | Run `pip install -r requirements.txt` (or use `./run.sh` which does this automatically) |
| AI chat says "limited mode" | Install & start Ollama, then pull a model — see [Enable AI chat](#enable-ai-chat-optional-but-recommended) |
| `Connection refused` on port 5000 | Make sure nothing else is using port 5000, or set `PORT=8080 python app.py` |
| Ollama is slow on first message | The first request loads the model into memory — subsequent messages are faster |

## Notes

- Memoria works in **limited mode** without Ollama — you can still track health data
- When Ollama is running, you get full conversational AI capabilities
- All data is stored locally in the `data/` directory as JSON files
- The AI always reminds users to consult healthcare professionals for medical advice
