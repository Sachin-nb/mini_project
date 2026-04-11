(() => {
  const GEMINI_API_KEY = "AIzaSyDcu74a-5HY9_MPDMScPq42GeoGFgtxPUU"; // ⬅️ Put your key here

  const PRIMARY_MODEL = "gemini-2.5-flash";
  const FALLBACK_MODEL = "gemini-2.0-flash";

  const chatEl = document.getElementById("chatContent");
  const inputEl = document.getElementById("promptInput");
  const sendBtn = document.getElementById("sendBtn");

  let isTyping = false;

  function addMsg(role, text) {
    const msgDiv = document.createElement("div");
    msgDiv.classList.add("msg", role);
    msgDiv.textContent = text;
    chatEl.appendChild(msgDiv);
    chatEl.scrollTop = chatEl.scrollHeight;
  }

  async function callGemini(prompt) {
    const urls = [
      `https://generativelanguage.googleapis.com/v1/models/${PRIMARY_MODEL}:generateContent?key=${GEMINI_API_KEY}`,
      `https://generativelanguage.googleapis.com/v1/models/${FALLBACK_MODEL}:generateContent?key=${GEMINI_API_KEY}`
    ];

    for (const url of urls) {
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          contents: [{ parts: [{ text: prompt }] }]
        })
      });

      if (res.ok) {
        const data = await res.json();
        return data.candidates?.[0]?.content?.parts?.[0]?.text || "No reply";
      }
    }

    return "Server busy. Try again later.";
  }

  async function handleSend() {
    const msg = inputEl.value.trim();
    if (!msg || isTyping) return;

    addMsg("user", msg);
    inputEl.value = "";
    isTyping = true;

    const typingMsg = document.createElement("div");
    typingMsg.classList.add("msg", "ai");
    typingMsg.textContent = "Typing...";
    chatEl.appendChild(typingMsg);

    try {
      const reply = await callGemini(msg);
      typingMsg.textContent = reply;
    } finally {
      isTyping = false;
      chatEl.scrollTop = chatEl.scrollHeight;
    }
  }

  sendBtn.addEventListener("click", handleSend);
  inputEl.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  });

})();

