"""Memoria - Complete AI-powered medical hub (Flask + Ollama)."""

from functools import wraps
import logging
import os
import time
import warnings

from flask import Flask, g, jsonify, redirect, render_template, request, session, url_for  # pyright: ignore[reportMissingImports]
from flask_cors import CORS  # pyright: ignore[reportMissingModuleSource]

import config
from ai.engine import AIEngine
from models.health_data import HealthProfile, SymptomTracker, VitalsTracker
from routes.api_routes import api_bp


_engines = {}


def current_user_id():
    return session.get("user_id", config.DEFAULT_USER["username"])


def current_user_name():
    user_id = current_user_id()
    profile_name = (HealthProfile(user_id).to_dict().get("name") or "").strip()
    resolved = profile_name or user_id or config.DEFAULT_USER["name"]
    if session.get("user_name") != resolved:
        session["user_name"] = resolved
    return resolved


def configure_runtime_output(app):
    """Reduce dev-server noise while keeping useful request visibility."""
    # Hide repetitive static asset request logs from Werkzeug.
    logging.getLogger("werkzeug").setLevel(logging.WARNING)

    @app.before_request
    def _start_timer():
        g._request_start = time.perf_counter()

    @app.after_request
    def _request_log(response):
        path = request.path or ""
        if path.startswith("/static/"):
            return response

        elapsed_ms = 0.0
        started = getattr(g, "_request_start", None)
        if started is not None:
            elapsed_ms = (time.perf_counter() - started) * 1000

        print(f"[{request.method}] {path} -> {response.status_code} ({elapsed_ms:.1f} ms)")
        return response


def get_engine():
    user_id = current_user_id()
    if user_id not in _engines:
        _engines[user_id] = AIEngine(user_id)
        profile = HealthProfile(user_id)
        _engines[user_id].set_health_profile(profile.to_dict())
    return _engines[user_id]


