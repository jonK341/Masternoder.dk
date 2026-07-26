/**
 * Fleet stream live chat — live / news / events + YouTube rail.
 */
(function () {
  "use strict";

  var BOOT = "/api/exchange/fleet-stream/chat/bootstrap";
  var MSG = "/api/exchange/fleet-stream/chat/messages";
  var CLAIM = "/api/exchange/fleet-stream/chat/claim-event";

  var state = {
    channel: "live",
    boot: null,
    lastIds: { live: "", news: "", events: "" },
    guestId: "",
    handle: "",
    timer: null,
  };

  function esc(s) {
    var d = document.createElement("div");
    d.textContent = s == null ? "" : String(s);
    return d.innerHTML;
  }

  function guestKey() {
    if (state.guestId) return state.guestId;
    try {
      state.guestId = localStorage.getItem("mn_fleet_guest") || "";
      if (!state.guestId) {
        state.guestId = "g_" + Math.random().toString(36).slice(2, 12);
        localStorage.setItem("mn_fleet_guest", state.guestId);
      }
    } catch (e) {
      state.guestId = "g_" + Date.now();
    }
    return state.guestId;
  }

  function renderMessages(el, rows) {
    var log = el.querySelector(".f5-stream-chat-log");
    if (!log) return;
    rows.forEach(function (m) {
      if (!m || !m.id) return;
      var ch = m.channel || state.channel;
      if (state.lastIds[ch] === m.id) return;
      state.lastIds[ch] = m.id;
      var div = document.createElement("div");
      var cls = "f5-stream-chat-msg";
      if (m.kind === "reward" || m.kind === "event") cls += " is-event";
      if (m.kind === "news") cls += " is-news";
      div.className = cls;
      div.innerHTML = "<strong>" + esc(m.handle || "?") + "</strong> " + esc(m.text || "");
      log.appendChild(div);
    });
    log.scrollTop = log.scrollHeight;
  }

  function fetchChannel(el, ch) {
    var since = state.lastIds[ch] || "";
    var url = MSG + "?channel=" + encodeURIComponent(ch) + "&limit=60";
    if (since) url += "&since_id=" + encodeURIComponent(since);
    return fetch(url, { credentials: "same-origin" })
      .then(function (r) {
        return r.json();
      })
      .then(function (d) {
        if (d && d.success) renderMessages(el, d.messages || []);
      })
      .catch(function () {});
  }

  function poll(el) {
    fetchChannel(el, state.channel);
    if (state.channel !== "news") fetchChannel(el, "news");
    if (state.channel !== "events") fetchChannel(el, "events");
  }

  function postMessage(el) {
    var ta = el.querySelector(".f5-stream-chat-text");
    var name = el.querySelector(".f5-stream-chat-name");
    var text = ta && ta.value ? ta.value.trim() : "";
    if (!text) return;
    state.handle = (name && name.value) || state.handle || "Guest";
    fetch(MSG, {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-Fleet-Guest": guestKey() },
      body: JSON.stringify({
        channel: state.channel,
        text: text,
        handle: state.handle,
        guest_id: guestKey(),
      }),
    })
      .then(function (r) {
        return r.json();
      })
      .then(function (d) {
        if (d.success && ta) ta.value = "";
        if (d.message) renderMessages(el, [d.message]);
        if (d.reward && d.reward.success) {
          renderMessages(el, [
            {
              id: "rw_" + Date.now(),
              channel: "events",
              handle: "MN2",
              text: "Reward credited for your comment.",
              kind: "reward",
            },
          ]);
        }
      });
  }

  function claimEvent(el) {
    fetch(CLAIM, {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-Fleet-Guest": guestKey() },
      body: JSON.stringify({ guest_id: guestKey() }),
    })
      .then(function (r) {
        return r.json();
      })
      .then(function (d) {
        if (d.message) renderMessages(el, [d.message]);
        else if (d.error === "login_required_for_mn2") {
          renderMessages(el, [
            {
              id: "auth_" + Date.now(),
              channel: "events",
              handle: "Fleet",
              text: "Log in on MasterNoder to claim MN2 event drops.",
              kind: "event",
            },
          ]);
        }
      });
  }

  function mount(target) {
    var el = typeof target === "string" ? document.getElementById(target) : target;
    if (!el) return;
    el.classList.add("f5-stream-chat");
    el.innerHTML =
      '<div class="f5-stream-chat-head">' +
      "<h2>Live chat</h2>" +
      '<div class="f5-stream-chat-yt" id="f5-chat-yt"></div></div>' +
      '<div class="f5-stream-chat-tabs" role="tablist">' +
      '<button type="button" class="f5-stream-chat-tab is-active" data-ch="live">Live</button>' +
      '<button type="button" class="f5-stream-chat-tab" data-ch="news">News</button>' +
      '<button type="button" class="f5-stream-chat-tab" data-ch="events">Events</button>' +
      "</div>" +
      '<div class="f5-stream-chat-log" aria-live="polite"></div>' +
      '<div class="f5-stream-chat-compose">' +
      '<input class="f5-stream-chat-name" type="text" maxlength="32" placeholder="Display name" />' +
      '<textarea class="f5-stream-chat-text" maxlength="420" placeholder="Comment on the fleet stream…"></textarea>' +
      '<div class="f5-stream-chat-actions">' +
      '<button type="button" class="f5-stream-chat-btn primary f5-stream-chat-send">Send</button>' +
      '<button type="button" class="f5-stream-chat-btn f5-stream-chat-claim">Claim MN2 drop</button>' +
      "</div></div>" +
      '<p class="f5-stream-chat-meta">Logged-in users earn MN2 for live comments (daily cap). Event drops credit wallet; optional on-chain micro-tx when enabled.</p>";

    el.querySelectorAll(".f5-stream-chat-tab").forEach(function (btn) {
      btn.addEventListener("click", function () {
        el.querySelectorAll(".f5-stream-chat-tab").forEach(function (b) {
          b.classList.remove("is-active");
        });
        btn.classList.add("is-active");
        state.channel = btn.getAttribute("data-ch") || "live";
        poll(el);
      });
    });
    el.querySelector(".f5-stream-chat-send").addEventListener("click", function () {
      postMessage(el);
    });
    el.querySelector(".f5-stream-chat-claim").addEventListener("click", function () {
      claimEvent(el);
    });
    var ta = el.querySelector(".f5-stream-chat-text");
    if (ta) {
      ta.addEventListener("keydown", function (ev) {
        if (ev.key === "Enter" && !ev.shiftKey) {
          ev.preventDefault();
          postMessage(el);
        }
      });
    }

    fetch(BOOT, { credentials: "same-origin" })
      .then(function (r) {
        return r.json();
      })
      .then(function (d) {
        state.boot = d;
        var yt = el.querySelector("#f5-chat-yt");
        if (!yt || !d.youtube) return;
        var ph = el.querySelector(".f5-stream-chat-text");
        if (ph && d.stream && d.stream.chat_placeholder) {
          ph.placeholder = d.stream.chat_placeholder;
        }
        if (d.youtube.embed_url) {
          var title = (d.stream && d.stream.title) || "YouTube live";
          var badge = (d.stream && d.stream.status_badge) || "LIVE";
          var watch = d.youtube.watch_url || d.youtube.channel_url || "";
          var studio = d.youtube.studio_url || "";
          yt.innerHTML =
            '<div class="f5-stream-chat-yt-bar">' +
            '<span class="f5-stream-chat-yt-badge">' +
            esc(badge) +
            "</span>" +
            '<span class="f5-stream-chat-yt-title">' +
            esc(title) +
            "</span>" +
            "</div>" +
            '<iframe class="f5-stream-chat-yt-frame" title="' +
            esc(title) +
            '" src="' +
            esc(d.youtube.embed_url) +
            '" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen referrerpolicy="strict-origin-when-cross-origin" loading="lazy"></iframe>' +
            '<div class="f5-stream-chat-yt-actions">' +
            '<button type="button" class="f5-stream-chat-yt-btn f5-stream-chat-yt-unmute">Unmute</button>' +
            (watch
              ? '<a class="f5-stream-chat-yt-btn" href="' +
                esc(watch) +
                '" target="_blank" rel="noopener noreferrer">Watch on YouTube</a>'
              : "") +
            (studio
              ? '<a class="f5-stream-chat-yt-btn subtle" href="' +
                esc(studio) +
                '" target="_blank" rel="noopener noreferrer">Studio</a>'
              : "") +
            "</div>";
          var unmuteBtn = yt.querySelector(".f5-stream-chat-yt-unmute");
          var frame = yt.querySelector(".f5-stream-chat-yt-frame");
          if (unmuteBtn && frame && d.youtube.embed_url_unmuted) {
            unmuteBtn.addEventListener("click", function () {
              frame.src = d.youtube.embed_url_unmuted;
              unmuteBtn.textContent = "Sound on";
              unmuteBtn.disabled = true;
            });
          }
        } else {
          yt.innerHTML =
            '<div class="f5-stream-chat-yt-placeholder">YouTube live ID not set — watch on ' +
            '<a href="' +
            esc(d.youtube.channel_url || "https://www.youtube.com") +
            '" target="_blank" rel="noopener">YouTube</a> and chat here.</div>';
        }
        var ms = d.poll_ms || 4000;
        if (state.timer) clearInterval(state.timer);
        state.timer = setInterval(function () {
          poll(el);
        }, ms);
        poll(el);
      });
  }

  window.MNFleetStreamChat = { mount: mount, poll: poll };

  function autoMount() {
    var ids = ["f5-stream-chat", "fp-fleet-chat"];
    ids.forEach(function (id) {
      var node = document.getElementById(id);
      if (node) mount(node);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", autoMount);
  } else {
    autoMount();
  }
})();
