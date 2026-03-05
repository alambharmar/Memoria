"""Memoria - AI Powered Health Assistant App.

Run with: python app.py
"""

import json

from flask import (
    Flask,
    Response,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

import config
from ai.engine import AIEngine
from models.health_data import HealthProfile, SymptomTracker, VitalsTracker

app = Flask(__name__)
app.secret_key = config.SECRET_KEY

# In-memory store for AI engines per session
_engines = {}


def get_engine():
    """Get or create an AI engine for the current session."""
    user_id = session.get("user_id", "default")
    if user_id not in _engines:
        _engines[user_id] = AIEngine(user_id)
        # Load health profile into engine
        profile = HealthProfile(user_id)
        _engines[user_id].set_health_profile(profile.to_dict())
    return _engines[user_id]


def login_required(f):
    """Simple login check decorator."""
    from functools import wraps

    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return decorated


# ─── Auth Routes ─────────────────────────────────────────────────────────────


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        if (
            username == config.DEFAULT_USER["username"]
            and password == config.DEFAULT_USER["password"]
        ):
            session["logged_in"] = True
            session["user_id"] = username
            session["user_name"] = config.DEFAULT_USER["name"]
            return redirect(url_for("dashboard"))
        error = "Invalid credentials. Try admin / memoria123"
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    user_id = session.get("user_id")
    if user_id and user_id in _engines:
        del _engines[user_id]
    session.clear()
    return redirect(url_for("login"))


# ─── Main Pages ──────────────────────────────────────────────────────────────


@app.route("/")
@login_required
def dashboard():
    user_id = session.get("user_id", "default")
    profile = HealthProfile(user_id)
    symptoms = SymptomTracker(user_id)
    vitals = VitalsTracker(user_id)
    engine = get_engine()

    return render_template(
        "dashboard.html",
        profile=profile.to_dict(),
        recent_symptoms=symptoms.get_entries(limit=5),
        recent_vitals=vitals.get_entries(limit=5),
        ollama_status=engine.check_ollama_status(),
        user_name=session.get("user_name", "User"),
    )


@app.route("/chat")
@login_required
def chat():
    engine = get_engine()
    return render_template(
        "chat.html",
        ollama_status=engine.check_ollama_status(),
        model=engine.model,
        user_name=session.get("user_name", "User"),
    )


@app.route("/profile")
@login_required
def profile_page():
    user_id = session.get("user_id", "default")
    profile = HealthProfile(user_id)
    return render_template(
        "profile.html",
        profile=profile.to_dict(),
        user_name=session.get("user_name", "User"),
    )


@app.route("/symptoms")
@login_required
def symptoms_page():
    user_id = session.get("user_id", "default")
    tracker = SymptomTracker(user_id)
    return render_template(
        "symptoms.html",
        entries=tracker.get_entries(limit=50),
        user_name=session.get("user_name", "User"),
    )


@app.route("/vitals")
@login_required
def vitals_page():
    user_id = session.get("user_id", "default")
    tracker = VitalsTracker(user_id)
    return render_template(
        "vitals.html",
        entries=tracker.get_entries(limit=50),
        user_name=session.get("user_name", "User"),
    )


# ─── API Endpoints ───────────────────────────────────────────────────────────


@app.route("/api/chat", methods=["POST"])
@login_required
def api_chat():
    data = request.get_json()
    message = data.get("message", "").strip()
    if not message:
        return jsonify({"error": "Empty message"}), 400

    engine = get_engine()
    result = engine.chat(message)
    return jsonify(result)


@app.route("/api/chat/stream", methods=["POST"])
@login_required
def api_chat_stream():
    data = request.get_json()
    message = data.get("message", "").strip()
    if not message:
        return jsonify({"error": "Empty message"}), 400

    engine = get_engine()

    def generate():
        for chunk in engine.stream_chat(message):
            yield f"data: {json.dumps({'chunk': chunk})}\n\n"
        yield "data: {\"done\": true}\n\n"

    return Response(generate(), mimetype="text/event-stream")


@app.route("/api/status")
@login_required
def api_status():
    engine = get_engine()
    ollama_ok = engine.check_ollama_status()
    models = engine.list_models() if ollama_ok else []
    return jsonify(
        {
            "ollama_available": ollama_ok,
            "current_model": engine.model,
            "available_models": models,
        }
    )


@app.route("/api/profile", methods=["GET", "POST"])
@login_required
def api_profile():
    user_id = session.get("user_id", "default")
    profile = HealthProfile(user_id)

    if request.method == "POST":
        data = request.get_json()
        profile.update(**data)
        # Update engine's health profile
        engine = get_engine()
        engine.set_health_profile(profile.to_dict())
        return jsonify({"status": "ok", "profile": profile.to_dict()})

    return jsonify(profile.to_dict())


@app.route("/api/profile/medication", methods=["POST", "DELETE"])
@login_required
def api_medication():
    user_id = session.get("user_id", "default")
    profile = HealthProfile(user_id)

    if request.method == "POST":
        data = request.get_json()
        med = profile.add_medication(
            name=data.get("name", ""),
            dosage=data.get("dosage", ""),
            frequency=data.get("frequency", ""),
            notes=data.get("notes", ""),
        )
        return jsonify({"status": "ok", "medication": med})

    if request.method == "DELETE":
        data = request.get_json()
        profile.remove_medication(data.get("name", ""))
        return jsonify({"status": "ok"})

    return jsonify({"error": "Method not allowed"}), 405


@app.route("/api/profile/condition", methods=["POST", "DELETE"])
@login_required
def api_condition():
    user_id = session.get("user_id", "default")
    profile = HealthProfile(user_id)

    if request.method == "POST":
        data = request.get_json()
        profile.add_condition(data.get("condition", ""))
        return jsonify({"status": "ok"})

    if request.method == "DELETE":
        data = request.get_json()
        profile.remove_condition(data.get("condition", ""))
        return jsonify({"status": "ok"})

    return jsonify({"error": "Method not allowed"}), 405


@app.route("/api/profile/allergy", methods=["POST", "DELETE"])
@login_required
def api_allergy():
    user_id = session.get("user_id", "default")
    profile = HealthProfile(user_id)

    if request.method == "POST":
        data = request.get_json()
        profile.add_allergy(data.get("allergy", ""))
        return jsonify({"status": "ok"})

    if request.method == "DELETE":
        data = request.get_json()
        profile.remove_allergy(data.get("allergy", ""))
        return jsonify({"status": "ok"})

    return jsonify({"error": "Method not allowed"}), 405


@app.route("/api/symptoms", methods=["GET", "POST"])
@login_required
def api_symptoms():
    user_id = session.get("user_id", "default")
    tracker = SymptomTracker(user_id)

    if request.method == "POST":
        data = request.get_json()
        entry = tracker.log_symptom(
            symptom=data.get("symptom", ""),
            severity=data.get("severity", 5),
            notes=data.get("notes", ""),
        )
        return jsonify({"status": "ok", "entry": entry})

    return jsonify(tracker.get_entries())


@app.route("/api/symptoms/<int:index>", methods=["DELETE"])
@login_required
def api_symptom_delete(index):
    user_id = session.get("user_id", "default")
    tracker = SymptomTracker(user_id)
    if tracker.delete_entry(index):
        return jsonify({"status": "ok"})
    return jsonify({"error": "Entry not found"}), 404


@app.route("/api/vitals", methods=["GET", "POST"])
@login_required
def api_vitals():
    user_id = session.get("user_id", "default")
    tracker = VitalsTracker(user_id)

    if request.method == "POST":
        data = request.get_json()
        entry = tracker.log_vitals(
            vital_type=data.get("type", ""),
            value=data.get("value", ""),
            unit=data.get("unit", ""),
            notes=data.get("notes", ""),
        )
        return jsonify({"status": "ok", "entry": entry})

    vital_type = request.args.get("type")
    return jsonify(tracker.get_entries(vital_type=vital_type))


@app.route("/api/vitals/<int:index>", methods=["DELETE"])
@login_required
def api_vital_delete(index):
    user_id = session.get("user_id", "default")
    tracker = VitalsTracker(user_id)
    if tracker.delete_entry(index):
        return jsonify({"status": "ok"})
    return jsonify({"error": "Entry not found"}), 404


@app.route("/api/memory/clear", methods=["POST"])
@login_required
def api_clear_memory():
    engine = get_engine()
    engine.memory.clear()
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  🧠 Memoria - AI Powered Health Assistant")
    print("=" * 60)
    print(f"  Server: http://127.0.0.1:5000")
    print(f"  Login:  {config.DEFAULT_USER['username']} / {config.DEFAULT_USER['password']}")
    print(f"  Ollama: {config.OLLAMA_HOST}")
    print(f"  Model:  {config.OLLAMA_MODEL}")
    print("=" * 60 + "\n")
    app.run(debug=config.DEBUG, host="127.0.0.1", port=5000)
