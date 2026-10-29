(function () {
  "use strict";

  var APP_BASE = (typeof window !== "undefined" && window.APP_BASE !== undefined)
    ? window.APP_BASE
    : (function () {
      var p = (typeof window !== "undefined" && window.location && window.location.pathname) || "";
      return p.indexOf("/vidgenerator/") === 0 ? "/vidgenerator" : "";
    })();

  var state = { catalog: null, category: "all", selected: null };

  function $(id) { return document.getElementById(id); }

  function methodClass(method) {
    return "method m-" + method;
  }

  function renderCategories() {
    var host = $("cats");
    host.innerHTML = "";
    var all = document.createElement("button");
    all.type = "button";
    all.className = "cat" + (state.category === "all" ? " active" : "");
    all.innerHTML = "All endpoints <span class=\"count\">" + state.catalog.total + "</span>";
    all.addEventListener("click", function () {
      state.category = "all";
      renderCategories();
      renderList();
    });
    host.appendChild(all);
    (state.catalog.categories || []).forEach(function (cat) {
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
  }

  function filtered() {
    var q = ($("q").value || "").trim().toLowerCase();
    return (state.catalog.endpoints || []).filter(function (row) {
      if (state.category !== "all" && row.category !== state.category) return false;
      if (!q) return true;
      return row.path.toLowerCase().indexOf(q) >= 0
        || row.method.toLowerCase().indexOf(q) >= 0
        || row.category.indexOf(q) >= 0;
    });
  }

  function renderList() {
    var host = $("list");
    var rows = filtered().slice(0, 250);
    host.innerHTML = "";
    if (!rows.length) {
      host.textContent = "No endpoints in this view.";
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
    if (filtered().length > 250) {
      var note = document.createElement("p");
      note.className = "meta";
      note.textContent = "Showing 250. Search to narrow the list.";
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
    var title = document.createElement("h2");
    title.textContent = row.method + " " + row.path;
    form.appendChild(title);
    var meta = document.createElement("p");
    meta.className = "meta";
    meta.textContent = "Category: " + row.category + (row.try_safe ? " · safe to try" : " · confirm before sending");
    form.appendChild(meta);

    var values = {};
    (row.params || []).forEach(function (name) {
      var label = document.createElement("label");
      label.className = "meta";
      label.textContent = name;
      var input = document.createElement("input");
      input.type = "text";
      input.placeholder = name;
      input.addEventListener("input", function () { values[name] = input.value; });
      form.appendChild(label);
      form.appendChild(input);
    });

    var query = document.createElement("input");
    query.type = "text";
    query.placeholder = "Query string, e.g. user_id=demo";
    form.appendChild(query);

    var body = null;
    if (row.method !== "GET") {
      body = document.createElement("textarea");
      body.rows = 6;
      body.value = "{}";
      form.appendChild(body);
    }

    var run = document.createElement("button");
    run.type = "button";
    run.className = "run";
    run.textContent = row.try_safe ? "Push and try" : "Send " + row.method;
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
    $("q").addEventListener("input", renderList);
    fetch(APP_BASE + "/api/lab/catalog").then(function (res) { return res.json(); }).then(function (data) {
      state.catalog = data;
      renderCategories();
      renderList();
    }).catch(function (err) {
      $("list").textContent = "Could not load catalog: " + err;
    });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();
