$ErrorActionPreference = "Continue"
$RepoRoot = "c:\Users\jonkh\UsecaseSampler\Masternoder.dk"
$Wt = Join-Path $RepoRoot ".worktrees\pr-split"
$BackupSha = "8d2fb58c5c476eaacbba173ba8073e2f2eca55a6"
$SourceBranch = "cursor/monetized-content-crypto"
Set-Location $Wt

function Checkout-SliceFiles {
    param([string[]]$Files)
    $ok = @()
    foreach ($f in $Files) {
        if ([string]::IsNullOrWhiteSpace($f)) { continue }
        git checkout $BackupSha -- $f 2>$null | Out-Null
        if ($LASTEXITCODE -ne 0) {
            git checkout $SourceBranch -- $f 2>$null | Out-Null
        }
        if ($LASTEXITCODE -eq 0) { $ok += $f }
    }
    return $ok
}

function New-PrSlice {
    param(
        [string]$Branch,
        [string]$Title,
        [string]$Body,
        [string[]]$Files
    )
    Write-Host "`n=== $Branch ===" -ForegroundColor Cyan
    git checkout main 2>&1 | Out-Null
    git branch -D $Branch 2>$null | Out-Null
    git checkout -b $Branch 2>&1 | Out-Null
    $checked = Checkout-SliceFiles -Files $Files
    if ($checked.Count -eq 0) {
        Write-Warning "No files checked out for $Branch"
        return $null
    }
    git add -- $checked
    $stat = git diff --cached --stat
    if (-not $stat) {
        Write-Warning "Nothing staged for $Branch"
        return $null
    }
    git commit -m $Title 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "commit failed for $Branch" }
    git push -u origin $Branch --force 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "push failed for $Branch" }
    $url = gh pr create --base main --head $Branch --title $Title --body $Body 2>&1
    Write-Host $url
    return $url
}

$pr1Files = @(
    "backend/services/mn2_masternode_service.py",
    "backend/services/mn2_masternode_hosting_service.py",
    "backend/services/mn2_rpc_client.py",
    "backend/routes/mn2_masternode_routes.py",
    "backend/routes/mn2_staking_routes.py",
    "config/masternoder2.conf.example",
    "cron/mn2_masternode_provision.sh",
    "data/mn2_masternode_config.json",
    "scripts/mn2_ensure_rpc_conf.sh",
    "scripts/mn2_fix_config_permissions.sh",
    "scripts/mn2_fix_daemon_privkey.sh",
    "scripts/mn2_hotfix_alias_provision_server.sh",
    "scripts/mn2_repair_masternode_conf.sh",
    "scripts/mn2_fleet_autostart.sh",
    "scripts/mn2_start_masternode.py",
    "scripts/mn2_masternode_fleet_ops_remote.py",
    "scripts/mn2_check_activetime_public.py",
    "scripts/mn2_test_ping_live.py",
    "scripts/mn2_patch_rpc_retries.sh",
    "scripts/mn2_masternode_reinstall_remote.py",
    "scripts/mn2_masternode_start_fleet_remote.py",
    "scripts/mn2_next_ops_remote.py",
    "scripts/mn2_unlock_collateral.sh",
    "systemd/mn2-fleet-autostart.service.example",
    "tests/unit/test_mn2_masternode_rpc.py",
    "docs/MN2_OPS.md",
    "docs/MN2_DAEMON_MULTI_PING_UPGRADE.md"
)

$pr2Files = @(
    "backend/services/mn2_chainz.py",
    "backend/services/mn2_explorer_data.py",
    "explorer/index.html",
    "static/js/mn2-crypto-hub.js",
    "static/js/mn2-explorer-overview.js",
    "static/css/mn2-crypto-hub.css",
    "scripts/fix_explorer_subdomains_remote.py"
)

$pr3Files = @("scripts/deploy.py", "deploy.py")

$pr4Files = @(
    "data/monetization_config.json",
    "backend/services/monetization_config_service.py",
    "backend/services/shop_checkout_promo_service.py",
    "scripts/shop_v4_production_smoke.py",
    "scripts/mn_hosting_coins_purchase_test_live.py",
    "hosting/index.html"
)

