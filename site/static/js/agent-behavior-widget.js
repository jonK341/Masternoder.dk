/**
 * Agent Behavior Widget (Real Players)
 * Renders agent behavior types + active-now + simulate-session actions.
 */

(function () {
  const API_BASE = "/api/agents/behavior";

  function escapeHtml(str) {
    return String(str ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function agentIds(count = 20) {
    return Array.from({ length: count }, (_, i) =>
      `agent_${String(i + 1).padStart(3, "0")}`
    );
  }

  async function fetchJson(url, opts) {
    const res = await fetch(url, opts);
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    return await res.json();
  }

  async function getBehaviorType(agentId) {
    return fetchJson(`${API_BASE}/get-behavior-type?agent_id=${encodeURIComponent(agentId)}`);
  }

  async function shouldBeActive(agentId) {
    return fetchJson(`${API_BASE}/should-be-active?agent_id=${encodeURIComponent(agentId)}`);
  }

  /** Batch fetch: 1 request instead of 2*count. Falls back to individual if batch fails. */
  async function fetchBatch(ids) {
    const url = `${API_BASE}/batch?agent_ids=${ids.map((id) => encodeURIComponent(id)).join(",")}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    const data = await res.json();
    if (!data.success || !Array.isArray(data.agents)) throw new Error("Invalid batch response");
    return data.agents;
  }

  async function simulateSession(agentId, execute) {
    return fetchJson(`${API_BASE}/simulate-session`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ agent_id: agentId, execute: !!execute }),
    });
  }

  function badge(text, kind) {
    const styles = {
      ok: "background: rgba(0,255,136,0.18); border: 1px solid rgba(0,255,136,0.35); color: var(--primary);",
      warn: "background: rgba(255,212,0,0.12); border: 1px solid rgba(255,212,0,0.25); color: #ffd400;",
      off: "background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.12); color: var(--text-secondary);",
      info: "background: rgba(0,212,255,0.12); border: 1px solid rgba(0,212,255,0.22); color: var(--secondary);",
    }[kind] || styles.off;

    return `<span style="display:inline-flex;align-items:center;gap:6px;padding:6px 10px;border-radius:999px;font-weight:700;font-size:12px;${styles}">${escapeHtml(text)}</span>`;
  }

  function renderSkeleton(containerId) {
    const el = document.getElementById(containerId);
    if (!el) return;
    el.innerHTML = `
      <div class="loading">Loading agent behavior...</div>
    `;
  }

  function renderTable(containerId, rows) {
    const el = document.getElementById(containerId);
    if (!el) return;

    el.innerHTML = `
      <div style="display:flex;flex-direction:column;gap:12px;">
        <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;">
          <div style="display:flex;align-items:center;gap:10px;">
            ${badge("Real-player behavior", "info")}
            ${badge(`${rows.length} agents`, "off")}
          </div>
          <label style="display:flex;align-items:center;gap:10px;color:var(--text-secondary);font-size:13px;">
            <input id="${containerId}-persist" type="checkbox" style="transform:scale(1.1);" />
            Persist sessions to DB (execute=true)
          </label>
        </div>

        <div style="overflow:auto;border:1px solid rgba(255,255,255,0.10);border-radius:14px;">
          <table style="width:100%;border-collapse:collapse;min-width:720px;">
            <thead>
              <tr style="text-align:left;background:rgba(255,255,255,0.04);">
                <th style="padding:12px 14px;color:var(--text-secondary);font-size:12px;text-transform:uppercase;letter-spacing:1.5px;">Agent</th>
                <th style="padding:12px 14px;color:var(--text-secondary);font-size:12px;text-transform:uppercase;letter-spacing:1.5px;">Type</th>
                <th style="padding:12px 14px;color:var(--text-secondary);font-size:12px;text-transform:uppercase;letter-spacing:1.5px;">Active now</th>
                <th style="padding:12px 14px;color:var(--text-secondary);font-size:12px;text-transform:uppercase;letter-spacing:1.5px;">Actions</th>
              </tr>
            </thead>
            <tbody>
              ${rows
                .map(
                  (r) => `
                  <tr style="border-top:1px solid rgba(255,255,255,0.06);">
                    <td style="padding:12px 14px;font-weight:800;color:var(--text-primary);">${escapeHtml(r.agentId)}</td>
                    <td style="padding:12px 14px;">${badge(r.behaviorType || "unknown", "info")}</td>
                    <td style="padding:12px 14px;">${
                      r.shouldBeActive
                        ? badge("ACTIVE", "ok")
                        : badge("inactive", "off")
                    }</td>
                    <td style="padding:12px 14px;">
                      <button data-agent="${escapeHtml(r.agentId)}" class="btn-primary" style="padding:8px 12px;border-radius:10px;font-size:13px;" onclick="window.agentBehaviorWidget.simulate('${escapeHtml(r.agentId)}','${containerId}')">
                        Simulate session
                      </button>
                      <span id="${containerId}-result-${escapeHtml(r.agentId)}" style="margin-left:10px;color:var(--text-secondary);font-size:13px;"></span>
                    </td>
                  </tr>
                `
                )
                .join("")}
            </tbody>
          </table>
        </div>
        <div style="color:var(--text-secondary);font-size:12px;">
          Tip: keep persist OFF unless you want sessions written into DB tables (xp_history/player_levels/daily_activities).
        </div>
      </div>
    `;
  }

  async function load(containerId, count = 20) {
    renderSkeleton(containerId);
    const ids = agentIds(count);

    let rows;
    try {
      const batch = await fetchBatch(ids);
      const byId = Object.fromEntries(batch.map((a) => [a.agent_id, a]));
      rows = ids.map((id) => {
        const a = byId[id];
        if (!a) return { agentId: id, behaviorType: "error", shouldBeActive: false };
        return {
          agentId: id,
          behaviorType: a.behavior_type || "unknown",
          shouldBeActive: !!a.should_be_active,
        };
      });
    } catch (e) {
      rows = await Promise.all(
        ids.map(async (id) => {
          try {
            const [t, a] = await Promise.all([getBehaviorType(id), shouldBeActive(id)]);
            return {
              agentId: id,
              behaviorType: t.behavior_type || t.behaviorType || "unknown",
              shouldBeActive: !!a.should_be_active,
            };
          } catch (err) {
            return { agentId: id, behaviorType: "error", shouldBeActive: false, error: String(err) };
          }
        })
      );
    }

    renderTable(containerId, rows);
  }

  async function simulate(agentId, containerId) {
    const persistEl = document.getElementById(`${containerId}-persist`);
    const persist = !!persistEl?.checked;
    const out = document.getElementById(`${containerId}-result-${agentId}`);
    if (out) out.textContent = "Running...";

    try {
      const res = await simulateSession(agentId, persist);
      const plan = res.session_plan || {};
      const xp = plan.total_xp ?? 0;
      const actions = Array.isArray(plan.actions) ? plan.actions.length : 0;
      if (out) out.textContent = `OK: ${actions} actions, ${xp} XP${persist ? " (persisted)" : ""}`;
    } catch (e) {
      if (out) out.textContent = `Error: ${String(e)}`;
    }
  }

  window.agentBehaviorWidget = {
    load,
    simulate,
  };
})();

