import { useCallback, useEffect, useRef, useState } from 'preact/hooks';
import {
  fetchCamgirlsAiFeatures,
  fetchCamgirlsCatalog,
  fetchCamgirlsLedgerQueue,
  fetchCamgirlsUpgrades,
  fetchCamgirlsUpgradesProgress,
  postCamgirlLedgerOffer,
  postCamgirlTip,
  triggerCamgirlAiFeature,
  unlockCamgirlUpgrade,
  type CamgirlAiFeature,
  type CamgirlPerformer,
  type CamgirlUpgrade,
  type CamgirlsUpgradesProgress,
  type LedgerOutreachLead,
} from '../api/client';

type Panel = 'performers' | 'upgrades' | 'ai-features' | 'ledger-outreach';

const CATEGORY_LABELS: Record<string, string> = {
  studio: 'Studio',
  chat: 'Chat',
  gifts: 'Gifts',
  lighting: 'Lighting',
  wardrobe: 'Wardrobe',
  rewards: 'Rewards',
  network: 'Network',
  premium: 'Premium',
  greetings: 'Greetings',
  reactions: 'Reactions',
  dances: 'Dances',
  games: 'Games',
  tips: 'Tips',
  vip_moments: 'VIP Moments',
  network_events: 'Network Events',
  trophy_tie_ins: 'Trophy Tie-ins',
  ai_chat_moods: 'AI Chat Moods',
  seasonal: 'Seasonal',
};

function effectivePrice(f: CamgirlAiFeature): number {
  const p = f.payment;
  if (p.unlocked_via_upgrade) return 0;
  return p.effective_price_mn2 ?? p.price_mn2 ?? 0;
}

function previewFeature(feature: CamgirlAiFeature, audioEnabled: boolean): HTMLAudioElement | null {
  if (!audioEnabled || !feature.sound?.url) return null;
  const audio = new Audio(feature.sound.url);
  audio.volume = feature.sound.volume_default ?? 0.5;
  audio.play().catch(() => {});
  return audio;
}

