let sessionLocked = false;

// ======================
// Utility: Send Violation
// ======================
function sendViolation(eventType) {
    if (sessionLocked) return; // stop further calls
    sessionLocked = true;

    // --- Implement your server reporting logic here ---
    // e.g., WebSocket or fetch API
    // fetch('/api/violation', { ... })

    lockExam();       // lock UI immediately
    removeAllHandlers(); // stop all detection
}


function lockExam() {
    document.body.innerHTML = '<h1>Session locked due to violation</h1>';
}

let devToolsInterval;
function removeAllHandlers() {
    document.removeEventListener('fullscreenchange', handleFullscreenChange);
    window.removeEventListener('blur', handleWindowBlur);
    window.removeEventListener('focus', handleWindowFocus);
    document.removeEventListener('visibilitychange', handleVisibilityChange);
    document.removeEventListener('keydown', blockCopyPaste);
    document.removeEventListener('keydown', blockDangerousKeys);
    document.removeEventListener('contextmenu', blockContextMenu);
    document.removeEventListener('paste', handlePaste);
    clearInterval(devToolsInterval);
}

// ======================
// Fullscreen Enforcement
// ======================
function enforceFullscreen() {
    if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen().catch(() => {});
    }
}
function handleFullscreenChange() {
    if (!document.fullscreenElement) {
        sendViolation('fullscreenExit');
        enforceFullscreen(); // optionally force re-entry
    }
}
document.addEventListener('fullscreenchange', handleFullscreenChange);

// ======================
// Window Focus / Blur
// ======================
function handleWindowBlur() { sendViolation('windowBlur'); }
function handleWindowFocus() { sendViolation('windowFocus'); }
window.addEventListener('blur', handleWindowBlur);
window.addEventListener('focus', handleWindowFocus);

// ======================
// Tab Visibility
// ======================
function handleVisibilityChange() {
    if (document.hidden) sendViolation('tabHidden');
    else sendViolation('tabVisible');
}
document.addEventListener('visibilitychange', handleVisibilityChange);

// ======================
// Copy / Paste / Context Menu
// ======================
function blockCopyPaste(e) {
    if (e.ctrlKey && ['c','v','x','u'].includes(e.key.toLowerCase())) {
        e.preventDefault();
        sendViolation('copyPasteAttempt');
    }
}
function blockContextMenu(e) {
    e.preventDefault();
    sendViolation('contextMenuAttempt');
}
function handlePaste(e) {
    e.preventDefault();
    sendViolation('pasteAttempt');
}
document.addEventListener('keydown', blockCopyPaste);
document.addEventListener('contextmenu', blockContextMenu);
document.addEventListener('paste', handlePaste);

// ======================
// DevTools / Inspect Detection
// ======================
devToolsInterval = setInterval(() => {
    const gap = window.outerWidth - window.innerWidth;
    if (gap > 160) sendViolation('devToolsDetected');
}, 1500);

const devtoolsTrap = /./;
devtoolsTrap.toString = function() { sendViolation('consoleOpened'); return ''; };
console.log('%c', devtoolsTrap);

// ======================
// Forbidden Keys (F12, F11, Escape)
// ======================
function blockDangerousKeys(e) {
    if (['F12','F11','Escape'].includes(e.key)) {
        e.preventDefault();
        sendViolation(`forbiddenKey_${e.key}`);
    }
}
window.addEventListener('keydown', blockDangerousKeys);

// ======================
// Heartbeat (optional)
// ======================
setInterval(() => {
    if (sessionLocked) return;
    // --- send heartbeat to server if needed ---
}, 3000);

// ======================
// Initialize on Load
// ======================
window.addEventListener('load', () => {
    enforceFullscreen();
});






// Create a WebSocket connection to your server
const ws = new WebSocket('wss://yourserver.example/ws?sessionId=' + sessionId);

// Connection opened
ws.addEventListener('open', () => {
    console.log('WebSocket connected');
});

// Listen for messages from the server
ws.addEventListener('message', (event) => {
    try {
        const msg = JSON.parse(event.data);

        switch(msg.action) {
            case 'banned':
                lockExam('You are banned. Contact admin.');
                break;
            case 'appealed':
                unlockExam();
                break;
            case 'forceFullscreen':
                enforceFullscreen();
                break;
            case 'customMessage':
                alert(msg.text);
                break;
            default:
                console.log('Unknown server action:', msg);
        }
    } catch(e) {
        console.error('Invalid message', event.data);
    }
});

// Optional: reconnect if WebSocket closes
ws.addEventListener('close', () => {
    setTimeout(() => location.reload(), 3000); // simple reconnect
});

// Send client events to server
function sendViolation(eventType) {
    if (sessionLocked) return;
    sessionLocked = true;
    lockExam('Violation detected');

    // Send violation to server
    if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({userId, sessionId, eventType, timestamp: Date.now()}));
    }

    removeAllHandlers();
}






