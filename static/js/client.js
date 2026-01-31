function startSession() {
    const duration = document.getElementById('duration').value;
    const mode = document.getElementById('mode').value;

    fetch('/api/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ duration, mode })
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === 'started') {
            window.location.reload();
        }
    });
}

function breakSession() {
    window.location.href = '/excuse';
}

function submitExcuse() {
    const excuse = document.getElementById('excuse').value;
    if (!excuse) return;

    fetch('/api/break', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ excuse })
    })
    .then(res => res.json())
    .then(data => {
        window.location.href = '/';
    });
}

// Timer Logic for Focus Page
if (window.initialStatus) {
    let remaining = window.initialStatus.remaining;
    const display = document.getElementById('timer-display');

    if (display) {
        // VISIBILITY ENFORCER (The Watcher)
        document.addEventListener("visibilitychange", () => {
            if (document.hidden) {
                // If they leave, we can either:
                // 1. Break session immediately (Hardcore)
                // 2. Play a sound / Alert
                // 3. Just log it? 
                // Let's do a hard alert for now
                alert("⚠️ FOCUS BREACH DETECTED ⚠️\n\nReturning to non-focus windows is prohibited.");
            }
        });

        const interval = setInterval(() => {
            remaining--;
            
            if (remaining <= 0) {
                clearInterval(interval);
                fetch('/api/complete', { method: 'POST' })
                .then(() => window.location.href = '/');
                return;
            }

            const m = Math.floor(remaining / 60).toString().padStart(2, '0');
            const s = (remaining % 60).toString().padStart(2, '0');
            display.innerText = `${m}:${s}`;
        }, 1000);
    }
}
