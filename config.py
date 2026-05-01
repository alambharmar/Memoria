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

# Default credentials (use env vars for public deployments)
DEFAULT_USER = {
    "username": os.environ.get("DEFAULT_USER_USERNAME", "memoria"),
    "password": os.environ.get("DEFAULT_USER_PASSWORD", "memoria"),
    "name": os.environ.get("DEFAULT_USER_NAME", "User"),
}
