/* ================================================================
   QUOTEPLAN AI ASSISTANT - MODERN UI JAVASCRIPT
   ================================================================ */

/* Global Elements */
const messagesContainer = document.getElementById("messagesContainer")
const questionInput = document.getElementById("questionInput")
const chatForm = document.getElementById("chatForm")
const sendBtn = document.getElementById("sendBtn")
const chatToggleBtn = document.getElementById("chatToggleBtn")
const chatWidget = document.getElementById("chatWidget")
const chatCloseBtn = document.getElementById("chatCloseBtn")
const unreadBadge = document.getElementById("unreadBadge")
const chatMessagesWrapper = document.querySelector(".chat-messages-wrapper")

let conversationCount = 0

/* ================================================================
   CHAT WIDGET TOGGLE
   ================================================================ */
function openChat() {
  chatWidget.classList.add("visible")
  chatToggleBtn.style.display = "none"
  unreadBadge.style.display = "none"
  questionInput.focus()
  // Auto-scroll to bottom when chat opens
  setTimeout(() => scrollToBottom(), 100)
}

function closeChat() {
  chatWidget.classList.remove("visible")
  chatToggleBtn.style.display = "flex"
}

chatToggleBtn.addEventListener("click", openChat)
chatCloseBtn.addEventListener("click", closeChat)

/* ================================================================
   QUICK PROMPT BUTTONS
   ================================================================ */
function setQuestionFromPrompt(button) {
  const text = button.textContent.trim()
  questionInput.value = text
  questionInput.focus()
  // Optionally auto-send
  chatForm.dispatchEvent(new Event("submit"))
}

/* ================================================================
   MESSAGE FORMATTING
   ================================================================ */
function escapeHtml(str) {
  return String(str).replace(
    /[&"'<>]/g,
    (m) =>
      ({
        "&": "&amp;",
        '"': "&quot;",
        "'": "&#39;",
        "<": "&lt;",
        ">": "&gt;",
      })[m],
  )
}

function formatMessage(text) {
  const escaped = escapeHtml(String(text))
  const withBold = escaped.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
  const withItalic = withBold.replace(/__(.+?)__/g, "<em>$1</em>")
  return withItalic.replace(/\n/g, "<br>")
}

/* Auto-scroll to latest message with smooth animation - Always enabled */
function scrollToBottom() {
  // Use requestAnimationFrame for smooth scrolling
  requestAnimationFrame(() => {
    chatMessagesWrapper.scrollTo({
      top: chatMessagesWrapper.scrollHeight,
      behavior: 'smooth'
    })
  })
}

/* ================================================================
   TYPING ANIMATION
   ================================================================ */
function typeText(element, text, speed = 20, callback = null) {
  let currentIndex = 0
  let displayText = ''
  
  const typeChar = () => {
    if (currentIndex < text.length) {
      // Add next character
      displayText += text[currentIndex]
      // Update element with formatted text up to current point
      element.innerHTML = formatMessage(displayText) + '<span class="typing-cursor">|</span>'
      currentIndex++
      // Auto-scroll during typing
      scrollToBottom()
      // Continue typing with variable speed (faster for spaces, slower for punctuation)
      const char = text[currentIndex - 1]
      const delay = char === ' ' ? speed * 0.5 : (char === '.' || char === '!' || char === '?') ? speed * 2 : speed
      setTimeout(typeChar, delay)
    } else {
      // Typing complete, remove cursor
      element.innerHTML = formatMessage(text)
      if (callback) callback()
    }
  }
  
  typeChar()
}

// Promise-based typing for async/await usage
function typeTextInElement(element, text, speed = 15) {
  return new Promise((resolve) => {
    let currentIndex = 0
    let displayText = ''
    
    const typeChar = () => {
      if (currentIndex < text.length) {
        displayText += text[currentIndex]
        element.innerHTML = formatMessage(displayText) + '<span class="typing-cursor">|</span>'
        currentIndex++
        scrollToBottom()
        const char = text[currentIndex - 1]
        const delay = char === ' ' ? speed * 0.5 : (char === '.' || char === '!' || char === '?') ? speed * 2 : speed
        setTimeout(typeChar, delay)
      } else {
        element.innerHTML = formatMessage(text)
        resolve()
      }
    }
    
    typeChar()
  })
}

/* ================================================================
   MESSAGE RENDERING
   ================================================================ */
function addMessage(text, isUser = false, useTyping = false) {
  // Remove greeting on first message
  if (conversationCount === 0 && !isUser) {
    const greeting = messagesContainer.querySelector(".message-greeting")
    const prompts = messagesContainer.querySelector(".quick-prompts")
    if (greeting) greeting.remove()
    if (prompts) prompts.remove()
  }

  const messageDiv = document.createElement("div")
  messageDiv.className = `message ${isUser ? "user-message" : "bot-message"}`

  const body = document.createElement("div")
  body.className = "message-body"

  const contentDiv = document.createElement("div")
  contentDiv.className = "message-content"
  
  // For bot messages with typing animation
  if (!isUser && useTyping) {
    contentDiv.innerHTML = '<span class="typing-cursor">|</span>'
    messagesContainer.appendChild(messageDiv)
    body.appendChild(contentDiv)
    messageDiv.appendChild(body)
    scrollToBottom()
    
    // Start typing animation
    typeText(contentDiv, text, 15, () => {
      scrollToBottom()
    })
  } else {
    // User messages or non-typing messages show immediately
    contentDiv.innerHTML = formatMessage(text)
    body.appendChild(contentDiv)
    messageDiv.appendChild(body)
    messagesContainer.appendChild(messageDiv)
    scrollToBottom()
  }

  if (isUser) conversationCount++
}

/* ================================================================
   LOADING INDICATOR
   ================================================================ */
function showLoadingIndicator() {
  const messageDiv = document.createElement("div")
  messageDiv.className = "message bot-message"
  messageDiv.id = "loading-indicator"

  const body = document.createElement("div")
  body.className = "message-body"

  const loadingDiv = document.createElement("div")
  loadingDiv.className = "loading"
  loadingDiv.innerHTML = '<div class="loading-dot"></div><div class="loading-dot"></div><div class="loading-dot"></div>'

  body.appendChild(loadingDiv)
  messageDiv.appendChild(body)
  messagesContainer.appendChild(messageDiv)
  scrollToBottom()
}

function removeLoadingIndicator() {
  const loadingIndicator = document.getElementById("loading-indicator")
  if (loadingIndicator) loadingIndicator.remove()
}

/* ================================================================
   API CALL & MESSAGE SENDING
   ================================================================ */
let lastQuestion = ""

async function sendMessage(event) {
  if (event) event.preventDefault()
  const question = questionInput.value.trim()
  if (!question) return

  lastQuestion = question

  addMessage(question, true)
  questionInput.value = ""
  showLoadingIndicator()
  sendBtn.disabled = true

  try {
    const response = await fetch("/api", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    })

    if (!response.ok) throw new Error(`API error: ${response.status}`)
    const data = await response.json()
    removeLoadingIndicator()

    if (data.success) {
      addStructuredResponse(data)
    } else {
      addMessage(data.error || data.answer || "Unable to fetch response. Please try again.", false, true)
    }
  } catch (err) {
    removeLoadingIndicator()
    console.error(err)
    addMessage("Connection error. Please check your connection and try again.", false, true)
  } finally {
    sendBtn.disabled = false
    questionInput.focus()
  }
}

