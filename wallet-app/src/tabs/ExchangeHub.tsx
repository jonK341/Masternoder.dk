import { useEffect, useState } from 'preact/hooks';
import { fetchExchangeWallet, type ExchangeWallet } from '../api/client';

export function ExchangeHub() {
  const [wallet, setWallet] = useState<ExchangeWallet | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchExchangeWallet()
      .then((data) => {
        if (!cancelled) {
          setWallet(data);
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

  const balances = wallet?.balances || wallet?.holdings || [];
  const mn2Entry = balances.find((b) => (b.symbol || b.asset || '').toUpperCase() === 'MN2');

  return (
    <div class="wallet-tab-panel">
      <section class="wallet-panel wallet-exchange-hero">
        <div style={{ padding: '16px' }}>
          <div style={{ fontWeight: 700, fontSize: '1.1rem' }}>25-Crypto Exchange</div>
          <p style={{ margin: '8px 0 0', color: 'var(--wallet-muted)', fontSize: '0.9rem' }}>
            Swap, limit orders, staking claims, and tax records — linked to your MN2 wallet.
          </p>
          <a href="/exchange" class="wallet-discord-btn wallet-discord-btn-primary" style={{ marginTop: '12px', display: 'inline-flex' }}>
            Open exchange →
          </a>
        </div>
      </section>

      <section class="wallet-panel" style={{ marginTop: '12px' }}>
        <div class="wallet-panel-header">
          <div>
            <div class="wallet-panel-title">Exchange wallet</div>
            <div class="wallet-panel-subtitle">Treasury balances on the exchange hub</div>
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
              <div class="wallet-kpi-label">MN2 balance</div>
              <div class="wallet-kpi-value">
                {mn2Entry?.balance != null
                  ? Number(mn2Entry.balance).toFixed(8)
                  : wallet?.mn2_balance != null
                    ? Number(wallet.mn2_balance).toFixed(8)
                    : '—'}
              </div>
            </div>
            <div class="wallet-kpi">
              <div class="wallet-kpi-label">Assets</div>
              <div class="wallet-kpi-value">{balances.length || wallet?.asset_count || '—'}</div>
            </div>
            <div class="wallet-kpi">
              <div class="wallet-kpi-label">Open orders</div>
              <div class="wallet-kpi-value">{wallet?.open_orders ?? '—'}</div>
            </div>
          </div>
        )}
      </section>

      <div class="wallet-exchange-links">
        <a href="/exchange?tab=swap" class="wallet-shop-card">
          <span class="wallet-shop-card-icon">🔄</span>
          <span class="wallet-shop-card-name">Swap</span>
          <span class="wallet-shop-card-desc">Instant crypto ↔ MN2 swaps</span>
        </a>
        <a href="/exchange?tab=staking" class="wallet-shop-card">
          <span class="wallet-shop-card-icon">🌱</span>
          <span class="wallet-shop-card-name">Staking</span>
          <span class="wallet-shop-card-desc">Claim exchange staking rewards</span>
        </a>
        <a href="/exchange?tab=tax" class="wallet-shop-card">
          <span class="wallet-shop-card-icon">📋</span>
          <span class="wallet-shop-card-name">Tax report</span>
          <span class="wallet-shop-card-desc">Export trade history</span>
        </a>
        <a href="/shop?tab=trophies" class="wallet-shop-card wallet-shop-card--highlight">
          <span class="wallet-shop-card-icon">🏆</span>
          <span class="wallet-shop-card-name">Trophy section</span>
          <span class="wallet-shop-card-desc">Top 25 editions and block drops</span>
        </a>
      </div>
    </div>
  );
}
