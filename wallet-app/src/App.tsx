import { useEffect, useState } from 'preact/hooks';
import { fetchSummary, type WalletSummary } from './api/client';
import { BalanceHero } from './components/BalanceHero';
import { TabNav, type TabId } from './components/TabNav';
import { CamgirlsHub } from './tabs/CamgirlsHub';
import { CasinoHub } from './tabs/CasinoHub';
import { Earn } from './tabs/Earn';
import { EncoderHub } from './tabs/EncoderHub';
import { ExchangeHub } from './tabs/ExchangeHub';
import { NetworkChat } from './tabs/NetworkChat';
import { NewsHub } from './tabs/NewsHub';
import { Overview } from './tabs/Overview';
import { PodcastHub } from './tabs/PodcastHub';
import { PortalHub } from './tabs/PortalHub';
import { RewardsHub } from './tabs/RewardsHub';
import { Settings } from './tabs/Settings';
import { ShopHub } from './tabs/ShopHub';
import { Upgrades } from './tabs/Upgrades';

function tabFromQuery(): TabId {
  const tab = new URLSearchParams(window.location.search).get('tab');
  const valid: TabId[] = [
    'overview', 'portal', 'rewards', 'earn', 'casino', 'shop', 'exchange',
    'encoder', 'news', 'podcast', 'network-chat', 'camgirls',
    'send', 'receive', 'activity', 'monitor-4d', 'explorer-5d',
    'trophies', 'battle', 'peers', 'staking', 'upgrades', 'settings',
  ];
  return valid.includes(tab as TabId) ? (tab as TabId) : 'overview';
}

export function App() {
  const [activeTab, setActiveTab] = useState<TabId>(tabFromQuery);
  const [summary, setSummary] = useState<WalletSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showFiat, setShowFiat] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetchSummary()
      .then((data) => {
        if (!cancelled) {
          setSummary(data);
          setLoading(false);
        }
      })
      .catch((err: Error) => {
        if (!cancelled) {
          setError(err.message || 'Failed to load wallet');
          setLoading(false);
        }
      });
    return () => { cancelled = true; };
  }, []);

  const onTabChange = (id: TabId) => {
    setActiveTab(id);
    const url = new URL(window.location.href);
    if (id === 'overview') {
      url.searchParams.delete('tab');
    } else {
      url.searchParams.set('tab', id);
    }
    window.history.replaceState({}, '', url.pathname + url.search);
  };

  const renderTab = () => {
    switch (activeTab) {
      case 'overview':
        return (
          <Overview
            summary={summary}
            loading={loading}
            error={error}
            onOpenUpgrades={() => onTabChange('upgrades')}
            onOpenPortal={() => onTabChange('portal')}
            onOpenRewards={() => onTabChange('rewards')}
            onOpenEarn={() => onTabChange('earn')}
            onOpenCasino={() => onTabChange('casino')}
            onOpenShop={() => onTabChange('shop')}
            onOpenExchange={() => onTabChange('exchange')}
          />
        );
      case 'portal':
        return (
          <PortalHub
            onOpenShop={() => onTabChange('shop')}
            onOpenExchange={() => onTabChange('exchange')}
            onOpenCasino={() => onTabChange('casino')}
          />
        );
      case 'rewards':
        return <RewardsHub />;
      case 'earn':
        return <Earn />;
      case 'casino':
        return <CasinoHub />;
      case 'shop':
        return <ShopHub trophyCounts={summary?.trophy_counts} />;
      case 'exchange':
        return <ExchangeHub />;
      case 'encoder':
        return <EncoderHub />;
      case 'news':
        return <NewsHub />;
      case 'podcast':
        return <PodcastHub />;
      case 'network-chat':
        return <NetworkChat />;
      case 'camgirls':
        return <CamgirlsHub />;
      case 'settings':
        return <Settings />;
      case 'upgrades':
        return <Upgrades />;
      default:
        return (
          <div class="wallet-panel wallet-tab-panel wallet-placeholder-tab">
            <strong>{activeTab}</strong> — coming in the next wallet v2 slice (WR-U2+).
          </div>
        );
    }
  };

  return (
    <div class="wallet-shell">
      <BalanceHero
        summary={summary}
        loading={loading}
        showFiat={showFiat}
        onToggleFiat={() => setShowFiat((v) => !v)}
      />
      <TabNav active={activeTab} onChange={onTabChange} />
      {renderTab()}
    </div>
  );
}
