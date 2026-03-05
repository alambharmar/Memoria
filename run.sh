#!/usr/bin/env bash
# Memoria — one-command setup & run script
# Usage:  ./run.sh            (setup + start server)
#         ./run.sh --setup    (setup only, don't start)
#         ./run.sh --start    (start only, skip setup)
set -e

VENV_DIR="venv"

setup() {
    echo ""
    echo "============================================================"
    echo "  🧠 Memoria — Setup"
    echo "============================================================"

    # Pick the right Python
    if command -v python3 &>/dev/null; then
        PY=python3
    elif command -v python &>/dev/null; then
        PY=python
    else
        echo "❌ Python 3 is required but not found."
        echo "   Install it from https://www.python.org/downloads/"
        exit 1
    fi

    # Check minimum version (3.10+)
    PY_VERSION=$($PY -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    PY_OK=$($PY -c 'import sys; print(int(sys.version_info >= (3, 10)))')
    echo "  Python: $PY ($PY_VERSION)"
    if [ "$PY_OK" != "1" ]; then
        echo "❌ Python 3.10 or newer is required (found $PY_VERSION)."
        echo "   Install it from https://www.python.org/downloads/"
        exit 1
    fi

    # Create virtual environment if missing
    if [ ! -d "$VENV_DIR" ]; then
        echo "  Creating virtual environment..."
        $PY -m venv "$VENV_DIR"
    fi

    # Activate
    # shellcheck disable=SC1091
    source "$VENV_DIR/bin/activate"

    # Install dependencies
    echo "  Installing dependencies..."
    pip install --quiet --upgrade pip
    pip install --quiet -r requirements.txt

    echo "  ✅ Setup complete!"
    echo ""
}

start() {
    # Activate venv if it exists
    if [ -d "$VENV_DIR" ]; then
        # shellcheck disable=SC1091
        source "$VENV_DIR/bin/activate"
    fi

    echo ""
    echo "============================================================"
    echo "  🧠 Memoria — Starting"
    echo "============================================================"

    # Check if Ollama is reachable (informational, not required)
    if command -v curl &>/dev/null; then
        if curl -s --max-time 2 http://localhost:11434/api/tags >/dev/null 2>&1; then
            echo "  ✅ Ollama detected — full AI mode"
        else
            echo "  ⚠️  Ollama not detected — running in limited mode"
            echo "     To enable AI chat, install Ollama:"
            echo "       brew install ollama   # macOS"
            echo "       # or visit https://ollama.ai"
            echo "     Then:  ollama serve && ollama pull llama3.2"
        fi
    fi

    echo ""
    echo "  Open http://127.0.0.1:5000 in your browser"
    echo "  Login: admin / memoria123"
    echo "============================================================"
    echo ""

    python app.py
    # 'python' here resolves to the venv's Python after activation above
}

# ─── Main ─────────────────────────────────────────────────────────
case "${1:-}" in
    --setup) setup ;;
    --start) start ;;
    *)       setup; start ;;
esac
