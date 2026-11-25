/* ============================================================
   Stigix 5G Lab — Launchpad Controller (Modals + Unslop/Slop Compare)
   ============================================================ */

(function () {
  'use strict';

  /* ── Modal Dialogs ── */
  const openModal = (targetId) => {
    const dialog = document.getElementById(targetId);
    if (dialog && typeof dialog.showModal === 'function') {
      dialog.showModal();
    }
  };

  const triggers = document.querySelectorAll('[data-dialog-target]');
  triggers.forEach((el) => {
    el.addEventListener('click', (e) => {
      e.stopPropagation();
      openModal(el.getAttribute('data-dialog-target'));
    });
    el.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        e.stopPropagation();
        openModal(el.getAttribute('data-dialog-target'));
      }
    });
  });

  const dialogs = document.querySelectorAll('dialog.modal');
  dialogs.forEach((dialog) => {
    dialog.addEventListener('close', () => {
      dialog.returnValue = '';
    });
  });

  // Fallback for browsers without native HTMLDialogElement.prototype.closedBy support
  if (typeof HTMLDialogElement !== 'undefined' && !('closedBy' in HTMLDialogElement.prototype)) {
    dialogs.forEach((dialog) => {
      dialog.addEventListener('click', (event) => {
        if (event.target !== dialog) return;
        const rect = dialog.getBoundingClientRect();
        const isDialogContent =
          rect.top <= event.clientY &&
          event.clientY <= rect.top + rect.height &&
          rect.left <= event.clientX &&
          event.clientX <= rect.left + rect.width;
        if (isDialogContent) return;
        dialog.close();
      });
    });
  }

  /* ── Unslop vs Slop Comparison Toggle ── */
  const STORAGE_KEY = 'stigix-launchpad-ui-mode';
  const cssUnslop = document.getElementById('css-unslop');
  const cssSlop = document.getElementById('css-slop');
  const modeButtons = document.querySelectorAll('[data-set-mode]');
  const swappableText = document.querySelectorAll('[data-unslop-text][data-slop-text]');

  const applyMode = (mode, persist) => {
    const normalized = mode === 'slop' ? 'slop' : 'unslop';
    document.documentElement.dataset.mode = normalized;

    if (cssUnslop && cssSlop) {
      cssUnslop.disabled = normalized === 'slop';
      cssSlop.disabled = normalized !== 'slop';
    }

    swappableText.forEach((el) => {
      const nextText = el.getAttribute(
        normalized === 'slop' ? 'data-slop-text' : 'data-unslop-text'
      );
      if (nextText !== null) {
        el.textContent = nextText;
      }
    });

    modeButtons.forEach((btn) => {
      const isActive = btn.getAttribute('data-set-mode') === normalized;
      btn.setAttribute('aria-pressed', isActive ? 'true' : 'false');
    });

    if (persist) {
      try {
        window.localStorage.setItem(STORAGE_KEY, normalized);
      } catch (_) {
        // Ignore storage errors in private/file contexts
      }
    }
  };

  modeButtons.forEach((btn) => {
    btn.addEventListener('click', () => {
      applyMode(btn.getAttribute('data-set-mode'), true);
    });
  });

  // Resolve initial mode: URL ?mode=slop|unslop > localStorage > default 'unslop'
  const urlMode = new URLSearchParams(window.location.search).get('mode');
  let initialMode = 'unslop';
  if (urlMode === 'slop' || urlMode === 'unslop') {
    initialMode = urlMode;
  } else {
    try {
      const saved = window.localStorage.getItem(STORAGE_KEY);
      if (saved === 'slop' || saved === 'unslop') {
        initialMode = saved;
      }
    } catch (_) {
      // Ignore storage errors
    }
  }

  applyMode(initialMode, false);
})();
