(function () {
  "use strict";

  var APP_BASE = (typeof window !== "undefined" && window.APP_BASE !== undefined)
    ? window.APP_BASE
    : "";

  var state = {
    catalog: null,
    category: "all",
    selected: null,
    filter: "all",
    showOther: false,
  };

  function $(id) { return document.getElementById(id); }

  function methodClass(method) {
    return "method m-" + method;
  }

  function visibleCategories() {
    var cats = state.catalog.categories || [];
    if (state.showOther) return cats;
    return cats.filter(function (cat) { return !cat.internal; });
  }

  function renderCategories() {
    var host = $("cats");
    host.innerHTML = "";
    var all = document.createElement("button");
    all.type = "button";
    all.className = "cat" + (state.category === "all" ? " active" : "");
    all.innerHTML = "All endpoints <span class=\"count\">" + filtered().length + "</span>";
    all.addEventListener("click", function () {
      state.category = "all";
      renderCategories();
      renderList();
    });
    host.appendChild(all);
    visibleCategories().forEach(function (cat) {
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "cat" + (state.category === cat.id ? " active" : "");
      btn.innerHTML = cat.label + " <span class=\"count\">" + cat.count + "</span>";
      btn.addEventListener("click", function () {
        state.category = cat.id;
        renderCategories();
        renderList();
      });
      host.appendChild(btn);
    });
    var toggle = $("toggle-other");
    if (toggle) {
      toggle.textContent = state.showOther ? "Hide other" : "Other";
      toggle.setAttribute("aria-pressed", state.showOther ? "true" : "false");
    }
  }

  function filtered() {
    var q = ($("q").value || "").trim().toLowerCase();
    return (state.catalog.endpoints || []).filter(function (row) {
      if (!state.showOther && row.internal) return false;
      if (state.category !== "all" && row.category !== state.category) return false;
      if (state.filter === "safe" && !row.try_safe) return false;
      if (state.filter === "GET" && row.method !== "GET") return false;
      if (state.filter === "POST" && row.method !== "POST") return false;
      if (!q) return true;
      return row.path.toLowerCase().indexOf(q) >= 0
        || row.method.toLowerCase().indexOf(q) >= 0
        || row.category.indexOf(q) >= 0;
    });
  }

  function updateStats() {
    var rows = filtered();
    $("stat-total").textContent = String(rows.length);
    $("stat-safe").textContent = String(rows.filter(function (r) { return r.try_safe; }).length);
    $("stat-cats").textContent = String(visibleCategories().length);
  }

  function renderList() {
    var host = $("list");
    var rows = filtered().slice(0, 300);
    host.innerHTML = "";
    updateStats();
    if (!rows.length) {
      host.innerHTML = "<p class=\"empty\">No endpoints in this view. Try another filter or show Other.</p>";
      return;
    }
    rows.forEach(function (row) {
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "ep" + (state.selected === row ? " active" : "");
      var badge = document.createElement("span");
      badge.className = methodClass(row.method);
      badge.textContent = row.method;
      var path = document.createElement("span");
      path.className = "path";
      path.textContent = row.path;
      btn.appendChild(badge);
      btn.appendChild(path);
      btn.addEventListener("click", function () { openTry(row); });
      host.appendChild(btn);
    });
    if (filtered().length > 300) {
      var note = document.createElement("p");
      note.className = "meta";
      note.textContent = "Showing 300. Search to narrow the list.";
      host.appendChild(note);
    }
  }

  function fillPath(path, values) {
    return path.replace(/<([^>]+)>/g, function (_, token) {
      var name = token.indexOf(":") >= 0 ? token.split(":").pop() : token;
      return encodeURIComponent(values[name] || "");
    });
  }

  function openTry(row) {
    state.selected = row;
    renderList();
    var form = $("form");
    form.innerHTML = "";
    $("try-hint").textContent = "";
    var title = document.createElement("h2");
    title.className = "title";
    title.textContent = row.method + " " + row.path;
    form.appendChild(title);
    var meta = document.createElement("p");
    meta.className = "meta";
    meta.textContent = labelFor(row.category)
      + (row.try_safe ? " · safe to try" : " · confirm before sending");
    form.appendChild(meta);

    var values = {};
    (row.params || []).forEach(function (name) {
      var wrap = document.createElement("div");
      wrap.className = "field";
      var label = document.createElement("label");
      label.textContent = name;
      var input = document.createElement("input");
      input.type = "text";
      input.placeholder = name;
      input.addEventListener("input", function () { values[name] = input.value; });
      wrap.appendChild(label);
      wrap.appendChild(input);
      form.appendChild(wrap);
    });

    var qWrap = document.createElement("div");
    qWrap.className = "field";
    var qLabel = document.createElement("label");
    qLabel.textContent = "Query string";
    var query = document.createElement("input");
    query.type = "text";
    query.placeholder = "e.g. user_id=demo";
    qWrap.appendChild(qLabel);
    qWrap.appendChild(query);
    form.appendChild(qWrap);

    var body = null;
    if (row.method !== "GET") {
      var bWrap = document.createElement("div");
      bWrap.className = "field";
      var bLabel = document.createElement("label");
      bLabel.textContent = "JSON body";
      body = document.createElement("textarea");
      body.rows = 6;
      body.value = "{}";
      bWrap.appendChild(bLabel);
      bWrap.appendChild(body);
      form.appendChild(bWrap);
    }

    var run = document.createElement("button");
    run.type = "button";
    run.className = "run";
    run.textContent = row.try_safe ? "Try now" : "Send " + row.method;
    run.addEventListener("click", function () {
      if (!row.try_safe && !window.confirm("Send " + row.method + " " + row.path + "?")) return;
      run.disabled = true;
      var path = fillPath(row.path, values);
      var qs = (query.value || "").replace(/^\?/, "");
      var url = path + (qs ? "?" + qs : "");
      var opts = { method: row.method, headers: { Accept: "application/json" } };
      if (body) {
        opts.headers["Content-Type"] = "application/json";
        opts.body = body.value || "{}";
      }
      var started = performance.now();
      fetch(url, opts).then(function (res) {
        return res.text().then(function (text) {
          return { status: res.status, text: text, ms: Math.round(performance.now() - started) };
        });
      }).then(function (result) {
        showResult(result);
      }).catch(function (err) {
        showResult({ status: 0, text: String(err), ms: Math.round(performance.now() - started) });
      }).finally(function () { run.disabled = false; });
    });
    form.appendChild(run);

    if (row.try_safe) run.click();
  }

  function labelFor(id) {
    var cats = state.catalog.categories || [];
    for (var i = 0; i < cats.length; i++) {
      if (cats[i].id === id) return cats[i].label;
    }
    return id;
  }

  function showResult(result) {
    var out = $("out");
    var pretty = result.text;
    try { pretty = JSON.stringify(JSON.parse(result.text), null, 2); } catch (e) {}
    var klass = result.status >= 200 && result.status < 400 ? "status-ok" : "status-bad";
    out.innerHTML = "";
    var line = document.createElement("div");
    line.className = klass;
    line.textContent = "HTTP " + result.status + " · " + result.ms + " ms";
    out.appendChild(line);
    out.appendChild(document.createTextNode("\n" + pretty));
  }

  function boot() {
    $("q").addEventListener("input", function () {
      renderCategories();
      renderList();
    });
    document.querySelectorAll("[data-filter]").forEach(function (chip) {
      chip.addEventListener("click", function () {
        state.filter = chip.getAttribute("data-filter");
        document.querySelectorAll("[data-filter]").forEach(function (el) {
          el.classList.toggle("active", el === chip);
        });
        renderCategories();
        renderList();
      });
    });
    $("toggle-other").addEventListener("click", function () {
      state.showOther = !state.showOther;
      if (!state.showOther && state.category !== "all") {
        var still = visibleCategories().some(function (c) { return c.id === state.category; });
        if (!still) state.category = "all";
      }
      loadCatalog();
    });
    loadCatalog();
  }

  function loadCatalog() {
    $("list").textContent = "Loading catalog…";
    var url = APP_BASE + "/api/lab/catalog?internal=" + (state.showOther ? "1" : "0");
    fetch(url).then(function (res) { return res.json(); }).then(function (data) {
      state.catalog = data;
      renderCategories();
      renderList();
    }).catch(function (err) {
      $("list").innerHTML = "<p class=\"empty\">Could not load catalog: " + err + "</p>";
    });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();
