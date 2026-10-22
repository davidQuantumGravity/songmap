// Depth toggles (Hear / Understand / Derive), theme toggle, mobile menu, reading progress,
// current-section chips, and client-side math only when the build could not pre-render it.
(function () {
  var KEY = "tb-layers", THEME = "tb-theme";
  function load() { try { return JSON.parse(localStorage.getItem(KEY)) || {}; } catch (e) { return {}; } }
  function save(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* private mode */ } }
  function apply(state) {
    ["hear", "understand", "derive"].forEach(function (l) {
      var on = state[l] !== false;
      document.body.classList.toggle("hide-" + l, !on);
      document.querySelectorAll('.layers button[data-layer="' + l + '"]').forEach(function (b) {
        b.setAttribute("aria-pressed", on ? "true" : "false");
      });
    });
  }
  document.addEventListener("DOMContentLoaded", function () {
    var state = load();
    apply(state);
    document.querySelectorAll(".layers button").forEach(function (b) {
      b.addEventListener("click", function () {
        var l = b.getAttribute("data-layer");
        state[l] = state[l] === false;
        var anyOn = ["hear", "understand", "derive"].some(function (k) { return state[k] !== false; });
        if (!anyOn) state[l] = true;
        save(KEY, JSON.stringify(state)); apply(state);
      });
    });

    var root = document.documentElement, tb = document.querySelector("header .theme");
    if (tb) tb.addEventListener("click", function () {
      var cur = root.getAttribute("data-theme") ||
        (window.matchMedia && matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
      var next = cur === "dark" ? "light" : "dark";
      root.setAttribute("data-theme", next); save(THEME, next);
    });

    var m = document.querySelector("header .menu");
    if (m) m.addEventListener("click", function () { document.body.classList.toggle("menu-open"); });
    document.querySelectorAll("aside.side a").forEach(function (a) {
      a.addEventListener("click", function () { document.body.classList.remove("menu-open"); });
    });

    var bar = document.querySelector(".progress i"), top = document.querySelector(".totop");
    var chips = {}, secs = [];
    document.querySelectorAll(".onpage a").forEach(function (a) { chips[a.getAttribute("href").slice(1)] = a; });
    document.querySelectorAll("main > section[id]").forEach(function (s) { if (chips[s.id]) secs.push(s); });
    function onScroll() {
      var h = document.documentElement, max = h.scrollHeight - h.clientHeight;
      if (bar) bar.style.setProperty("--p", (max > 0 ? 100 * h.scrollTop / max : 0) + "%");
      if (top) top.classList.toggle("on", h.scrollTop > 600);
      var cur = null;
      secs.forEach(function (s) { if (s.getBoundingClientRect().top < 140) cur = s.id; });
      Object.keys(chips).forEach(function (k) { chips[k].classList.toggle("on", k === cur); });
    }
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();

    if (window.renderMathInElement) {
      renderMathInElement(document.querySelector("main"), {
        delimiters: [{ left: "$$", right: "$$", display: true }, { left: "$", right: "$", display: false }],
        throwOnError: false
      });
    }
  });
})();
