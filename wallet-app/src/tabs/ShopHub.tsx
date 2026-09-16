import type { TrophyCounts } from '../api/client';

type Props = {
  trophyCounts?: TrophyCounts;
};

const SHOP_CATEGORIES = [
  {
    id: 'trophies',
    name: 'Trophies',
    icon: '🏆',
    description: 'Top 25 editions, block drops, and collector trophies',
    href: '/shop?tab=trophies',
    highlight: true,
  },
  {
    id: 'boosts',
    name: 'Boosts',
    icon: '⚡',
    description: 'XP multipliers, staking boosts, and power-ups',
    href: '/shop?tab=boosts',
  },
  {
    id: 'digital',
    name: 'Digital goods',
    icon: '📦',
    description: 'Themes, media packs, and platform perks',
    href: '/shop',
  },
  {
    id: 'paypal',
    name: 'PayPal on-ramp',
    icon: '💳',
    description: 'Buy MN2 with PayPal — held balance shown in wallet',
    href: '/shop?tab=paypal',
  },
];

export function ShopHub({ trophyCounts }: Props) {
  const owned = trophyCounts?.top25_owned ?? 0;

  return (
    <div class="wallet-tab-panel">
      <section class="wallet-panel wallet-shop-hero">
        <div style={{ padding: '16px' }}>
          <div style={{ fontWeight: 700, fontSize: '1.1rem' }}>MN2 Shop</div>
          <p style={{ margin: '8px 0 0', color: 'var(--wallet-muted)', fontSize: '0.9rem' }}>
            Trophies, boosts, and digital goods — wallet balance debits on purchase.
            {owned > 0 ? ` You own ${owned} Top 25 edition${owned === 1 ? '' : 's'}.` : ''}
          </p>
          <a href="/shop" class="wallet-discord-btn wallet-discord-btn-primary" style={{ marginTop: '12px', display: 'inline-flex' }}>
            Open full shop →
          </a>
        </div>
      </section>

      <div class="wallet-shop-grid">
        {SHOP_CATEGORIES.map((cat) => (
          <a
            key={cat.id}
            href={cat.href}
            class={`wallet-shop-card${cat.highlight ? ' wallet-shop-card--highlight' : ''}`}
          >
            <span class="wallet-shop-card-icon" aria-hidden="true">{cat.icon}</span>
            <span class="wallet-shop-card-name">{cat.name}</span>
            <span class="wallet-shop-card-desc">{cat.description}</span>
          </a>
        ))}
      </div>

      <section class="wallet-panel" style={{ marginTop: '12px' }}>
        <div style={{ padding: '14px 16px', fontSize: '0.85rem', color: 'var(--wallet-muted)' }}>
          Trophy transfers and auctions ship in plan 001 — use the full shop for listings and PayPal checkout.
        </div>
      </section>
    </div>
  );
}
