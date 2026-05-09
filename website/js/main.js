/**
 * Lorapok Red Bot — Marketing site JS
 * Scroll animations, live status badge, smooth scroll
 */

(function () {
  'use strict';

  // ── Scroll-triggered fade-in ──────────────────────────────────────────────

  function initFadeIn() {
    const targets = document.querySelectorAll(
      '.feature-card, .pricing-card, .deploy-card, .hero-stats .stat, .arch-diagram'
    );
    targets.forEach(el => el.classList.add('fade-in'));

    const observer = new IntersectionObserver(
      entries => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            entry.target.classList.add('visible');
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12 }
    );

    targets.forEach(el => observer.observe(el));
  }

  // ── Live status badge ─────────────────────────────────────────────────────

  function initStatusBadge() {
    const dot = document.getElementById('status-dot');
    const text = document.getElementById('status-text');
    if (!dot || !text) return;

    // Read API URL from data attribute on body, or default to empty (same origin)
    const apiUrl = document.body.dataset.apiUrl || '';

    async function checkStatus() {
      try {
        const res = await fetch(apiUrl + '/health', { signal: AbortSignal.timeout(4000) });
        if (res.ok) {
          dot.classList.add('online');
          dot.classList.remove('offline');
          text.textContent = 'Bot Online';
        } else {
          throw new Error('non-ok');
        }
      } catch {
        dot.classList.add('offline');
        dot.classList.remove('online');
        text.textContent = 'Bot Offline';
      }
    }

    checkStatus();
    setInterval(checkStatus, 60_000);
  }

  // ── Smooth scroll for anchor links ───────────────────────────────────────

  function initSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(link => {
      link.addEventListener('click', e => {
        const id = link.getAttribute('href').slice(1);
        const target = document.getElementById(id);
        if (target) {
          e.preventDefault();
          target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      });
    });
  }

  // ── Staggered card animation delay ───────────────────────────────────────

  function initStaggerDelay() {
    document.querySelectorAll('.features-grid .feature-card').forEach((card, i) => {
      card.style.transitionDelay = `${i * 60}ms`;
    });
    document.querySelectorAll('.pricing-grid .pricing-card').forEach((card, i) => {
      card.style.transitionDelay = `${i * 80}ms`;
    });
  }

  // ── Init ──────────────────────────────────────────────────────────────────

  document.addEventListener('DOMContentLoaded', () => {
    initFadeIn();
    initStatusBadge();
    initSmoothScroll();
    initStaggerDelay();
  });
})();
