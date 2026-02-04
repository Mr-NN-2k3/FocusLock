from flask import Flask, render_template, request, jsonify
from app.core.engine import FocusEngine

app = Flask(__name__)
engine = FocusEngine()


@app.route("/")
def index():
    status = engine.get_status()
    # ONLY Deep Work (Strict) forces you into the lock screen
    if status.get("active") and status.get("mode") == "deep":
        return render_template("focus.html", status=status)
    return render_template("index.html", status=status)


@app.route("/excuse")
def excuse():
    return render_template("excuse.html")


@app.route("/analytics")
def analytics():
    from app.core.store import EventStore
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
    data = request.json
    keywords = data.get("allowed_keywords", "").split(",")
    engine.start_session(data["duration"], data["mode"], allowed_keywords=keywords)
    return jsonify({"status": "started"})


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


@app.route("/api/evaluate", methods=["POST"])
def api_evaluate():
    result = engine.classify_activity(request.json["reason"])
    return jsonify({"classification": result})


@app.route("/api/heartbeat", methods=["POST"])
def api_heartbeat():
    engine.heartbeat()
    return jsonify({"status": "alive"})


@app.route("/api/break", methods=["POST"])
def api_break():
    engine.break_session(request.json["excuse"])
    return jsonify({"status": "broken"})


@app.route("/api/integrity")
def api_integrity():
    valid, message = engine.store.verify_integrity()
    return jsonify({"valid": valid, "message": message})


if __name__ == "__main__":
    app.run(debug=True)
