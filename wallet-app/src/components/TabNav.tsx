export type TabId =
  | 'overview'
  | 'portal'
  | 'rewards'
  | 'earn'
  | 'shop'
  | 'exchange'
  | 'send'
  | 'receive'
  | 'activity'
  | 'monitor-4d'
  | 'explorer-5d'
  | 'trophies'
  | 'battle'
  | 'peers'
  | 'staking'
  | 'upgrades'
  | 'settings';

export const TABS: { id: TabId; label: string; primary?: boolean }[] = [
  { id: 'overview', label: 'Overview' },
  { id: 'portal', label: 'Portal', primary: true },
  { id: 'rewards', label: 'Rewards', primary: true },
  { id: 'earn', label: 'Earn', primary: true },
  { id: 'shop', label: 'Shop' },
  { id: 'exchange', label: 'Exchange' },
  { id: 'send', label: 'Send' },
  { id: 'receive', label: 'Receive' },
  { id: 'activity', label: 'Activity' },
  { id: 'monitor-4d', label: '4D Monitor' },
  { id: 'explorer-5d', label: '5D Explorer' },
  { id: 'trophies', label: 'Trophies' },
  { id: 'battle', label: 'Battle' },
  { id: 'peers', label: 'Peers' },
  { id: 'staking', label: 'Staking' },
  { id: 'upgrades', label: 'Upgrades' },
  { id: 'settings', label: 'Settings' },
];

type Props = {
  active: TabId;
  onChange: (id: TabId) => void;
};

export function TabNav({ active, onChange }: Props) {
  return (
    <nav
      class="wallet-panel"
      aria-label="Wallet sections"
      style={{
        borderRadius: 0,
        borderLeft: 'none',
        borderRight: 'none',
        margin: '0 -12px',
        overflowX: 'auto',
        display: 'flex',
        gap: 0,
        scrollbarWidth: 'thin',
      }}
    >
      {TABS.map((tab) => {
        const isActive = tab.id === active;
        const isPrimary = Boolean(tab.primary);
        return (
          <button
            key={tab.id}
            type="button"
            onClick={() => onChange(tab.id)}
            aria-current={isActive ? 'page' : undefined}
            class={isPrimary ? 'wallet-tab-btn--primary' : undefined}
            style={{
              flex: '0 0 auto',
              border: 'none',
              borderBottom: isActive ? '2px solid var(--wallet-accent)' : '2px solid transparent',
              background: 'transparent',
              color: isActive ? 'var(--wallet-accent)' : isPrimary ? 'var(--wallet-text)' : 'var(--wallet-muted)',
              fontWeight: isActive || isPrimary ? 700 : 500,
              padding: '12px 14px',
              cursor: 'pointer',
              fontSize: '0.85rem',
              whiteSpace: 'nowrap',
            }}
          >
            {tab.label}
          </button>
        );
      })}
    </nav>
  );
}
