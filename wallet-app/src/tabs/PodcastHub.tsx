import { useEffect, useState } from 'preact/hooks';
import { fetchPodcastEpisodes, type PodcastEpisode } from '../api/client';

function formatDuration(sec?: number): string {
  if (!sec) return '—';
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return `${m}:${String(s).padStart(2, '0')}`;
}

export function PodcastHub() {
  const [episodes, setEpisodes] = useState<PodcastEpisode[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchPodcastEpisodes(8)
      .then((data) => {
        if (!cancelled) {
          setEpisodes(data.episodes || []);
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

  return (
    <div class="wallet-tab-panel">
      <section class="wallet-panel wallet-exchange-hero">
        <div style={{ padding: '16px' }}>
          <div style={{ fontWeight: 700, fontSize: '1.1rem' }}>MasterNoder Podcast</div>
          <p style={{ margin: '8px 0 0', color: 'var(--wallet-muted)', fontSize: '0.9rem' }}>
            Latest episodes — YouTube, Discord, GitHub cross-posts with MN2 rewards.
          </p>
          <a href="/podcast" class="wallet-discord-btn wallet-discord-btn-primary" style={{ marginTop: '12px', display: 'inline-flex' }}>
            Open podcast hub →
          </a>
        </div>
      </section>

      <section class="wallet-panel" style={{ marginTop: '12px' }}>
        <div class="wallet-panel-header">
          <div class="wallet-panel-title">Latest episodes</div>
        </div>
        {loading ? (
          <div style={{ padding: '16px' }}>
            <div class="wallet-skeleton" style={{ height: '80px' }} />
          </div>
        ) : error ? (
          <div class="wallet-error wallet-error--inline" role="alert">{error}</div>
        ) : (
          <ul style={{ listStyle: 'none', margin: 0, padding: '8px 16px 16px' }}>
            {episodes.map((ep) => (
              <li key={ep.id} style={{ borderBottom: '1px solid var(--wallet-border)', padding: '12px 0' }}>
                <div style={{ fontWeight: 600 }}>{ep.title}</div>
                {ep.description && (
                  <p style={{ margin: '6px 0 0', fontSize: '0.85rem', color: 'var(--wallet-muted)' }}>
                    {ep.description.slice(0, 140)}{ep.description.length > 140 ? '…' : ''}
                  </p>
                )}
                <div style={{ marginTop: '6px', fontSize: '0.75rem', color: 'var(--wallet-muted)' }}>
                  {formatDuration(ep.duration_sec)}
                  {ep.published_at ? ` · ${ep.published_at.slice(0, 10)}` : ''}
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
