export type TabId =
  | 'overview'
  | 'portal'
  | 'rewards'
  | 'earn'
  | 'casino'
  | 'shop'
  | 'exchange'
  | 'encoder'
  | 'news'
  | 'podcast'
  | 'network-chat'
  | 'camgirls'
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

type TabDef = { id: TabId; label: string; primary?: boolean };

export const TAB_GROUPS: { label: string; tabs: TabDef[] }[] = [
  {
    label: 'Core',
    tabs: [
      { id: 'overview', label: 'Overview' },
      { id: 'portal', label: 'Portal', primary: true },
      { id: 'send', label: 'Send' },
      { id: 'receive', label: 'Receive' },
      { id: 'activity', label: 'Activity' },
      { id: 'settings', label: 'Settings' },
    ],
  },
  {
    label: 'Earn',
    tabs: [
      { id: 'rewards', label: 'Rewards', primary: true },
      { id: 'earn', label: 'Earn', primary: true },
      { id: 'casino', label: 'Casino', primary: true },
      { id: 'upgrades', label: 'Upgrades' },
    ],
  },
  {
    label: 'Media',
    tabs: [
      { id: 'encoder', label: 'Encoder' },
      { id: 'news', label: 'News' },
      { id: 'podcast', label: 'Podcast' },
    ],
  },
  {
    label: 'Social',
    tabs: [
      { id: 'network-chat', label: 'Chat' },
      { id: 'exchange', label: 'Exchange' },
      { id: 'shop', label: 'Shop' },
    ],
  },
  {
    label: 'Camgirls',
    tabs: [
      { id: 'camgirls', label: 'Camgirls' },
    ],
  },
  {
    label: 'More',
    tabs: [
      { id: 'monitor-4d', label: '4D Monitor' },
      { id: 'explorer-5d', label: '5D Explorer' },
      { id: 'trophies', label: 'Trophies' },
      { id: 'battle', label: 'Battle' },
      { id: 'peers', label: 'Peers' },
      { id: 'staking', label: 'Staking' },
    ],
  },
];

export const TABS: TabDef[] = TAB_GROUPS.flatMap((g) => g.tabs);

type Props = {
  active: TabId;
  onChange: (id: TabId) => void;
};

export function TabNav({ active, onChange }: Props) {
  return (
    <nav
      class="wallet-panel wallet-tab-nav"
      aria-label="Wallet sections"
      style={{
        borderRadius: 0,
        borderLeft: 'none',
        borderRight: 'none',
        margin: '0 -12px',
        overflowX: 'auto',
        scrollbarWidth: 'thin',
      }}
    >
      <div style={{ display: 'flex', flexWrap: 'nowrap', minWidth: 'min-content' }}>
        {TAB_GROUPS.map((group) => (
          <div
            key={group.label}
            style={{
              display: 'flex',
              flexDirection: 'column',
              flex: '0 0 auto',
              borderRight: '1px solid var(--wallet-edge)',
            }}
          >
            <div
              style={{
                fontSize: '0.65rem',
                textTransform: 'uppercase',
                letterSpacing: '0.08em',
                color: 'var(--wallet-muted)',
                padding: '6px 12px 2px',
                whiteSpace: 'nowrap',
              }}
            >
              {group.label}
            </div>
            <div style={{ display: 'flex' }}>
              {group.tabs.map((tab) => {
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
                      padding: '10px 12px',
                      cursor: 'pointer',
                      fontSize: '0.82rem',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {tab.label}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </nav>
  );
}
