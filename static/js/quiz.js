(() => {
  const questions = window.__QUESTIONS__ || [];
  const promptEl = document.getElementById("prompt");
  const choicesEl = document.getElementById("choices");
  const prevBtn = document.getElementById("prevBtn");
  const nextBtn = document.getElementById("nextBtn");
  const progressText = document.getElementById("progressText");
  const barFill = document.getElementById("barFill");

  let idx = 0;
  const answers = {}; // { qid: optionIndex }

  function render() {
    const q = questions[idx];
    if (!q) return;

    // progress
    progressText.textContent = `${idx + 1} / ${questions.length}`;
    const pct = Math.round(((idx + 1) / questions.length) * 100);
    barFill.style.width = `${pct}%`;

    // prompt
    promptEl.textContent = q.prompt;

    // choices
    choicesEl.innerHTML = "";
    q.options.forEach((opt, i) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "choice";
      btn.textContent = opt.text;

      const selected = answers[q.id] === i;
      if (selected) btn.classList.add("selected");

      btn.addEventListener("click", () => {
        answers[q.id] = i;
        // rerender choices to reflect selection
        render();
      });

      choicesEl.appendChild(btn);
    });

    prevBtn.disabled = idx === 0;
    nextBtn.textContent = idx === questions.length - 1 ? "See Result" : "Next";

    // require selection before moving next
    nextBtn.disabled = typeof answers[q.id] !== "number";
  }

  async function submitAndGo() {
    const res = await fetch(window.__SUBMIT_URL__, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ answers })
    });

    if (res.status === 409) {
        alert("You have already submitted this quiz. The first result is locked.");
        window.location.href = "/"; // or redirect to a 'locked' page
        return;
    }

    const data = await res.json();
    if (data.ok) window.location.href = window.__RESULT_URL__;
    else alert("Submit failed: " + (data.error || "unknown_error"));
    }

  prevBtn.addEventListener("click", () => {
    if (idx > 0) idx--;
    render();
  });

  nextBtn.addEventListener("click", () => {
    if (idx < questions.length - 1) {
      idx++;
      render();
    } else {
      submitAndGo();
    }
  });

  render();
})();
