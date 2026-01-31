# FocusLock High-Level Roadmap

## 🧭 Strategy
We are following an engineering-first approach: **MVP Authority** -> **Advanced V1** -> **Flagship V2**.
The core principle is **System > User**.

---

## Phase 1: MVP Authority (Current)
*Goal: Establishing the "Contract" and basic enforcement.*
- [x] **Core Timer**: Server-side authoritative timing.
- [x] **Basic Excuse**: Forcing honesty on failure.
- [x] **Glass Interface**: Premium aesthetics (CSS Variables).
- [x] **Event-Log Architecture**: Moving from state-overwrite to event-sourcing (Preparation for V1).

## Phase 2: Advanced V1 (Next Target)
*Goal: "The Watcher" - Systems that detect and punish patterns.*
- [x] **Context-Aware Blocking**: Implemented via Page Visibility API (User cannot leave tab).
- [ ] **Progressive Penalties**: Breaking focus costs time (Cool-downs).
- [x] **Failure Pattern Mining**: Visualizing *why* you break (Analytics Dashboard).
- [ ] **Tamper Detection**: flagging suspicious "offline" gaps.

## Phase 3: Flagship V2 (The Ideal)
*Goal: "The Predictive Cage" - AI and deep psychological locks.*
- [ ] **Focus Failure Prediction**: AI warns you before you break.
- [ ] **Focus Debt System**: Unpaid focus minutes accumulate.
- [ ] **Offline-Resilience**: Local-first sync.
- [ ] **Cryptographic Integrity**: Hashing history so it cannot be edited.

---

## 🏗 Architectural Decision Record (ADR)
**Decision 001: Event-Sourced Persistence**
*   **Context**: Advanced features (Analytics, Tamper Detection, Replay) require full history, not just current state.
*   **Decision**: Move `Store` from "Snapshot" (overwriting JSON) to "Append-Only Event Log" (SQLite/JSON Lines).
*   **Benefit**: Enables "Time Travel" debugging of user behavior and "Focus Debt" calculation.
