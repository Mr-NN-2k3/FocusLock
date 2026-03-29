from flask import Flask, render_template, request, jsonify, make_response
from backend.engine import FocusEngine

app = Flask(__name__, template_folder="templates", static_folder="static")
engine = FocusEngine()

# Bug #14 (partial): Add CORS headers for Flutter/web frontend compatibility.
# For production, replace with flask-cors + auth + rate limiting.
@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/analytics")
def analytics():
    from backend.store import EventStore
    store = EventStore()
    events = store.get_events()

    total = sum(1 for e in events if e["type"] == "SESSION_START")
    broken = sum(1 for e in events if e["type"] == "SESSION_BROKEN")
    predicted = sum(1 for e in events if e["type"] == "FAILURE_PREDICTED")

    rate = 0 if total == 0 else int(((total - broken) / total) * 100)

    return render_template(
        "analytics.html",
        events=events,
        total_sessions=total,
        failures=broken,
        success_rate=rate,
        predicted=predicted
    )


@app.route("/api/start", methods=["POST"])
def api_start():
    data = request.json or {}

    # Bug #2 Fix: Validate that duration is present
    duration = data.get("duration")
    if duration is None:
        return jsonify({"error": "duration is required"}), 400

    # Bug #8 Fix: Reject invalid range (must be 1-1440 minutes i.e. 1 min to 24 hours)
    try:
        duration = int(duration)
    except (TypeError, ValueError):
        return jsonify({"error": "duration must be an integer"}), 400
    if duration <= 0 or duration > 1440:
        return jsonify({"error": "duration must be between 1 and 1440 minutes"}), 400

    # Handle whitelist/blacklist as either arrays or comma-separated strings
    wl = data.get("whitelist", [])
    bl = data.get("blacklist", [])
    if isinstance(wl, str):
        wl = [x.strip() for x in wl.split(",") if x.strip()]
    if isinstance(bl, str):
        bl = [x.strip() for x in bl.split(",") if x.strip()]

    engine.start_session(
        duration,
        data.get("mode", "deep"),
        whitelist=wl,
        blacklist=bl,
        intent=data.get("intent", "")
    )
    return jsonify({"status": "started"})


@app.route("/api/continue", methods=["POST"])
def api_continue():
    data = request.json
    success = engine.extend_session(data.get("duration", 10))
    return jsonify({"status": "extended" if success else "failed"})


@app.route("/api/stop", methods=["POST"])
def api_stop():
    success = engine.stop_session()
    return jsonify({"status": "stopped" if success else "failed"})


@app.route("/api/afk", methods=["POST"])
def api_afk():
    data = request.json
    if data.get("status"):
        engine.pause_session()
        return jsonify({"status": "paused"})
    else:
        engine.resume_session()
        return jsonify({"status": "resumed"})


@app.route("/api/status")
def api_status():
    return jsonify(engine.get_status())


@app.route("/api/violation", methods=["POST"])
def api_violation():
    engine.register_violation(request.json["type"])
    return jsonify({"status": "logged"})


@app.route("/api/heartbeat", methods=["POST"])
def api_heartbeat():
    engine.heartbeat()
    return jsonify({"status": "alive"})


@app.route("/api/break", methods=["POST"])
def api_break():
    engine.break_session(request.json.get("excuse", "No reason"))
    return jsonify({"status": "broken"})


@app.route("/api/integrity")
def api_integrity():
    valid, message = engine.store.verify_integrity()
    return jsonify({"valid": valid, "message": message})


@app.route("/api/feedback", methods=["POST"])
def api_feedback():
    from backend.logger import logger
    data = request.json
    logger.log_user_feedback(
        log_id=data.get("log_id", ""),
        correct_label=data.get("label", ""),
        comment=data.get("comment", "")
    )
    return jsonify({"status": "saved"})


if __name__ == "__main__":
    import os
    import subprocess
    import webbrowser
    import time
    from threading import Thread

    if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        print("Starting FocusLock... Training model first.")
        subprocess.run(["python", "backend/train_model.py"], check=True)
        print("Model trained. Starting Web Server...")

        def open_browser():
            time.sleep(1.5)
            webbrowser.open("http://127.0.0.1:5000/")

        Thread(target=open_browser, daemon=True).start()

    app.run(debug=True)