/* ================================================================
   STRUCTURED RESPONSE RENDERING WITH TYPING ANIMATION
   ================================================================ */
async function addStructuredResponse(data) {
  const messageDiv = document.createElement("div")
  messageDiv.className = "message bot-message"

  const body = document.createElement("div")
  body.className = "message-body"

  const contentDiv = document.createElement("div")
  contentDiv.className = "enhanced-reply"

  // Add container to DOM first for smooth animation
  body.appendChild(contentDiv)
  messageDiv.appendChild(body)
  messagesContainer.appendChild(messageDiv)
  scrollToBottom()

  // Summary section with typing
  if (data.short) {
    const summaryBox = document.createElement("div")
    summaryBox.className = "answer-section summary-box"
    const summaryTitle = document.createElement("h3")
    summaryTitle.innerHTML = "📋 Summary"
    summaryBox.appendChild(summaryTitle)
    const summaryContent = document.createElement("div")
    summaryContent.className = "typing-content"
    summaryBox.appendChild(summaryContent)
    contentDiv.appendChild(summaryBox)
    scrollToBottom()
    
    await typeTextInElement(summaryContent, data.short, 12)
  }

  // Steps section
  const hasSteps = data.steps && Array.isArray(data.steps) && data.steps.length
  if (hasSteps) {
    const stepBox = document.createElement("div")
    stepBox.className = "answer-section steps-box"

    const header = document.createElement("div")
    header.style.display = "flex"
    header.style.justifyContent = "space-between"
    header.style.alignItems = "center"
    header.style.marginBottom = "8px"

    const title = document.createElement("h3")
    title.innerHTML = "📌 Steps"
    title.style.margin = "0"
    header.appendChild(title)

    const copyBtn = document.createElement("button")
    copyBtn.className = "copy-btn"
    copyBtn.textContent = "Copy"
    copyBtn.style.fontSize = "11px"
    copyBtn.style.padding = "4px 8px"
    copyBtn.onclick = () => {
      const stepText = data.steps.join("\n")
      navigator.clipboard.writeText(stepText)
      copyBtn.textContent = "Copied!"
      setTimeout(() => (copyBtn.textContent = "Copy"), 1500)
    }
    header.appendChild(copyBtn)
    stepBox.appendChild(header)

    const ol = document.createElement("ol")
    ol.style.marginTop = "8px"
    ol.className = "typing-content"
    stepBox.appendChild(ol)
    contentDiv.appendChild(stepBox)
    scrollToBottom()
    
    // Type each step
    for (let i = 0; i < data.steps.length; i++) {
      const li = document.createElement("li")
      li.className = "typing-step"
      ol.appendChild(li)
      scrollToBottom()
      await typeTextInElement(li, data.steps[i], 10)
    }
  }

  // Full answer (if no steps) with typing
  if (!hasSteps && data.answer) {
    const ansBox = document.createElement("div")
    ansBox.className = "answer-section answer-box"
    const ansContent = document.createElement("div")
    ansContent.className = "typing-content"
    ansBox.appendChild(ansContent)
    contentDiv.appendChild(ansBox)
    scrollToBottom()
    
    await typeTextInElement(ansContent, data.answer, 12)
  }

  // Follow-up tip with typing
  if (data.follow_up) {
    const followBox = document.createElement("div")
    followBox.className = "answer-section followup-box"
    const followTitle = document.createElement("h3")
    followTitle.innerHTML = "✨ Tip"
    followBox.appendChild(followTitle)
    const followContent = document.createElement("div")
    followContent.className = "typing-content"
    followBox.appendChild(followContent)
    contentDiv.appendChild(followBox)
    scrollToBottom()
    
    await typeTextInElement(followContent, data.follow_up, 12)
  }

  // Final scroll
  scrollToBottom()
}

