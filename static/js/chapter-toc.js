/**
 * chapter-toc.js
 * Builds the right-side "On this page" TOC from headings inside
 * #quarto-document-content, then scroll-spies to highlight the active link.
 *
 * Depth is read from data-toc-depth on #chapterToc:
 *   2 (default) – h1 + h2, flat list
 *   3           – h1 + h2 + h3, h3s nested under their h2 in an accordion
 */
(function () {
  'use strict';

  document.addEventListener('DOMContentLoaded', function () {
    var content = document.getElementById('quarto-document-content');
    var tocList = document.getElementById('chapterTocList');
    var toc     = document.getElementById('chapterToc');

    if (!content || !tocList || !toc) return;

    var depth = parseInt(toc.getAttribute('data-toc-depth') || '2', 10);
    var selector = depth >= 3
      ? 'h1[id], h2[id], h3[id]'
      : 'h1[id], h2[id]';

    var headings = Array.from(content.querySelectorAll(selector));

    if (headings.length < 2) { toc.hidden = true; return; }

    // links[] and itemMap{id → li} used by scroll-spy
    var links   = [];
    var itemMap = {};

    // ── Suppress scroll-spy accordion changes during programmatic scrolls ─
    // When a TOC link is clicked the browser smooth-scrolls, firing the
    // IntersectionObserver on intermediate headings along the way.  That
    // would close the just-opened subnav before the scroll finishes.
    // We suppress accordion auto-expand until scrolling comes to rest.
    var suppressSpy   = false;
    var suppressTimer = null;

    function startSuppressSpy() {
      suppressSpy = true;
      clearTimeout(suppressTimer);

      // Re-enable 150 ms after the last scroll event (scroll has stopped)
      function onScroll() {
        clearTimeout(suppressTimer);
        suppressTimer = setTimeout(endSuppressSpy, 150);
      }
      function endSuppressSpy() {
        suppressSpy = false;
        window.removeEventListener('scroll', onScroll);
      }

      window.addEventListener('scroll', onScroll);
      // Safety fallback in case no scroll events fire (target already visible)
      suppressTimer = setTimeout(endSuppressSpy, 1200);
    }

    // ── Helper: build an <a> from a heading ──────────────────────────────
    function makeLink(h) {
      var a = document.createElement('a');
      a.href      = '#' + h.id;
      a.className = 'chapter-toc__link';
      var clone = h.cloneNode(true);
      var icon  = clone.querySelector('.anchor-section-href');
      if (icon) icon.remove();
      a.textContent = clone.textContent.trim();
      return a;
    }

    // ── Helper: close every open subnav and reset toggle icons ───────────
    function closeAllSubnavs() {
      tocList.querySelectorAll('.chapter-toc__subnav').forEach(function (nav) {
        nav.classList.remove('is-open');
      });
      tocList.querySelectorAll('.chapter-toc__toggle').forEach(function (btn) {
        btn.setAttribute('aria-expanded', 'false');
        btn.textContent = '▸';
      });
    }

    // ── Helper: open one subnav (and its toggle) ─────────────────────────
    function openSubnav(subnav, toggleBtn) {
      subnav.classList.add('is-open');
      if (toggleBtn) {
        toggleBtn.setAttribute('aria-expanded', 'true');
        toggleBtn.textContent = '▾';
      }
    }

    // ── Build flat list (depth = 2) ──────────────────────────────────────
    if (depth < 3) {
      headings.forEach(function (h) {
        var li = document.createElement('li');
        li.className = 'chapter-toc__item chapter-toc__item--' +
          h.tagName.toLowerCase();
        var a = makeLink(h);
        li.appendChild(a);
        tocList.appendChild(li);
        links.push(a);
        itemMap[h.id] = li;
      });
    }

    // ── Build accordion list (depth = 3) ─────────────────────────────────
    else {
      toc.classList.add('chapter-toc--depth-3');

      // Group consecutive h3s under their preceding h2 (or h1).
      // A "group" is { heading, children[] } where heading is h1 or h2.
      var groups = [];
      headings.forEach(function (h) {
        if (h.tagName === 'H3' && groups.length) {
          groups[groups.length - 1].children.push(h);
        } else {
          groups.push({ heading: h, children: [] });
        }
      });

      groups.forEach(function (group) {
        var h       = group.heading;
        var li      = document.createElement('li');
        li.className = 'chapter-toc__item chapter-toc__item--' +
          h.tagName.toLowerCase();

        if (group.children.length === 0) {
          // Simple entry – no toggle
          var a = makeLink(h);
          li.appendChild(a);
          links.push(a);
          itemMap[h.id] = li;

        } else {
          // Entry with collapsible subnav
          var row = document.createElement('div');
          row.className = 'chapter-toc__row';

          var a = makeLink(h);
          row.appendChild(a);
          links.push(a);

          var btn = document.createElement('button');
          btn.className = 'chapter-toc__toggle';
          btn.setAttribute('aria-label', 'Toggle subsections');
          btn.setAttribute('aria-expanded', 'false');
          btn.textContent = '▸';
          row.appendChild(btn);
          li.appendChild(row);

          var subnav = document.createElement('ul');
          subnav.className = 'chapter-toc__subnav';

          group.children.forEach(function (h3) {
            var subLi = document.createElement('li');
            subLi.className = 'chapter-toc__item chapter-toc__item--h3';
            var a3 = makeLink(h3);
            subLi.appendChild(a3);
            subnav.appendChild(subLi);
            links.push(a3);
            // Store back-references for scroll-spy auto-expand
            itemMap[h3.id]          = subLi;
            subLi._parentLi         = li;
            subLi._parentSubnav     = subnav;
            subLi._parentToggleBtn  = btn;
          });

          li._subnav    = subnav;
          li._toggleBtn = btn;
          li.appendChild(subnav);

          // Shared accordion toggle logic
          function handleToggle() {
            var wasOpen = subnav.classList.contains('is-open');
            closeAllSubnavs();
            if (!wasOpen) openSubnav(subnav, btn);
          }

          // Toggle button click
          btn.addEventListener('click', handleToggle);

          // Clicking the h2 link also opens/closes the accordion.
          // Suppress scroll-spy first so the smooth scroll to the target
          // heading doesn't fire intermediate observers that close the
          // subnav we just opened.  Browser still follows the href.
          a.addEventListener('click', function () {
            startSuppressSpy();
            handleToggle();
          });
        }

        tocList.appendChild(li);
        itemMap[h.id] = li;
      });
    }

    // ── Scroll-spy ───────────────────────────────────────────────────────
    function setActive(id) {
      var displayId = id;
      var targetLi  = itemMap[id];

      // If the active heading is an h3 whose subnav is currently collapsed,
      // highlight the parent h2 link instead — the h3 entry is not visible.
      if (depth >= 3 && targetLi && targetLi._parentSubnav) {
        if (!targetLi._parentSubnav.classList.contains('is-open')) {
          var parentLink = targetLi._parentLi &&
            targetLi._parentLi.querySelector('.chapter-toc__link');
          if (parentLink) {
            displayId = parentLink.getAttribute('href').slice(1);
          }
        }
      }

      links.forEach(function (link) {
        link.classList.toggle('active', link.getAttribute('href') === '#' + displayId);
      });

      // Auto-expand the parent h2 when an h3 becomes active during normal
      // (non-programmatic) scrolling.
      if (depth >= 3 && !suppressSpy && targetLi && targetLi._parentSubnav) {
        if (!targetLi._parentSubnav.classList.contains('is-open')) {
          closeAllSubnavs();
          openSubnav(targetLi._parentSubnav, targetLi._parentToggleBtn);
        }
      }
    }

    if (headings.length) setActive(headings[0].id);

    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) { setActive(entry.target.id); }
        });
      },
      { rootMargin: '-8% 0px -85% 0px', threshold: 0 }
    );

    headings.forEach(function (h) { observer.observe(h); });
  });
}());
