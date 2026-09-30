# MasterNoder2 v1.2.3.0 — release & daemon upgrade

**Status (2026-06-23):** Source merged ([PR #1](https://github.com/jonK341/MasterNoder2/pull/1)).  
**Git tag `v1.2.3.0`:** published · **GitHub release + tarball:** live ([v1.2.3.0](https://github.com/jonK341/MasterNoder2/releases/tag/v1.2.3.0)).  
**Production daemon:** v1.2.3.0-61caddb applied 2026-06-20 (`mn2_daemon_upgrade_remote.py --apply` + `--verify-post` PASS).  
**Latest site deploy (2026-06-22):** `deploy.py mn2_staking` + `static_pages` + `mn2_env` + `apply_updates.py --ask-pass` — see [MN2_TODO.md](MN2_TODO.md).

Production daemon path: `/opt/masternoder2d/masternoder2d` · datadir `/var/www/html/config` · systemd `masternoder2d`.

---

## Quick status

```powershell
python scripts/mn2_release_status.py
python scripts/mn2_daemon_upgrade_remote.py --check-release
```

---

## Pipeline (3 steps)

### 1 — Build on Linux, WSL, or **production server**

**Windows without WSL** — build on the Linux server (auto-installs `autoconf`, boost, ssl via apt):

```powershell
python scripts/mn2_build_release_remote.py --ask-pass --publish --draft
```

Uses **depends** by default (bundled OpenSSL — avoids `unsupported SSL version` on OpenSSL 3 hosts). First run ~30–60 min. Do **not** build on Windows native (`bash` / `configure` will fail).

Fast path (OpenSSL 3 OK): add `--fast` — passes `--with-unsupported-ssl` to configure (~5–15 min, less portable).

Preferred for production releases: depends build (no `--fast`) after [PR #34](https://github.com/jonK341/Masternoder.dk/pull/34) apt dependency fix.

Auto-retry when depends boost fails: add `--auto-fast` (retries once with system libs; skipped when failure is OpenSSL-related).

**WSL or Linux build host** — needs **~2 GB RAM**, `git`, `build-essential`:

```bash
# WSL or Linux build host
cd /path/to/Masternoder.dk
bash scripts/mn2_build_release.sh
```

Output: `/tmp/mn2-build/dist/masternoder2d.tar.gz` (+ `.sha256`, `RELEASE_MANIFEST.json`)

Build is **tag-pinned** (`git checkout v1.2.3.0`), runs **offline smoke tests** (`mn2_build_smoke.sh`), and bundles `masternoder2-tx`.

Faster dev build (not portable): `USE_DEPENDS=0 bash scripts/mn2_build_release.sh` (adds `--with-unsupported-ssl` on OpenSSL 3 hosts)

### Qt wallet builds (v1.3.0.0)

Qt packages are **not** built by the daemon script. Use the Qt pipeline:

```powershell
# Linux Qt on production server (fast / system libs, ~15–30 min)
python scripts/mn2_build_qt_release_remote.py --target linux --fast

# Windows Qt zip (mingw depends cross-compile, ~60–120 min)
python scripts/mn2_build_qt_release_remote.py --target win

# Upload Qt assets to existing v1.3.0.0 GitHub release
python scripts/mn2_publish_release.py --qt-assets --skip-tag
```

WSL or Linux:

```bash
bash scripts/mn2_build_qt_release.sh --target linux   # MasterNoder2-qt-linux.tar.gz
bash scripts/mn2_build_qt_release.sh --target win       # MasterNoder2-qt-win.zip
```

**GCC 15 hosts:** compat patch `docs/patches/mn2-gcc15-httpserver-deque.patch` is applied automatically.

**GitHub Actions:** `.github/workflows/mn2-release-build.yml` — workflow_dispatch with targets `daemon`, `qt-linux`, `qt-win`, or `all`. Set repo secret `MN2_RELEASE_TOKEN` (PAT with `repo` on `jonK341/MasterNoder2`) for cross-repo publish.

### 2 — Publish GitHub release

Requires `gh auth login` with access to `jonK341/MasterNoder2`.

```powershell
# Draft first (recommended)
python scripts/mn2_publish_release.py --tarball dist/masternoder2d.tar.gz --manifest dist/RELEASE_MANIFEST.json --skip-tag --draft

# Verify local assets before upload
python scripts/mn2_publish_release.py --tarball dist/masternoder2d.tar.gz --manifest dist/RELEASE_MANIFEST.json --verify

# Promote draft → published
python scripts/mn2_publish_release.py --tarball dist/masternoder2d.tar.gz --promote
```

(`--skip-tag` when tag `v1.2.3.0` already exists.)

Assets after publish:  
https://github.com/jonK341/MasterNoder2/releases/download/v1.2.3.0/masternoder2d.tar.gz  
https://github.com/jonK341/MasterNoder2/releases/download/v1.2.3.0/RELEASE_MANIFEST.json

### 3 — Upgrade production

**Maintenance window** — stops wallet briefly, backs up `wallet.dat`, swaps binary.

```powershell
python scripts/mn2_daemon_upgrade_remote.py --ask-pass
python scripts/mn2_daemon_upgrade_remote.py --ask-pass --apply
python scripts/mn2_daemon_upgrade_remote.py --ask-pass --verify-post
```

`--apply` verifies tarball + installed binary sha256 from `RELEASE_MANIFEST.json` when the manifest asset exists. Post-checks include `getstakinginfo`, `getnewaddress`, `mnsync`, and `/api/mn2/health`.

---

## What v1.2.3.0 fixes

- **mnsync** MNW deadlock fix (steadier sync / staking health)
- **`getstakinginfo`** RPC alias (app + explorer staking tiles)

---

## Manual build reference

See [MasterNoder2 doc/build-unix.md](https://github.com/jonK341/MasterNoder2/blob/main/doc/build-unix.md).

Release tarball layout (match v1.2.2.0):

```
masternoder2d.tar.gz
├── masternoder2d/
│   ├── masternoder2d      # daemon
│   ├── masternoder2-cli   # RPC client
│   └── masternoder2-tx    # tx tool
└── RELEASE_MANIFEST.json  # git sha, per-binary sha256, tarball sha256
```

---

## Troubleshooting

| Error | Fix |
|--------|-----|
| `unsupported SSL version` | On `--fast`: script passes `--with-unsupported-ssl` — pull latest and retry. **Preferred:** depends build (no `--fast`). Do not build on Windows native. |
| `Failed to build Boost.Build engine` / `boost...stamp_configured` | depends boost bootstrap failed on host. Retry: `python scripts/mn2_build_release_remote.py --ask-pass --fast --publish --draft` or use `--auto-fast` (not when OpenSSL error). |
| `undefined reference to arc4random_addrandom` | `libbsd-dev` + `-lbsd` (in build script). |
| `undefined reference to __gmpz_*` | `libgmp-dev` + `-lgmp`; do not pass `LIBS=` on `make` cmdline (overrides Makefile). |
| `Cannot --apply until v1.2.3.0 release asset exists` | Complete build + publish steps first. |

---

## Do not

- Run `--apply` before the GitHub asset exists (script blocks this)
- Swap binaries during active reindex
- Skip `wallet.dat` backup before upgrade

---

## Related

- [MN2_DAEMON_SETUP.md](MN2_DAEMON_SETUP.md) — install & RPC config
- [MN2_OPS.md](MN2_OPS.md) — scanner, env, reconciliation
- [MN2_UPGRADE_PLAN_v123.md](MN2_UPGRADE_PLAN_v123.md) — full upgrade track
