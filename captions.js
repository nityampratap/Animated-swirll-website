/* ═══════════════════════════════════════════════════════════════════
   SWIRL — Chapter Caption Controller
   Reads data-in / data-out (scroll fractions) from .chapter-caption
   elements and fades them in/out via opacity + subtle parallax.
   ═══════════════════════════════════════════════════════════════════ */

(function () {
  'use strict';

  var captions = document.querySelectorAll('.chapter-caption');
  var film     = window.__swirlFilm;

  if (!captions.length) return;

  var FADE_RANGE = 0.025;       // 2.5% of total scroll for fade in/out

  function update() {
    if (!film) { film = window.__swirlFilm; }
    if (!film || !film.getScrollFraction) return;

    var frac = film.getScrollFraction();

    for (var i = 0; i < captions.length; i++) {
      var el      = captions[i];
      var dataIn  = parseFloat(el.getAttribute('data-in'));
      var dataOut = parseFloat(el.getAttribute('data-out'));

      if (isNaN(dataIn) || isNaN(dataOut)) continue;

      var opacity = 0;

      if (dataIn < 0) {
        // Special: visible from before scroll 0
        if (frac <= dataOut - FADE_RANGE) {
          opacity = 1;
        } else if (frac <= dataOut) {
          opacity = (dataOut - frac) / FADE_RANGE;
        }
      } else if (frac >= dataIn && frac <= dataOut) {
        // Normal chapter
        if (frac < dataIn + FADE_RANGE) {
          opacity = (frac - dataIn) / FADE_RANGE;
        } else if (frac > dataOut - FADE_RANGE) {
          opacity = (dataOut - frac) / FADE_RANGE;
        } else {
          opacity = 1;
        }
      }

      opacity = Math.max(0, Math.min(1, opacity));
      el.style.opacity = opacity;

      // Gentle parallax: slide up as you scroll through the chapter
      var progress = 0;
      if (dataOut !== dataIn) {
        progress = (frac - dataIn) / (dataOut - dataIn);
      }
      progress = Math.max(0, Math.min(1, progress));

      var translateY = (1 - progress) * 25 - 5;      // +20 → -5
      el.style.transform = 'translateY(' + translateY + 'px)';
    }
  }

  window.addEventListener('scroll', function () {
    requestAnimationFrame(update);
  }, { passive: true });

  // Initial paint
  update();
  // Also fire after manifest loads (small delay for safety)
  setTimeout(update, 500);
})();
