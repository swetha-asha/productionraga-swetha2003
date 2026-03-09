async function sendMessage() {
    const userInput = document.getElementById("user-input");
    const message = userInput.value.trim();
    const chatBox = document.getElementById("chat-box");
    const sendBtn = document.getElementById("send-btn");

    if (message === "") return;

    // 1. Add User Message
    addMessage(message, 'user');
    userInput.value = "";

    // 2. Add Loading Indicator
    const botMsgId = "bot-" + Date.now();
    addMessage('<span class="loading">Thinking</span>', 'bot', botMsgId);

    // Disable input while thinking
    userInput.disabled = true;
    sendBtn.disabled = true;

    // 0. Get or Init Session ID
    let sessionId = localStorage.getItem("rag_session_id");
    if (!sessionId) {
        sessionId = "sess-" + Math.random().toString(36).substr(2, 9);
        localStorage.setItem("rag_session_id", sessionId);
    }

    try {
        const response = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                message: message,
                sessionId: sessionId
            })
        });

        const data = await response.json();

        // 3. Update Bot Message
        updateMessage(botMsgId, data.reply || data.error || "Sorry, something went wrong.");

        if (data.action) {
            handleResponseActions(data.action);
        }
    } catch (error) {
        updateMessage(botMsgId, "Failed to connect to the server.");
    } finally {
        userInput.disabled = false;
        sendBtn.disabled = false;
        userInput.focus();
    }
}

function addMessage(text, sender, id = null) {
    const chatBox = document.getElementById("chat-box");
    const msgDiv = document.createElement("div");
    msgDiv.className = `message ${sender}-message`;
    if (id) msgDiv.id = id;

    const avatar = sender === 'user' ? 'U' : 'AI';

    msgDiv.innerHTML = `
        <span class="avatar">${avatar}</span>
        <div class="bubble">${text}</div>
    `;

    chatBox.appendChild(msgDiv);
    chatBox.scrollTop = chatBox.scrollHeight;
}

function updateMessage(id, newText) {
    const msgDiv = document.getElementById(id);
    if (msgDiv) {
        const bubble = msgDiv.querySelector(".bubble");
        bubble.innerHTML = newText;
        document.getElementById("chat-box").scrollTop = document.getElementById("chat-box").scrollHeight;
    }
}

function useChip(text) {
    document.getElementById("user-input").value = text;
    sendMessage();
}

function startSignup() {
    document.getElementById("user-input").value = "sign up";
    sendMessage();
}

function startSignin() {
    document.getElementById("user-input").value = "login";
    sendMessage();
}

function clearChat() {
    localStorage.removeItem("rag_session_id");
    location.reload(); // Hard reset for UI buttons too
}

// Update the sendMessage handling of actions
async function handleResponseActions(action) {
    if (action === "AUTH_SUCCESS") {
        const signinBtn = document.getElementById("signin-btn");
        signinBtn.classList.add("btn-highlight");
        setTimeout(() => signinBtn.classList.remove("btn-highlight"), 3000);
    }
}

// Handle Enter Key
document.getElementById("user-input").addEventListener("keypress", function (e) {
    if (e.key === "Enter") {
        sendMessage();
    }
});
