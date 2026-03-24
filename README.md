# FocusLock
**Authority over your own mind.**

FocusLock is a **behavior enforcement system for deep work**.  
It replaces motivation with **rules, accountability, and server-side authority**.

This is **not** a Pomodoro timer.  
FocusLock treats focus as a **contract** — once started, it cannot be casually abandoned without consequence.

---

## 🆕 What's New (v3.0 Cognitive Engine Redesign)

### 🧠 True Cognitive Behavior Engine
- **Decoupled Architecture**: Strict separation of concerns (Monitor -> Feature Classifier -> Decision Engine). The system now treats raw events, extracts semantic features, and processes state cleanly without logic cross-contamination.
- **Hybrid AI Pipeline**: Fast heuristic passes mapped to a `<100ms` strict execution budget. If context is ambiguous, the system naturally falls back to `SentenceTransformers` embeddings.
- **Drift Detection & Awareness**: The system now distinguishes between a 10-second necessary task switch and a scrolling binge. Frequent window switching triggers a gentle `WARNING` overlay before locking down.

### 🎨 Glassmorphism & UI Overhaul
- **Premium Glassmorphism Design System**: Frosted glass panels, dynamic floating ambient orbs, and layered visual depth.
- **Activity Tracker & Confidence Gauges**: Real-time telemetry exposes exactly what the AI engine thinks of your active window, including Semantic Match and Confidence scores.
- **Custom Modals (No More OS Alerts)**: Distractions and warning drifts are handled by beautifully animated, non-intrusive edge glows or in-app modals.

### 🏆 Gamified Authority
- **Offline-Resilient Event Sourcing**: Every state transition (Pause, Extend, Complete) is cryptographically locked in a SQLite chain.
- **Accurate Progression Logging**: Time extensions (`SESSION_EXTEND`) correctly yield XP scaling.

---

## 🧠 Core Philosophy

### System > User
The system is the authority. User actions are *requests*, not commands.

### Time Is Sacred
All timing is enforced **server-side**. The client never controls the actual time state.

### History Is Truth
All behavior is recorded as **append-only events**. No silent edits. No state overwrites.

---

## 🚀 Features

- **Event-Driven AI Alignment Engine**  
  Monitors foreground windows and evaluates the contextual distance between the user's intended goal and their actual screen utilizing a hybrid heuristic-ML pipeline.
- **Drift Detection & Cooldown Interventions**  
  Provides soft intervention warnings (`WARNING` state) to snap the user back prior to registering definitive Focus Violations (`DISTRACTION` state).
- **Server-Authoritative Focus Sessions**  
  Sessions are strictly enforced by the python backend.
- **Cryptographic Event Chain**  
  Every event (`START`, `FOCUS_VIOLATION`, `PAUSED`) is hashed (SHA-256) and appended securely.
- **Data & Logging Pipeline**  
  Maintains structured logs (`backend/data/activity_log.jsonl`) and tracks ML training frames to continually augment the model over time.

---

## 🏗 Architecture Overview

### Backend — Event Driven Engine Layer
- **Language/Framework**: Python 3 & Flask
- **Data Layers**: Local SQLite & JSON Feature stores
- **Pipeline Components**:
  - `monitor.py` (Data Extractor via `psutil` / Windows API)
  - `classifier.py` (NLP & Scikit-Learn Feature Generator)
  - `engine.py` (State Machine & Drift Decision)
  
The backend acts as the immutable arbiter of focus states, tracking time, applying session penalties, and orchestrating the AI evaluations.

### Frontend — Execution & Rendering Layer
- Web Client / Flask Templates
- Vanilla CSS featuring CSS Variables and Backdrop-Filters
- Vanilla JS (Polling the API)

*(Also supports external client implementations like Flutter via the standard JSON API).*

---

## 📂 Project Structure

```text
focuslock/
│
├── backend/
│   ├── engine.py        # Decision State Machine, Drift, Cooldowns
│   ├── classifier.py    # Hybrid Feature Generator (Heuristics + NLP)
│   ├── monitor.py       # Data extraction (Window Title + Process Name)
│   ├── logger.py        # Structured Log initialization
│   ├── store.py         # Event-sourced SQLite store + Crypto Hashing
│   ├── train_model.py   # AI Pipeline Training Script
│   ├── dataset_generator.py
│   └── data/            # Local logging and ML staging data
│
├── focuslock_app/       # Legacy / Optional Flutter Desktop Frontend
│   └── lib/ ...
│
├── templates/           # Flask HTML Web Client
│   └── index.html       # Main UI Layout
├── static/              # Web Client Assets
│   ├── css/main.css     # Glassmorphism Design System
│   └── js/client.js     # Dom manipulation and Polling logic
│
├── focuslock.db         # SQLite event log (auto-created)
├── run.py               # Application Entry (Flask API)
└── README.md
```

---

## ▶️ Running FocusLock

### 1️⃣ Prerequisites
- **Python 3.9+**
- (Windows OS recommended for native Win32 window-tracking API compatibility)

### 2️⃣ Install Dependencies
```bash
pip install flask sentence-transformers scikit-learn numpy psutil joblib
```
*(Note: `ctypes` is standard in Python; you do not need to install `pywin32`)*

### 3️⃣ Start the Application
To run the server and UI organically:
```bash
python run.py
```
> The system will automatically execute the dataset generator (if missing) and open your default web browser to the Glassmorphism application located at `http://127.0.0.1:5000`.

---

## 🔐 System Rules (Non-Negotiable)

* You cannot start a new session if one is already active.
* You cannot end a session silently.
* All failures are logged permanently in the SQLite chain.
* The system’s decision classification is final.

Deleting the database is equivalent to **resetting your discipline history**.

---

## 🧑‍💻 Contributors

* **Nitin**
* **Nevil**

---

## ⚠️ Disclaimer

FocusLock is intentionally strict.

If you are looking for gentle reminders, flexible timers, or motivational quotes...
**This system is not for you.**
