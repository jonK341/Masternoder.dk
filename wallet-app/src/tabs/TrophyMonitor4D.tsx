import { useEffect, useState } from 'preact/hooks';
import { fetchTrophyMonitor4d, type TrophyMonitor4dResponse } from '../api/client';

export function TrophyMonitor4D() {
  const [data, setData] = useState<TrophyMonitor4dResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [soundOn, setSoundOn] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetchTrophyMonitor4d()
      .then((res) => {
        if (!cancelled) {
          setData(res);
          setLoading(false);
        }
      })
      .catch((err: Error) => {
        if (!cancelled) {
          setError(err.message || 'Failed to load 4D monitor');
          setLoading(false);
        }
      });
    return () => { cancelled = true; };
  }, []);

  const network = data?.network;
  const trophies = data?.trophies ?? [];
  const teaser = data?.block_teaser;

  return (
    <div class="wallet-tab-panel wallet-monitor-4d">
      <section class="wallet-panel wallet-monitor-4d-hero">
        <div class="wallet-panel-header">
          <div>
            <div class="wallet-panel-title">4D Trophy Monitor</div>
            <div class="wallet-panel-subtitle">Network holodeck + your trophy GIFs</div>
          </div>
          <button
            type="button"
            class="wallet-trophy-chip"
            onClick={() => setSoundOn((v) => !v)}
            aria-pressed={soundOn}
          >
            {soundOn ? 'Sound on' : 'Sound off'}
          </button>
        </div>
        <div class="wallet-monitor-4d-network" aria-label="Network strip">
          <div class="wallet-monitor-4d-stat">
            <span>Block height</span>
            <strong>{network?.block_height ?? '—'}</strong>
          </div>
          <div class="wallet-monitor-4d-stat">
            <span>Peers</span>
            <strong>{network?.connections ?? '—'}</strong>
          </div>
          <div class="wallet-monitor-4d-stat">
            <span>MN2 USD</span>
            <strong>{network?.mn2_usd_price != null ? `$${Number(network.mn2_usd_price).toFixed(4)}` : '—'}</strong>
          </div>
          <div class="wallet-monitor-4d-stat">
            <span>Mempool</span>
            <strong>{network?.mempool_tx ?? '—'}</strong>
          </div>
        </div>
        {teaser && (
          <div class="wallet-monitor-4d-teaser">
            <div class="wallet-panel-subtitle">Latest block drop</div>
            <strong>{teaser.name || teaser.item_id}</strong>
            {teaser.explorer_url && (
              <a href={teaser.explorer_url} class="wallet-link">Explorer →</a>
            )}
          </div>
        )}
      </section>

      {loading && (
        <section class="wallet-panel">
          <div class="wallet-skeleton" style={{ height: '160px' }} />
        </section>
      )}

      {error && (
        <section class="wallet-panel wallet-trophies-error" role="alert">{error}</section>
      )}

      {!loading && !error && data?.guest && (
        <section class="wallet-panel wallet-trophies-empty">
          <p>Sign in to animate your trophy holodeck.</p>
          <a href="/profile" class="wallet-discord-btn wallet-discord-btn-primary">Create account →</a>
        </section>
      )}

      {!loading && !error && !data?.guest && trophies.length === 0 && (
        <section class="wallet-panel wallet-trophies-empty">
          <p>No trophies yet — collect from the shop floor.</p>
          <a href="/shop?tab=trophies" class="wallet-discord-btn wallet-discord-btn-primary">Browse trophies →</a>
        </section>
      )}

      {!loading && !error && trophies.length > 0 && (
        <section class="wallet-panel wallet-monitor-4d-stage" aria-label="Trophy holodeck">
          <div class="wallet-monitor-4d-grid">
            {trophies.map((t) => (
              <article key={t.edition_key || `${t.item_id}-${t.edition_no}`} class="wallet-monitor-4d-card">
                {t.gif_url ? (
                  <img src={t.gif_url} alt="" class="wallet-monitor-4d-gif" loading="lazy" />
                ) : t.image_url ? (
                  <img src={t.image_url} alt="" class="wallet-monitor-4d-gif" loading="lazy" />
                ) : (
                  <span class="wallet-trophy-gallery-icon" aria-hidden="true">🏆</span>
                )}
                <div class="wallet-monitor-4d-card-body">
                  <div class="wallet-trophy-gallery-name">{t.item_name || t.item_id}</div>
                  <div class="wallet-trophy-gallery-meta">#{t.edition_no}</div>
                </div>
                {soundOn && t.sound_url && (
                  <audio src={t.sound_url} preload="none" />
                )}
              </article>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
