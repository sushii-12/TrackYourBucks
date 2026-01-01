// =========================
// TrackYourBucks JS (updated)
// - smaller click glow
// - proximity-based card glow
// =========================

// 1) Click glow (smaller)
document.addEventListener("click", function (e) {
  // Ignore clicks on scrollbars (some browsers)
  if (e.clientX === 0 && e.clientY === 0) return;

  const glow = document.createElement("span");
  glow.className = "click-glow";
  glow.style.left = e.clientX + "px";
  glow.style.top = e.clientY + "px";
  document.body.appendChild(glow);

  setTimeout(() => glow.remove(), 600);
});

// 2) Proximity card glow
(function () {
  const cards = Array.from(document.querySelectorAll(".tyb-card"));
  if (!cards.length) return;

  // threshold in px - how near cursor must be for max effect
  const MAX_DISTANCE = 220;   // start seeing glow inside this radius
  const MIN_DISTANCE = 28;    // when very near, full effect

  let mouseX = -9999, mouseY = -9999;
  let ticking = false;

  // update mouse coords
  document.addEventListener("mousemove", (e) => {
    mouseX = e.clientX;
    mouseY = e.clientY;
    if (!ticking) {
      window.requestAnimationFrame(updateGlow);
      ticking = true;
    }
  });

  // when leaving window remove all glows
  document.addEventListener("mouseleave", () => {
    cards.forEach((c) => c.classList.remove("card-glow"));
  });

  function updateGlow() {
    ticking = false;
    for (const card of cards) {
      // get bounding center of card
      const rect = card.getBoundingClientRect();
      const cx = rect.left + rect.width / 2;
      const cy = rect.top + rect.height / 2;

      const dx = mouseX - cx;
      const dy = mouseY - cy;
      const dist = Math.sqrt(dx * dx + dy * dy);

      if (dist < MAX_DISTANCE) {
        // add glow, but intensity varies with distance
        card.classList.add("card-glow");

        // intensity 0..1 where 1 is closest
        const t = Math.max(0, Math.min(1, (MAX_DISTANCE - dist) / (MAX_DISTANCE - MIN_DISTANCE)));

        // scale pseudo-element and shadow subtly based on t (CSS variables not used to remain simple)
        const scale = 0.9 + 0.25 * t; // 0.9..1.15
        const blur = 12 + 18 * t;     // 12..30
        const w = 220 + 220 * t;      // 220..440
        const h = 110 + 110 * t;      // 110..220

        // set inline styles on ::after via style property on element's dataset and CSS custom properties
        // We'll use style.setProperty on the element to adjust the pseudo-element via CSS variables.
        card.style.setProperty("--card-glow-scale", scale);
        card.style.setProperty("--card-glow-blur", `${blur}px`);
        card.style.setProperty("--card-glow-w", `${w}px`);
        card.style.setProperty("--card-glow-h", `${h}px`);
        card.style.setProperty("--card-glow-opacity", `${0.9 * t}`);
      } else {
        card.classList.remove("card-glow");
        // remove inline vars
        card.style.removeProperty("--card-glow-scale");
        card.style.removeProperty("--card-glow-blur");
        card.style.removeProperty("--card-glow-w");
        card.style.removeProperty("--card-glow-h");
        card.style.removeProperty("--card-glow-opacity");
      }
    }
  }
})();
