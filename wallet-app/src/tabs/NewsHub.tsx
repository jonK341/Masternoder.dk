import { useEffect, useState } from 'preact/hooks';
import { fetchPlatformNews, type NewsItem } from '../api/client';

export function NewsHub() {
  const [items, setItems] = useState<NewsItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchPlatformNews(12)
      .then((data) => {
        if (!cancelled) {
          setItems(data.news || []);
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
          <div style={{ fontWeight: 700, fontSize: '1.1rem' }}>Platform News</div>
          <p style={{ margin: '8px 0 0', color: 'var(--wallet-muted)', fontSize: '0.9rem' }}>
            MasterNoder announcements, casino drops, and wallet updates.
          </p>
          <a href="/news" class="wallet-discord-btn wallet-discord-btn-primary" style={{ marginTop: '12px', display: 'inline-flex' }}>
            Full news board →
          </a>
        </div>
      </section>

      <section class="wallet-panel" style={{ marginTop: '12px' }}>
        <div class="wallet-panel-header">
          <div class="wallet-panel-title">Recent headlines</div>
        </div>
        {loading ? (
          <div style={{ padding: '16px' }}>
            <div class="wallet-skeleton" style={{ height: '80px' }} />
          </div>
        ) : error ? (
          <div class="wallet-error wallet-error--inline" role="alert">{error}</div>
        ) : items.length === 0 ? (
          <div style={{ padding: '16px', color: 'var(--wallet-muted)' }}>No news items yet.</div>
        ) : (
          <ul class="wallet-news-list" style={{ listStyle: 'none', margin: 0, padding: '8px 16px 16px' }}>
            {items.map((item) => (
              <li key={item.id} style={{ borderBottom: '1px solid var(--wallet-border)', padding: '12px 0' }}>
                <a href={item.href || '/news'} style={{ color: 'var(--wallet-text)', textDecoration: 'none', fontWeight: 600 }}>
                  {item.title}
                </a>
                {item.summary && (
                  <p style={{ margin: '6px 0 0', fontSize: '0.85rem', color: 'var(--wallet-muted)' }}>{item.summary}</p>
                )}
                <div style={{ marginTop: '4px', fontSize: '0.75rem', color: 'var(--wallet-muted)' }}>
                  {item.date}{item.category ? ` · ${item.category}` : ''}
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
