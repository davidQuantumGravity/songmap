// Depth toggles (Hear / Understand / Derive), auto-play of the examples, theme toggle, mobile menu, reading progress,
// current-section chips, and client-side math only when the build could not pre-render it.
(function () {
  var KEY = "tb-layers", THEME = "tb-theme", AUTO = "tb-autoplay";
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

    // Auto-play: when an example ends, the next one on the page that is shown (its depth layer on) scrolls into
    // view and plays. Starting any example pauses the others either way.
    var media = Array.prototype.slice.call(document.querySelectorAll("main video, main audio"));
    var auto = false;
    try { auto = localStorage.getItem(AUTO) === "1"; } catch (e) { /* private mode */ }
    function showAuto() {
      document.querySelectorAll(".layers .autoplay").forEach(function (b) { b.setAttribute("aria-pressed", auto ? "true" : "false"); });
    }
    showAuto();
    document.querySelectorAll(".layers .autoplay").forEach(function (b) {
      b.addEventListener("click", function () { auto = !auto; save(AUTO, auto ? "1" : "0"); showAuto(); });
    });
    media.forEach(function (el, i) {
      el.addEventListener("play", function () {
        media.forEach(function (o) { if (o !== el && !o.paused) o.pause(); });
      });
      el.addEventListener("ended", function () {
        if (!auto) return;
        for (var j = i + 1; j < media.length; j++) {
          var next = media[j];
          if (next.offsetParent === null) continue;          // inside a hidden depth layer
          next.scrollIntoView({ behavior: "smooth", block: "center" });
          var p = next.play();
          if (p && p.catch) p.catch(function () { /* the browser refused: the reader presses play */ });
          return;
        }
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
