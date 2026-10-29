"""Static shop catalog seed data (no Flask routes). Used by migrations and shop_routes."""

def build_seed_shop_items(*, include_dynamic_offers=True):
    """Return 100+ shop items across categories (themes, boosts, cosmetic, etc.)."""
    items = []
    idx = 0

    def add(name, desc, cat, price, icon="🛍️", rarity="common", tags=None, item_id=None):
        nonlocal idx
        idx += 1
        row = {
            "id": item_id or f"shop-{idx}",
            "name": name,
            "description": desc,
            "category": cat,
            "price": price,
            "icon": icon,
            "rarity": rarity,
        }
        if tags:
            row["tags"] = tags
        items.append(row)

    themes = [
        ("Galaxy Dark", "Dark space theme for UI", "🎨"),
        ("Neon Green", "Neon green accent theme", "💚"),
        ("Ocean Blue", "Calm ocean blue theme", "🌊"),
        ("Sunset Purple", "Purple gradient theme", "🌅"),
        ("Electric Magnet", "Electric Magnet tech theme", "🧲"),
        ("Star Map", "Star map background theme", "⭐"),
        ("Trophy Gold", "Gold trophy hunter theme", "🏆"),
        ("Debugger Pro", "Debugger-style dark theme", "🔧"),
    ]
    for n, d, i in themes:
        add(n, d, "themes", 50 + idx * 5, i, "common" if idx % 3 else "rare")

    boosts = [
        ("XP Booster 1h", "+20% XP for 1 hour", "⚡"),
        ("XP Booster 2h", "+20% XP for 2 hours", "⚡"),
        ("XP Booster 24h", "+20% XP for 24 hours", "⚡"),
        ("Game Time +30m", "Extra 30 min game session", "⏱️"),
        ("Game Time +1h", "Extra 1 hour game session", "⏱️"),
        ("Game Time +2h", "Extra 2h game session", "⏱️"),
        ("Game Time +4h", "Extra 4h game session", "⏱️"),
        ("Weekend Pass", "48h extended game time (weekend)", "🎫"),
        ("Clickthrough Bonus", "Boost clickthrough rewards", "👆"),
        ("Generation Speed", "Faster video generation", "🎬"),
        ("Battle Power 1h", "Temporary battle boost 1 hour", "⚔️"),
        ("Quest Booster", "+25% quest rewards for 24h", "📜"),
        ("Progression Boost", "Faster progression", "📊"),
    ]
    for n, d, i in boosts:
        add(n, d, "boosts", 30 + idx * 3, i, "common")

    # Star Map 25: boosters, gametime, trophies
    starmap25_boosts = [
        ("Star Map 25 Booster 1h", "2x investigation points for 1 hour on Star Map 25", "🌟"),
        ("Star Map 25 Booster 6h", "2x investigation points for 6 hours", "🌟"),
        ("Star Map 25 Booster 24h", "2x investigation points for 24 hours", "🌟"),
        ("Star Map 25 Game Time +30m", "Extra 30 min Hunter game + Star Map 25 session", "⏱️"),
        ("Star Map 25 Game Time +1h", "Extra 1h Hunter game + Star Map 25 session", "⏱️"),
        ("Star Map 25 Game Time +2h", "Extra 2h Hunter game + Star Map 25 session", "⏱️"),
    ]
    for n, d, i in starmap25_boosts:
        add(n, d, "starmap25", 35 + idx * 2, i, "rare")
    starmap25_trophies = [
        ("Star Map 25 — Terra Trophy", "Trophy: First investigation (Terra)", "🏆"),
        ("Star Map 25 — Segmentum Clear", "Trophy: All 5 Segmentum fortresses investigated", "🏆"),
        ("Star Map 25 — Full Clear Trophy", "Trophy: All 25 points investigated", "🏆"),
        ("Star Map 25 — Lore Master", "Trophy: Unlock all 25 lore entries", "📜"),
    ]
    for n, d, i in starmap25_trophies:
        add(n, d, "starmap25", {"game_points": 50 + idx * 5}, i, "rare")
    starmap25_levels_calendar = [
        ("System Level Skip Token", "Unlock one system to next level (max 5)", "📈"),
        ("Daily Reset Bonus 24h", "2x buildup collect for 24h after next daily reset", "🔄"),
        ("High-Level Structure Unlock", "Unlock one Orbital Fortress / Cathedral / Primarch's Gate without level", "🏗️"),
        ("Calendar Slot — Agent Task", "Schedule one agent/AI appointment (content, learning, analytics)", "📅"),
        ("Star Map 25 Level Pack", "Bundle: 1 level skip + 1 daily reset bonus", "📦"),
    ]
    for n, d, i in starmap25_levels_calendar:
        add(n, d, "starmap25", 80 + idx * 10, i, "rare")

    cosmetics = [
        ("Avatar Frame Gold", "Gold avatar frame", "🖼️"),
        ("Avatar Frame Neon", "Neon avatar frame", "🖼️"),
        ("Profile Badge Star", "Star profile badge", "⭐"),
        ("Profile Badge Trophy", "Trophy profile badge", "🏆"),
        ("Chat Bubble Glow", "Glowing chat bubble", "💬"),
        ("Cursor Trail", "Custom cursor trail", "✨"),
    ]
    for n, d, i in cosmetics:
        add(n, d, "cosmetic", 25 + idx * 2, i, "common")

    tech = [
        ("Electric Magnet Module", "Agent tech: verification, DNA, star map", "🧲"),
        ("Event Tracker", "Track new tasks and events", "📡"),
        ("3D Monitor Plugin", "3D visual effects monitor", "📺"),
        ("Lab Access", "Unlock Lab experiments", "🔬"),
        ("API Scanner Pro", "Extended API scanning", "🔍"),
        ("Path Corrector", "Intelligent path correction", "🧭"),
    ]
    for n, d, i in tech:
        add(n, d, "tech", {"xp": 100 + idx * 20, "generation_points": 50}, i, "rare")

    battle = [
        ("Battle Ticket", "One battle entry", "🎫"),
        ("Strength Potion", "Temp battle strength", "🧪"),
        ("Shield Token", "One-time battle shield", "🛡️"),
        ("Victory Boost", "Post-victory bonus", "🏆"),
        ("Combat Points Pack", "100 combat points", "⚔️"),
    ]
    for n, d, i in battle:
        add(n, d, "battle", {"battle_points": 50 + idx * 10}, i, "rare")

    premium = [
        ("Valued Seller Badge", "Valued seller choice badge", "💎"),
        ("Premium Theme Pack", "All premium themes", "🎨"),
        ("Unified Points Bundle", "Mixed points bundle", "💎"),
        ("Legendary Avatar", "Legendary avatar unlock", "👤"),
    ]
    for n, d, i in premium:
        add(n, d, "premium", 200 + idx * 50, i, "legendary")

    gen = [
        ("Clip Pack 4–6s", "4–6 second clip generation pack", "🎬"),
        ("30s Video Credit", "One 30s video generation", "🎬"),
        ("Checkpoint Toggle", "Enable checkpoint in generator", "✅"),
        ("Service Worker Pro", "Enhanced generation worker", "⚙️"),
    ]
    for n, d, i in gen:
        add(n, d, "generation", {"generation_points": 80 + idx * 15}, i, "rare")

    skill = [
        ("Skill Point Pack S", "50 skill points", "🧠"),
        ("Skill Point Pack M", "150 skill points", "🧠"),
        ("Skill Point Pack L", "500 skill points", "🧠"),
    ]
    for n, d, i in skill:
        add(n, d, "skill", {"skill_points": 50 + idx * 25}, i, "common")

    progression = [
        ("Progression Boost S", "Small progression boost", "📊"),
        ("Progression Boost M", "Medium progression boost", "📊"),
        ("Progression Boost L", "Large progression boost", "📊"),
    ]
    for n, d, i in progression:
        add(n, d, "progression", {"progression_points": 30 + idx * 20}, i, "common")

    social = [
        ("Social Points Pack", "100 social points", "👥"),
        ("Friend Invite Bonus", "Bonus for inviting friends", "🤝"),
        ("Guild Crest", "Custom guild crest", "👥"),
    ]
    for n, d, i in social:
        add(n, d, "social", {"social_points": 40 + idx * 10}, i, "common")

    achievement = [
        ("Achievement Unlock", "Unlock hidden achievement", "🏆"),
        ("Trophy Display", "Extra trophy display slot", "🏆"),
        ("Milestone Marker", "Custom milestone marker", "📌"),
    ]
    for n, d, i in achievement:
        add(n, d, "achievement", {"achievement_points": 60 + idx * 15}, i, "rare")

    # Hunters trophies (shop trophies — display / collectibles)
    hunters_trophies = [
        ("Winter Wedding Trophy", "Trophy: Complete The Winter Wedding in London (1017) story or one-shot", "💒"),
        ("Medieval Crown Trophy", "Trophy: Unlock medieval sector spells and complete a medieval encounter", "👑"),
        ("Time Reversal Trophy", "Trophy: Use time reversal (rewind) at least once in a session", "⏪"),
        ("Power Combo Trophy", "Trophy: Trigger a power combo (e.g. Contract Seal + Jarl's Fury)", "⚡"),
        ("Jarl's Favor Trophy", "Trophy: Earn Thorkill's favor in Winter Wedding", "🪓"),
    ]
    for n, d, i in hunters_trophies:
        add(n, d, "trophies", {"game_points": 55 + idx * 5, "achievement_points": 30}, i, "rare")

    # Story unlocks (Hunters stories)
    stories_cat = [
        ("Winter Wedding Story Unlock", "Full Winter Wedding (1017) campaign: roles, conflicts, NPCs, twist, power combos", "📜"),
        ("Medieval Campaign Pack", "Medieval sector + Time Reversal rules + Power Combo reference", "🏰"),
    ]
    for n, d, i in stories_cat:
        add(n, d, "stories", {"game_points": 80, "xp": 50}, i, "epic")

    # New boosters: power combo, time reversal, medieval
    new_boosters = [
        ("Power Combo Booster 1h", "Unlock power combo effects for 1 hour in Hunters sessions", "⚡"),
        ("Time Reversal Booster 1h", "One extra narrative rewind per hour in story mode", "⏪"),
        ("Medieval Might 1h", "+1 to Persuasion and Intimidation in medieval-themed encounters for 1h", "🛡️"),
    ]
    for n, d, i in new_boosters:
        add(n, d, "boosts", 35 + idx * 2, i, "rare")

    # May 2026 wave — booster packs, game time, exclusive bonuses
    wave_boosters = [
        ("Casino Luck Booster 6h", "+15% casino quest rewards for 6 hours", "🎰", "booster-casino-luck-6h"),
        ("Generation Speed Booster 3h", "Faster video generation for 3 hours", "🎬", "booster-gen-speed-3h"),
        ("XP Surge Booster 3h", "+30% XP for 3 hours", "⚡", "booster-xp-surge-3h"),
        ("Quest Rush Booster 12h", "+35% quest rewards for 12 hours", "📜", "booster-quest-rush-12h"),
        ("Battle Fury Booster 2h", "2x battle points for 2 hours", "⚔️", "booster-battle-fury-2h"),
    ]
    for n, d, i, iid in wave_boosters:
        add(n, d, "boosts", 55 + idx * 4, i, "rare", tags=["shop_wave_may2026"], item_id=iid)

    wave_gametime = [
        ("Hunter Game Time +4h", "Extra 4h Hunter + Star Map session", "⏱️", "gametime-hunter-4h"),
        ("Creator Session +3h", "Extended generator and lab session time", "🎬", "gametime-creator-3h"),
        ("Weekend Marathon Pass", "72h extended game time (weekend marathon)", "🎫", "gametime-weekend-marathon"),
    ]
    for n, d, i, iid in wave_gametime:
        add(n, d, "boosts", 65 + idx * 5, i, "epic", tags=["game_time", "shop_wave_may2026"], item_id=iid)

    exclusive_items = [
        ("VIP Gold Badge", "Exclusive VIP badge for your profile — limited shop drop", "👑", "exclusive-vip-badge-shop"),
        ("Neon Crown Frame", "Exclusive neon avatar frame — not in regular rotation", "💎", "exclusive-neon-crown"),
        ("Casino High Roller Title", "Exclusive casino title shown on leaderboard", "🎰", "exclusive-casino-title"),
        ("Founder's Bonus Pack", "200 bonus coins + 1h XP booster — one-time exclusive", "🎁", "exclusive-founders-pack"),
    ]
    for n, d, i, iid in exclusive_items:
        add(n, d, "exclusive", 149 + idx * 25, i, "legendary", tags=["exclusive", "shop_wave_may2026"], item_id=iid)

    booster_packs = [
        ("Booster Trio Pack", "XP 2h + Quest 24h + Battle 1h bundled", "📦", "pack-booster-trio"),
        ("Pro Booster Pack", "XP 24h + Casino Luck 6h + Gen Speed 3h", "🧰", "pack-booster-pro"),
        ("Weekend Power Pack", "Weekend pass + Hunter 4h + Quest Rush 12h", "🎫", "pack-weekend-power"),
    ]
    for n, d, i, iid in booster_packs:
        add(n, d, "bundles", 199 + idx * 30, i, "legendary", tags=["booster_pack", "shop_wave_may2026"], item_id=iid)

    # Security & account
    security_items = [
        ("Password Protection Unlock", "Unlock password protection for your account (reward for progress)", "🔐"),
        ("Account Backup Token", "One-time backup code for account recovery", "📋"),
        ("Session Extender", "Extend current session by 2 hours", "⏱️"),
    ]
    for n, d, i in security_items:
        add(n, d, "premium", 60 + idx * 5, i, "rare")

    # More achievements & milestones
    more_achievement_items = [
        ("Achievement Reveal", "Reveal one hidden achievement", "🎯"),
        ("Milestone Badge Bronze", "Bronze milestone display badge", "🥉"),
        ("Milestone Badge Silver", "Silver milestone display badge", "🥈"),
        ("Milestone Badge Gold", "Gold milestone display badge", "🥇"),
        ("Progress Showcase", "Showcase your top 3 achievements on profile", "📊"),
    ]
    for n, d, i in more_achievement_items:
        add(n, d, "achievement", {"achievement_points": 45 + idx * 5, "game_points": 20}, i, "rare")

    # Seasonal & limited
    seasonal = [
        ("Spring Bloom Theme", "Limited spring theme with floral accents", "🌸"),
        ("Summer Solar Theme", "Bright summer solar theme", "☀️"),
        ("Autumn Harvest Theme", "Warm autumn harvest theme", "🍂"),
        ("Winter Frost Theme", "Cool winter frost theme", "❄️"),
        ("Lunar New Year Badge", "Limited Lunar New Year profile badge", "🧧"),
        ("Anniversary Frame", "Special anniversary avatar frame", "🎂"),
    ]
    for n, d, i in seasonal:
        add(n, d, "cosmetic", 70 + idx * 3, i, "rare")

    # More battle & PvP
    more_battle = [
        ("Double Battle Rewards 1h", "2x battle points for 1 hour", "⚔️"),
        ("Battle Shield 3x", "Three one-time battle shields", "🛡️"),
        ("Victory Streak Booster", "Bonus points for win streaks", "🔥"),
        ("Ranked Entry Ticket", "One ranked battle entry", "🎫"),
    ]
    for n, d, i in more_battle:
        add(n, d, "battle", {"battle_points": 40 + idx * 8}, i, "rare")

    # More social & crew
    more_social = [
        ("Crew Banner", "Custom crew banner for your guild", "🚩"),
        ("Friend Slot +5", "Expand friend list by 5 slots", "👥"),
        ("Activity Pin", "Pin one activity to your profile", "📌"),
        ("Challenge Issuer", "Issue a custom challenge to friends", "🎯"),
    ]
    for n, d, i in more_social:
        add(n, d, "social", {"social_points": 50 + idx * 6}, i, "rare")

    # Quick find: popular / featured
    featured = [
        ("Starter Bundle", "XP Booster 1h + Game Time 30m + 50 coins", "🎁"),
        ("Star Map Explorer Pack", "Star Map 25 Booster 6h + 2 investigations bonus", "🗺️"),
        ("Battle Starter Pack", "3 Battle Tickets + Strength Potion", "⚔️"),
        ("Creator Pack", "30s Video Credit + Generation Speed Booster", "🎬"),
    ]
    for n, d, i in featured:
        add(n, d, "premium", 120 + idx * 15, i, "epic")

    currency = [
        ("Coin Pack S", "100 coins", "🪙"),
        ("Coin Pack M", "500 coins", "🪙"),
        ("Coin Pack L", "2000 coins", "🪙"),
    ]
    for n, d, i in currency:
        add(n, d, "currency", 99 + idx * 50, i, "common")

    upgrades = [
        ("Upgrade Slot +1", "Extra upgrade slot", "⭐"),
        ("Storage Upgrade", "More storage space", "📦"),
        ("Speed Upgrade", "Faster processing", "⚡"),
    ]
    for n, d, i in upgrades:
        add(n, d, "upgrades", 75 + idx * 25, i, "rare")

    unified = [
        ("Unified Points Mix S", "Mixed points small", "💎"),
        ("Unified Points Mix M", "Mixed points medium", "💎"),
        ("Unified Points Mix L", "Mixed points large", "💎"),
    ]
    for n, d, i in unified:
        add(n, d, "unified_points", {"xp": 80, "battle_points": 40, "generation_points": 40}, i, "rare")

    # Inventory — ideas: Electric Magnet, Star Map, Lab, Verification, DNA, Rulebook, etc.
    inventory = [
        ("Electric Magnet Tech Download", "Download EM tech: verification, DNA test, star map specials", "🧲"),
        ("Verification Kit", "Run verification — validate tech integrity & endpoints", "✔️"),
        ("DNA Test Kit", "Run DNA test — biosignature check", "🧬"),
        ("Star Map — 7 Nearest Stars", "Host→b: Sun, Proxima, Alpha Cen, Barnard, Lalande, Sirius, Eps Eri, Ross 128", "🌟"),
        ("Star Map Flyers Pack", "Info & flyers for star map; Electric Magnet promo", "📄"),
        ("Event Tracker Module", "Track new tasks; agent event tracker", "🎯"),
        ("3D Monitor Access", "3D visual effects for vidgenerator (placeholder)", "🖥️"),
        ("Lab Experiments Pack", "Lab: EM download, Verification, DNA, Event Tracker", "🔬"),
        ("Rulebook V.2 — 19 Spells", "19 theme-based spells in 5 sectors", "📜"),
        ("Effect Clusters Pack", "Galactic, Verification, Combat, Support, Utility", "⚡"),
        ("Trophy Hunters Star Map", "Star map integrated with Trophy Hunters game", "🏆"),
        ("Agent Skills Upgrade", "Advance agent skill sets & abilities", "📋"),
        ("Geo Reference Unlock", "GPS coords & geo-reference via profile", "📍"),
        ("Aggregator Fulfill", "Fill missing Hunter game data via fulfill API", "🔗"),
        ("Hunters Profiling", "Agent tech, specials, level_info, geo_ref", "📊"),
        ("Unified Dashboard Verification", "Verification & plugin compatibility", "📊"),
        ("Generator Checkpoint Toggle", "Checkpoint on/off in generator", "✅"),
        ("Clip 4–6s + 30s Video", "Clip vs 30s vid service; service_worker", "🎬"),
        ("Point Triggers Bundle", "Triggers for run_verification, dna_test, view_star_map, etc.", "🔔"),
        ("Knowledge Base Expansion", "Database knowledge & new elements", "📚"),
        ("Communication Psychology — 25 Theories", "Agenda-setting, framing, influence; integrated with starmap, DNA, points", "🧠"),
        ("Comm-Psych Theory Unlock Pack", "Unlock 5 random Communication Psychology theories at once", "📋"),
        ("Framing & Influence Bundle", "Framing, Cultivation, Sleeper Effect, ELM — theory pack", "🎭"),
        ("Digital Power Pack", "Network effects, Echo chamber, Gamification, Scarcity — theory pack", "📡"),
        ("Monetization & Control Pack", "Reciprocity, FUD, Halo Effect, Symbolic Convergence — theory pack", "💎"),
    ]
    for j, (n, d, i) in enumerate(inventory):
        rare = "Tech" in n or "Module" in n or "Pack" in n or "Upgrade" in n or "Unlock" in n or "Bundle" in n
        add(n, d, "inventory", 55 + j * 8, i, "rare" if rare else "common")

    # Extra 40+ for 100+ total: Valued Seller's Choice, Game Time, Boosters
    for j in range(1, 15):
        add(f"Valued Seller's Choice #{j}", "Curated pick from valued sellers", "premium", 150 + j * 10, "🏅", "rare")
    for j in range(1, 15):
        add(f"Game Time +{j * 15}m", f"Extra {j * 15} min game session", "boosts", 20 + j * 2, "⏱️", "common")
    for j in range(1, 15):
        add(f"Booster Pack #{j}", "Assorted boosters pack", "boosts", 40 + j * 3, "📦", "common")

    # Super stack inventory expansion: large, structured inventory set.
    stack_lines = [
        ("Conversion Engine", "AI-assisted conversion module", "📈"),
        ("Retention Engine", "Lifecycle retention optimization module", "🔁"),
        ("Creative Engine", "Ad + content creative generation module", "🎨"),
        ("Video Factory", "Bulk short-video generation module", "🎬"),
        ("Battle Ops", "Battle readiness and tactical support module", "⚔️"),
        ("Growth Ops", "Cross-channel growth and scaling module", "🚀"),
        ("Commerce Ops", "Shop operations and merchandising module", "🛒"),
        ("Insight Ops", "Performance analytics and diagnostics module", "📊"),
        ("Automation Ops", "Workflow automation and trigger module", "🤖"),
        ("Trust Ops", "Quality, trust, and verification module", "🛡️"),
        ("Monetization Ops", "Offer and pricing optimization module", "💎"),
        ("Premium Vault", "Premium strategic assets module", "🏆"),
    ]
    for line_idx, (line_name, line_desc, icon) in enumerate(stack_lines, start=1):
        for tier in range(1, 11):
            add(
                f"{line_name} Pack T{tier}",
                f"{line_desc} tier {tier} with scalable stack bonuses",
                "inventory",
                120 + (line_idx * 14) + (tier * 22),
                icon,
                "legendary" if tier >= 8 else "rare",
            )

    add(
        "Super Stack Inventory Bundle",
        "One-click bundle for advanced inventory stacking and growth operations",
        "premium",
        4500,
        "🧱",
        "legendary",
    )
    add("Super Stack Core", "Core entitlement for inventory super-stack bundle", "inventory", 1200, "🧱", "legendary")
    add("Conversion Stack Pack", "Stacked conversion optimization assets", "inventory", 420, "📈", "rare")
    add("Retention Stack Pack", "Stacked retention optimization assets", "inventory", 420, "🔁", "rare")
    add("Creative Stack Pack", "Stacked creative studio assets", "inventory", 420, "🎨", "rare")
    add("Video Stack Pack", "Stacked video pipeline assets", "inventory", 420, "🎬", "rare")
    add("Battle Stack Pack", "Stacked battle operations assets", "inventory", 390, "⚔️", "rare")
    add("Growth Stack Pack", "Stacked growth operations assets", "inventory", 440, "🚀", "rare")
    add("Commerce Stack Pack", "Stacked commerce operations assets", "inventory", 440, "🛒", "rare")
    add("Insight Stack Pack", "Stacked analytics and diagnostics assets", "inventory", 440, "📊", "rare")
    add("Automation Stack Pack", "Stacked workflow automation assets", "inventory", 440, "🤖", "rare")
    add("Trust Stack Pack", "Stacked trust and quality assets", "inventory", 390, "🛡️", "rare")
    add("Premium Vault Stack", "Stacked premium strategic assets", "inventory", 980, "🏆", "legendary")

    # --- Seasonal themes + theme-tied boost & game time (append-only; keeps earlier shop-* ids stable) ---
    _wave_tags = ["seasonal_theme", "shop_wave_v5", "media_priority"]
    seasonal_theme_pack = [
        ("Spring Bloom", "Fresh spring UI palette — soft greens, petals, light rain glass", "🌸"),
        ("Summer Solaris", "Bright summer accents — gold, sky blue, heat shimmer", "☀️"),
        ("Autumn Ember", "Warm copper & amber leaves, cozy dusk", "🍂"),
        ("Winter Frost", "Ice-blue glass, frost edges, aurora hints", "❄️"),
        ("Aurora Borealis", "Northern lights shimmer across panels & nav", "🌌"),
        ("Crimson Night", "Deep red noir with subtle neon trim", "🌑"),
        ("Sage Matrix", "Matrix-style green code rain & terminal HUD", "🟩"),
        ("Coral Reef", "Teal bioluminescence & coral depth", "🪸"),
        ("Desert Mirage", "Dusk violet dunes & heat haze", "🏜️"),
        ("Cherry Blossom", "Soft pink sakura, lantern glow, calm UI", "🌺"),
        ("Midnight Velvet", "Luxury purple velvet with gold filigree", "🎩"),
    ]
    for n, d, icon in seasonal_theme_pack:
        add(
            n,
            d,
            "themes",
            72 + idx * 2,
            icon,
            "legendary" if idx % 5 == 0 else ("epic" if idx % 3 == 0 else "rare"),
            tags=_wave_tags,
        )

    season_boosters = [
        ("Spring Surge Booster 2h", "Seasonal: +18% XP & activity — spring bloom event (2 hours)", "🌸"),
        ("Solstice Blaze Booster 4h", "Seasonal: +22% generation points — summer solstice (4 hours)", "☀️"),
        ("Harvest Moon Booster 3h", "Seasonal: +25% quest rewards — autumn harvest (3 hours)", "🍂"),
        ("Winter Veil Booster 6h", "Seasonal: +15% battle & skill — winter veil (6 hours)", "❄️"),
        ("Equinox Balance Pack 24h", "Seasonal: mild boosts to all point types — equinox (24 hours)", "⚖️"),
    ]
    for n, d, icon in season_boosters:
        add(n, d, "boosts", 48 + idx * 3, icon, "epic", tags=["season_booster", "shop_wave_v5", "media_priority"])

    theme_synergy_boosts = [
        ("Aurora Synergy Booster 90m", "Synergy with Aurora Borealis theme — brighter FX & +XP pulse", "🌌"),
        ("Matrix Pulse Booster 1h", "Synergy with Sage Matrix — snappier HUD micro-feedback", "🟩"),
        ("Velvet Rush Booster 2h", "Synergy with Midnight Velvet — premium progression tick", "🎩"),
        ("Coral Current Booster 2h", "Synergy with Coral Reef — calmer focus, +activity", "🪸"),
        ("Crimson Edge Booster 1h", "Synergy with Crimson Night — contrast pop & +battle", "🌑"),
        ("Mirage Drift Booster 90m", "Synergy with Desert Mirage — exploration bonus", "🏜️"),
    ]
    for n, d, icon in theme_synergy_boosts:
        add(n, d, "boosts", 52 + idx * 3, icon, "rare", tags=["theme_synergy", "shop_wave_v5", "media_priority"])

    theme_game_time = [
        ("Theme Session +45m — Seasonal Pass", "Extra play time while any seasonal wave-v5 theme is equipped", "⏱️"),
        ("Theme Session +90m — Aurora Pack", "Stacked time when Aurora Borealis theme is active", "⏱️"),
        ("Theme Session +2h — Matrix Session", "Long session for Matrix / terminal HUD themes", "⏱️"),
        ("Theme Weekend Bridge +12h", "Bridge session across weekend — pairs with seasonal boosters", "🎫"),
    ]
    for n, d, icon in theme_game_time:
        add(n, d, "boosts", 40 + idx * 4, icon, "rare", tags=["theme_gametime", "shop_wave_v5", "media_priority"])

    # Dynamic "best agent for sale" offer (skipped during DB migrations — avoids loading the app)
    if include_dynamic_offers:
        try:
            from backend.services.agent_skillset import agent_skillset
            best = agent_skillset.get_best_agent_for_sale()
            if best:
                items.append({
                    "id": "shop-best-agent-offer",
                    "name": f"Best Agent License: {best.get('name', 'Elite Agent')}",
                    "description": (
                        f"Top performer with level {best.get('level', 1)}, "
                        f"sales power {best.get('sales_skill_power_total', 0)}, "
                        f"battle power {best.get('battle_skill_power_total', 0)}."
                    ),
                    "category": "premium",
                    "price": 1500 + int(best.get('level', 1)) * 100,
                    "icon": "🤖",
                    "rarity": "legendary",
                    "agent_offer": best,
                })
        except Exception:
            pass

    # Tabletop-inspired themes (stable ids; append-only)
    add(
        "Magic: The Gathering",
        "Mana gems, duels, and spell-slinging chrome for your UI — tabletop CCG-inspired look. Fan tribute; not affiliated with Wizards of the Coast.",
        "themes",
        198,
        "🃏",
        "legendary",
        tags=["tabletop", "tcg", "mtg", "shop_wave_v6"],
        item_id="theme-magic-the-gathering",
    )
    add(
        "D&D",
        "Dungeon crawl chrome for your UI — dragons, polyhedral dice, maps, and scroll energy (former D6D line folded in). Fan tribute inspired by Dungeons & Dragons; not affiliated with Wizards of the Coast.",
        "themes",
        198,
        "🐉",
        "legendary",
        tags=["tabletop", "trpg", "dnd", "d6", "dice", "shop_wave_v6"],
        item_id="theme-dnd",
    )
    add(
        "Mafia",
        "Noir smoke, pinstripes, and low-lit backroom UI — cinematic organized-crime aesthetic (generic tribute; not an endorsement of real-world crime).",
        "themes",
        175,
        "🎩",
        "epic",
        tags=["cinema", "noir", "mafia", "shop_wave_v6"],
        item_id="theme-mafia",
    )
    add(
        "AI Core",
        "Neural lattice, glass HUD, and copilot glow — futurist AI workspace chrome for panels and nav.",
        "themes",
        175,
        "🤖",
        "epic",
        tags=["ai", "futurist", "copilot", "shop_wave_v6"],
        item_id="theme-ai-core",
    )
    add(
        "Christmas",
        "Pine, ribbon, frost glass, and warm lights — seasonal holiday UI theme.",
        "themes",
        120,
        "🎄",
        "rare",
        tags=["seasonal", "holiday", "christmas", "shop_wave_v6"],
        item_id="theme-christmas",
    )
    add(
        "Home Base",
        "Cozy desk lamp, wood tones, and calm neutrals — home office / studio feel for your UI.",
        "themes",
        120,
        "🏠",
        "rare",
        tags=["home", "workspace", "cozy", "shop_wave_v6"],
        item_id="theme-home-base",
    )

    # Monthly themes: one for each month (append-only)
    monthly_theme_pack = [
        ("January Aurora", "Crisp arctic glow and clean new-year energy for the UI.", "🧊"),
        ("February Velvet Hearts", "Soft velvet reds and warm highlights for a romantic winter mood.", "💘"),
        ("March Clover Rain", "Fresh rain, clover greens, and early-spring contrast.", "☘️"),
        ("April Blossom Rain", "Pastel blossom tones with rainy spring window light.", "🌸"),
        ("May Meadow", "Bright meadow greens with long-day calm and floral accents.", "🌿"),
        ("June Solstice", "Sunlit gold and sky tones inspired by midsummer evenings.", "🌞"),
        ("July Fireworks", "Neon night sky with festive spark trails and bold contrast.", "🎆"),
        ("August Sunset Coast", "Warm coastal dusk palette with amber and ocean haze.", "🏖️"),
        ("September Harvest Gold", "Harvest fields, warm amber, and structured autumn focus.", "🌾"),
        ("October Midnight Ember", "Spooky ember glow, moonlit shadows, and noir-orange accents.", "🎃"),
        ("November Hearth", "Cozy hearth browns, wool textures, and low-light comfort.", "🪵"),
        ("December Snowlight", "Snow glow, festive lights, and winter-glass shimmer.", "❄️"),
    ]
    month_ids = [
        "theme-january", "theme-february", "theme-march", "theme-april", "theme-may", "theme-june",
        "theme-july", "theme-august", "theme-september", "theme-october", "theme-november", "theme-december",
    ]
    for m_i, (name, desc, icon) in enumerate(monthly_theme_pack):
        add(
            name,
            desc,
            "themes",
            130 + (m_i % 4) * 10,
            icon,
            "rare" if m_i < 8 else "epic",
            tags=["monthly_theme", "shop_wave_v7", "calendar_theme"],
            item_id=month_ids[m_i],
        )

    # Profile MN2 "5-day" wallet monitor (UTC bars) — thematic shop tie-ins (append-only)
    add(
        "5D Monitor — Dual-Bar Pro",
        "Tie-in flair for the Profile MN2 5-day chart (per-day in/out bars). Cosmetic-telemetry vibe; does not change on-chain balances.",
        "tech",
        140,
        "📊",
        "rare",
        tags=["mn2_5d", "profile_wallet", "wallet_monitor"],
        item_id="mn2-5d-dual-bar-pro",
    )
    add(
        "5D Monitor — UTC Rail Skin",
        "Skin pack language for UTC midnight alignment on the 5-day wallet strip labels.",
        "cosmetic",
        95,
        "🕛",
        "rare",
        tags=["mn2_5d", "profile_wallet", "wallet_monitor"],
        item_id="mn2-5d-utc-rail-skin",
    )
    add(
        "5D Monitor — Net Flow Pulse 24h",
        "24h UI pulse that highlights net MN2 direction on your next Profile refresh (stacks narratively with other boosts).",
        "boosts",
        110,
        "📈",
        "rare",
        tags=["mn2_5d", "profile_wallet", "wallet_monitor"],
        item_id="mn2-5d-net-flow-24h",
    )
    add(
        "5D Monitor — Deep Stack Ledger",
        "Ledger-styled inventory ribbon echoing five-day depth on the MN2 card (read-only presentation token).",
        "inventory",
        130,
        "📒",
        "rare",
        tags=["mn2_5d", "profile_wallet", "wallet_monitor"],
        item_id="mn2-5d-deep-stack-ledger",
    )
    add(
        "5D Monitor — Withdrawal Beacon",
        "Reminder token: pair with the 5-day chart before MN2 withdraw — emphasizes safety checks on Profile.",
        "tech",
        125,
        "📡",
        "rare",
        tags=["mn2_5d", "profile_wallet", "wallet_monitor"],
        item_id="mn2-5d-withdrawal-beacon",
    )

    # ---- Top 25 Legends: flagship numbered collectible series (June 2026 wave) ----
    # 25 ranked, escalating items spanning every MasterNoder surface. Coin-priced so
    # they work with coins / in-wallet MN2 / on-chain MN2 / PayPal and earn loyalty.
    top25_series = [
        ("Genesis Node Sigil", "Founding-block sigil — proof you were here from the start.", "🌱"),
        ("Hunter's First Mark", "Engraved mark for completing your first Hunter contract.", "🎯"),
        ("Star Map Cartographer", "Charter badge for mapping the Star Map 25 frontier.", "🗺️"),
        ("Arena Gladiator Crest", "Crest forged in the weekly Arena.", "🛡️"),
        ("Casino High-Roller Chip", "Solid chip minted for the bold at the tables.", "🎰"),
        ("Lab Pioneer Seal", "Seal of the first experiments in the Lab.", "🔬"),
        ("Agent Commander Insignia", "Insignia for fielding a full agent squad.", "🎖️"),
        ("Quest Vanguard Banner", "Banner carried by the relentless quest-runner.", "🚩"),
        ("Skill Sage Emblem", "Emblem of mastery across the skill trees.", "🧠"),
        ("MN2 Holder's Token", "Token honoring committed MN2 holders.", "🪙"),
        ("Staking Architect Medal", "Medal for engineering a staking strategy.", "🏗️"),
        ("Generation Maestro Reel", "Reel celebrating prolific creators.", "🎬"),
        ("Trophy Hall Keystone", "Keystone for a stacked trophy hall.", "🏆"),
        ("Marketplace Magnate Ledger", "Ledger of a thriving auction trader.", "📒"),
        ("Loyalty Luminary Star", "Star awarded to top loyalty members.", "✨"),
        ("Battle Warlord Pennant", "Pennant of a feared arena warlord.", "⚔️"),
        ("Explorer Voyager Compass", "Compass for charting the deepest sectors.", "🧭"),
        ("Casino Fortune Crown", "Crown for legendary fortune at the tables.", "👑"),
        ("Hunter Apex Trophy", "Apex trophy for the elite Hunter.", "🦅"),
        ("Star Map Sovereign Orb", "Orb radiating control over the Star Map.", "🔮"),
        ("MN2 Whale Monolith", "Monolith reserved for true MN2 whales.", "🐋"),
        ("Eternal Founder Halo", "Halo for the eternal founders' circle.", "😇"),
        ("Mythic Agent Ascendant", "Mark of an ascended, mythic agent operator.", "🛰️"),
        ("Grandmaster Legend Plate", "Plate engraved for grandmasters of the platform.", "🥇"),
        ("Masternoder Sovereign Crown", "The pinnacle: #25 of the Top 25 Legends series.", "💠"),
    ]
    for n, (nm, desc, icon) in enumerate(top25_series, start=1):
        if n <= 10:
            price = 150 + n * 60
        elif n <= 20:
            price = 800 + (n - 10) * 150
        else:
            price = 2500 + (n - 20) * 600
        if n <= 8:
            rarity = "rare"
        elif n <= 16:
            rarity = "epic"
        else:
            rarity = "legendary"
        add(
            f"#{n:02d} {nm}",
            f"{desc} — Top 25 Legends, rank {n} of 25.",
            "top25",
            price,
            icon,
            rarity,
            tags=["top25", "collectible", "series_top25", "limited", f"rank_{n}", "shop_wave_jun2026"],
            item_id=f"top25-{n:02d}",
        )

    # ---- Lab V2.1 hub wave (June 2026): boosters, crypto grants, trophy packs ----
    lab_wave_v21 = [
        ("Lab Hub Access Token", "Unlocks full Lab V2.1 tab navigation and share-card deep links.", "🔬", "lab-hub-v21-token", 85, "rare"),
        ("Lab Research Booster 1h", "+25% lab first-research point bonuses for 1 hour.", "⚡", "lab-booster-1h", 45, "common"),
        ("Lab Research Booster 6h", "+25% lab first-research point bonuses for 6 hours.", "⚡", "lab-booster-6h", 120, "rare"),
        ("Lab AI Copilot Pass 24h", "AI copilot recommendations and agent refine priority for 24h.", "🤖", "lab-ai-copilot-24h", 150, "rare"),
        ("Lab Systems Audit Kit", "One-click systems recheck badge + profile logbook stamp.", "⚙️", "lab-systems-audit-kit", 65, "common"),
        ("Lab Idea Board Premium", "Pin extra ideas with reduced cooldown (cosmetic unlock).", "💡", "lab-idea-board-premium", 55, "common"),
        ("Lab Trophy Booster Pack", "Bundle: Pulse Runner + Deep Scan Pioneer trophy progress boost.", "🏆", "lab-trophy-booster-pack", {"game_points": 80, "trophy_points": 20}, "epic"),
        ("Lab Crypto Reward Pack S", "Small MN2 research grant — credited via shop MN2 flow.", "🪙", "lab-crypto-reward-s", {"mn2": 0.01}, "rare"),
        ("Lab Crypto Reward Pack M", "Medium MN2 research grant for chapter milestones.", "🪙", "lab-crypto-reward-m", {"mn2": 0.05}, "epic"),
        ("Lab Crypto Reward Pack L", "Large MN2 sovereign research grant.", "🪙", "lab-crypto-reward-l", {"mn2": 0.15}, "legendary"),
        ("Chapter V Unlock Bundle", "Cosmetic bundle celebrating Chapter V research rail.", "🧠", "lab-chapter5-bundle", 220, "epic"),
        ("Lab Co-Tech Accelerator", "Reduces perceived co-tech draft spacing (flair item).", "🧪", "lab-cotech-accelerator", 90, "rare"),
        ("Lab Roundtable Chime", "Unlock roundtable sound palette on 4D monitor.", "🪑", "lab-roundtable-chime", 40, "common"),
        ("Lab Explorer Deep Scan Duo", "Bundle: exploration + deep scan flair badges.", "🛰️", "lab-explore-deep-duo", 110, "rare"),
        ("Lab Sovereign Seal", "Collectible seal for Sovereign Research Core researchers.", "👑", "lab-sovereign-seal", 350, "legendary"),
    ]
    for nm, desc, icon, iid, price, rarity in lab_wave_v21:
        add(nm, desc, "lab", price, icon, rarity, tags=["lab", "lab_wave_v21", "shop_wave_jun2026"], item_id=iid)

    return items
