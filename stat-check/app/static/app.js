(() => {
  const phase = document.querySelector("[data-deadline]");
  const countdown = document.querySelector("[data-countdown]");
  const timer = countdown?.closest(".timer");
  const deadlineReload = document.querySelector("[data-reload-on-deadline]");

  if (phase && countdown && phase.dataset.deadline) {
    const deadline = new Date(phase.dataset.deadline).getTime();
    const update = () => {
      const remaining = Math.max(0, deadline - Date.now());
      const seconds = Math.floor(remaining / 1000);
      const minutes = Math.floor(seconds / 60);
      countdown.textContent = `${String(minutes).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
      timer?.classList.toggle("urgent", seconds <= 60);
      if (remaining <= 0 && deadlineReload) {
        const reloadKey = [
          "stat-check:deadline-reload",
          deadlineReload.dataset.sessionId,
          phase.dataset.deadline,
        ].join(":");
        if (window.sessionStorage.getItem(reloadKey) !== "1") {
          window.sessionStorage.setItem(reloadKey, "1");
          window.location.reload();
        }
      }
    };
    update();
    window.setInterval(update, 1000);
  }

  document.querySelectorAll("[data-copy]").forEach((button) => {
    button.addEventListener("click", async () => {
      const text = button.parentElement?.querySelector("code")?.textContent?.trim();
      if (!text) return;
      await navigator.clipboard.writeText(text);
      button.textContent = "已复制";
      window.setTimeout(() => {
        button.textContent = "复制";
      }, 1200);
    });
  });

  document.querySelectorAll(".answer-form").forEach((form) => {
    form.addEventListener("submit", () => {
      const button = form.querySelector("button[type='submit']");
      if (!button) return;
      button.disabled = true;
      button.textContent = "正在提交…";
    });
  });

  const stateWatch = document.querySelector("[data-state-watch]");
  if (stateWatch) {
    const checkState = async () => {
      try {
        const response = await fetch(stateWatch.dataset.stateUrl, {
          cache: "no-store",
          headers: { Accept: "application/json" },
        });
        if (!response.ok) return;
        const state = await response.json();
        const sessionChanged = String(state.session_id) !== stateWatch.dataset.sessionId;
        const phaseChanged = state.phase !== stateWatch.dataset.phase;
        const deadlineChanged = (state.phase_ends_at || "") !== stateWatch.dataset.phaseEndsAt;
        if (sessionChanged || phaseChanged || deadlineChanged) {
          window.location.reload();
        }
      } catch (_) {
        // A brief network interruption should not replace the student's current page.
      }
    };
    window.setInterval(checkState, 3000);
  }

  const autoReload = document.querySelector("[data-auto-reload]");
  if (autoReload) {
    const delay = Number(autoReload.dataset.autoReload) || 5000;
    window.setInterval(() => {
      if (document.visibilityState === "visible" && !autoReload.matches(":focus-within")) {
        window.location.reload();
      }
    }, delay);
  }
})();
