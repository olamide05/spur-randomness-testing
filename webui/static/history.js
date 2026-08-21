(() => {
  "use strict";

  const clocks = Array.from(document.querySelectorAll(".execution-clock"));
  if (clocks.length === 0) return;

  function formatDuration(totalSeconds) {
    const seconds = Math.max(0, Math.floor(totalSeconds));
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const remainder = seconds % 60;
    return [hours, minutes, remainder]
      .map((value) => String(value).padStart(2, "0"))
      .join(":");
  }

  function updateClocks() {
    const now = Date.now() / 1000;
    clocks.forEach((clock) => {
      const startedAt = Number.parseFloat(clock.dataset.startedAt);
      const finishedAt = Number.parseFloat(clock.dataset.finishedAt);
      if (!Number.isFinite(startedAt)) {
        clock.textContent = "--:--:--";
        return;
      }
      const end = Number.isFinite(finishedAt) ? finishedAt : now;
      clock.textContent = formatDuration(end - startedAt);
    });
  }

  updateClocks();
  window.setInterval(updateClocks, 1000);
})();
