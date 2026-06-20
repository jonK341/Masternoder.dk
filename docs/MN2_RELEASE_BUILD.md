# MasterNoder2 v1.2.3.0 — release & daemon upgrade

**Status (2026-06-17):** Source merged ([PR #1](https://github.com/jonK341/MasterNoder2/pull/1)).  
**Git tag `v1.2.3.0`:** exists · **GitHub release + tarball:** not published yet (latest release: v1.2.2.0).

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

Fast path (may fail on Ubuntu 22.04+): add `--fast`

**WSL or Linux build host** — needs **~2 GB RAM**, `git`, `build-essential`:

```bash
# WSL or Linux build host
cd /path/to/Masternoder.dk
bash scripts/mn2_build_release.sh
```

Output: `/tmp/mn2-build/dist/masternoder2d.tar.gz` (+ `.sha256`, `RELEASE_MANIFEST.json`)

Build is **tag-pinned** (`git checkout v1.2.3.0`), runs **offline smoke tests** (`mn2_build_smoke.sh`), and bundles `masternoder2-tx`.

Faster dev build (not portable): `USE_DEPENDS=0 bash scripts/mn2_build_release.sh`

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
| `unsupported SSL version` | Do not build on Windows; use remote script (depends build). Avoid `--fast`. |
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