$pr5Files = @(
    "docs/MN2_TODO.md",
    "docs/MN2_RELEASE_BUILD.md",
    "docs/PLATFORM_TODO.md",
    ".env.example"
)

$pr6Files = @(
    "backend/routes/all_page_routes.py",
    "backend/routes/compendium_routes.py",
    "backend/routes/podcast_routes.py",
    "backend/services/compendium_crypto_rewards_service.py",
    "backend/services/podcast_agent_service.py",
    "backend/services/podcast_audio_service.py",
    "backend/services/podcast_crypto_rewards_service.py",
    "backend/services/podcast_encode_service.py",
    "backend/services/podcast_expansions_service.py",
    "backend/services/podcast_service.py",
    "backend/services/podcast_social_service.py",
    "data/podcast_agent_projects.json",
    "data/podcast_channels.json",
    "data/podcast_crypto_daily.json",
    "data/podcast_customers.json",
    "data/podcast_episodes.json",
    "data/podcast_portal_lines.json",
    "data/podcast_social.json",
    "docs/PODCAST.md",
    "podcast",
    "static/css/podcast-hub.css",
    "static/css/podcast-portal-strip.css",
    "static/js/podcast-hub.js",
    "static/js/podcast-portal-lines.js",
    "static/audio",
    "tests/unit/test_compendium_crypto_rewards.py",
    "tests/unit/test_podcast.py",
    "tests/unit/test_podcast_routes.py"
)

$pageShellIndexes = @(
    "academic-perspective/index.html","advanced_calculator/index.html","agent_support/index.html",
    "agents/index.html","aggregator/index.html","battle/index.html","battlegrounds/index.html",
    "beta_testing/index.html","champions-league/index.html","chat/index.html","compendium/index.html",
    "customers/index.html","danish-divine-tech-tree/index.html","dashboard/agents_control/index.html",
    "dashboard/master_control/index.html","debugger/index.html","editor/index.html","gallery/index.html",
    "game/index.html","generator/index.html","index.html","lab/index.html","metal/index.html",
    "milkyway/index.html","news/index.html","profile/index.html","quests/index.html",
    "rights-law/index.html","social-monitor/index.html","social/index.html","starmap25/index.html",
    "theme-points/index.html","theme_premium/index.html","time-achievement-guides/index.html",
    "trophies/index.html","user/index.html","victory-tech-tree/index.html"
)

$pr7Files = @(
    "static/css/page-shell.css",
    "scripts/apply-page-shell-css.py",
    "scripts/fix-head-link-order.py",
    "static/js/navigation-toolbar.js"
) + $pageShellIndexes

$allSliceFiles = [System.Collections.Generic.HashSet[string]]::new([string[]]($pr1Files + $pr2Files + $pr3Files + $pr4Files + $pr5Files + $pr6Files + $pr7Files))

$excludePatterns = @(
    "^\.pytest", "^dist/", "^data/mn2_ledger\.json$", "^data/chat/",
    "^data/todos/", "^\.pytest_tmp/", "camgirls_payout", "camgirls_performers_production",
    "generator_api_keys", "mn2_copy_trading", "rulebook_v16", "rulebook_v3_2", "social_networks"
)

$branchDiff = git diff main $SourceBranch --name-only
$pr8Files = @()
foreach ($f in $branchDiff) {
    if ($allSliceFiles.Contains($f)) { continue }
    $skip = $false
    foreach ($pat in $excludePatterns) {
        if ($f -match $pat) { $skip = $true; break }
    }
    if (-not $skip) { $pr8Files += $f }
}

$results = @()
$results += New-PrSlice -Branch "pr/mn2-fleet-provision-ops" -Title "fix(mn2): fleet provisioning, RPC ops, and hosting alias repair" -Body "## Summary`n- MN2 masternode fleet provisioning fixes (alias sanitization, config perms, RPC timeouts)`n- Ops scripts for fleet autostart, activetime checks, and repair`n`n## Test plan`n- [ ] pytest tests/unit/test_mn2_masternode_rpc.py`n- [ ] Run mn2_check_activetime_public.py against prod" -Files $pr1Files