export function CamgirlsHub() {
  const panelFromQuery = (): Panel => {
    const p = new URLSearchParams(window.location.search).get('panel');
    if (p === 'upgrades') return 'upgrades';
    if (p === 'ai-features') return 'ai-features';
    if (p === 'ledger-outreach') return 'ledger-outreach';
    return 'performers';
  };

  const [panel, setPanel] = useState<Panel>(panelFromQuery);
  const [performers, setPerformers] = useState<CamgirlPerformer[]>([]);
  const [upgrades, setUpgrades] = useState<CamgirlUpgrade[]>([]);
  const [aiFeatures, setAiFeatures] = useState<CamgirlAiFeature[]>([]);
  const [aiCategories, setAiCategories] = useState<string[]>([]);
  const [progress, setProgress] = useState<CamgirlsUpgradesProgress | null>(null);
  const [loading, setLoading] = useState(true);
  const [upgradesLoaded, setUpgradesLoaded] = useState(false);
  const [aiLoaded, setAiLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [unlocking, setUnlocking] = useState<string | null>(null);
  const [tipping, setTipping] = useState<string | null>(null);
  const [triggering, setTriggering] = useState<string | null>(null);
  const [tipFlash, setTipFlash] = useState<string | null>(null);
  const [aiFlash, setAiFlash] = useState<string | null>(null);
  const [filter, setFilter] = useState('all');
  const [aiFilter, setAiFilter] = useState('all');
  const [selectedPerformer, setSelectedPerformer] = useState('');
  const [audioUnlocked, setAudioUnlocked] = useState(false);
  const [previewId, setPreviewId] = useState<string | null>(null);
  const previewAudioRef = useRef<HTMLAudioElement | null>(null);
  const [ledgerLeads, setLedgerLeads] = useState<LedgerOutreachLead[]>([]);
  const [ledgerLoaded, setLedgerLoaded] = useState(false);
  const [ledgerFlash, setLedgerFlash] = useState<string | null>(null);
  const [offering, setOffering] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchCamgirlsCatalog()
      .then((data) => {
        if (!cancelled) {
          setPerformers(data.performers || []);
          if ((data.performers || []).length > 0) {
            setSelectedPerformer(data.performers[0].id);
          }
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

  const loadUpgrades = useCallback(() => {
    if (upgradesLoaded) return Promise.resolve();
    setError(null);
    return Promise.all([fetchCamgirlsUpgrades(), fetchCamgirlsUpgradesProgress()])
      .then(([catalog, prog]) => {
        setUpgrades(catalog.upgrades || []);
        setProgress(prog);
        setUpgradesLoaded(true);
      })
      .catch((err: Error) => setError(err.message));
  }, [upgradesLoaded]);

  const loadLedgerQueue = useCallback(() => {
    if (ledgerLoaded) return Promise.resolve();
    setError(null);
    return fetchCamgirlsLedgerQueue(25)
      .then((data) => {
        setLedgerLeads(data.queue || []);
        setLedgerLoaded(true);
      })
      .catch((err: Error) => setError(err.message));
  }, [ledgerLoaded]);

  const loadAiFeatures = useCallback(() => {
    if (aiLoaded) return Promise.resolve();
    setError(null);
    const cat = aiFilter === 'all' ? undefined : aiFilter;
    const perf = selectedPerformer || undefined;
    return fetchCamgirlsAiFeatures(cat, perf)
      .then((data) => {
        setAiFeatures(data.features || []);
        setAiCategories(data.categories || []);
        setAiLoaded(true);
      })
      .catch((err: Error) => setError(err.message));
  }, [aiLoaded, aiFilter, selectedPerformer]);

  useEffect(() => {
    if (panel === 'upgrades') loadUpgrades();
    if (panel === 'ai-features') loadAiFeatures();
    if (panel === 'ledger-outreach') loadLedgerQueue();
  }, [panel, loadUpgrades, loadAiFeatures, loadLedgerQueue]);

  useEffect(() => {
    if (panel !== 'ai-features') return;
    setAiLoaded(false);
    const cat = aiFilter === 'all' ? undefined : aiFilter;
    const perf = selectedPerformer || undefined;
    fetchCamgirlsAiFeatures(cat, perf)
      .then((data) => {
        setAiFeatures(data.features || []);
        setAiCategories(data.categories || []);
        setAiLoaded(true);
      })
      .catch((err: Error) => setError(err.message));
  }, [aiFilter, selectedPerformer, panel]);

  const switchPanel = (p: Panel) => {
    setPanel(p);
    const url = new URL(window.location.href);
    if (p === 'performers') {
      url.searchParams.delete('panel');
    } else {
      url.searchParams.set('panel', p);
    }
    window.history.replaceState({}, '', url.pathname + url.search);
  };

  const handleLedgerOffer = async (lead: LedgerOutreachLead, rail: 'paypal' | 'usdt' | 'usdc') => {
    if (offering) return;
    const mn2Raw = window.prompt(`MN2 amount for ${lead.display_name || lead.ledger_row_id}:`, '100');
    if (mn2Raw == null) return;
    const priceRaw = window.prompt('Price USD:', '9.99');
    if (priceRaw == null) return;
    const mn2 = parseFloat(mn2Raw);
    const price = parseFloat(priceRaw);
    if (!Number.isFinite(mn2) || !Number.isFinite(price) || mn2 <= 0 || price <= 0) {
      setLedgerFlash('Invalid MN2 amount or price');
      window.setTimeout(() => setLedgerFlash(null), 3000);
      return;
    }
    setOffering(lead.ledger_row_id);
    setLedgerFlash(null);
    try {
      const result = await postCamgirlLedgerOffer(
        lead.ledger_row_id,
        mn2,
        price,
        rail,
        selectedPerformer || lead.assigned_camgirl_id,
      );
      setLedgerFlash(result.success ? `Offer created (${rail}) — ${mn2} MN2 @ $${price}` : (result.error || 'Offer failed'));
    } catch (err: unknown) {
      setLedgerFlash(err instanceof Error ? err.message : 'Offer failed');
    } finally {
      setOffering(null);
      window.setTimeout(() => setLedgerFlash(null), 5000);
    }
  };

  const unlocked = new Set(progress?.unlocked_ids || []);
  const available = new Set(progress?.available_ids || []);

  const handleTip = async (performer: CamgirlPerformer) => {
    if (tipping) return;
    const min = performer.tip_min_mn2 ?? 5;
    const raw = window.prompt(`Tip ${performer.name} (min ${min} MN2):`, String(min));
    if (raw == null) return;
    const amount = parseFloat(raw);
    if (!Number.isFinite(amount) || amount < min) {
      setTipFlash(`Minimum tip is ${min} MN2`);
      window.setTimeout(() => setTipFlash(null), 3000);
      return;
    }
    setTipping(performer.id);
    setTipFlash(null);
    try {
      const result = await postCamgirlTip(performer.id, amount);
      if (result.success) {
        setTipFlash(`Tipped ${amount} MN2 → balance ${result.camgirl_balance?.toFixed(4) ?? '—'}`);
        setPerformers((prev) => prev.map((p) => (
          p.id === performer.id
            ? { ...p, mn2_balance: result.camgirl_balance ?? p.mn2_balance }
            : p
        )));
      } else {
        setTipFlash(result.error || result.message || 'Tip failed');
      }
    } catch (err: unknown) {
      setTipFlash(err instanceof Error ? err.message : 'Tip failed');
    } finally {
      setTipping(null);
      window.setTimeout(() => setTipFlash(null), 4000);
    }
  };

  const handleUnlock = async (upgrade: CamgirlUpgrade) => {
    if (unlocking || unlocked.has(upgrade.id)) return;
    setUnlocking(upgrade.id);
    try {
      const result = await unlockCamgirlUpgrade(upgrade.id);
      if (result.progress) setProgress(result.progress);
      else await loadUpgrades();
    } finally {
      setUnlocking(null);
    }
  };

  const enableAudio = () => setAudioUnlocked(true);

  const handlePreview = (feature: CamgirlAiFeature) => {
    if (!audioUnlocked) enableAudio();
    if (previewAudioRef.current) {
      previewAudioRef.current.pause();
      previewAudioRef.current = null;
    }
    setPreviewId(feature.id);
    previewAudioRef.current = previewFeature(feature, true);
    window.setTimeout(() => setPreviewId((cur) => (cur === feature.id ? null : cur)), feature.animation?.duration_ms || 1500);
  };

  const resolvePerformerForFeature = (feature: CamgirlAiFeature): string | undefined => {
    const ids = feature.performer_ids || [];
    if (ids.includes('all')) return selectedPerformer || performers[0]?.id;
    if (selectedPerformer && ids.includes(selectedPerformer)) return selectedPerformer;
    return ids[0];
  };

  const handleTrigger = async (feature: CamgirlAiFeature) => {
    if (triggering) return;
    if (!audioUnlocked) enableAudio();
    const performerId = resolvePerformerForFeature(feature);
    setTriggering(feature.id);
    setAiFlash(null);
    try {
      const result = await triggerCamgirlAiFeature(feature.id, performerId);
      if (result.success && result.playback) {
        const anim = result.playback.animation;
        const snd = result.playback.sound;
        if (snd?.url) {
          const audio = new Audio(snd.url);
          audio.volume = snd.volume_default ?? 0.5;
          audio.play().catch(() => {});
        }
        setAiFlash(`Triggered ${result.name} — paid ${result.paid_mn2 ?? 0} MN2`);
        setPreviewId(feature.id);
        window.setTimeout(() => setPreviewId(null), anim?.duration_ms || 1500);
      } else {
        setAiFlash(result.error || result.message || 'Trigger failed');
      }
    } catch (err: unknown) {
      setAiFlash(err instanceof Error ? err.message : 'Trigger failed');
    } finally {
      setTriggering(null);
      window.setTimeout(() => setAiFlash(null), 4000);
    }
  };

  const filteredUpgrades = filter === 'all'
    ? upgrades
    : upgrades.filter((u) => u.category === filter);

  const filteredAi = aiFilter === 'all'
    ? aiFeatures
    : aiFeatures.filter((f) => f.category === aiFilter);

  return (
    <div class="wallet-tab-panel">
      <section class="wallet-panel wallet-exchange-hero">
        <div style={{ padding: '16px' }}>
          <div style={{ fontWeight: 700, fontSize: '1.1rem' }}>Camgirls Studio</div>
          <p style={{ margin: '8px 0 0', color: 'var(--wallet-muted)', fontSize: '0.9rem' }}>
            25 performers — SFW wallet cards link to the full studio experience. 250 section upgrades. 100 AI feature bundles.
          </p>
          <a href="/camgirls" class="wallet-discord-btn wallet-discord-btn-primary" style={{ marginTop: '12px', display: 'inline-flex' }}>
            Open full studio →
          </a>
        </div>
      </section>

      <div style={{ display: 'flex', gap: '8px', marginTop: '12px', flexWrap: 'wrap' }}>
        <button
          type="button"
          class={`wallet-discord-btn${panel === 'performers' ? ' wallet-discord-btn-primary' : ''}`}
          onClick={() => switchPanel('performers')}
        >
          Performers (25)
        </button>
        <button
          type="button"
          class={`wallet-discord-btn${panel === 'upgrades' ? ' wallet-discord-btn-primary' : ''}`}
          onClick={() => switchPanel('upgrades')}
        >
          Upgrades (250)
        </button>
        <button
          type="button"
          class={`wallet-discord-btn${panel === 'ai-features' ? ' wallet-discord-btn-primary' : ''}`}
          onClick={() => switchPanel('ai-features')}
        >
          AI Features (100)
        </button>
        <button
          type="button"
          class={`wallet-discord-btn${panel === 'ledger-outreach' ? ' wallet-discord-btn-primary' : ''}`}
          onClick={() => switchPanel('ledger-outreach')}
        >
          Ledger outreach
        </button>
      </div>

      {panel === 'performers' && (
        <>
          {loading ? (
            <div class="wallet-skeleton" style={{ height: '200px', marginTop: '12px' }} />
          ) : error ? (
            <div class="wallet-error wallet-error--inline" role="alert">{error}</div>
          ) : (
            <>
              {tipFlash && (
                <div style={{ marginTop: '12px', fontSize: '0.85rem', color: 'var(--wallet-accent)' }}>{tipFlash}</div>
              )}
              <div class="wallet-shop-grid" style={{ marginTop: '12px' }}>
                {performers.map((p) => (
                  <div key={p.id} class="wallet-shop-card" style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    <img
                      src={p.avatar_url || '/static/camgirls/avatar-demo.svg'}
                      alt=""
                      width={48}
                      height={48}
                      style={{ borderRadius: 'var(--wallet-radius)' }}
                    />
                    <span class="wallet-shop-card-name">
                      {p.name}
                      {p.online ? (
                        <span style={{ color: 'var(--wallet-accent)', marginLeft: '6px', fontSize: '0.7rem' }}>● online</span>
                      ) : null}
                    </span>
                    <span class="wallet-shop-card-desc">{p.tagline}</span>
                    <span style={{ fontSize: '0.75rem', color: 'var(--wallet-muted)' }}>
                      {p.tier} · unlock {p.price_mn2} MN2
                    </span>
                    <span style={{ fontFamily: 'var(--wallet-font-mono)', fontSize: '0.85rem', color: 'var(--wallet-accent)' }}>
                      {(p.mn2_balance ?? 0).toFixed(4)} MN2
                    </span>
                    {p.wallet_user_id && (
                      <span style={{ fontSize: '0.65rem', color: 'var(--wallet-muted)', wordBreak: 'break-all' }}>
                        {p.wallet_user_id}
                      </span>
                    )}
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '4px' }}>
                      <button
                        type="button"
                        class="wallet-discord-btn wallet-discord-btn-primary"
                        disabled={tipping === p.id}
                        onClick={() => handleTip(p)}
                      >
                        {tipping === p.id ? 'Tipping…' : 'Tip'}
                      </button>
                      <a href={p.studio_path || '/camgirls'} class="wallet-discord-btn" style={{ textDecoration: 'none' }}>
                        Studio
                      </a>
                      {p.explorer_url ? (
                        <a href={p.explorer_url} class="wallet-discord-btn" style={{ textDecoration: 'none' }} target="_blank" rel="noopener noreferrer">
                          Explorer
                        </a>
                      ) : null}
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </>
      )}

      {panel === 'upgrades' && (
        <section class="wallet-panel" style={{ marginTop: '12px' }}>
          <div class="wallet-panel-header" style={{ flexWrap: 'wrap', gap: '8px' }}>
            <div>
              <div class="wallet-panel-title">Section upgrades</div>
              <div class="wallet-panel-subtitle">
                {progress ? `${progress.unlocked_count}/${progress.total} unlocked` : 'Loading…'}
              </div>
            </div>
            <select
              value={filter}
              onChange={(e) => setFilter((e.target as HTMLSelectElement).value)}
              style={{
                background: 'var(--wallet-bg-elevated)',
                border: 'var(--wallet-border)',
                color: 'var(--wallet-text)',
                padding: '6px 10px',
                borderRadius: 'var(--wallet-radius)',
              }}
            >
              <option value="all">All categories</option>
              {(progress?.by_category ? Object.keys(progress.by_category) : []).map((cat) => (
                <option key={cat} value={cat}>{CATEGORY_LABELS[cat] || cat}</option>
              ))}
            </select>
          </div>
          {!upgradesLoaded ? (
            <div style={{ padding: '16px' }}>
              <div class="wallet-skeleton" style={{ height: '120px' }} />
            </div>
          ) : (
            <div style={{ maxHeight: '480px', overflowY: 'auto', padding: '8px 16px 16px' }}>
              {filteredUpgrades.slice(0, 80).map((u) => {
                const isUnlocked = unlocked.has(u.id);
                const canUnlock = available.has(u.id);
                return (
                  <div
                    key={u.id}
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      gap: '12px',
                      padding: '10px 0',
                      borderBottom: '1px solid var(--wallet-border)',
                      fontSize: '0.85rem',
                    }}
                  >
                    <div>
                      <div style={{ fontWeight: 600 }}>{u.name}</div>
                      <div style={{ color: 'var(--wallet-muted)', fontSize: '0.75rem' }}>{u.id} · {u.tier}</div>
                    </div>
                    {isUnlocked ? (
                      <span style={{ color: 'var(--wallet-accent)' }}>Unlocked</span>
                    ) : canUnlock ? (
                      <button
                        type="button"
                        class="wallet-discord-btn wallet-discord-btn-primary"
                        disabled={unlocking === u.id}
                        onClick={() => handleUnlock(u)}
                      >
                        Unlock
                      </button>
                    ) : (
                      <span style={{ color: 'var(--wallet-muted)', fontSize: '0.75rem' }}>Locked</span>
                    )}
                  </div>
                );
              })}
              {filteredUpgrades.length > 80 && (
                <p style={{ color: 'var(--wallet-muted)', fontSize: '0.8rem', marginTop: '12px' }}>
                  Showing first 80 — filter by category to browse all 250.
                </p>
              )}
            </div>
          )}
        </section>
      )}

      {panel === 'ai-features' && (
        <section class="wallet-panel" style={{ marginTop: '12px' }}>
          <div class="wallet-panel-header" style={{ flexWrap: 'wrap', gap: '8px' }}>
            <div>
              <div class="wallet-panel-title">AI Features</div>
              <div class="wallet-panel-subtitle">
                {aiLoaded ? `${filteredAi.length} bundles — animation + payment + sound` : 'Loading…'}
              </div>
            </div>
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              <select
                value={selectedPerformer}
                onChange={(e) => setSelectedPerformer((e.target as HTMLSelectElement).value)}
                style={{
                  background: 'var(--wallet-bg-elevated)',
                  border: 'var(--wallet-border)',
                  color: 'var(--wallet-text)',
                  padding: '6px 10px',
                  borderRadius: 'var(--wallet-radius)',
                }}
              >
                {performers.map((p) => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
              <select
                value={aiFilter}
                onChange={(e) => setAiFilter((e.target as HTMLSelectElement).value)}
                style={{
                  background: 'var(--wallet-bg-elevated)',
                  border: 'var(--wallet-border)',
                  color: 'var(--wallet-text)',
                  padding: '6px 10px',
                  borderRadius: 'var(--wallet-radius)',
                }}
              >
                <option value="all">All categories</option>
                {(aiCategories.length ? aiCategories : Object.keys(CATEGORY_LABELS).slice(8)).map((cat) => (
                  <option key={cat} value={cat}>{CATEGORY_LABELS[cat] || cat}</option>
                ))}
              </select>
            </div>
          </div>
          {aiFlash && (
            <div style={{ padding: '0 16px', fontSize: '0.85rem', color: 'var(--wallet-accent)' }}>{aiFlash}</div>
          )}
          {!audioUnlocked && (
            <div style={{ padding: '8px 16px' }}>
              <button type="button" class="wallet-discord-btn" onClick={enableAudio}>
                Enable sound preview
              </button>
            </div>
          )}
          {!aiLoaded ? (
            <div style={{ padding: '16px' }}>
              <div class="wallet-skeleton" style={{ height: '200px' }} />
            </div>
          ) : (
            <div class="wallet-shop-grid" style={{ padding: '8px 16px 16px', maxHeight: '560px', overflowY: 'auto' }}>
              {filteredAi.map((f) => {
                const price = effectivePrice(f);
                const isPreview = previewId === f.id;
                const anim = f.animation;
                const isCss = anim?.type === 'css';
                return (
                  <div
                    key={f.id}
                    class="wallet-shop-card"
                    style={{
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '6px',
                      outline: isPreview ? '2px solid var(--wallet-accent)' : undefined,
                    }}
                    onMouseEnter={() => handlePreview(f)}
                    onClick={() => handlePreview(f)}
                  >
                    <div
                      style={{
                        height: '64px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        background: 'var(--wallet-bg-elevated)',
                        borderRadius: 'var(--wallet-radius)',
                        overflow: 'hidden',
                      }}
                    >
                      {isCss ? (
                        <div
                          class={anim.asset_url}
                          style={{
                            width: '48px',
                            height: '48px',
                            borderRadius: '50%',
                            background: 'linear-gradient(135deg, var(--wallet-accent), transparent)',
                            animation: isPreview ? 'pulse 1s ease-in-out infinite' : undefined,
                          }}
                        />
                      ) : (
                        <img
                          src={anim?.asset_url || '/static/camgirls/preview-demo.svg'}
                          alt=""
                          width={48}
                          height={48}
                          style={{
                            borderRadius: 'var(--wallet-radius)',
                            transform: isPreview ? 'scale(1.1)' : undefined,
                            transition: 'transform 0.2s',
                          }}
                        />
                      )}
                    </div>
                    <span class="wallet-shop-card-name">{f.name}</span>
                    <span style={{ fontSize: '0.7rem', color: 'var(--wallet-muted)' }}>
                      {f.id} · {CATEGORY_LABELS[f.category] || f.category}
                    </span>
                    <span class="wallet-shop-card-desc" style={{ fontSize: '0.75rem' }}>
                      {f.description?.slice(0, 80)}…
                    </span>
                    <span style={{ fontFamily: 'var(--wallet-font-mono)', fontSize: '0.85rem', color: 'var(--wallet-accent)' }}>
                      {price === 0 ? 'Free (upgrade)' : `${price.toFixed(2)} MN2`}
                    </span>
                    <button
                      type="button"
                      class="wallet-discord-btn wallet-discord-btn-primary"
                      disabled={triggering === f.id}
                      onClick={(e) => { e.stopPropagation(); handleTrigger(f); }}
                    >
                      {triggering === f.id ? 'Triggering…' : price === 0 ? 'Trigger free' : `Pay ${price.toFixed(2)} MN2`}
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </section>
      )}

      {panel === 'ledger-outreach' && (
        <section class="wallet-panel" style={{ marginTop: '12px' }}>
          <div class="wallet-panel-header">
            <div>
              <div class="wallet-panel-title">Ledger outreach</div>
              <div class="wallet-panel-subtitle">
                Community fulfillment leads — sell MN2 via PayPal, USDT, or USDC
              </div>
            </div>
          </div>
          {ledgerFlash && (
            <div style={{ padding: '8px 16px', fontSize: '0.85rem', color: 'var(--wallet-accent)' }}>{ledgerFlash}</div>
          )}
          {!ledgerLoaded ? (
            <div style={{ padding: '16px' }}>
              <div class="wallet-skeleton" style={{ height: '120px' }} />
            </div>
          ) : ledgerLeads.length === 0 ? (
            <div style={{ padding: '16px', color: 'var(--wallet-muted)' }}>No leads in queue — run community ledger sync.</div>
          ) : (
            <div class="wallet-shop-grid" style={{ padding: '12px' }}>
              {ledgerLeads.map((lead) => (
                <div key={lead.ledger_row_id} class="wallet-shop-card" style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <span class="wallet-shop-card-name">
                    #{lead.ledger_rank ?? '—'} {lead.display_name || lead.ledger_row_id}
                  </span>
                  <span style={{ fontSize: '0.75rem', color: 'var(--wallet-muted)' }}>
                    priority {lead.priority_score ?? 0} · buyer {lead.buyer_score ?? 0}
                  </span>
                  <span style={{ fontSize: '0.7rem', color: 'var(--wallet-muted)' }}>
                    {(lead.sources || []).slice(0, 3).join(', ')}
                  </span>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '4px' }}>
                    <button
                      type="button"
                      class="wallet-discord-btn wallet-discord-btn-primary"
                      disabled={offering === lead.ledger_row_id}
                      onClick={() => handleLedgerOffer(lead, 'paypal')}
                    >
                      PayPal
                    </button>
                    <button
                      type="button"
                      class="wallet-discord-btn"
                      disabled={offering === lead.ledger_row_id}
                      onClick={() => handleLedgerOffer(lead, 'usdt')}
                    >
                      USDT
                    </button>
                    <button
                      type="button"
                      class="wallet-discord-btn"
                      disabled={offering === lead.ledger_row_id}
                      onClick={() => handleLedgerOffer(lead, 'usdc')}
                    >
                      USDC
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      )}
    </div>
  );
}
