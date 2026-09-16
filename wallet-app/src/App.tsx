import { useEffect, useState } from 'preact/hooks';
import { fetchSummary, type WalletSummary } from './api/client';
import { BalanceHero } from './components/BalanceHero';
import { TabNav, type TabId } from './components/TabNav';
import { Overview } from './tabs/Overview';

function tabFromQuery(): TabId {
  const tab = new URLSearchParams(window.location.search).get('tab');
  const valid: TabId[] = [
    'overview', 'send', 'receive', 'activity', 'monitor-4d', 'explorer-5d',
    'trophies', 'battle', 'peers', 'staking', 'settings',
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

  return (
    <div class="wallet-shell">
      <BalanceHero
        summary={summary}
        loading={loading}
        showFiat={showFiat}
        onToggleFiat={() => setShowFiat((v) => !v)}
      />
      <TabNav active={activeTab} onChange={onTabChange} />
      {activeTab === 'overview' ? (
        <Overview summary={summary} loading={loading} error={error} />
      ) : (
        <div class="wallet-panel wallet-tab-panel wallet-placeholder-tab">
          <strong>{activeTab}</strong> — coming in the next wallet v2 slice (WR-U2+).
        </div>
      )}
    </div>
  );
}
