# FocusLock
**Authority over your own mind.**

FocusLock is a **behavior enforcement system for deep work**.  
It replaces motivation with **rules, accountability, and server-side authority**.

This is **not** a Pomodoro timer.  
FocusLock treats focus as a **contract** — once started, it cannot be casually abandoned without consequence.

---

## 🆕 What's New (v2.0 Redesign)

### 🎨 Glassmorphism & UI Overhaul
- **Premium Flutter Frontend**: A completely reimagined desktop application using Flutter, featuring frosted glass cards, blurred backgrounds, soft shadows, and dynamic gradient animations.
- **Lightbox Warnings**: Native windows alerts are replaced with immersive, blurred Lightbox modals that freeze your session screen when a distraction is detected.
- **Session Continuation**: Sessions no longer instantly end when time runs out. A modal allows you to "Continue" and increment your time and maintaining your focus streak!

### 🧠 Expanded AI Classification System
- **Context-Aware Intent**: Focus categories expanded to include `Studying`, `Coding`, `Interview Preparation`, `Research`, `Writing`, and more.
- **Advanced Tolerance**: The heuristic engine intelligently forgives research concepts and platforms (like LeetCode, HackerRank, system design) while penalizing entertainment and shopping.
- **Whitelist Customization**: Per-session keyword whitelists so you can declare exactly what strings dictate safe focus zones.

### 🏆 Gamified Authority
- Discipline is now quantifiable via Multipliers & Streak tracking. 
- Completing and extending sequential focus loops significantly boosts your XP yield.

---

## 🧠 Core Philosophy

### System > User
The system is the authority.  
User actions are *requests*, not commands.

### Time Is Sacred
All timing is enforced **server-side**.  
The client never controls the actual time state.

### Failure Is Allowed, Denial Is Not
Breaking focus requires an **explicit excuse**, permanently logged.

### History Is Truth
All behavior is recorded as **append-only events**.  
No silent edits. No state overwrites.

---

## 🚀 Features

### ✅ Implemented (MVP Authority)

- **AI Intent Alignment Engine**  
  Monitors foreground windows and evaluates the contextual distance between the user's intent and their actual screen title using SentenceTransformers (`all-MiniLM-L6-v2`) and TF-IDF encodings.

- **Server-Authoritative Focus Sessions**  
  Sessions are enforced by backend time, never client timers.

- **Event-Sourced Architecture**  
  All actions (`START`, `BROKEN`, `EXTEND`, `COMPLETE`) are stored as immutable events in SQLite.

- **Cryptographic Event Chain**  
  Every event is hashed (SHA-256) and linked to the previous event. Any manual editing of the database breaks the chain and triggers a system alert.

- **Focus Debt System**  
  If you break a session, the remaining time is added to your "Focus Debt". It accumulates until paid.

- **Offline-Resilient Architecture**  
  Local-first design ensures functionality without internet.

- **Single Active Session Rule**  
  Only one focus contract may exist at a time.

- **Predictive Failure Detection**  
  Status checks analyze patterns (fatigue, violations) to warn of impending failure.

---

## 🏗 Architecture Overview

### Backend — Authority & AI Layer
- Python 3 & Flask
- Scikit-learn (RandomForest) & SentenceTransformers for AI Window Tracking
- SQLite (Append-Only Event Log + SHA-256 Chain)

The backend is the **single source of truth** for:
- Session state  
- AI prediction & Heuristic evaluating
- Time progression  
- Behavioral history  
- **Integrity verification**

### Frontend — Execution & Rendering Layer
- Flutter (Windows Desktop)
- Riverpod (State Management)
- Glassmorphism & Google Fonts
- Local Polling via HTTP

The frontend:
- Displays state beautifully
- Animates visual consequences (Lightboxes)
- Extends sessions via UX triggers
- **Never enforces rules/time inherently**

---

## 📂 Project Structure

```text
focuslock/
│
├── backend/
│   ├── engine.py        # Focus logic, extension overrides
│   ├── monitor.py       # ML Pipeline, Sentence Embedder, Win32 Observer
│   ├── store.py         # Event-sourced SQLite store + Crypto Hashing
│   ├── train_model.py   # AI Pipeline Training Script
│   └── dataset_generator.py
│
├── focuslock_app/       # THE NEW FLUTTER FRONTEND
│   ├── lib/
│   │   ├── main.dart
│   │   ├── providers.dart
│   │   ├── ui_components.dart
│   │   ├── api_service.dart
│   │   ├── setup_session.dart
│   │   └── active_session.dart
│   └── pubspec.yaml
│
├── templates/           # Legacy Diagnostics/Analytics views
├── focuslock.db         # SQLite event log (auto-created)
├── run.py               # Application Entry (System API)
└── README.md
```

---

## ▶️ Running FocusLock

### 1️⃣ Prerequisites
- Python 3.9+  
- Flutter SDK (with Desktop Windows support enabled)

### 2️⃣ Start the System API (Backend)
```bash
pip install flask sentence-transformers scikit-learn numpy ctypes joblib
python run.py
```
> The webserver runs natively on `http://127.0.0.1:5000` executing the API polling mechanism.

### 3️⃣ Start the Application (Frontend)
In a secondary terminal window:
```bash
cd focuslock_app
flutter pub get
flutter run -d windows
```

---

## 🔐 System Rules (Non-Negotiable)

* You cannot start a new session if one is already active.
* You cannot end a session silently.
* All failures are logged permanently.
* The system’s record is final.

Deleting the database is equivalent to **resetting your discipline history**.

---

## 🧑‍💻 Contributors

* **Nitin**
* **Nevil**

---

## ⚠️ Disclaimer

FocusLock is intentionally strict.

If you are looking for:
* gentle reminders
* flexible timers
* motivational quotes

**This system is not for you.**
