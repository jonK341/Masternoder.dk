import { useEffect, useState } from 'preact/hooks';
import { fetchSiteFeatures, type SiteFeature } from '../api/client';

type Props = {
  emphasizePrimary?: boolean;
  onOpenShop?: () => void;
  onOpenExchange?: () => void;
};

const CATEGORY_LABELS: Record<string, string> = {
  portal: 'Portal',
  rewards: 'Rewards',
  commerce: 'Commerce',
  wallet: 'Wallet',
  network: 'Network',
  play: 'Play',
  collect: 'Collect',
  create: 'Create',
  agents: 'Agents',
  social: 'Social',
  account: 'Account',
  library: 'Library',
  admin: 'Admin',
  tools: 'Tools',
};

export function SiteFeaturesHub({ emphasizePrimary = true, onOpenShop, onOpenExchange }: Props) {
  const [features, setFeatures] = useState<SiteFeature[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchSiteFeatures()
      .then((data) => {
        if (!cancelled) {
          setFeatures(data.features || []);
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

  const primary = emphasizePrimary ? features.filter((f) => f.primary) : [];
  const rest = emphasizePrimary ? features.filter((f) => !f.primary) : features;

  const handleClick = (feature: SiteFeature, e: Event) => {
    if (feature.id === 'shop' && onOpenShop) {
      e.preventDefault();
      onOpenShop();
      return;
    }
    if (feature.id === 'exchange' && onOpenExchange) {
      e.preventDefault();
      onOpenExchange();
      return;
    }
  };

  const renderCard = (feature: SiteFeature) => (
    <a
      key={feature.id}
      href={feature.path}
      class={`wallet-feature-card${feature.primary ? ' wallet-feature-card--primary' : ''}`}
      title={feature.description}
      onClick={(e) => handleClick(feature, e)}
    >
      <span class="wallet-feature-icon" aria-hidden="true">{feature.icon}</span>
      <span class={`wallet-feature-name${feature.primary ? ' wallet-feature-name--bold' : ''}`}>
        {feature.name}
      </span>
      <span class="wallet-feature-desc">{feature.description}</span>
    </a>
  );

  if (loading) {
    return (
      <div class="wallet-features-grid wallet-features-grid--loading" aria-busy="true">
        {Array.from({ length: 8 }).map((_, i) => (
          <div class="wallet-feature-card wallet-feature-card--skeleton" key={i}>
            <div class="wallet-skeleton" style={{ height: '72px' }} />
          </div>
        ))}
      </div>
    );
  }

  if (error) {
    return <div class="wallet-error wallet-error--inline" role="alert">{error}</div>;
  }

  const grouped = rest.reduce<Record<string, SiteFeature[]>>((acc, f) => {
    const cat = f.category || 'other';
    if (!acc[cat]) acc[cat] = [];
    acc[cat].push(f);
    return acc;
  }, {});

  return (
    <div class="wallet-site-features-hub">
      {primary.length > 0 && (
        <section class="wallet-features-primary" aria-label="Primary site features">
          <h3 class="wallet-features-section-title">Portal &amp; Rewards</h3>
          <div class="wallet-features-grid wallet-features-grid--primary">
            {primary.map(renderCard)}
          </div>
        </section>
      )}
      {Object.keys(grouped).sort().map((cat) => (
        <section key={cat} class="wallet-features-category" aria-label={CATEGORY_LABELS[cat] || cat}>
          <h3 class="wallet-features-section-title">{CATEGORY_LABELS[cat] || cat}</h3>
          <div class="wallet-features-grid">
            {grouped[cat].map(renderCard)}
          </div>
        </section>
      ))}
    </div>
  );
}
