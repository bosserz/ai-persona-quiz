(() => {
  const audio = document.getElementById("bgm");
  const toggleBtn = document.getElementById("soundToggle");
  const volumeSlider = document.getElementById("soundVolume");

  if (!audio) return;

  // Defaults
  const savedMuted = localStorage.getItem("bgm_muted");
  const savedVol = localStorage.getItem("bgm_volume");

  audio.volume = savedVol ? Math.max(0, Math.min(1, Number(savedVol))) : 0.25;
  audio.muted = savedMuted ? savedMuted === "true" : true;

  function syncUI() {
    if (toggleBtn) toggleBtn.textContent = audio.muted ? "Sound: Off" : "Sound: On";
    if (volumeSlider) volumeSlider.value = String(audio.volume);
  }
  syncUI();

  async function tryPlay() {
    // Attempt playback; will only succeed after a user gesture in most browsers.
    try {
      await audio.play();
    } catch (e) {
      // Autoplay blocked; that's okay. We'll retry on next gesture.
    }
  }

  // Start audio on first user gesture
  const startOnGesture = async () => {
    if (!audio.muted) await tryPlay();
    window.removeEventListener("pointerdown", startOnGesture);
    window.removeEventListener("keydown", startOnGesture);
  };
  window.addEventListener("pointerdown", startOnGesture, { once: false });
  window.addEventListener("keydown", startOnGesture, { once: false });

  // Toggle sound
  if (toggleBtn) {
    toggleBtn.addEventListener("click", async () => {
      audio.muted = !audio.muted;
      localStorage.setItem("bgm_muted", String(audio.muted));
      syncUI();
      if (!audio.muted) await tryPlay();
    });
  }

  // Volume control
  if (volumeSlider) {
    volumeSlider.addEventListener("input", () => {
      audio.volume = Number(volumeSlider.value);
      localStorage.setItem("bgm_volume", String(audio.volume));
    });
  }

  // Pause when tab is hidden; resume when visible (optional but polite)
  document.addEventListener("visibilitychange", async () => {
    if (document.hidden) {
      audio.pause();
    } else {
      if (!audio.muted) await tryPlay();
    }
  });
})();
