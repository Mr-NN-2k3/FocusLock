# FocusLock High-Level Roadmap

## 🧭 Strategy
**Current Version**: v1.1 ("The Watcher")
**Core Principle**: System > User.

We are moving from *detection* (now) to *cognition* (next).

---

## ✅ Phase 1: MVP Authority (Completed)
*Goal: Establishing the "Contract" and basic enforcement.*
- [x] **Core Timer**: Server-side authoritative timing.
- [x] **Basic Excuse**: Forcing honesty on failure.
- [x] **Glass Interface**: Premium aesthetics.
- [x] **Event-Log Architecture**: Immutable append-only history.

## ✅ Phase 2: The Watcher (Completed v1.1)
*Goal: Systems that see and judge.*
- [x] **Active Window Monitoring**: Hooks into OS APIs (`user32.dll`) to track foreground apps.
- [x] **Conditional Deep Work**: "Standard" vs "Deep" modes.
- [x] **The AI Court (Alpha)**: Keyword-based evaluation of context switching.
- [x] **Distraction Flashing**: Aggressive visual intervention on violation.

---

## 🚧 Phase 3: True Intelligence (Next Target)
*Goal: Replacing heuristics with actual cognition.*
- [ ] **Local LLM Integration**: Replace `keyword` matching with a local LLM (Phi-2 or Mistral) for semantic understanding of excuses.
- [ ] **Process Termination**: Move from "warning" to "killing" distraction processes (optional "Hardcore Mode").
- [ ] **Smart Resumption**: Auto-resuming sessions if distraction is brief and accidental.

## 🔮 Phase 4: Social & Physical (Future)
*Goal: External accountability.*
- [ ] **Multiplayer Contracts**: Linked sessions. If one fails, both fail.
- [ ] **Hardware Locks**: Integration with physical blockers (e.g., Internet disconnected via router API).
- [ ] **Public Debt Ledger**: Exposing Focus Debt to a public URL for accountability.

---

## 🏗 Architectural Decision Record (ADR)
**Decision 001: Event-Sourced Persistence**
*   **Context**: Advanced features (Analytics, Tamper Detection, Replay) require full history.
*   **Decision**: SQLite Append-Only Log.
*   **Benefit**: Enables "Time Travel" debugging and future AI training data.
