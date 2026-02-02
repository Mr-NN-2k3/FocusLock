
# FocusLock

**Authority over your own mind.**

FocusLock is a **behavior enforcement system for deep work**.  
It replaces motivation with **rules, accountability, and server-side authority**.

This is **not** a Pomodoro timer.  
FocusLock treats focus as a **contract** — once started, it cannot be casually abandoned without consequence.

---

## 🆕 What's New (v1.1)

### 👁️ Intelligent Pattern Monitoring
The system now watches *you*.
- **Active Window Tracking**: FocusLock monitors your active applications. If you switch to an unauthorized window (e.g., social media, games), the system detects it immediately.
- **Distraction Flashing**: The interface aggressively flashes red to snap you out of a distraction loop.

### ⚖️ The AI Court
Context switching is sometimes necessary, but never free.
- **Justification Required**: If you leave the focus window, you must explain why.
- **Automated Judgment**: The system evaluates your excuse. Valid research is allowed; vague excuses are penalized as violations.

### 🔀 Conditional Deep Work
- **Standard Mode**: strict timing, but standard app permissions.
- **Deep Mode**: Total lockdown. Fullscreen enforcement, strict window monitoring, and zero tolerance for unrelated activities.

---

## 🧠 Core Philosophy

### System > User
The system is the authority.  
User actions are *requests*, not commands.

### Time Is Sacred
All timing is enforced **server-side**.  
The client never decides time.

### Failure Is Allowed, Denial Is Not
Breaking focus requires an **explicit excuse**, permanently logged.

### History Is Truth
All behavior is recorded as **append-only events**.  
No silent edits. No state overwrites.

---

## 🚀 Features

### ✅ Implemented (MVP Authority)

- **Server-Authoritative Focus Sessions**  
  Sessions are enforced by backend time, never client timers.

- **Event-Sourced Architecture**  
  All actions (`START`, `BROKEN`, `COMPLETE`) are stored as immutable events in SQLite.

- **Cryptographic Event Chain**  
  Every event is hashed (SHA-256) and linked to the previous event. Any manual editing of the database breaks the chain and triggers a system alert.

- **Focus Debt System**  
  Time owes you. If you break a session, the remaining time is added to your "Focus Debt". It accumulates until paid.

- **Forced Excuse Logging**  
  You cannot end a session without admitting why you failed.

- **Offline-Resilient Architecture**  
  Local-first design ensures functionality without internet, syncing state upon reconnection.

- **Single Active Session Rule**  
  Only one focus contract may exist at a time.

- **Glassmorphism System UI**  
  High-contrast, distraction-free interface designed to induce flow.

- **Analytics & Event Stream**  
  Visual audit of behavior and session outcomes.

- **Predictive Failure Detection**  
  Status checks analyze patterns (fatigue, violations) to warn of impending failure.

---

### 🧪 Future Experiments

- **Social Focus Contracts** (Multiplayer accountability)
- **Hardware Integration** (Locking specific apps/sites via OS APIs)

---

## 🏗 Architecture Overview

### Backend — Authority Layer

- Python 3  
- Flask  
- SQLite (Append-Only Event Log + SHA-256 Chain)

The backend is the **single source of truth** for:

- session state  
- time progression  
- behavioral history  
- **integrity verification**

---

### Frontend — Execution Layer

- HTML5 / CSS3  
- Vanilla JavaScript  
- Glassmorphism UI with strict visual hierarchy  

The frontend:

- displays state  
- reports user actions  
- **never enforces rules**

---

## 🧾 Event-Sourced Design

FocusLock stores **no mutable session state**.

Instead, it records events:

- `SESSION_START`  
- `SESSION_BREAK_ATTEMPT`  
- `SESSION_BROKEN`  
- `SESSION_COMPLETE`

All current state is **derived by replaying events**.

This enables:

- behavioral analytics  
- tamper detection (via Hash Chain)  
- focus-debt calculation  
- future AI prediction

---

## 📂 Project Structure

```

focuslock/
│
├── app/
│   ├── core/
│   │   ├── engine.py        # Focus logic & authority
│   │   ├── store.py         # Event-sourced SQLite store + Crypto
│   │   └── **init**.py
│   │
│   ├── templates/
│   │   ├── base.html
│   │   ├── index.html
│   │   ├── focus.html
│   │   ├── excuse.html
│   │   └── analytics.html
│   │
│   ├── static/
│   │   ├── css/
│   │   │   └── main.css
│   │   └── js/
│   │       └── client.js
│
├── focuslock.db             # SQLite event log (auto-created)
├── run.py                   # Application entry point
└── README.md

````

---

## ▶️ Running FocusLock

### 1️⃣ Prerequisites

- Python 3.9+  
- pip  

### 2️⃣ Install Dependencies

```bash
pip install flask
````

(No heavy frameworks. No unnecessary dependencies.)

### 3️⃣ Start the System

```bash
python run.py
```

### 4️⃣ Open the Interface

Navigate to:

```
http://localhost:5000
```

---

## 🔐 System Rules (Non-Negotiable)

* You cannot start a new session if one is already active.
* You cannot end a session silently.
* All failures are logged permanently.
* The system’s record is final.
* **Debts must be paid.**

Deleting the database is equivalent to **resetting your discipline history**.

---

## 📊 Analytics

Visit:

```
/analytics
```

View:

* total sessions
* failures
* consistency rate
* full event stream

This is a **behavioral audit**, not motivation fluff.

---

## 🧑‍💻 Contributors

* **Nitin**
* **Nevil**

---

## 📌 Positioning (For Evaluators & Recruiters)

FocusLock demonstrates:

* event-sourced backend design
* authoritative state control
* disciplined system architecture
* psychological UX (Focus Debt, Prediction)
* cryptographic data integrity

Correctness, authority, and integrity are prioritized over convenience.

---

## ⚠️ Disclaimer

FocusLock is intentionally strict.

If you are looking for:

* gentle reminders
* flexible timers
* motivational quotes

**This system is not for you.**