$results += New-PrSlice -Branch "pr/mn2-explorer-hub" -Title "fix(mn2): explorer performance and masternodes tab UI" -Body "## Summary`n- Fast path for chain overview; fix masternodes table rendering`n- Nginx subdomain fix script for camgirls explorer ajax`n`n## Test plan`n- [ ] Load explorer masternodes tab`n- [ ] Verify network overview loads under 5s" -Files $pr2Files

$results += New-PrSlice -Branch "pr/deploy-tooling" -Title "fix(deploy): multi-manifest deploy and ask-pass SSH" -Body "## Summary`n- Merge multiple deploy manifests in scripts/deploy.py`n- Root deploy.py connect_deploy_ssh with --ask-pass`n`n## Test plan`n- [ ] python scripts/deploy.py mn2_staking static_pages --upload-only --ask-pass (dry run)" -Files $pr3Files

$results += New-PrSlice -Branch "pr/mn2-hosting-shop" -Title "fix(shop): MN2 hosting checkout config and live smoke scripts" -Body "## Summary`n- Monetization config collateral text; hosting page updates`n- Shop smoke and coins-rail MN hosting purchase test scripts`n`n## Test plan`n- [ ] shop_v4_production_smoke.py`n- [ ] mn_hosting_coins_purchase_test_live.py with MN2_TEST_SKIP_PURCHASE=1" -Files $pr4Files

$results += New-PrSlice -Branch "pr/docs-mn2-status" -Title "docs(mn2): ops status, release build, and env example" -Body "## Summary`n- Update MN2_TODO, MN2_RELEASE_BUILD, PLATFORM_TODO`n- Document RPC env vars in .env.example`n`n## Test plan`n- [ ] Review doc accuracy vs prod fleet state" -Files $pr5Files

$results += New-PrSlice -Branch "pr/podcast-hub" -Title "feat(podcast): podcast hub routes, services, and UI" -Body "## Summary`n- New podcast backend services, data, pages, and tests`n`n## Test plan`n- [ ] pytest tests/unit/test_podcast*.py" -Files $pr6Files

$results += New-PrSlice -Branch "pr/platform-page-shell" -Title "style(ui): shared page-shell CSS across site pages" -Body "## Summary`n- Add page-shell.css and apply across platform index pages`n- Navigation toolbar alignment`n`n## Test plan`n- [ ] Spot-check 3 pages for layout regressions" -Files $pr7Files

Write-Host "`n=== pr/monetization-crypto-core ($($pr8Files.Count) files) ===" -ForegroundColor Cyan
git checkout main 2>&1 | Out-Null
git branch -D pr/monetization-crypto-core 2>$null | Out-Null
git checkout -b pr/monetization-crypto-core 2>&1 | Out-Null
$batchSize = 100
for ($i = 0; $i -lt $pr8Files.Count; $i += $batchSize) {
    $batch = $pr8Files[$i..([Math]::Min($i + $batchSize - 1, $pr8Files.Count - 1))]
    git checkout $SourceBranch -- @batch 2>$null
}
git add -A
git diff --cached --quiet
if ($LASTEXITCODE -ne 0) {
    git commit -m "feat: monetization crypto platform core (casino, camgirls, agents, staking market)" | Out-Null
    git push -u origin pr/monetization-crypto-core --force 2>&1 | Out-Null
    $url8 = gh pr create --base main --head pr/monetization-crypto-core --title "feat: monetization crypto platform core" --body "## Summary`n- Monetized content catalog, casino, camgirls, agents, MN2 staking/market, tier D`n- Remaining committed work from cursor/monetized-content-crypto`n`n## Test plan`n- [ ] Run focused unit tests for touched modules`n- [ ] Smoke test shop, casino, camgirls flows" 2>&1
    Write-Host $url8
    $results += $url8
} else {
    Write-Warning "PR8 empty"
}

Write-Host "`n=== DONE ===" -ForegroundColor Green
$results | ForEach-Object { Write-Host $_ }
