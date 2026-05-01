"""API routes for the AI-powered medical hub."""

from functools import wraps

from flask import Blueprint, jsonify, request, session

from services.ai_service import AIService
from services.doc_reader import DocumentReadError, extract_text
from services.memory import MemoryStore


api_bp = Blueprint("api_bp", __name__)
store = MemoryStore()
ai_service = AIService()


def login_required_json(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("logged_in"):
            return jsonify({"error": "Authentication required"}), 401
        return fn(*args, **kwargs)

    return wrapper


def _current_user():
    username = session.get("user_id", "")
    store.ensure_user(username)
    return username


@api_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()

    if not username or not password:
        return jsonify({"error": "username and password are required"}), 400

    if not store.verify_user(username, password):
        return jsonify({"error": "Invalid credentials"}), 401

    session["logged_in"] = True
    session["user_id"] = username
    profile_name = (store.get_profile(username).get("name") or "").strip()
    session["user_name"] = profile_name or username
    return jsonify({"status": "ok", "user": username})


@api_bp.route("/logout", methods=["POST"])
@login_required_json
def logout():
    session.clear()
    return jsonify({"status": "ok"})


@api_bp.route("/profile", methods=["GET"])
@login_required_json
def get_profile():
    user = _current_user()
    return jsonify(store.get_profile(user))


@api_bp.route("/profile/update", methods=["POST"])
@login_required_json
def update_profile():
    user = _current_user()
    payload = request.get_json(silent=True) or {}
    profile = store.update_profile(user, payload)
    return jsonify({"status": "ok", "profile": profile})


@api_bp.route("/medications", methods=["POST", "GET"])
@login_required_json
def medications():
    user = _current_user()
    if request.method == "GET":
        return jsonify({"medications": store.get_profile(user).get("medications", [])})

    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Medication name is required"}), 400

    item = {
        "name": name,
        "dosage": (data.get("dosage") or "").strip(),
        "frequency": (data.get("frequency") or "").strip(),
        "notes": (data.get("notes") or "").strip(),
    }
    profile = store.add_medication(user, item)
    return jsonify({"status": "ok", "medications": profile.get("medications", [])})


@api_bp.route("/symptoms/add", methods=["POST"])
@login_required_json
def add_symptom():
    user = _current_user()
    data = request.get_json(silent=True) or {}
    symptoms = data.get("symptoms", [])
    severity = (data.get("severity") or "low").lower()

    if not isinstance(symptoms, list) or not symptoms:
        return jsonify({"error": "symptoms list is required"}), 400
    if severity not in {"low", "medium", "high"}:
        return jsonify({"error": "severity must be low/medium/high"}), 400

    entry = {
        "date": data.get("date", ""),
        "symptoms": symptoms,
        "severity": severity,
    }
    store.add_symptom(user, entry)

    return jsonify({
        "status": "ok",
        "entry": entry,
        "alerts": store.get_alerts(user),
    })


@api_bp.route("/symptoms/history", methods=["GET"])
@login_required_json
def symptom_history():
    user = _current_user()
    history = store.symptom_history(user)
    return jsonify({"history": history})


@api_bp.route("/chat/history", methods=["GET"])
@login_required_json
def get_chat_history():
    user = _current_user()
    return jsonify({"history": store.chat_history(user)})


@api_bp.route("/chat/clear", methods=["POST"])
@login_required_json
def clear_chat_history():
    user = _current_user()
    store.clear_chat_history(user)
    return jsonify({"status": "ok", "history": []})


@api_bp.route("/chat", methods=["POST"])
@login_required_json
def chat():
    user = _current_user()
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"error": "message is required"}), 400

    profile = store.get_profile(user)
    history = store.chat_history(user)

    store.add_chat_message(user, "user", message)
    result = ai_service.chat(message, profile=profile, chat_history=history)
    reply = result.get("response") or "I could not generate a response."
    store.add_chat_message(user, "assistant", reply)

    return jsonify(
        {
            "response": reply,
            "source": result.get("source", "fallback"),
            "history": store.chat_history(user),
        }
    )


@api_bp.route("/upload", methods=["POST"])
@login_required_json
def upload_document():
    user = _current_user()

    if "file" not in request.files:
        return jsonify({"error": "file is required"}), 400

    uploaded = request.files["file"]
    try:
        text = extract_text(uploaded)
    except DocumentReadError as exc:
        return jsonify({"error": str(exc)}), 400

    profile = store.get_profile(user)
    result = ai_service.analyze_document(text, profile=profile)
    payload = {
        "filename": uploaded.filename,
        "analysis": result.get("analysis", ""),
        "source": result.get("source", "fallback"),
    }
    store.add_document_analysis(user, payload)

    return jsonify({"status": "ok", "document": payload})


@api_bp.route("/timeline", methods=["GET"])
@login_required_json
def timeline():
    user = _current_user()
    return jsonify({"timeline": store.timeline(user)})


@api_bp.route("/alerts", methods=["GET"])
@login_required_json
def alerts():
    user = _current_user()
    return jsonify({"alerts": store.get_alerts(user)})


@api_bp.route("/quick/fever", methods=["GET"])
@login_required_json
def quick_fever():
    return jsonify(ai_service.quick_action("fever"))


@api_bp.route("/quick/cough", methods=["GET"])
@login_required_json
def quick_cough():
    return jsonify(ai_service.quick_action("cough"))


@api_bp.route("/status", methods=["GET"])
def status():
    return jsonify({"status": "ok", "ollama": ai_service.is_available()})