def login_required_page(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return fn(*args, **kwargs)

    return wrapper


def create_app():
    app = Flask(__name__)
    app.secret_key = config.SECRET_KEY
    CORS(app)
    configure_runtime_output(app)

    app.register_blueprint(api_bp)

    @app.route("/")
    @login_required_page
    def dashboard():
        user_id = current_user_id()
        profile_model = HealthProfile(user_id)
        symptom_model = SymptomTracker(user_id)
        vitals_model = VitalsTracker(user_id)
        engine = get_engine()

        recent_symptoms = symptom_model.get_entries(limit=5)
        return render_template(
            "dashboard.html",
            profile=profile_model.to_dict(),
            recent_symptoms=recent_symptoms,
            recent_vitals=vitals_model.get_entries(limit=5),
            ai_status=engine.check_ai_status(),
            user_name=current_user_name(),
        )

    @app.route("/login", methods=["GET"])
    def login():
        return render_template("login.html", error=None)

    @app.route("/session/login", methods=["POST"])
    def session_login():
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        if (
            username == config.DEFAULT_USER["username"]
            and password == config.DEFAULT_USER["password"]
        ):
            session["logged_in"] = True
            session["user_id"] = username
            session["user_name"] = (HealthProfile(username).to_dict().get("name") or "").strip() or username
            return redirect(url_for("dashboard"))
        return render_template("login.html", error="Invalid credentials. Check your username and password.")

    @app.route("/logout", methods=["GET"])
    def logout():
        user_id = session.get("user_id")
        if user_id in _engines:
            del _engines[user_id]
        session.clear()
        return redirect(url_for("login"))

    @app.route("/chat", methods=["GET"], endpoint="chat")
    @login_required_page
    def chat_page():
        engine = get_engine()
        return render_template(
            "chat.html",
            ai_status=engine.check_ai_status(),
            model=engine.model,
            user_name=current_user_name(),
        )

    @app.route("/profile-ui", methods=["GET"], endpoint="profile_page")
    @login_required_page
    def profile_page():
        user_id = current_user_id()
        profile = HealthProfile(user_id)
        return render_template(
            "profile.html",
            profile=profile.to_dict(),
            user_name=current_user_name(),
        )

    @app.route("/track-ui", methods=["GET"], endpoint="track_page")
    @login_required_page
    def track_page():
        user_id = current_user_id()
        sym_tracker = SymptomTracker(user_id)
        vit_tracker = VitalsTracker(user_id)
        return render_template(
            "track_health.html",
            symptoms=sym_tracker.get_entries(limit=100),
            vitals=vit_tracker.get_entries(limit=100),
            user_name=current_user_name(),
        )
        
    @app.route("/settings-ui", methods=["GET"], endpoint="settings_page")
    @login_required_page
    def settings_page():
        return render_template(
            "settings.html",
            user_name=current_user_name(),
        )

    @app.route("/api/chat", methods=["POST"])
    @login_required_page
    def api_chat_compat():
        data = request.get_json(silent=True) or {}
        message = (data.get("message") or "").strip()
        if not message:
            return jsonify({"error": "Empty message"}), 400
        result = get_engine().chat(message)
        return jsonify(result)

    @app.route("/api/memory/clear", methods=["POST"])
    @login_required_page
    def api_clear_memory_compat():
        get_engine().memory.clear()
        return jsonify({"status": "ok"})

    @app.route("/api/status", methods=["GET"])
    @login_required_page
    def api_status_compat():
        engine = get_engine()
        ai_ok = engine.check_ai_status()
        models = engine.list_models() if ai_ok else []
        return jsonify(
            {
                "ai_available": ai_ok,
                "current_model": engine.model,
                "available_models": models,
            }
        )

    @app.route("/api/profile", methods=["GET", "POST"])
    @login_required_page
    def api_profile_compat():
        user_id = current_user_id()
        profile = HealthProfile(user_id)
        if request.method == "POST":
            data = request.get_json(silent=True) or {}
            profile.update(**data)
            session["user_name"] = (profile.to_dict().get("name") or "").strip() or user_id
            get_engine().set_health_profile(profile.to_dict())
            return jsonify({"status": "ok", "profile": profile.to_dict()})
        return jsonify(profile.to_dict())

    @app.route("/api/profile/condition", methods=["POST", "DELETE"])
    @login_required_page
    def api_condition_compat():
        user_id = current_user_id()
        profile = HealthProfile(user_id)
        data = request.get_json(silent=True) or {}
        if request.method == "POST":
            profile.add_condition(data.get("condition", ""))
        else:
            profile.remove_condition(data.get("condition", ""))
        get_engine().set_health_profile(profile.to_dict())
        return jsonify({"status": "ok"})

    @app.route("/api/profile/allergy", methods=["POST", "DELETE"])
    @login_required_page
    def api_allergy_compat():
        user_id = current_user_id()
        profile = HealthProfile(user_id)
        data = request.get_json(silent=True) or {}
        if request.method == "POST":
            profile.add_allergy(data.get("allergy", ""))
        else:
            profile.remove_allergy(data.get("allergy", ""))
        get_engine().set_health_profile(profile.to_dict())
        return jsonify({"status": "ok"})

    @app.route("/api/profile/medication", methods=["POST", "DELETE"])
    @login_required_page
    def api_medication_compat():
        user_id = current_user_id()
        profile = HealthProfile(user_id)
        data = request.get_json(silent=True) or {}
        if request.method == "POST":
            med = profile.add_medication(
                name=data.get("name", ""),
                dosage=data.get("dosage", ""),
                frequency=data.get("frequency", ""),
                notes=data.get("notes", ""),
            )
            get_engine().set_health_profile(profile.to_dict())
            return jsonify({"status": "ok", "medication": med})
        profile.remove_medication(data.get("name", ""))
        get_engine().set_health_profile(profile.to_dict())
        return jsonify({"status": "ok"})

    @app.route("/api/symptoms", methods=["GET", "POST"])
    @login_required_page
    def api_symptoms_compat():
        user_id = current_user_id()
        tracker = SymptomTracker(user_id)
        if request.method == "POST":
            data = request.get_json(silent=True) or {}
            entry = tracker.log_symptom(
                symptom=data.get("symptom", ""),
                severity=data.get("severity", 5),
                notes=data.get("notes", ""),
            )
            return jsonify({"status": "ok", "entry": entry})
        return jsonify(tracker.get_entries())

    @app.route("/api/symptoms/<int:index>", methods=["DELETE"])
    @login_required_page
    def api_symptom_delete_compat(index):
        user_id = current_user_id()
        tracker = SymptomTracker(user_id)
        if tracker.delete_entry(index):
            return jsonify({"status": "ok"})
        return jsonify({"error": "Entry not found"}), 404

    @app.route("/api/vitals", methods=["GET", "POST"])
    @login_required_page
    def api_vitals_compat():
        user_id = current_user_id()
        tracker = VitalsTracker(user_id)
        if request.method == "POST":
            data = request.get_json(silent=True) or {}
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
    @login_required_page
    def api_vital_delete_compat(index):
        user_id = current_user_id()
        tracker = VitalsTracker(user_id)
        if tracker.delete_entry(index):
            return jsonify({"status": "ok"})
        return jsonify({"error": "Entry not found"}), 404

    @app.errorhandler(404)
    def not_found(_):
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(405)
    def method_not_allowed(_):
        return jsonify({"error": "Method not allowed"}), 405

    @app.errorhandler(500)
    def internal_error(_):
        return jsonify({"error": "Internal server error"}), 500

    return app


app = create_app()


if __name__ == "__main__":
    warnings.filterwarnings(
        "ignore",
        message=r"resource_tracker: There appear to be .* leaked semaphore objects.*",
        category=UserWarning,
    )

    debug_enabled = config.DEBUG
    use_reloader = os.environ.get("FLASK_RELOAD", "0") == "1"

    # With the reloader on, Flask starts a parent and child process.
    # Print banner only in the active child process to avoid duplicates.
    should_print_banner = not use_reloader or os.environ.get("WERKZEUG_RUN_MAIN") == "true"
    if should_print_banner:
        print("=" * 60)
        print("Memoria AI Medical Hub")
        print("API base: http://127.0.0.1:5000")
        print(
            f"Default login: {config.DEFAULT_USER['username']} / {config.DEFAULT_USER['password']}"
        )
        print(f"Ollama model: {config.OLLAMA_MODEL}")
        print(f"Debug: {'on' if debug_enabled else 'off'} | Reloader: {'on' if use_reloader else 'off'}")
        print("=" * 60)

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=debug_enabled,
        use_reloader=use_reloader,
        threaded=True,
    )
