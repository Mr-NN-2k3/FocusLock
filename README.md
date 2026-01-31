# FocusLock

**"Authority over your own mind."**

FocusLock is a behavior enforcement system designed to help you strictly manage your focus sessions. It replaces "motivation" with "system rules".

## Tech Stack
- **Core**: Python 3 (Flask) - Handles logic, time authority, and data.
- **Interface**: HTML5 / CSS3 (Glassmorphism) - Accessible via Browser.
- **Persistence**: Local JSON (`focuslock_data.json`).

## How to Run

1.  **Start the System**:
    ```powershell
    python run.py
    ```
2.  **Access the Interface**:
    Open [http://localhost:5000](http://localhost:5000) in your browser.

## Features
- **Strict Sessions**: Once started, the system tracks time authoritatively.
- **Excuse Log**: You cannot simply "stop". You must admit *why* you failed.
- **Premium UI**: Designed to induce a "Flow State" with high-contrast, deep-focus aesthetics.
