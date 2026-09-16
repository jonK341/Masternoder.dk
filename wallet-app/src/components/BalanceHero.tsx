import type { WalletSummary } from '../api/client';

type Props = {
  summary: WalletSummary | null;
  loading: boolean;
  showFiat: boolean;
  onToggleFiat: () => void;
};

function formatMn2(n: number | undefined | null): string {
  const v = Number(n ?? 0);
  return v.toFixed(8);
}

export function BalanceHero({ summary, loading, showFiat, onToggleFiat }: Props) {
  const liquid = summary?.liquid_mn2 ?? summary?.mn2_balance ?? 0;
  const held = summary?.held_mn2 ?? 0;
  const price = summary?.mn2_usd_price;
  const fiat = price != null ? liquid * price : null;

  return (
    <header class="wallet-panel wallet-hero" aria-label="Wallet balance">
      <div style={{ padding: '20px 18px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '12px', flexWrap: 'wrap' }}>
          <div>
            <div class="wallet-kpi-label">Liquid MN2</div>
            {loading ? (
              <div class="wallet-skeleton" style={{ width: '180px', height: '2rem' }} />
            ) : (
              <div class="wallet-kpi-value" style={{ fontSize: '1.75rem' }}>
                {formatMn2(liquid)}
              </div>
            )}
            {showFiat && fiat != null && !loading && (
              <div style={{ color: 'var(--wallet-muted)', fontSize: '0.9rem', marginTop: '4px' }}>
                ≈ ${fiat.toFixed(2)} USD
              </div>
            )}
          </div>
          <button
            type="button"
            onClick={onToggleFiat}
            style={{
              border: 'var(--wallet-border)',
              borderRadius: 'var(--wallet-radius)',
              background: 'var(--wallet-bg-elevated)',
              color: 'var(--wallet-accent)',
              padding: '6px 10px',
              cursor: 'pointer',
              fontSize: '0.8rem',
            }}
          >
            {showFiat ? 'MN2' : 'USD'}
          </button>
        </div>
        <div style={{ display: 'flex', gap: '16px', marginTop: '12px', flexWrap: 'wrap', fontSize: '0.85rem', color: 'var(--wallet-muted)' }}>
          {loading ? (
            <div class="wallet-skeleton" style={{ width: '120px' }} />
          ) : (
            <>
              <span>Held: <span style={{ fontFamily: 'var(--wallet-font-mono)', color: 'var(--wallet-text)' }}>{formatMn2(held)}</span></span>
              {summary?.withdrawable_mn2 != null && (
                <span>Withdrawable: <span style={{ fontFamily: 'var(--wallet-font-mono)', color: 'var(--wallet-text)' }}>{formatMn2(summary.withdrawable_mn2)}</span></span>
              )}
            </>
          )}
        </div>
      </div>
    </header>
  );
}
