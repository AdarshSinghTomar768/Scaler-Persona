const messagesEl = document.getElementById("messages");
const chatForm = document.getElementById("chatForm");
const messageInput = document.getElementById("messageInput");
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

  if (role === "assistant" && content.toLowerCase().includes("calendly.com")) {
    bookingResultEl.innerHTML = `Booking is live here: <a href="${bookingLinkEl.href}" target="_blank" rel="noreferrer">open the scheduling page</a>.`;
    document.querySelector(".action-panel")?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }
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

function updateBookingTargets(url) {
  if (!url) return;
  bookingLinkEl.href = url;
}

async function loadAvailability() {
  const response = await fetch("/api/availability");
  const payload = await response.json();
  if (!response.ok) {
    bookingResultEl.textContent = payload.detail || "Failed to load booking details.";
    return;
  }

  if (!payload.slots || payload.slots.length === 0) {
    if (payload.booking_url) {
      updateBookingTargets(payload.booking_url);
      bookingResultEl.innerHTML = `Live booking is ready on <a href="${payload.booking_url}" target="_blank" rel="noreferrer">Calendly</a>.`;
    } else {
      bookingResultEl.textContent = payload.message || "Booking details are unavailable right now.";
    }
    return;
  }

  const firstSlot = payload.slots[0];
  if (firstSlot && payload.booking_url) {
    bookingResultEl.innerHTML = `Current availability starts from <strong>${firstSlot.start}</strong>. Complete the booking on <a href="${payload.booking_url}" target="_blank" rel="noreferrer">Calendly</a>.`;
    return;
  }

  bookingResultEl.textContent = "Booking details are available on the live scheduling page.";
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
  bookingResultEl.textContent = error.message;
});
