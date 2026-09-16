import { useEffect, useState } from 'preact/hooks';
import { fetchIntegrationHub, type IntegrationHub } from '../api/client';

export function EncoderHub() {
  const [hub, setHub] = useState<IntegrationHub | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchIntegrationHub()
      .then((data) => {
        if (!cancelled) {
          setHub(data);
          setLoading(false);
        }
      })
      .catch((err: Error) => {
        if (!cancelled) {
          setError(err.message);
          setLoading(false);
        }
      });
    return () => { cancelled = true; };
  }, []);

  const enc = hub?.units?.['WR-INT-ENC'];
  const jobs = enc?.recent_jobs_count ?? '—';

  return (
    <div class="wallet-tab-panel">
      <section class="wallet-panel wallet-exchange-hero">
        <div style={{ padding: '16px' }}>
          <div style={{ fontWeight: 700, fontSize: '1.1rem' }}>Video Encoder</div>
          <p style={{ margin: '8px 0 0', color: 'var(--wallet-muted)', fontSize: '0.9rem' }}>
            AI video generation, trophy GIF clips, and podcast encode pipeline.
          </p>
          <a href="/generator" class="wallet-discord-btn wallet-discord-btn-primary" style={{ marginTop: '12px', display: 'inline-flex' }}>
            Open generator →
          </a>
        </div>
      </section>

      <section class="wallet-panel" style={{ marginTop: '12px' }}>
        <div class="wallet-panel-header">
          <div>
            <div class="wallet-panel-title">Encode jobs</div>
            <div class="wallet-panel-subtitle">Recent generation history (last 30 days)</div>
          </div>
        </div>
        {loading ? (
          <div style={{ padding: '16px' }}>
            <div class="wallet-skeleton" style={{ height: '48px' }} />
          </div>
        ) : error ? (
          <div class="wallet-error wallet-error--inline" role="alert">{error}</div>
        ) : (
          <div class="wallet-kpi-grid" style={{ padding: '14px 16px' }}>
            <div class="wallet-kpi">
              <div class="wallet-kpi-label">Recent jobs</div>
              <div class="wallet-kpi-value">{jobs}</div>
            </div>
          </div>
        )}
      </section>

      <div class="wallet-exchange-links">
        <a href="/generator" class="wallet-shop-card">
          <span class="wallet-shop-card-icon">🎬</span>
          <span class="wallet-shop-card-name">New encode</span>
          <span class="wallet-shop-card-desc">Start a video generation job</span>
        </a>
        <a href="/shop?tab=trophies" class="wallet-shop-card wallet-shop-card--highlight">
          <span class="wallet-shop-card-icon">🏆</span>
          <span class="wallet-shop-card-name">Trophy GIFs</span>
          <span class="wallet-shop-card-desc">Block trophy clips and shop editions</span>
        </a>
        <a href="/podcast" class="wallet-shop-card">
          <span class="wallet-shop-card-icon">🎙️</span>
          <span class="wallet-shop-card-name">Podcast encode</span>
          <span class="wallet-shop-card-desc">AI audio pipeline from generator</span>
        </a>
      </div>
    </div>
  );
}
