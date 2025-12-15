const messagesContainer = document.getElementById('messagesContainer');
const questionInput = document.getElementById('questionInput');
const chatForm = document.getElementById('chatForm');
const sendBtn = document.getElementById('sendBtn');
const spinner = document.getElementById('spinner');

function scrollToBottom() {
    setTimeout(() => {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }, 0);
}

function addMessage(text, isUser = false) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${isUser ? 'user-message' : 'bot-message'}`;

    const avatar = document.createElement('div');
    avatar.className = 'avatar';
    avatar.textContent = isUser ? '🙂' : '🤖';

    const body = document.createElement('div');
    body.className = 'message-body';

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.innerHTML = escapeHtml(String(text)).replace(/\n/g, '<br>');

    body.appendChild(contentDiv);
    if (isUser) {
        messageDiv.appendChild(body);
        messageDiv.appendChild(avatar);
    } else {
        messageDiv.appendChild(avatar);
        messageDiv.appendChild(body);
    }

    messagesContainer.appendChild(messageDiv);
    scrollToBottom();
}

function showLoadingIndicator() {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message bot-message';
    messageDiv.id = 'loading-indicator';

    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'loading';
    loadingDiv.innerHTML = '<div class="loading-dot"></div><div class="loading-dot"></div><div class="loading-dot"></div>';

    messageDiv.appendChild(loadingDiv);
    messagesContainer.appendChild(messageDiv);
    scrollToBottom();
}

function removeLoadingIndicator() {
    const loadingIndicator = document.getElementById('loading-indicator');
    if (loadingIndicator) loadingIndicator.remove();
}

async function sendMessage(event) {
    event.preventDefault();
    const question = questionInput.value.trim();
    if (!question) return;

    addMessage(question, true);
    questionInput.value = '';

    showLoadingIndicator();
    sendBtn.disabled = true;
    spinner.style.display = 'inline-block';

    try {
        const response = await fetch('/api', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question })
        });

        if (!response.ok) throw new Error(`API error: ${response.status}`);
        const data = await response.json();
        removeLoadingIndicator();

        if (data.success) {
            addStructuredResponse(data);
        } else {
            addMessage('Error: ' + (data.error || 'Unknown'), false);
        }
    } catch (err) {
        removeLoadingIndicator();
        console.error(err);
        addMessage('Connection error, please try again.', false);
    } finally {
        sendBtn.disabled = false;
        spinner.style.display = 'none';
        questionInput.focus();
    }
}

function addStructuredResponse(data) {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message bot-message';

    const avatar = document.createElement('div');
    avatar.className = 'avatar';
    avatar.textContent = '🤖';

    const body = document.createElement('div');
    body.className = 'message-body';

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content enhanced-reply';

    // Summary
    if (data.short) {
        const summaryBox = document.createElement('div');
        summaryBox.className = 'summary-box';
        summaryBox.innerHTML = `<strong>Summary:</strong><br>${escapeHtml(data.short).replace(/\n/g,"<br>")}`;
        contentDiv.appendChild(summaryBox);
    }

    // Steps
    const hasSteps = data.steps && Array.isArray(data.steps) && data.steps.length;
    if (hasSteps) {
        const stepBox = document.createElement('div');
        stepBox.className = 'step-box';

        const headerDiv = document.createElement('div');
        headerDiv.style.display = 'flex';
        headerDiv.style.justifyContent = 'space-between';
        headerDiv.style.alignItems = 'center';
        headerDiv.style.marginBottom = '6px';

        const title = document.createElement('div');
        title.innerHTML = '<strong>Steps:</strong>';

        const copyBtn = document.createElement('button');
        copyBtn.className = 'copy-btn';
        copyBtn.textContent = 'Copy Steps';
        copyBtn.onclick = () => {
            navigator.clipboard.writeText(data.steps.join("\n"));
            copyBtn.textContent = 'Copied!';
            setTimeout(() => (copyBtn.textContent = 'Copy Steps'), 1200);
        };

        headerDiv.appendChild(title);
        headerDiv.appendChild(copyBtn);
        stepBox.appendChild(headerDiv);

        const ol = document.createElement('ol');
        data.steps.forEach(s => {
            const li = document.createElement('li');
            li.textContent = s;
            ol.appendChild(li);
        });
        stepBox.appendChild(ol);
        contentDiv.appendChild(stepBox);
    }

    // Full answer (if no steps)
    if (!hasSteps) {
        const ansBox = document.createElement('div');
        ansBox.className = 'answer-box';
        ansBox.innerHTML = `${escapeHtml(data.answer || '').replace(/\n/g,"<br>")}`;
        contentDiv.appendChild(ansBox);
    }

    // Follow-up tip
    if (data.follow_up) {
        const followBox = document.createElement('div');
        followBox.className = 'followup-box';
        followBox.innerHTML = `<strong>Tip:</strong> ${escapeHtml(data.follow_up)}`;
        contentDiv.appendChild(followBox);
    }

    body.appendChild(contentDiv);
    messageDiv.appendChild(avatar);
    messageDiv.appendChild(body);
    messagesContainer.appendChild(messageDiv);
    scrollToBottom();
}

function escapeHtml(str) {
    return str.replace(/[&"'<>]/g, m => ({'&':'&amp;','"':'&quot;',"'":'&#39;','<':'&lt;','>':'&gt;'}[m]));
}

window.addEventListener('load', () => questionInput.focus());
questionInput.addEventListener('keypress', e => {
    if(e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        chatForm.dispatchEvent(new Event('submit'));
    }
});
