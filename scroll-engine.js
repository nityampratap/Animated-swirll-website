/* ═══════════════════════════════════════════════════════════════════
   SWIRL — Scroll-Scrubbed Canvas Engine
   Dependency-free. Reads frame-manifest.json, preloads WebP frames
   progressively, scrubs via requestAnimationFrame on scroll.
   ═══════════════════════════════════════════════════════════════════ */

(function () {
  'use strict';

  // ─── DOM refs ────────────────────────────────────────────────────
  var canvas      = document.getElementById('film-canvas');
  var ctx         = canvas.getContext('2d');
  var spacer      = document.getElementById('film-spacer');
  var captionLayer= document.getElementById('caption-layer');
  var overlay     = document.getElementById('film-canvas-overlay');
  var loadingEl   = document.getElementById('film-loading');

  // ─── State ───────────────────────────────────────────────────────
  var manifest      = null;
  var loadedFrames  = {};          // index → Image
  var currentIdx    = -1;
  var ticking       = false;
  var totalLoaded   = 0;
  var filmActive    = true;

  // ─── Bootstrap ───────────────────────────────────────────────────
  fetch('frame-manifest.json')
    .then(function (r) { return r.json(); })
    .then(function (data) {
      manifest = data;

      // Set spacer height: 100vh per chapter
      var numCh = data.chapters ? data.chapters.length : 7;
      spacer.style.height = (numCh * 100) + 'vh';

      resize();
      preload();
      onScroll();                  // draw initial frame

      if (loadingEl) loadingEl.style.display = 'none';
    })
    .catch(function (err) {
      console.warn('[scroll-engine] No frame-manifest.json yet — run build.py first.', err);
      // Show helpful message
      if (loadingEl) {
        loadingEl.querySelector('p').textContent =
          'Run  python build.py all  to generate frames';
      }
    });

  // ─── Resize canvas to viewport ──────────────────────────────────
  function resize() {
    canvas.width  = window.innerWidth;
    canvas.height = window.innerHeight;
    if (currentIdx >= 0) drawFrame(currentIdx);
  }
  window.addEventListener('resize', resize);

  // ─── Scroll fraction within spacer (0→1) ────────────────────────
  function getScrollFraction() {
    var rect = spacer.getBoundingClientRect();
    // spacerTop in viewport-relative terms: rect.top is negative when scrolled
    var scrollable = rect.height - window.innerHeight;
    if (scrollable <= 0) return 0;
    var scrolled = -rect.top;               // how far into spacer
    return Math.max(0, Math.min(1, scrolled / scrollable));
  }

  // ─── Is the film spacer still in view? ──────────────────────────
  function isFilmVisible() {
    var rect = spacer.getBoundingClientRect();
    return rect.bottom > 0;
  }

  // ─── Draw a frame on canvas (cover-fit) ─────────────────────────
  function drawFrame(idx) {
    var img = loadedFrames[idx];
    if (!img) {
      // find nearest loaded frame
      for (var d = 1; d < (manifest ? manifest.totalFrames : 500); d++) {
        if (loadedFrames[idx - d]) { img = loadedFrames[idx - d]; break; }
        if (loadedFrames[idx + d]) { img = loadedFrames[idx + d]; break; }
      }
    }
    if (!img) return;

    var cw = canvas.width,  ch = canvas.height;
    var iw = img.naturalWidth, ih = img.naturalHeight;
    if (!iw || !ih) return;

    var scale = Math.max(cw / iw, ch / ih);
    var dw = iw * scale, dh = ih * scale;
    var dx = (cw - dw) / 2, dy = (ch - dh) / 2;

    ctx.clearRect(0, 0, cw, ch);
    ctx.drawImage(img, dx, dy, dw, dh);
  }

  // ─── Scroll handler ─────────────────────────────────────────────
  function onScroll() {
    if (!manifest) return;

    var vis = isFilmVisible();

    // Show/hide canvas + captions
    if (!vis && filmActive) {
      canvas.style.opacity = '0';
      canvas.style.pointerEvents = 'none';
      captionLayer.style.opacity = '0';
      captionLayer.style.pointerEvents = 'none';
      if (overlay) overlay.classList.remove('active');
      filmActive = false;
    } else if (vis && !filmActive) {
      canvas.style.opacity = '1';
      canvas.style.pointerEvents = 'auto';
      captionLayer.style.opacity = '1';
      filmActive = true;
    }

    if (!vis) return;

    var frac = getScrollFraction();
    var idx  = Math.min(
      manifest.totalFrames - 1,
      Math.max(0, Math.floor(frac * manifest.totalFrames))
    );

    // Bottom-of-film gradient (fade to background as film ends)
    if (overlay) {
      if (frac > 0.92) {
        overlay.classList.add('active');
      } else {
        overlay.classList.remove('active');
      }
    }

    if (idx !== currentIdx) {
      currentIdx = idx;
      if (!ticking) {
        requestAnimationFrame(function () {
          drawFrame(currentIdx);
          ticking = false;
        });
        ticking = true;
      }
    }
  }

  window.addEventListener('scroll', onScroll, { passive: true });

  // ─── Progressive preload ────────────────────────────────────────
  //  Pass 1: every 20th frame  (instant skeleton)
  //  Pass 2: every 5th frame   (smooth scrub)
  //  Pass 3: every remaining   (pixel-perfect)
  function preload() {
    if (!manifest) return;
    var total = manifest.totalFrames;
    var passes = [
      Math.max(1, Math.floor(total / 20)),
      Math.max(1, Math.floor(total / 60)),
      1
    ];

    var passIdx = 0;

    function runPass() {
      if (passIdx >= passes.length) return;
      var step   = passes[passIdx];
      var loaded = 0;
      var expected = 0;

      for (var i = 0; i < total; i += step) {
        if (loadedFrames[i]) continue;
        expected++;
        (function (idx) {
          var img = new Image();
          img.onload = function () {
            loadedFrames[idx] = img;
            totalLoaded++;
            loaded++;
            // if this is frame 0, draw immediately
            if (idx === 0 && currentIdx < 0) {
              currentIdx = 0;
              drawFrame(0);
            }
            if (loaded >= expected) {
              passIdx++;
              if (typeof requestIdleCallback !== 'undefined') {
                requestIdleCallback(runPass);
              } else {
                setTimeout(runPass, 60);
              }
            }
          };
          img.onerror = function () {
            loaded++;
            if (loaded >= expected) {
              passIdx++;
              if (typeof requestIdleCallback !== 'undefined') {
                requestIdleCallback(runPass);
              } else {
                setTimeout(runPass, 60);
              }
            }
          };
          img.src = 'frames/frame_' + String(idx).padStart(5, '0') + '.webp';
        })(i);
      }

      if (expected === 0) {
        passIdx++;
        runPass();
      }
    }

    runPass();
  }

  // ─── Expose fraction getter for captions.js ─────────────────────
  window.__swirlFilm = {
    getScrollFraction: getScrollFraction,
    isFilmVisible: isFilmVisible,
  };
})();
