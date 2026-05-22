/* ─────────────────────────────────────────────────────────────
   rekipedia · reki.js  (sidebar toggle + wiki search)
   ───────────────────────────────────────────────────────────── */

(function () {
  "use strict";

  /* ── Hamburger / sidebar toggle ──────────────────────────── */
  function initSidebar() {
    const btn     = document.getElementById("hamburger-btn");
    const overlay = document.getElementById("sidebar-overlay");
    if (!btn) return;

    function open()  { document.body.classList.add("sidebar-open"); }
    function close() { document.body.classList.remove("sidebar-open"); }
    function toggle(){ document.body.classList.toggle("sidebar-open"); }

    btn.addEventListener("click", toggle);
    if (overlay) overlay.addEventListener("click", close);

    // close on nav link click (mobile UX)
    document.querySelectorAll(".sidebar a").forEach(function (a) {
      a.addEventListener("click", function () {
        if (window.innerWidth <= 768) close();
      });
    });

    // close on resize to desktop
    window.addEventListener("resize", function () {
      if (window.innerWidth > 768) close();
    });
  }

  /* ── Collapsible category groups ────────────────────────── */
  function toggleCat(el) {
    el.classList.toggle("collapsed");
  }
  window.toggleCat = toggleCat;   // keep template onclick= working

  /* ── Wiki sidebar search ─────────────────────────────────── */
  function initSearch() {
    var searchInput  = document.getElementById("wiki-search");
    var wikiNav      = document.getElementById("wiki-nav");
    var searchResults= document.getElementById("wiki-search-results");
    var searchTimer  = null;
    if (!searchInput) return;

    searchInput.addEventListener("input", function () {
      var q = this.value.trim();
      clearTimeout(searchTimer);
      if (!q || q.length < 2) {
        if (wikiNav)      wikiNav.style.display = "";
        if (searchResults){ searchResults.innerHTML = ""; searchResults.classList.remove("visible"); }
        return;
      }
      searchTimer = setTimeout(function () {
        fetch("/api/wiki/search?q=" + encodeURIComponent(q))
          .then(function (r) { return r.json(); })
          .then(function (items) {
            if (wikiNav) wikiNav.style.display = "none";
            if (!searchResults) return;
            if (!items.length) {
              searchResults.innerHTML = '<p class="no-results">No results for "' + q + '"</p>';
            } else {
              searchResults.innerHTML = items.map(function (item) {
                return '<a class="search-result-item" href="/wiki/' + item.slug + '">' +
                  '<div class="search-result-title">◦ ' + item.title + "</div>" +
                  (item.snippet ? '<div class="search-result-snippet">' + item.snippet + "</div>" : "") +
                  '<div class="search-result-section">' + item.section.replace(/[-_]/g, " ") + "</div>" +
                  "</a>";
              }).join("");
            }
            searchResults.classList.add("visible");
          })
          .catch(function () {});
      }, 250);
    });

    searchInput.addEventListener("keydown", function (e) {
      if (e.key === "Escape") {
        this.value = "";
        if (wikiNav) wikiNav.style.display = "";
        if (searchResults){ searchResults.innerHTML = ""; searchResults.classList.remove("visible"); }
      }
    });
  }

  /* ── Boot ────────────────────────────────────────────────── */
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      initSidebar();
      initSearch();
    });
  } else {
    initSidebar();
    initSearch();
  }
})();
