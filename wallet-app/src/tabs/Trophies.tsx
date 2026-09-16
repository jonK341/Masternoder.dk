import { useEffect, useState } from 'preact/hooks';
import {
  fetchWalletTrophies,
  type TrophyEdition,
  type WalletTrophiesResponse,
} from '../api/client';

type SeriesFilter = '' | 'top25' | 'block-mint';

const SERIES_CHIPS: { id: SeriesFilter; label: string }[] = [
  { id: '', label: 'All' },
  { id: 'top25', label: 'Top 25' },
  { id: 'block-mint', label: 'Block' },
];

export function Trophies() {
  const [series, setSeries] = useState<SeriesFilter>('');
  const [data, setData] = useState<WalletTrophiesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetchWalletTrophies(series || undefined)
      .then((res) => {
        if (!cancelled) {
          setData(res);
          setLoading(false);
        }
      })
      .catch((err: Error) => {
        if (!cancelled) {
          setError(err.message || 'Failed to load trophies');
          setLoading(false);
        }
      });
    return () => { cancelled = true; };
  }, [series]);

  const counts = data?.counts;
  const editions = data?.editions ?? [];

  return (
    <div class="wallet-tab-panel wallet-trophies-tab">
      <section class="wallet-panel wallet-trophies-hero">
        <div class="wallet-panel-header">
          <div>
            <div class="wallet-panel-title">Trophy collection</div>
            <div class="wallet-panel-subtitle">
              Platform-ledger editions — not on-chain NFTs
            </div>
          </div>
          {counts && counts.total_editions > 0 && (
            <span class="wallet-badge">🏆 {counts.total_editions}</span>
          )}
        </div>
        <p class="wallet-trophies-disclaimer">
          MN2 cannot mint trophies on-chain today. These are licensed digital collectibles
          stored in your shop inventory with edition numbers.
        </p>
        {counts && counts.top25_total > 0 && (
          <div class="wallet-trophies-progress">
            Top 25: <strong>{counts.top25_owned}</strong> / {counts.top25_total} editions
          </div>
        )}
        <div class="wallet-trophy-chips" role="group" aria-label="Trophy series filter">
          {SERIES_CHIPS.map((chip) => (
            <button
              key={chip.id || 'all'}
              type="button"
              class={`wallet-trophy-chip${series === chip.id ? ' wallet-trophy-chip--active' : ''}`}
              onClick={() => setSeries(chip.id)}
            >
              {chip.label}
            </button>
          ))}
        </div>
      </section>

      {loading && (
        <section class="wallet-panel">
          <div class="wallet-skeleton" style={{ height: '120px' }} />
        </section>
      )}

      {error && (
        <section class="wallet-panel wallet-trophies-error" role="alert">
          {error}
        </section>
      )}

      {!loading && !error && data?.guest && (
        <section class="wallet-panel wallet-trophies-empty">
          <p>{data.message || 'Sign in to view your trophy collection.'}</p>
          <a href="/profile" class="wallet-discord-btn wallet-discord-btn-primary">Create account →</a>
        </section>
      )}

      {!loading && !error && !data?.guest && editions.length === 0 && (
        <section class="wallet-panel wallet-trophies-empty">
          <p>No trophies in this series yet.</p>
          <a href="/shop?tab=trophies" class="wallet-discord-btn wallet-discord-btn-primary">
            Browse shop trophies →
          </a>
        </section>
      )}

      {!loading && !error && editions.length > 0 && (
        <section class="wallet-panel" aria-label="Owned trophy editions">
          <div class="wallet-trophy-gallery" role="list">
            {editions.map((ed) => (
              <TrophyEditionCard key={ed.edition_key} edition={ed} />
            ))}
          </div>
        </section>
      )}

      {!loading && !error && data?.catalog_preview && data.catalog_preview.length > 0 && (
        <section class="wallet-panel">
          <div class="wallet-panel-header">
            <div class="wallet-panel-title">Collect more</div>
            <div class="wallet-panel-subtitle">Available in the shop</div>
          </div>
          <div class="wallet-trophy-gallery wallet-trophy-gallery--compact" role="list">
            {data.catalog_preview.map((item) => (
              <a
                key={item.id}
                href={item.shop_url || '/shop?tab=trophies'}
                class="wallet-trophy-gallery-card wallet-trophy-gallery-card--shop"
                role="listitem"
              >
                {item.image_url ? (
                  <img src={item.image_url} alt="" class="wallet-trophy-gallery-img" loading="lazy" />
                ) : (
                  <span class="wallet-trophy-gallery-icon" aria-hidden="true">🏆</span>
                )}
                <span class="wallet-trophy-gallery-name">{item.name || item.id}</span>
                {item.effective_price_usd != null && (
                  <span class="wallet-trophy-gallery-price">
                    ${Number(item.effective_price_usd).toFixed(2)}
                  </span>
                )}
              </a>
            ))}
          </div>
        </section>
      )}

      <section class="wallet-panel wallet-trophies-actions">
        <a href="/shop?tab=trophies" class="wallet-link">Shop trophies</a>
        <span class="wallet-trophies-actions-sep">·</span>
        <a href="/shop?tab=auction" class="wallet-link">Auction house</a>
      </section>
    </div>
  );
}

function TrophyEditionCard({ edition }: { edition: TrophyEdition }) {
  const title = edition.item_name || edition.item_id;
  return (
    <article class="wallet-trophy-gallery-card" role="listitem">
      {edition.image_url ? (
        <img src={edition.image_url} alt="" class="wallet-trophy-gallery-img" loading="lazy" />
      ) : (
        <div class="wallet-trophy-gallery-icon-wrap">
          <span class="wallet-trophy-gallery-icon" aria-hidden="true">🏆</span>
        </div>
      )}
      <div class="wallet-trophy-gallery-body">
        <div class="wallet-trophy-gallery-name">{title}</div>
        <div class="wallet-trophy-gallery-meta">
          Edition #{edition.edition_no}
          {edition.serial_key ? ` · ${edition.serial_key}` : ''}
        </div>
        {edition.legacy_stack ? (
          <div class="wallet-trophy-gallery-tag">Legacy stack</div>
        ) : edition.acquired_via ? (
          <div class="wallet-trophy-gallery-tag">via {edition.acquired_via}</div>
        ) : null}
        {edition.hold_until ? (
          <div class="wallet-trophy-gallery-meta">Hold until {edition.hold_until.slice(0, 10)}</div>
        ) : null}
        <div class="wallet-trophy-gallery-ctas">
          <a
            href={edition.trade_actions?.shop_detail || '/shop?tab=trophies'}
            class="wallet-trophy-cta"
          >
            View
          </a>
          <a
            href={edition.trade_actions?.auction_list || '/shop?tab=auction'}
            class="wallet-trophy-cta"
          >
            List
          </a>
        </div>
      </div>
    </article>
  );
}
