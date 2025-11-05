(function () {
  // Defensive helper: find "Manage Announcements" button by attribute or visible text
  function findManageButton() {
    const byAttr = document.querySelector('[data-action="manage-announcements"], #manage-announcements-btn');
    if (byAttr) return byAttr;
    return Array.from(document.querySelectorAll('button, a'))
      .find(el => el.textContent && el.textContent.trim() === 'Manage Announcements');
  }

  // Defensive modal selectors: common ids/classes used for modals
  function findModal() {
    return document.getElementById('announcement-modal')
      || document.getElementById('announcementsModal')
      || document.querySelector('.announcements-modal')
      || document.querySelector('.modal.announcements')
      || document.querySelector('.modal');
  }

  function showModal(modal) {
    if (!modal) return;
    modal.classList.remove('hidden');
    const content = modal.querySelector('.announcement-modal-content') || modal.querySelector('.modal-content');
    if (content) content.classList.remove('hidden');
    setTimeout(() => {
      modal.classList.add('show');
      if (content) content.classList.add('show');
    }, 10);

    // Add backdrop if absent
    if (!document.querySelector('.__announcements-backdrop')) {
      const backdrop = document.createElement('div');
      backdrop.className = '__announcements-backdrop';
      Object.assign(backdrop.style, {
        position: 'fixed',
        left: 0,
        top: 0,
        right: 0,
        bottom: 0,
        background: 'rgba(0,0,0,0.4)',
        zIndex: 2999 // ensure backdrop is below modal (modal z-index: 3000, modal-content: 3001)
      });
      document.body.appendChild(backdrop);
      backdrop.addEventListener('click', () => hideModal(modal, backdrop));
    }
  }

  function hideModal(modal, backdrop) {
    if (!modal) return;
    modal.classList.remove('show');
    const content = modal.querySelector('.announcement-modal-content') || modal.querySelector('.modal-content');
    if (content) content.classList.remove('show');
    setTimeout(() => {
      modal.classList.add('hidden');
      if (content) content.classList.add('hidden');
      if (backdrop) backdrop.remove();
      const bd = document.querySelector('.__announcements-backdrop');
      if (bd) bd.remove();
    }, 300);
  }

  function attachCloseHandlers(modal) {
    if (!modal) return;
    // common close button selectors
    const closeSelectors = ['[data-dismiss="modal"]', '.modal-close', '.close', '.close-modal', '.js-modal-close'];
    closeSelectors.forEach(sel => {
      modal.querySelectorAll(sel).forEach(el => {
        el.addEventListener('click', () => hideModal(modal));
      });
    });
  }

  function init() {
    const btn = findManageButton();
    const modal = findModal();
    if (!btn) return;
    btn.addEventListener('click', () => {
      showModal(modal);
    });
    attachCloseHandlers(modal);
    // Close when clicking outside
    window.addEventListener('click', (e) => {
      if (e.target === modal) hideModal(modal);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();