/** Streamer hub — Camgirl voice deck for chapter narration (parent page, iframe is visual-only). */
(function () {
  "use strict";

  function init() {
    if (!window.MNCamgirlsStreamVoice) return;
    window.MNCamgirlsStreamVoice.init({
      storageKey: "mn-f5-voice",
      deckId: "streamer-voice-deck",
      onLine: function (speaker, text) {
        var st = document.getElementById("streamer-status");
        if (!st) return;
        if (speaker && speaker.name) st.textContent = speaker.name + " · " + text.slice(0, 160);
        else st.textContent = text.slice(0, 200);
      },
    });
    document.addEventListener("mn:voice-state", function () {
      /* keep streamer status in sync when composer enables voice */
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
