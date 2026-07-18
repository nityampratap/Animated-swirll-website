/* ═══════════════════════════════════════════════════════════════════
   SWIRL — Sticky Nav + Scroll Reveal
   Nav appears once user scrolls past the film section.
   Scroll-reveal animations for homepage sections.
   ═══════════════════════════════════════════════════════════════════ */

(function () {
  'use strict';

  // ─── Sticky Nav ──────────────────────────────────────────────────
  var nav    = document.getElementById('sticky-nav');
  var spacer = document.getElementById('film-spacer');

  function updateNav() {
    if (!spacer || !nav) return;
    var rect = spacer.getBoundingClientRect();
    if (rect.bottom <= 60) {
      nav.classList.add('visible');
    } else {
      nav.classList.remove('visible');
    }
  }

  window.addEventListener('scroll', updateNav, { passive: true });
  updateNav();

  // ─── Smooth-scroll nav links ────────────────────────────────────
  var navLinks = document.querySelectorAll('#sticky-nav a[href^="#"]');
  for (var i = 0; i < navLinks.length; i++) {
    navLinks[i].addEventListener('click', function (e) {
      var href = this.getAttribute('href');
      if (href && href.startsWith('#')) {
        var target = document.querySelector(href);
        if (target) {
          e.preventDefault();
          target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      }
    });
  }

  // ─── Scroll Reveal (IntersectionObserver) ────────────────────────
  var reveals = document.querySelectorAll('.reveal');

  if ('IntersectionObserver' in window && reveals.length) {
    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.classList.add('visible');
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12, rootMargin: '0px 0px -60px 0px' }
    );

    for (var j = 0; j < reveals.length; j++) {
      observer.observe(reveals[j]);
    }
  } else {
    // Fallback: just show everything
    for (var k = 0; k < reveals.length; k++) {
      reveals[k].classList.add('visible');
    }
  }

  // ─── Mobile nav toggle (hamburger) ──────────────────────────────
  var hamburger = document.getElementById('nav-hamburger');
  var mobileMenu = document.getElementById('nav-mobile-menu');

  if (hamburger && mobileMenu) {
    hamburger.addEventListener('click', function () {
      var open = mobileMenu.classList.toggle('open');
      hamburger.setAttribute('aria-expanded', open);
    });

    // Close on link click
    var mobileLinks = mobileMenu.querySelectorAll('a');
    for (var m = 0; m < mobileLinks.length; m++) {
      mobileLinks[m].addEventListener('click', function () {
        mobileMenu.classList.remove('open');
        hamburger.setAttribute('aria-expanded', 'false');
      });
    }
  }
})();
