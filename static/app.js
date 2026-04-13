const messagesEl = document.getElementById("messages");
const chatForm = document.getElementById("chatForm");
const messageInput = document.getElementById("messageInput");
const availabilityEl = document.getElementById("availability");
const bookingResultEl = document.getElementById("bookingResult");
const bookingLinkEl = document.getElementById("bookingLink");

const history = [];

function renderMessage(role, content, sources = []) {
  const wrapper = document.createElement("article");
  wrapper.className = `message ${role}`;

  const body = document.createElement("div");
  body.textContent = content;
  wrapper.appendChild(body);

  if (sources.length) {
    const sourcesEl = document.createElement("div");
    sourcesEl.className = "sources";
    sourcesEl.innerHTML = sources
      .map((source) => {
        const label = `${source.source_name}: ${source.title}`;
        if (source.url) {
          return `<div><a href="${source.url}" target="_blank" rel="noreferrer">${label}</a><br>${source.excerpt}</div>`;
        }
        return `<div>${label}<br>${source.excerpt}</div>`;
      })
      .join("");
    wrapper.appendChild(sourcesEl);
  }

  messagesEl.appendChild(wrapper);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

async function sendMessage(message) {
  renderMessage("user", message);
  history.push({ role: "user", content: message });

  const response = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, history: history.slice(-6) }),
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.detail || "Chat request failed.");
  }

  renderMessage("assistant", payload.answer, payload.sources || []);
  history.push({ role: "assistant", content: payload.answer });
}

function setComposerPrompt(prompt) {
  messageInput.value = prompt;
  messageInput.focus();
}

async function loadAvailability() {
  availabilityEl.textContent = "Loading availability...";
  const response = await fetch("/api/availability");
  const payload = await response.json();
  if (!response.ok) {
    availabilityEl.textContent = payload.detail || "Failed to load availability.";
    return;
  }

  if (!payload.slots || payload.slots.length === 0) {
    const link = payload.booking_url
      ? `<a href="${payload.booking_url}" target="_blank" rel="noreferrer">Open live booking page</a>`
      : "";
    availabilityEl.innerHTML = `<div class="empty">${payload.message || "No slots available."}</div>${link}`;
    if (payload.booking_url) {
      bookingLinkEl.href = payload.booking_url;
      bookingResultEl.innerHTML = `Use <a href="${payload.booking_url}" target="_blank" rel="noreferrer">Calendly</a> to complete the booking.`;
    }
    return;
  }

  availabilityEl.innerHTML = "";
  payload.slots.forEach((slot) => {
    const button = document.createElement("button");
    button.className = "slot";
    button.type = "button";
    button.textContent = `${slot.start}${slot.end ? ` to ${slot.end}` : ""}`;
    button.addEventListener("click", () => {
      bookingResultEl.innerHTML = `Selected slot: <strong>${slot.start}</strong>. Complete the booking on <a href="${payload.booking_url}" target="_blank" rel="noreferrer">Calendly</a>.`;
    });
    availabilityEl.appendChild(button);
  });
}

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = messageInput.value.trim();
  if (!message) return;
  messageInput.value = "";
  try {
    await sendMessage(message);
  } catch (error) {
    renderMessage("assistant", error.message);
  }
});

document.getElementById("loadAvailability").addEventListener("click", () => {
  loadAvailability().catch((error) => {
    availabilityEl.textContent = error.message;
  });
});

document.getElementById("seedQuestions").addEventListener("click", async () => {
  const prompts = [
    "Why are you the right person for this role?",
    "Tell me about your RAG experience at WNS.",
    "Explain the tradeoffs in your computer vision powered image search project.",
  ];
  for (const prompt of prompts) {
    await sendMessage(prompt);
  }
});

document.querySelectorAll(".prompt-chip").forEach((button) => {
  button.addEventListener("click", () => {
    setComposerPrompt(button.dataset.prompt || "");
  });
});

renderMessage(
  "assistant",
  "I am Adarsh's AI representative. Ask about resume details, project tradeoffs, or load availability to book an interview."
);

loadAvailability().catch((error) => {
  availabilityEl.textContent = error.message;
});
