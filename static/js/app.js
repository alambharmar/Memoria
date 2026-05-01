(function () {
  "use strict";

  // Guard: only run chat logic on the chat page
  if (!document.getElementById("chat-input")) return;

  /* -----------------------------------------------------------
     DOM References
     ----------------------------------------------------------- */
  const shell = document.getElementById("shell");
  const sidebar = document.getElementById("sidebar");
  const sidebarToggle = document.getElementById("sidebar-toggle");
  const sidebarOpenBtn = document.getElementById("sidebar-open-btn");
  const newChatBtn = document.getElementById("new-chat-btn");
  const historyList = document.getElementById("history-list");
  const chatStage = document.getElementById("chat-stage");
  const messagesEl = document.getElementById("messages");
  const chatForm = document.getElementById("chat-form");
  const chatInput = document.getElementById("chat-input");
  const sendBtn = document.getElementById("send-btn");
  const errorBanner = document.getElementById("error-banner");
  const errorText = document.getElementById("error-text");
  const errorDismiss = document.getElementById("error-dismiss");
  const profileTrigger = document.getElementById("profile-trigger");
  const profileDropdown = document.getElementById("profile-dropdown");

  /* -----------------------------------------------------------
     State
     ----------------------------------------------------------- */
  let conversations = [];
  let activeConvoId = null;
  let isSending = false;

  /* -----------------------------------------------------------
     Helpers
     ----------------------------------------------------------- */
  function uid() {
    return Date.now().toString(36) + Math.random().toString(36).slice(2, 7);
  }

  function escapeHtml(str) {
    const d = document.createElement("div");
    d.textContent = str;
    return d.innerHTML;
  }

  function scrollToBottom() {
    requestAnimationFrame(function () {
      chatStage.scrollTo({ top: chatStage.scrollHeight, behavior: "smooth" });
    });
  }

  /* -----------------------------------------------------------
     Textarea Auto-Resize
     ----------------------------------------------------------- */
  chatInput.addEventListener("input", function () {
    this.style.height = "auto";
    this.style.height = Math.min(this.scrollHeight, 160) + "px";
    sendBtn.classList.toggle("active", this.value.trim().length > 0);
  });

  /* -----------------------------------------------------------
     Error Handling
     ----------------------------------------------------------- */
  function showError(msg) {
    errorText.textContent = msg;
    errorBanner.classList.add("visible");
    scrollToBottom();
  }

  function hideError() {
    errorBanner.classList.remove("visible");
  }

  errorDismiss.addEventListener("click", hideError);

  /* -----------------------------------------------------------
     Messages
     ----------------------------------------------------------- */
  function createMessageEl(role, content) {
    var article = document.createElement("article");
    article.className = "message " + (role === "user" ? "user-msg" : "ai-msg");
    var body = document.createElement("div");
    body.className = "msg-body";

    if (role === "user") {
      body.textContent = content;
    } else {
      body.innerHTML = formatAIResponse(content);
    }

    article.appendChild(body);
    return article;
  }

  function formatAIResponse(text) {
    var paragraphs = text.split(/\n\n+/);
    return paragraphs
      .map(function (p) {
        var trimmed = p.trim();
        if (!trimmed) return "";
        return "<p>" + escapeHtml(trimmed).replace(/\n/g, "<br>") + "</p>";
      })
      .join("");
  }

  function appendMessage(role, content) {
    removeTypingIndicator();
    var el = createMessageEl(role, content);
    messagesEl.appendChild(el);
    scrollToBottom();
    return el;
  }

  /* -----------------------------------------------------------
     Typing Indicator
     ----------------------------------------------------------- */
  function showTypingIndicator() {
    removeTypingIndicator();
    var div = document.createElement("div");
    div.className = "typing-indicator";
    div.id = "typing-indicator";
    div.innerHTML = "<span></span><span></span><span></span>";
    messagesEl.appendChild(div);
    scrollToBottom();
  }

  function removeTypingIndicator() {
    var el = document.getElementById("typing-indicator");
    if (el) el.remove();
  }

  /* -----------------------------------------------------------
     Welcome State
     ----------------------------------------------------------- */
  function showWelcomeState() {
    messagesEl.innerHTML = "";
    var div = document.createElement("div");
    div.className = "welcome-state";
    div.innerHTML =
      '<img class="welcome-icon" src="/static/img/icon.png" alt="Memoria">' +
      "<h2>How can I help you today?</h2>" +
      "<p>Ask me about symptoms, medications, health conditions, or anything related to your wellbeing.</p>";
    messagesEl.appendChild(div);
  }

  /* -----------------------------------------------------------
     Conversations (Client-Side History)
     ----------------------------------------------------------- */
  function createConversation() {
    var convo = { id: uid(), title: "New conversation", messages: [], resetPending: true };
    conversations.unshift(convo);
    activeConvoId = convo.id;
    return convo;
  }

  function getActiveConvo() {
    return conversations.find(function (c) {
      return c.id === activeConvoId;
    });
  }

  function renderHistory() {
    historyList.innerHTML = "";
    conversations.forEach(function (convo) {
      var li = document.createElement("li");
      li.className = "history-item" + (convo.id === activeConvoId ? " active" : "");
      li.textContent = convo.title;
      li.addEventListener("click", function () {
        switchConversation(convo.id);
      });
      historyList.appendChild(li);
    });
  }

  function switchConversation(id) {
    activeConvoId = id;
    var convo = getActiveConvo();
    if (!convo) return;

    messagesEl.innerHTML = "";
    if (convo.messages.length === 0) {
      showWelcomeState();
    } else {
      convo.messages.forEach(function (m) {
        var el = createMessageEl(m.role, m.content);
        el.style.animation = "none";
        messagesEl.appendChild(el);
      });
      scrollToBottom();
    }
    renderHistory();
  }

  /* -----------------------------------------------------------
     Chat Submission
     ----------------------------------------------------------- */
  async function sendMessage(text) {
    if (isSending || !text) return;
    hideError();
    isSending = true;
    sendBtn.classList.add("sending");
    sendBtn.classList.remove("active");

    var convo = getActiveConvo();
    if (!convo) {
      convo = createConversation();
    }

    if (convo.resetPending) {
      try {
        await fetch("/api/memory/clear", { method: "POST" });
      } catch (_) {
        // Keep local UX responsive even when clear API is unavailable.
      }
      convo.resetPending = false;
    }

    // Clear welcome state on first message
    var welcomeEl = messagesEl.querySelector(".welcome-state");
    if (welcomeEl) welcomeEl.remove();

    // User message
    convo.messages.push({ role: "user", content: text });
    if (convo.messages.length === 1) {
      convo.title = text.length > 40 ? text.slice(0, 40) + "…" : text;
    }
    appendMessage("user", text);
    renderHistory();

    // Reset input
    chatInput.value = "";
    chatInput.style.height = "auto";

    showTypingIndicator();

    try {
      var response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }),
      });

      if (!response.ok) {
        var errData = await response.json().catch(function () {
          return {};
        });
        throw new Error(errData.error || "Something went wrong. Please try again.");
      }

      var data = await response.json();
      var reply = data.response || "I could not generate a response.";

      convo.messages.push({ role: "assistant", content: reply });
      appendMessage("assistant", reply);
    } catch (err) {
      removeTypingIndicator();
      showError(err.message || "Connection error. Check your network and try again.");
    } finally {
      isSending = false;
      sendBtn.classList.remove("sending");
      chatInput.focus();
    }
  }

  /* -----------------------------------------------------------
     New Chat
     ----------------------------------------------------------- */
  async function startNewChat() {
    var convo = createConversation();
    showWelcomeState();
    renderHistory();
    chatInput.value = "";
    chatInput.style.height = "auto";
    sendBtn.classList.remove("active");
    hideError();

    try {
      await fetch("/api/memory/clear", { method: "POST" });
      convo.resetPending = false;
    } catch (_) {
      // Silent — non-critical
    }
  }

  /* -----------------------------------------------------------
     Event Bindings
     ----------------------------------------------------------- */

  // Form submit
  chatForm.addEventListener("submit", function (e) {
    e.preventDefault();
    var text = chatInput.value.trim();
    if (text) sendMessage(text);
  });

  // Keyboard: Enter to send, Shift+Enter for newline
  chatInput.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      var text = chatInput.value.trim();
      if (text) sendMessage(text);
    }
  });

  // New chat
  newChatBtn.addEventListener("click", startNewChat);

  // Sidebar toggle
  sidebarToggle.addEventListener("click", function () {
    shell.classList.toggle("sidebar-collapsed");
  });

  sidebarOpenBtn.addEventListener("click", function () {
    shell.classList.remove("sidebar-collapsed");
  });

  // Profile dropdown
  profileTrigger.addEventListener("click", function (e) {
    e.stopPropagation();
    var isOpen = profileDropdown.classList.toggle("open");
    profileTrigger.setAttribute("aria-expanded", isOpen);
  });

  document.addEventListener("click", function (e) {
    if (!profileTrigger.contains(e.target) && !profileDropdown.contains(e.target)) {
      profileDropdown.classList.remove("open");
      profileTrigger.setAttribute("aria-expanded", "false");
    }
  });

  // Close sidebar on outside click (mobile)
  document.addEventListener("click", function (e) {
    if (
      window.innerWidth <= 768 &&
      !shell.classList.contains("sidebar-collapsed") &&
      !sidebar.contains(e.target) &&
      !sidebarOpenBtn.contains(e.target)
    ) {
      shell.classList.add("sidebar-collapsed");
    }
  });

  // Clear Chat Implementation
  const clearChatBtn = document.getElementById("clear-chat-btn");
  if (clearChatBtn) {
    clearChatBtn.addEventListener("click", () => {
      if (confirm("Are you sure you want to delete this specific chat?")) {
        // Only delete the active conversation from the list
        conversations = conversations.filter(c => c.id !== activeConvoId);
        
        // If there are no chats left, create a fresh one
        if (conversations.length === 0) {
          createConversation();
        } else {
          // Otherwise, switch to the most recent one (the first in the list)
          activeConvoId = conversations[0].id;
        }
        
        // Reset backend memory so it forgets the deleted thread
        fetch("/api/memory/clear", { method: "POST" }).catch(console.error);
        
        // Render UI
        switchConversation(activeConvoId);
      }
    });
  }

  /* -----------------------------------------------------------
     Init
     ----------------------------------------------------------- */
  createConversation();
  showWelcomeState();
  renderHistory();
  chatInput.focus();

  fetch("/api/memory/clear", { method: "POST" }).catch(function () {
    // Non-blocking: UI remains usable even if clear fails.
  });
})();
