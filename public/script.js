document.getElementById('startBtn').addEventListener('click', async () => {
    const startBtn = document.getElementById('startBtn');
    const logsOutput = document.getElementById('logsOutput');
    
    const botToken = document.getElementById('botToken').value.trim();
    const clientId = document.getElementById('clientId').value.trim();
    const clientSecret = document.getElementById('clientSecret').value.trim();
    const redirectUri = document.getElementById('redirectUri').value.trim();
    const guildId = document.getElementById('guildId').value.trim();
    
    const tokenInputText = document.getElementById('tokenInput').value.trim();
    const authsCacheText = document.getElementById('authsCache').value.trim();

    if(!botToken || !clientId || !clientSecret || !guildId) {
        alert("Please completely fill out all App Config parameters.");
        return;
    }

    let tokens = [];
    if (tokenInputText) {
        tokens = tokenInputText.split('\n').map(t => t.trim()).filter(t => t.length > 0);
    }

    let cachedAuths = [];
    if(authsCacheText) {
        try {
            cachedAuths = JSON.parse(authsCacheText);
        } catch(e) {
            alert("Cached Auths field must be a valid JSON Array framework layout.");
            return;
        }
    }

    if(tokens.length === 0 && cachedAuths.length === 0) {
        alert("Please provide at least one source token or a valid authorization cache configuration.");
        return;
    }

    // Freeze interface during runtime executions
    startBtn.disabled = true;
    startBtn.textContent = "Processing Queue...";
    appendLog("System", "Initialising server joiner engine workspace pipeline.");

    // Match original CLI architecture priority: Run cached session maps first
    if(cachedAuths && cachedAuths.length > 0) {
        appendLog("System", `Found ${cachedAuths.length} entries in saved cache. Direct processing routing active.`);
        for(const item of cachedAuths) {
            await runJoinPipeline({
                botToken, clientId, clientSecret, redirectUri, guildId,
                token: item.Token,
                accessToken: item.AccessToken
            });
        }
    } else {
        // Fallback execution stream processing the raw tokens list
        appendLog("System", `Spawning execution sequence handling ${tokens.length} tokens.`);
        for(const token of tokens) {
            await runJoinPipeline({
                botToken, clientId, clientSecret, redirectUri, guildId, token
            });
        }
    }

    startBtn.disabled = false;
    startBtn.textContent = "Execute OAuth Pipeline";
    appendLog("System", "All connection tasks finalized.");
});

async function runJoinPipeline(payload) {
    try {
        const response = await fetch('/api/join', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        // Safety Check: Ensure the server returned a success status before parsing JSON
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Server returned HTTP ${response.status}. Details: ${errorText.substring(0, 50)}...`);
        }

        const result = await response.json();
        const simplifiedToken = payload.token.substring(0, 22) + "...";

        if(result.success) {
            appendLog("Success", `${result.message} : Account token -> ${simplifiedToken}`);
        } else {
            appendLog("Denied", `${result.message} : Account token -> ${simplifiedToken}`);
        }
    } catch (error) {
        // This will now gracefully catch and display Vercel runtime errors in the UI
        appendLog("Denied", `Network Pipeline Fault: ${error.message}`);
    }
}

function appendLog(status, message) {
    const logsOutput = document.getElementById('logsOutput');
    const time = new Date().toLocaleTimeString();
    
    const entry = document.createElement('div');
    entry.className = 'log-entry';

    let statusClass = 'system-message';
    if(status === "Success") statusClass = 'log-status-success';
    if(status === "Denied") statusClass = 'log-status-denied';

    entry.innerHTML = `
        <span class="log-time">[${time}]</span>
        <span class="${statusClass}">[${status}]</span>
        <span class="log-desc">${message}</span>
    `;
    
    logsOutput.appendChild(entry);
    logsOutput.scrollTop = logsOutput.scrollHeight;
}

document.getElementById('clearLogs').addEventListener('click', () => {
    document.getElementById('logsOutput').innerHTML = '<span class="system-message">[System Status]: Log terminal cleared.</span>';
});