/* ================================================================
   DRAGGABLE CHAT WIDGET
   ================================================================ */
(function enableDraggableChatWidget() {
  const chatHeader = chatWidget && chatWidget.querySelector('.chat-header');
  if (!chatWidget || !chatHeader) return;

  let isDragging = false;
  let dragStartX = 0;
  let dragStartY = 0;
  let startLeft = 0;
  let startTop = 0;

  function onMouseDown(e) {
    if (e.button !== 0) return; // only left click
    isDragging = true;
    chatWidget.style.transition = 'none';
    dragStartX = e.clientX;
    dragStartY = e.clientY;
    // calculate initial widget position
    const rect = chatWidget.getBoundingClientRect();
    startLeft = rect.left;
    startTop = rect.top;
    document.body.style.userSelect = 'none';
    chatWidget.style.cursor = 'grabbing';
    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);
  }
  function onMouseMove(e) {
    if (!isDragging) return;
    let deltaX = e.clientX - dragStartX;
    let deltaY = e.clientY - dragStartY;
    let newLeft = startLeft + deltaX;
    let newTop = startTop + deltaY;
    // Clamp position to viewport
    const w = chatWidget.offsetWidth;
    const h = chatWidget.offsetHeight;
    const minLeft = 0, minTop = 0;
    const maxLeft = window.innerWidth - w;
    const maxTop = window.innerHeight - h;
    newLeft = Math.max(minLeft, Math.min(newLeft, maxLeft));
    newTop = Math.max(minTop, Math.min(newTop, maxTop));
    chatWidget.style.left = newLeft + 'px';
    chatWidget.style.top = newTop + 'px';
    chatWidget.style.right = 'auto';
    chatWidget.style.bottom = 'auto';
  }
  function onMouseUp() {
    isDragging = false;
    chatWidget.style.transition = '';
    chatWidget.style.cursor = '';
    document.body.style.userSelect = '';
    window.removeEventListener('mousemove', onMouseMove);
    window.removeEventListener('mouseup', onMouseUp);
  }
  chatHeader.addEventListener('mousedown', onMouseDown);

  // Touch support
  chatHeader.addEventListener('touchstart', function(e) {
    if (e.touches.length !== 1) return;
    isDragging = true;
    chatWidget.style.transition = 'none';
    dragStartX = e.touches[0].clientX;
    dragStartY = e.touches[0].clientY;
    const rect = chatWidget.getBoundingClientRect();
    startLeft = rect.left;
    startTop = rect.top;
    chatWidget.style.cursor = 'grabbing';
    window.addEventListener('touchmove', onTouchMove, {passive: false});
    window.addEventListener('touchend', onTouchEnd);
  });
  function onTouchMove(e) {
    if (!isDragging || e.touches.length !== 1) return;
    e.preventDefault(); // prevent scroll
    let deltaX = e.touches[0].clientX - dragStartX;
    let deltaY = e.touches[0].clientY - dragStartY;
    let newLeft = startLeft + deltaX;
    let newTop = startTop + deltaY;
    const w = chatWidget.offsetWidth;
    const h = chatWidget.offsetHeight;
    newLeft = Math.max(0, Math.min(newLeft, window.innerWidth-w));
    newTop = Math.max(0, Math.min(newTop, window.innerHeight-h));
    chatWidget.style.left = newLeft + 'px';
    chatWidget.style.top = newTop + 'px';
    chatWidget.style.right = 'auto';
    chatWidget.style.bottom = 'auto';
  }
  function onTouchEnd() {
    isDragging = false;
    chatWidget.style.transition = '';
    chatWidget.style.cursor = '';
    window.removeEventListener('touchmove', onTouchMove);
    window.removeEventListener('touchend', onTouchEnd);
  }
})();

/* ================================================================
   EVENT LISTENERS
   ================================================================ */
chatForm.addEventListener("submit", sendMessage)

questionInput.addEventListener("keypress", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault()
    sendMessage()
  }
})

/* Auto-focus on load */
window.addEventListener("load", () => {
  questionInput.focus()
  // Initial scroll to bottom
  scrollToBottom()
})
