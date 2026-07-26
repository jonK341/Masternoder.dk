/**
 * Rotating stream chapters — encoded AI content + live composer dock.
 */
(function () {
  "use strict";

  var API = "/api/exchange/fleet-stream/composer?stream=1&live=1";
  var state = {
    data: null,
    timer: null,
    lastChapterId: "",
  };

  function $(id) {
    return document.getElementById(id);
  }

  function esc(s) {
    var d = document.createElement("div");
    d.textContent = s == null ? "" : String(s);
    return d.innerHTML;
  }

  function qsStream() {
    var m = /[?&]mode=stream|[?&]stream=1/.test(window.location.search);
    var iframe = window.frameElement;
    return m || (document.body && document.body.classList.contains("f5-stream"));
  }

  function mountEl() {
    return (
      $("stream-chapter-composer") ||
      $("f5-composer-dock") ||
      document.querySelector("[data-stream-composer]")
    );
  }

  function render(el, data) {
    if (!el || !data || !data.success) return;
    var cur = data.current;
    if (!cur) {
      el.innerHTML = "<p class='sc-meta'>No chapters configured.</p>";
      return;
    }
    var chapters = data.chapters || [];
    el.innerHTML =
      '<aside class="sc-panel" aria-live="polite">' +
      '<div class="sc-head">' +
      '<img class="sc-visual" src="' + esc(cur.visual) + '" alt="" width="40" height="40" loading="lazy" />' +
      '<div><p class="sc-kicker">🎼 Stream composer · rotate ' + esc(String(data.rotate_sec || 75)) + "s</p>" +
      "<strong class='sc-title'>" + esc(cur.title) + "</strong>" +
      "<span class='sc-encode'>" + esc(cur.encode_profile) + " encode</span></div></div>" +
      "<p class='sc-body'>" + esc(cur.ai_content) + "</p>" +
      '<div class="sc-dots" role="tablist" aria-label="Chapter rotation">' +
      chapters
        .map(function (ch, i) {
          return (
            '<button type="button" class="sc-dot' +
            (i === data.current_index ? " is-active" : "") +
            '" data-idx="' +
            i +
            '" aria-label="' +
            esc(ch.title) +
            '"></button>'
          );
        })
        .join("") +
      "</div>" +
      '<div class="sc-actions">' +
      '<button type="button" class="sc-btn" id="sc-prev">Prev</button>' +
      '<button type="button" class="sc-btn primary" id="sc-speak">Speak chapter</button>' +
      '<button type="button" class="sc-btn" id="sc-next">Next</button>' +
      "</div></aside>";

    el.querySelectorAll(".sc-dot").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var idx = parseInt(btn.getAttribute("data-idx"), 10);
        load(idx);
      });
    });
    var prev = el.querySelector("#sc-prev");
    var next = el.querySelector("#sc-next");
    var speak = el.querySelector("#sc-speak");
    if (prev) {
      prev.addEventListener("click", function () {
        var n = ((data.current_index || 0) - 1 + chapters.length) % chapters.length;
        load(n);
      });
    }
    if (next) {
      next.addEventListener("click", function () {
        var n = ((data.current_index || 0) + 1) % chapters.length;
        load(n);
      });
    }
    if (speak) {
      speak.addEventListener("click", function () {
        announceChapter(cur);
      });
    }
  }

  function announceChapter(ch) {
    if (!ch) return;
    document.dispatchEvent(
      new CustomEvent("mn:stream-chapter", {
        detail: { chapter: ch, speak: true },
      })
    );
  }

  function onChapterChange(data) {
    var cur = data && data.current;
    if (!cur || cur.id === state.lastChapterId) return;
    state.lastChapterId = cur.id;
    document.dispatchEvent(
      new CustomEvent("mn:stream-chapter", {
        detail: { chapter: cur, speak: false, composer: data },
      })
    );
  }

  function load(index) {
    var url = API;
    if (index != null && !isNaN(index)) {
      url += "&index=" + encodeURIComponent(String(index));
    }
    return fetch(url, { credentials: "same-origin" })
      .then(function (r) {
        return r.json();
      })
      .then(function (d) {
        state.data = d;
        var el = mountEl();
        render(el, d);
        onChapterChange(d);
        schedule(d.rotate_sec || 75);
        return d;
      })
      .catch(function () {
        var el = mountEl();
        if (el) el.innerHTML = "<p class='sc-meta'>Composer offline.</p>";
      });
  }

  function schedule(sec) {
    if (state.timer) clearInterval(state.timer);
    state.timer = setInterval(function () {
      load(null);
    }, Math.max(30000, (sec || 75) * 1000));
  }

  function init() {
    var el = mountEl();
    if (!el) return;
    var streamOnly = el.getAttribute("data-stream-only") === "1";
    if (streamOnly && !qsStream()) {
      el.hidden = true;
      return;
    }
    el.hidden = false;
    load(null);
  }

  window.MNStreamChapterComposer = { load: load, getState: function () { return state.data; } };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
