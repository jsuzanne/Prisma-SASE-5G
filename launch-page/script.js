/* ============================================================
   Stigix 5G Lab — Launchpad Modal Controller
   ============================================================ */

(function () {
  'use strict';

  const openModal = (targetId) => {
    const dialog = document.getElementById(targetId);
    if (dialog && typeof dialog.showModal === 'function') {
      dialog.showModal();
    }
  };

  const triggers = document.querySelectorAll('[data-dialog-target]');
  triggers.forEach((el) => {
    el.addEventListener('click', () => {
      openModal(el.getAttribute('data-dialog-target'));
    });
    el.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
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
})();
