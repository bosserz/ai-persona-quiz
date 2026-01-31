(() => {
  const canvas = document.getElementById("bg");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");

  let w = 0, h = 0;
  let running = true;

  function resize() {
    w = canvas.width = window.innerWidth * devicePixelRatio;
    h = canvas.height = window.innerHeight * devicePixelRatio;
    canvas.style.width = window.innerWidth + "px";
    canvas.style.height = window.innerHeight + "px";
  }
  window.addEventListener("resize", resize);
  resize();

  const N = Math.min(120, Math.floor((window.innerWidth * window.innerHeight) / 14000));
  const pts = Array.from({ length: N }, () => ({
    x: Math.random() * w,
    y: Math.random() * h,
    vx: (Math.random() - 0.5) * 0.35 * devicePixelRatio,
    vy: (Math.random() - 0.5) * 0.35 * devicePixelRatio,
    r: (1 + Math.random() * 2.2) * devicePixelRatio
  }));

  function tick() {
    if (!running) return requestAnimationFrame(tick);

    ctx.clearRect(0, 0, w, h);

    // soft background wash
    ctx.fillStyle = "rgba(10, 14, 25, 0.65)";
    ctx.fillRect(0, 0, w, h);

    // points
    for (const p of pts) {
      p.x += p.vx;
      p.y += p.vy;

      if (p.x < 0 || p.x > w) p.vx *= -1;
      if (p.y < 0 || p.y > h) p.vy *= -1;

      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fillStyle = "rgba(255,255,255,0.75)";
      ctx.fill();
    }

    // lines (nearest neighbors)
    for (let i = 0; i < pts.length; i++) {
      for (let j = i + 1; j < pts.length; j++) {
        const a = pts[i], b = pts[j];
        const dx = a.x - b.x, dy = a.y - b.y;
        const d2 = dx * dx + dy * dy;
        const max = (170 * devicePixelRatio) ** 2;
        if (d2 < max) {
          const alpha = 1 - d2 / max;
          ctx.strokeStyle = `rgba(120,180,255,${0.18 * alpha})`;
          ctx.lineWidth = 1 * devicePixelRatio;
          ctx.beginPath();
          ctx.moveTo(a.x, a.y);
          ctx.lineTo(b.x, b.y);
          ctx.stroke();
        }
      }
    }

    requestAnimationFrame(tick);
  }

  tick();

  window.__BG_TOGGLE__ = () => {
    running = !running;
    if (running) tick();
  };
})();
