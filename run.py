from flask import Flask, render_template, jsonify, request, redirect, url_for
from app.core.engine import FocusEngine

app = Flask(__name__)
engine = FocusEngine()

@app.route('/')
def index():
    status = engine.get_status()
    if status.get("active"):
        return redirect(url_for('focus'))
    return render_template('index.html')

@app.route('/focus')
def focus():
    status = engine.get_status()
    if not status.get("active"):
        return redirect(url_for('index'))
    return render_template('focus.html', status=status)

@app.route('/excuse')
def excuse():
    return render_template('excuse.html')

@app.route('/api/start', methods=['POST'])
def start_session():
    data = request.json
    engine.start_session(data.get('duration', 25), data.get('mode', 'deep'))
    return jsonify({"status": "started"})

@app.route('/api/status')
def get_status():
    return jsonify(engine.get_status())

@app.route('/api/break', methods=['POST'])
def break_session():
    data = request.json
    engine.break_session(data.get('excuse'))
    return jsonify({"status": "broken"})

@app.route('/api/complete', methods=['POST'])
def complete_session():
    engine.complete_session()
    return jsonify({"status": "completed"})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
