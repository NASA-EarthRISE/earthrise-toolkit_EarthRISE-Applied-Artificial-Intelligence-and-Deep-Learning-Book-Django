/**
 * Sidebar behaviour:
 * - Collapsible part groups (click label to toggle)
 * - Mobile: slide-in/out via toggle button + overlay
 * - Persist collapse state in sessionStorage
 * - Scroll active link into view on page load
 */
(function () {
  'use strict';

  // ── Part group collapse ──────────────────────────────────────────────

  document.querySelectorAll('.sidebar-section__label').forEach(function (label) {
    var sectionKey = 'sidebar-part-' + label.dataset.slug;
    var chapterList = label.nextElementSibling;

    if (!chapterList) return;

    // Restore persisted state
    if (sessionStorage.getItem(sectionKey) === 'collapsed') {
      chapterList.hidden = true;
      label.setAttribute('aria-expanded', 'false');
    } else {
      label.setAttribute('aria-expanded', 'true');
    }

    label.addEventListener('click', function () {
      var isCollapsed = chapterList.hidden;
      chapterList.hidden = !isCollapsed;
      label.setAttribute('aria-expanded', isCollapsed ? 'true' : 'false');
      sessionStorage.setItem(sectionKey, isCollapsed ? 'open' : 'collapsed');
    });
  });

  // ── Mobile sidebar toggle ────────────────────────────────────────────

  var toggle = document.getElementById('sidebarToggle');
  var sidebar = document.getElementById('siteSidebar');
  var overlay = document.getElementById('sidebarOverlay');

  if (toggle && sidebar) {
    toggle.addEventListener('click', openSidebar);
  }

  if (overlay) {
    overlay.addEventListener('click', closeSidebar);
  }

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') closeSidebar();
  });

  function openSidebar() {
    sidebar.classList.add('is-open');
    if (overlay) overlay.classList.add('is-visible');
    toggle.setAttribute('aria-expanded', 'true');
    sidebar.focus();
  }

  function closeSidebar() {
    sidebar.classList.remove('is-open');
    if (overlay) overlay.classList.remove('is-visible');
    if (toggle) toggle.setAttribute('aria-expanded', 'false');
  }

  // ── Scroll active link into view ─────────────────────────────────────

  var activeLink = sidebar && sidebar.querySelector('.sidebar-link.active');
  if (activeLink) {
    activeLink.scrollIntoView({ block: 'nearest' });
  }

})();
