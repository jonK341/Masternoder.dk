import { useCallback, useEffect, useState } from 'preact/hooks';
import {
  fetchEarnStatus,
  postEarnClick,
  type EarnEvent,
  type EarnGameLink,
  type EarnStatus,
} from '../api/client';

function formatCooldown(sec: number): string {
  if (sec <= 0) return '';
  if (sec < 60) return `${sec}s`;
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return s > 0 ? `${m}m ${s}s` : `${m}m`;
}

export function Earn() {
  const [status, setStatus] = useState<EarnStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [clicking, setClicking] = useState<string | null>(null);
  const [flash, setFlash] = useState<string | null>(null);

  const refresh = useCallback(() => {
    setLoading(true);
    setError(null);
    fetchEarnStatus()
      .then((data) => {
        setStatus(data);
        setLoading(false);
      })
      .catch((err: Error) => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  useEffect(() => {
    if (!status?.events?.some((e) => (e.cooldown_remaining_sec ?? 0) > 0)) return undefined;
    const t = window.setInterval(() => refresh(), 5000);
    return () => window.clearInterval(t);
  }, [status, refresh]);

  const handleClick = async (event: EarnEvent) => {
    if (!event.available || clicking) return;
    setClicking(event.event_id);
    setFlash(null);
    try {
      const result = await postEarnClick(event.event_id);
      if (result.success && (result.mn2_awarded ?? 0) > 0) {
        setFlash(`+${result.mn2_awarded!.toFixed(6)} MN2`);
      } else if (result.error) {
        setFlash(result.error.replace(/_/g, ' '));
      }
      refresh();
    } catch (err: unknown) {
      setFlash(err instanceof Error ? err.message : 'Click failed');
    } finally {
      setClicking(null);
      window.setTimeout(() => setFlash(null), 3000);
    }
  };

  const gameLinks = status?.game_links ?? [];

  return (
    <div class="wallet-tab-panel wallet-earn-tab">
      <section class="wallet-panel wallet-earn-hero">
        <div style={{ padding: '16px' }}>
          <div class="wallet-earn-title">Micro-Earn</div>
          <p style={{ margin: '8px 0 12px', color: 'var(--wallet-muted)', fontSize: '0.9rem' }}>
            Small engagement bonuses — not investment returns. Daily caps apply.
          </p>
          {status?.engagement_disclaimer && (
            <p class="wallet-muted-note" style={{ padding: 0, marginBottom: '12px' }}>
              {status.engagement_disclaimer}
            </p>
          )}
          {loading ? (
            <div class="wallet-skeleton" style={{ height: '48px' }} />
          ) : status?.guest ? (
            <div class="wallet-muted-note" style={{ padding: 0 }}>
              {status.message || 'Sign in to earn micro MN2.'}
            </div>
          ) : (
            <div class="wallet-kpi-grid">
              <div class="wallet-kpi">
                <div class="wallet-kpi-label">Earned today</div>
                <div class="wallet-kpi-value">
                  {(status?.earned_today_mn2 ?? 0).toFixed(6)} MN2
                </div>
              </div>
              <div class="wallet-kpi">
                <div class="wallet-kpi-label">Remaining</div>
                <div class="wallet-kpi-value">
                  {(status?.remaining_today_mn2 ?? 0).toFixed(6)} MN2
                </div>
              </div>
              <div class="wallet-kpi">
                <div class="wallet-kpi-label">Daily cap</div>
                <div class="wallet-kpi-value">
                  {(status?.global_daily_cap_mn2 ?? 0).toFixed(4)} MN2
                </div>
              </div>
            </div>
          )}
          {flash && (
            <div class="wallet-earn-flash" role="status">{flash}</div>
          )}
        </div>
      </section>

      {error && <div class="wallet-error wallet-error--inline" role="alert">{error}</div>}

      <section class="wallet-panel" style={{ marginTop: '12px' }}>
        <div class="wallet-panel-header">
          <div>
            <div class="wallet-panel-title">Click events</div>
            <div class="wallet-panel-subtitle">Network pulse, daily open, game taps</div>
          </div>
        </div>
        {loading ? (
          <div style={{ padding: '16px' }}>
            <div class="wallet-skeleton" style={{ height: '160px' }} />
          </div>
        ) : (
          <ul class="wallet-earn-event-list">
            {(status?.events ?? []).map((ev) => (
              <li key={ev.event_id} class="wallet-earn-event">
                <div class="wallet-earn-event-body">
                  <div class="wallet-earn-event-name">
                    {ev.name}
                    {ev.unit_id && (
                      <span class="wallet-badge" style={{ marginLeft: '8px' }}>{ev.unit_id}</span>
                    )}
                  </div>
                  <div class="wallet-earn-event-desc">{ev.description}</div>
                  <div class="wallet-earn-event-meta">
                    <span>Next: {(ev.next_amount_mn2 ?? 0).toFixed(6)} MN2</span>
                    <span>{ev.clicks_today}/{ev.max_clicks_per_day} clicks</span>
                    {(ev.cooldown_remaining_sec ?? 0) > 0 && (
                      <span>Cooldown: {formatCooldown(ev.cooldown_remaining_sec!)}</span>
                    )}
                  </div>
                </div>
                <button
                  type="button"
                  class="wallet-discord-btn wallet-earn-pulse-btn"
                  disabled={!ev.available || Boolean(status?.guest) || clicking === ev.event_id}
                  onClick={() => handleClick(ev)}
                  aria-label={`Earn from ${ev.name}`}
                >
                  {ev.event_id === 'network_pulse_click' ? 'Pulse' : 'Tap'}
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section class="wallet-panel" style={{ marginTop: '12px' }}>
        <div class="wallet-panel-header">
          <div>
            <div class="wallet-panel-title">Games &amp; click-through</div>
            <div class="wallet-panel-subtitle">Deep links to site earn surfaces</div>
          </div>
        </div>
        <div class="wallet-earn-games-grid">
          {gameLinks.map((link: EarnGameLink) => (
            <a key={link.id} href={link.path} class="wallet-earn-game-card">
              <span class="wallet-earn-game-icon" aria-hidden="true">{link.icon}</span>
              <span class="wallet-earn-game-name">{link.name}</span>
              <span class="wallet-earn-game-desc">{link.description}</span>
            </a>
          ))}
        </div>
      </section>
    </div>
  );
}
