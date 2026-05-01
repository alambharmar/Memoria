"""Configuration for the Memoria application."""

import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

# Flask configuration
SECRET_KEY = os.environ.get("SECRET_KEY", "memoria-secret-key-change-in-production")
DEBUG = os.environ.get("FLASK_DEBUG", "1") == "1"

# Ollama configuration
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3"

# Hardcoded user credentials (as requested, login is not the focus)
DEFAULT_USER = {
    "username": "admin",
    "password": "memoria123",
    "name": "User",
}
