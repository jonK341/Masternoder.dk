import type { TrophyCounts } from '../api/client';

type Props = {
  trophyCounts?: TrophyCounts;
  loading?: boolean;
};

/** Placeholder trophy carousel — full holodeck ships in WR-G1 / plan 001. */
export function TrophySlot({ trophyCounts, loading }: Props) {
  const total = trophyCounts?.total ?? 0;
  const top25 = trophyCounts?.top25_owned ?? 0;
  const slots = Math.min(5, Math.max(1, total || 3));

  return (
    <section class="wallet-panel wallet-trophy-slot" aria-label="Trophy showcase">
      <div class="wallet-panel-header">
        <div>
          <div class="wallet-panel-title">Trophy carousel</div>
          <div class="wallet-panel-subtitle">Edition showcase — GIF holodeck in 4D Monitor tab</div>
        </div>
        {total > 0 && (
          <span class="wallet-badge" title="Owned trophy editions">🏆 {total}</span>
        )}
      </div>
      <div class="wallet-trophy-carousel" role="list">
        {loading ? (
          Array.from({ length: 3 }).map((_, i) => (
            <div class="wallet-trophy-card wallet-trophy-card--skeleton" key={i} role="listitem">
              <div class="wallet-skeleton" style={{ height: '72px' }} />
            </div>
          ))
        ) : total > 0 ? (
          Array.from({ length: slots }).map((_, i) => (
            <div class="wallet-trophy-card" key={i} role="listitem" title={`Edition slot ${i + 1}`}>
              <div class="wallet-trophy-card-inner">
                <span class="wallet-trophy-icon">🏆</span>
                <span class="wallet-trophy-edition">#{i + 1}</span>
              </div>
            </div>
          ))
        ) : (
          <div class="wallet-trophy-empty">
            <p>No trophies yet — browse the shop Top 25 series.</p>
            <a href="/shop?tab=trophies" class="wallet-link">Shop trophies →</a>
          </div>
        )}
      </div>
      {top25 > 0 && (
        <div class="wallet-trophy-footer">
          Top 25 progress: <strong>{top25}</strong> edition{top25 === 1 ? '' : 's'} owned
        </div>
      )}
    </section>
  );
}
