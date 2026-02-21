document.addEventListener('DOMContentLoaded', () => {
    const startForm = document.getElementById('start-form');
    const sessionSetupView = document.getElementById('session-setup-view');
    const sessionActiveView = document.getElementById('session-active-view');
    const timerDisplay = document.getElementById('timer-display');
    const breakBtn = document.getElementById('break-btn');
    const violationOverlay = document.getElementById('violation-overlay');
    const themeToggle = document.getElementById('theme-toggle');

    let currentTheme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', currentTheme);
    themeToggle.textContent = `THEME: ${currentTheme.toUpperCase()}`;

    themeToggle.addEventListener('click', () => {
        currentTheme = currentTheme === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', currentTheme);
        localStorage.setItem('theme', currentTheme);
        themeToggle.textContent = `THEME: ${currentTheme.toUpperCase()}`;
    });

    // -------- OPTIMIZED TIMER LOGIC --------
    let localRemaining = 0;
    let timerInterval = null;
    let isTimerRunning = false;

    function startLocalTimer() {
        if (isTimerRunning) return;
        isTimerRunning = true;
        
        if (timerInterval) clearInterval(timerInterval);
        timerInterval = setInterval(() => {
            if (localRemaining > 0) {
                localRemaining--;
                updateTimerDisplay(localRemaining);
            } else {
                // Time up - Force a status check to confirm completion
                checkStatus(); 
            }
        }, 1000);
    }

    function stopLocalTimer() {
        isTimerRunning = false;
        if (timerInterval) clearInterval(timerInterval);
    }

    function updateTimerDisplay(seconds) {
        if (!timerDisplay) return;
        const mins = Math.floor(seconds / 60).toString().padStart(2, '0');
        const secs = (seconds % 60).toString().padStart(2, '0');
        timerDisplay.textContent = `${mins}:${secs}`;
    }

    // -------- API INTERACTIONS --------

    if (startForm) {
        startForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const duration = document.getElementById('duration').value;
            const mode = document.getElementById('mode').value;
            const whitelist = document.getElementById('whitelist').value;
            const blacklist = document.getElementById('blacklist').value;

            try {
                if (mode === 'deep') {
                    try { await document.documentElement.requestFullscreen(); } 
                    catch (e) { console.log("Fullscreen denied", e); }
                }

                const res = await fetch('/api/start', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ duration, mode, whitelist, blacklist })
                });
                const data = await res.json();
                if (data.status === 'started') {
                    updateUI(true);
                }
            } catch (err) {
                console.error("Start failed", err);
            }
        });
    }

    if (breakBtn) {
        breakBtn.addEventListener('click', async () => {
            const excuse = prompt("CRITICAL: Why are you breaking the contract?");
            if (!excuse) return;

            await fetch('/api/break', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ excuse })
            });
            updateUI(false);
        });
    }

    async function checkStatus() {
        try {
            const res = await fetch('/api/status');
            const status = await res.json();
            
            // Handle Violation Overlay
            if (violationOverlay) {
                if (status.is_distracted) {
                    violationOverlay.classList.remove('hidden');
                } else {
                    violationOverlay.classList.add('hidden');
                }
            }

            // Update User Stats
            if (status.user_stats) {
                const levelEl = document.getElementById('user-level');
                const xpEl = document.getElementById('user-xp');
                if (levelEl) levelEl.textContent = status.user_stats.level;
                if (xpEl) xpEl.textContent = status.user_stats.xp;
            }

            if (status.active) {
                // SYNC LOCAL TIMER
                // We rely on server truth for keeping it accurate
                localRemaining = status.remaining;
                startLocalTimer(); 
                
                showActiveSession(status);
            } else {
                stopLocalTimer();
                if (status.completed && status.summary) {
                    const desc = `Congratulations on your focus of ${status.summary.duration} mins!\n\nDetailed Description:\nMode: ${status.summary.mode.toUpperCase()}\nGoal/Intent: ${status.summary.intent || 'None'}\nViolations Detected: ${status.summary.violations}\nPenalties Incurred: ${status.summary.penalties} seconds\n\nTotal XP Earned: ${status.user_stats.xp}`;
                    alert(desc);
                }
                showSetup();
            }
        } catch (err) {
            console.error("Status check failed", err);
        }
    }

    function showActiveSession(status) {
        if (!sessionActiveView) return;
        sessionSetupView.classList.add('hidden');
        sessionActiveView.classList.remove('hidden');

        // Initial Display Update
        updateTimerDisplay(status.remaining);
        
        // Paused Visuals
        if (timerDisplay) {
            if (status.paused) {
                timerDisplay.style.opacity = "0.5";
            } else {
                timerDisplay.style.opacity = "1";
            }
        }

        const penaltiesEl = document.getElementById('session-penalties');
        if (penaltiesEl) penaltiesEl.textContent = status.penalties;
        
        // Prediction Alert
        const predAlert = document.getElementById('prediction-alert');
        if (predAlert) {
            if (status.prediction && status.prediction.warning) {
                predAlert.classList.remove('hidden');
                const reasonEl = document.getElementById('prediction-reason');
                if (reasonEl) reasonEl.textContent = status.prediction.reasons.join(", ");
            } else {
                predAlert.classList.add('hidden');
            }
        }
    }

    function showSetup() {
        if (!sessionSetupView) return;
        sessionSetupView.classList.remove('hidden');
        sessionActiveView.classList.add('hidden');
        if (violationOverlay) violationOverlay.classList.add('hidden');
    }

    function updateUI(active) {
        if (active) {
            checkStatus();
        } else {
            showSetup();
        }
    }

    // Init: Poll every 10 seconds instead of 1 second
    setInterval(checkStatus, 10000);
    checkStatus();
});
