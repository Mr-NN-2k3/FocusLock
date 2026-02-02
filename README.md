FocusLock

“Authority over your own mind.”

FocusLock is a behavior enforcement system for deep work.
It replaces motivation with rules, accountability, and server-side authority.

This is not a typical Pomodoro or focus timer.
FocusLock treats focus as a contract — once started, it cannot be casually abandoned without consequence.

🧠 Core Philosophy

System > User
The system is the authority. User actions are requests, not commands.

Time Is Sacred
All timing is enforced server-side. The client never decides time.

Failure Is Allowed, Denial Is Not
Breaking focus requires an explicit excuse, permanently logged.

History Is Truth
All behavior is recorded as append-only events. No silent edits. No state overwrites.

🚀 Features
✅ Implemented (MVP Authority)

Server-Authoritative Focus Sessions

Sessions are enforced by backend time, not client timers.

Event-Sourced Architecture

All actions (START, BROKEN, COMPLETE) are stored as immutable events in SQLite.

Forced Excuse Logging

You cannot end a session without admitting why you failed.

Single Active Session Rule

Only one focus contract can exist at a time.

Glassmorphism “System UI”

High-contrast, distraction-free interface designed to induce flow.

Analytics & Event Stream

Visual audit of your behavior and session outcomes.

🧪 In Progress (Advanced V1)

Progressive penalties for breaking focus

Tab-switch and visibility violation logging

Failure pattern analytics (time-based, reason-based)

Suspicious offline gap detection

🔮 Planned (Flagship V2)

Predictive focus failure warnings

Focus Debt system (unpaid minutes accumulate)

Offline-resilient local-first sync

Cryptographic integrity (tamper-evident event history)

🏗 Architecture Overview
Backend (Authority Layer)

Python 3

Flask

SQLite (Append-Only Event Log)

The backend is the single source of truth for:

session state

time progression

behavioral history

Frontend (Execution Layer)

HTML5 / CSS3

Vanilla JavaScript

Glassmorphism UI with strict visual hierarchy

The frontend:

displays state

reports user actions

never enforces rules

🧾 Event-Sourced Design

FocusLock does not store mutable session state.

Instead, it stores events:

SESSION_START
SESSION_BREAK_ATTEMPT
SESSION_BROKEN
SESSION_COMPLETE


All current state is derived by replaying events.

This enables:

behavioral analytics

tamper detection

focus debt calculation

future AI prediction

📂 Project Structure
focuslock/
│
├── app/
│   ├── core/
│   │   ├── engine.py        # Focus logic & authority
│   │   ├── store.py         # Event-sourced SQLite store
│   │   └── __init__.py
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

▶️ How to Run FocusLock
1️⃣ Prerequisites

Python 3.9+

pip (Python package manager)

2️⃣ Install Dependencies
pip install flask


(No heavy frameworks. No unnecessary dependencies.)

3️⃣ Start the System
python run.py

4️⃣ Access the Interface

Open your browser and go to:

http://localhost:5000

🔐 System Rules (Important)

You cannot start a new session if one is already active.

You cannot end a session silently.

All failures are logged permanently.

The system’s record is final.

Deleting the database is equivalent to resetting your discipline history.

📊 Analytics

Visit:

/analytics


To view:

total sessions

failures

consistency rate

full event stream

This is a behavioral audit, not motivation fluff.

🧑‍💻 Contributors

Niitin

Nevil

📌 Positioning (For Evaluators & Recruiters)

FocusLock demonstrates:

event-sourced backend design

authoritative state control

disciplined system architecture

psychological UX aligned with product goals

This project prioritizes correctness, authority, and integrity over convenience.

⚠️ Disclaimer

FocusLock is intentionally strict.

If you are looking for:

gentle reminders

flexible timers

motivational quotes

This system is not for you.
