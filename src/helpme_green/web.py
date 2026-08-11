INDEX_HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#101613">
<title>helpme.green</title>
<style>
:root {
  color-scheme: dark;
  --ink: #e4eee6;
  --muted: #9caea1;
  --quiet: #728277;
  --line: #34453a;
  --panel: #151f19;
  --panel-deep: #0c120f;
  --accent: #a7dc92;
  --accent-ink: #122016;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background: #101613;
  color: var(--ink);
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  font-size: 16px;
}
button, textarea, input { font: inherit; }
button { cursor: pointer; }
.shell { min-height: 100vh; }
.topbar {
  border-bottom: 1px solid var(--line);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 22px clamp(20px, 5vw, 72px);
}
.wordmark { color: var(--ink); font-size: 18px; letter-spacing: -.02em; }
.status { color: var(--muted); display: flex; align-items: center; gap: 9px; font-size: 13px; }
.status::before {
  content: "";
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--accent);
  box-shadow: 0 0 0 4px rgba(167, 220, 146, .1);
}
.topbar-actions { align-items: center; display: flex; gap: 17px; }
.new-conversation {
  background: transparent;
  border: 1px solid var(--line);
  border-radius: 6px;
  color: var(--muted);
  font-size: 12px;
  padding: 8px 11px;
}
.new-conversation:hover { border-color: #66805f; color: var(--ink); }
.new-conversation:disabled { cursor: wait; opacity: .55; }
.layout {
  width: min(1180px, calc(100% - 40px));
  margin: 0 auto;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 260px;
  gap: clamp(36px, 8vw, 112px);
  padding: clamp(54px, 9vh, 112px) 0 60px;
}
.main { min-width: 0; }
.eyebrow {
  color: var(--accent);
  font-size: 12px;
  letter-spacing: .11em;
  margin: 0 0 17px;
  text-transform: uppercase;
}
h1 {
  font-size: clamp(33px, 5vw, 48px);
  font-weight: 470;
  letter-spacing: -.055em;
  line-height: 1.02;
  margin: 0;
  max-width: 690px;
}
.intro {
  color: var(--muted);
  font-size: 17px;
  line-height: 1.6;
  margin: 21px 0 46px;
  max-width: 610px;
}
.conversation {
  border-top: 1px solid var(--line);
  margin-bottom: 24px;
}
.message {
  border-bottom: 1px solid rgba(52, 69, 58, .72);
  padding: 22px 0 24px;
}
.message-label {
  color: var(--quiet);
  font-size: 12px;
  letter-spacing: .08em;
  margin-bottom: 9px;
  text-transform: uppercase;
}
.message.user .message-label { color: var(--accent); }
.message-body {
  color: var(--ink);
  line-height: 1.65;
  max-width: 720px;
  white-space: pre-wrap;
}
.message.user .message-body { color: #cbd9cd; }
.composer {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 13px;
  transition: border-color .2s ease, box-shadow .2s ease;
}
.composer:focus-within {
  border-color: #66805f;
  box-shadow: 0 0 0 3px rgba(167, 220, 146, .07);
}
textarea {
  background: transparent;
  border: 0;
  color: var(--ink);
  display: block;
  min-height: 72px;
  outline: 0;
  resize: vertical;
  width: 100%;
}
textarea::placeholder { color: var(--quiet); }
.composer-footer {
  align-items: center;
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding-top: 10px;
}
.hint { color: var(--quiet); font-size: 12px; }
.send, .continue {
  background: var(--accent);
  border: 0;
  border-radius: 6px;
  color: var(--accent-ink);
  font-weight: 650;
  padding: 10px 17px;
}
.send:hover, .continue:hover { background: #c0ecab; }
.send:disabled { cursor: wait; opacity: .55; }
.rail {
  align-self: start;
  border-left: 1px solid var(--line);
  padding-left: 24px;
  position: sticky;
  top: 28px;
}
.rail h2 {
  font-size: 14px;
  font-weight: 600;
  letter-spacing: .01em;
  margin: 0 0 10px;
}
.rail-copy {
  color: var(--quiet);
  font-size: 13px;
  line-height: 1.5;
  margin: 0 0 23px;
}
.hearing { margin: 0; }
.hearing-row { border-top: 1px solid rgba(52, 69, 58, .72); padding: 13px 0 14px; }
.hearing-row dt {
  color: var(--quiet);
  font-size: 11px;
  letter-spacing: .09em;
  margin-bottom: 6px;
  text-transform: uppercase;
}
.hearing-row dd { color: #cbd9cd; font-size: 14px; line-height: 1.45; margin: 0; }
.background { border-top: 1px solid var(--line); margin-top: 26px; padding-top: 17px; }
.background summary { color: var(--muted); cursor: pointer; font-size: 13px; }
.background p { color: var(--quiet); font-size: 12px; line-height: 1.5; margin: 12px 0 0; }
.background ul { color: var(--quiet); font-size: 12px; line-height: 1.5; margin: 12px 0 0; padding-left: 17px; }
.auth-gate {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 10px;
  margin-bottom: 24px;
  padding: 18px;
}
.auth-gate[hidden] { display: none; }
.auth-gate p { color: var(--muted); font-size: 14px; line-height: 1.5; margin: 0 0 13px; }
.auth-row { display: flex; gap: 9px; }
.auth-row input {
  background: var(--panel-deep);
  border: 1px solid var(--line);
  border-radius: 6px;
  color: var(--ink);
  min-width: 0;
  padding: 10px 11px;
  width: 100%;
}
.auth-row input:focus { border-color: #66805f; outline: 0; }
.error { color: #f1b9a9; font-size: 13px; margin-top: 10px; }
@media (max-width: 780px) {
  .layout { display: block; padding-top: 56px; }
  .rail { border-left: 0; border-top: 1px solid var(--line); margin-top: 46px; padding: 25px 0 0; position: static; }
  .background { max-width: 520px; }
}
@media (max-width: 500px) {
  .topbar { padding: 18px 20px; }
  .status { font-size: 12px; }
  .layout { width: min(100% - 32px, 1180px); }
  h1 { font-size: 40px; }
  .intro { font-size: 16px; margin-bottom: 35px; }
  .composer-footer { align-items: flex-end; flex-direction: column; }
  .hint { align-self: flex-start; }
  .send { width: 100%; }
  .auth-row { align-items: stretch; flex-direction: column; }
  .continue { width: 100%; }
}
</style>
</head>
<body>
<div class="shell">
  <header class="topbar">
    <div class="wordmark">helpme.green</div>
    <div class="topbar-actions">
      <button class="new-conversation" id="newConversation" type="button">New conversation</button>
      <div class="status">Local assistant</div>
    </div>
  </header>
  <div class="layout">
    <main class="main">
      <h1>What are you trying to figure out?</h1>
      <p class="intro">Tell me what you have, what is happening with it, or what you want to change. We can work it out from there.</p>

      <section class="auth-gate" id="authGate" hidden>
        <p>This local console is protected. Enter its token once to start the conversation.</p>
        <form class="auth-row" id="authForm">
          <input id="token" type="password" autocomplete="off" placeholder="Console token">
          <button class="continue" type="submit">Continue</button>
        </form>
        <div class="error" id="authError" hidden></div>
      </section>

      <section class="conversation" id="conversation" aria-live="polite"></section>
      <form class="composer" id="composer">
        <textarea id="message" rows="3" placeholder="Tell me what you’re dealing with…" aria-label="Message"></textarea>
        <div class="composer-footer">
          <span class="hint">Enter to send · Shift+Enter for a new line</span>
          <button class="send" id="send" type="submit">Send</button>
        </div>
      </form>
    </main>

    <aside class="rail" aria-label="Conversation context">
      <h2>What I’m hearing</h2>
      <p class="rail-copy">This updates as you talk. It is a shared summary, not a form you have to complete.</p>
      <dl class="hearing">
        <div class="hearing-row"><dt>Object</dt><dd id="hearingObject">—</dd></div>
        <div class="hearing-row"><dt>Condition</dt><dd id="hearingCondition">—</dd></div>
        <div class="hearing-row"><dt>Goal</dt><dd id="hearingGoal">—</dd></div>
      </dl>
      <details class="background" id="background" hidden>
        <summary>Background I have available</summary>
        <p>These references can help orient the conversation. They are not proof that something is safe, permitted, or worth doing.</p>
        <ul id="sourceList"></ul>
      </details>
    </aside>
  </div>
</div>
<script>
(() => {
  let sessionId = null;
  let conversationGeneration = 0;
  let token = "";
  let starting = false;
  const conversation = document.getElementById("conversation");
  const composer = document.getElementById("composer");
  const message = document.getElementById("message");
  const send = document.getElementById("send");
  const newConversation = document.getElementById("newConversation");
  const authGate = document.getElementById("authGate");
  const authForm = document.getElementById("authForm");
  const authInput = document.getElementById("token");
  const authError = document.getElementById("authError");
  const hearingFields = {
    object: document.getElementById("hearingObject"),
    condition: document.getElementById("hearingCondition"),
    goal: document.getElementById("hearingGoal")
  };
  const background = document.getElementById("background");
  const sourceList = document.getElementById("sourceList");

  function headers() {
    const result = {"Content-Type": "application/json"};
    if (token) result.Authorization = "Bearer " + token;
    return result;
  }

  async function request(url, options) {
    const response = await fetch(url, Object.assign({}, options, {headers: headers()}));
    const body = await response.json().catch(() => ({}));
    if (response.status === 401) {
      authGate.hidden = false;
      authInput.focus();
      throw new Error("auth_required");
    }
    if (!response.ok) throw new Error(body.error || ("Request failed (" + response.status + ")"));
    return body;
  }

  function addMessage(role, text) {
    const article = document.createElement("article");
    article.className = "message " + role;
    const label = document.createElement("div");
    label.className = "message-label";
    label.textContent = role === "user" ? "You" : "helpme.green";
    const body = document.createElement("div");
    body.className = "message-body";
    body.textContent = text;
    article.append(label, body);
    conversation.appendChild(article);
    article.scrollIntoView({behavior: "smooth", block: "nearest"});
  }

  function updateContext(data) {
    const hearing = data && data.hearing ? data.hearing : {};
    Object.keys(hearingFields).forEach((key) => {
      hearingFields[key].textContent = hearing[key] || "—";
    });
    const sources = data && Array.isArray(data.sources) ? data.sources : [];
    sourceList.replaceChildren();
    sources.forEach((source) => {
      const item = document.createElement("li");
      item.textContent = source.label + (source.detail ? " — " + source.detail : "");
      sourceList.appendChild(item);
    });
    background.hidden = sources.length === 0;
  }

  function showConnectionError(error) {
    if (error && error.message === "auth_required") return;
    addMessage("assistant", "I couldn’t connect to the local assistant. Nothing has been decided from your message; try again in a moment.");
  }

  async function createSession() {
    if (starting || sessionId) return;
    starting = true;
    send.disabled = true;
    newConversation.disabled = true;
    try {
      const body = await request("/api/sessions", {method: "POST", body: "{}"});
      sessionId = body.session_id;
      addMessage("assistant", body.message || "Tell me what you have, what you are trying to figure out, or what you want to change.");
      message.focus();
    } catch (error) {
      showConnectionError(error);
    } finally {
      starting = false;
      send.disabled = false;
      newConversation.disabled = false;
    }
  }

  async function startNewConversation() {
    if (starting) return;
    conversationGeneration += 1;
    sessionId = null;
    message.value = "";
    conversation.replaceChildren();
    updateContext({});
    await createSession();
  }

  async function sendMessage(event) {
    event.preventDefault();
    const text = message.value.trim();
    if (!text || !sessionId || send.disabled) return;
    const requestGeneration = conversationGeneration;
    const requestSessionId = sessionId;
    message.value = "";
    addMessage("user", text);
    send.disabled = true;
    try {
      const body = await request("/api/sessions/" + encodeURIComponent(requestSessionId) + "/message", {
        method: "POST",
        body: JSON.stringify({message: text})
      });
      if (requestGeneration !== conversationGeneration || requestSessionId !== sessionId) return;
      addMessage("assistant", body.text || "I’m here. Tell me a little more about what you’re trying to do.");
      updateContext(body.data || {});
    } catch (error) {
      if (requestGeneration !== conversationGeneration || requestSessionId !== sessionId) return;
      showConnectionError(error);
      message.value = text;
    } finally {
      send.disabled = false;
      message.focus();
    }
  }

  authForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    token = authInput.value.trim();
    authError.hidden = true;
    sessionId = null;
    conversation.replaceChildren();
    await createSession();
    if (!sessionId) {
      authError.hidden = false;
      authError.textContent = "That token did not start a session. Check it and try again.";
    } else {
      authGate.hidden = true;
    }
  });
  composer.addEventListener("submit", sendMessage);
  message.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      composer.requestSubmit();
    }
  });
  newConversation.addEventListener("click", startNewConversation);
  createSession();
})();
</script>
</body>
</html>"""
