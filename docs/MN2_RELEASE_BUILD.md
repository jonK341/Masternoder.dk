# MasterNoder2 v1.2.3.0 — release build checklist

Build on a **Linux host** with Qt/toolchain matching production (see `MN2_DAEMON_SETUP.md`).

## Steps

1. Clone [MasterNoder2](https://github.com/jonK341/MasterNoder2) at merged `main` (PR #1 merged).
2. Tag release:

```bash
git tag -a v1.2.3.0 -m "mnsync + getstakinginfo fixes"
git push origin v1.2.3.0
```

3. Build static binary tarball:

```bash
# Project-specific — follow MasterNoder2 README / contrib/gitian or Makefile
make release   # or ./autogen.sh && ./configure && make
tar czf masternoder2d.tar.gz bin/masternoder2d ...
```

4. Attach `masternoder2d.tar.gz` (+ checksums) to GitHub Release **v1.2.3.0**.

5. Apply on production:

```powershell
python scripts/mn2_daemon_upgrade_remote.py --ask-pass --apply
```

6. Verify:

```bash
masternoder2-cli getstakinginfo
masternoder2-cli mnsync
```

## Manual ops (network)

- **Revive 1 masternode** — improves `mnsync` stability and pool minting (see `MN2_OPS.md`).
- **Rotate `DEPLOY_PASS`** in local `.env` after any credential exposure; then non-interactive deploy scripts work without `--ask-pass`.

## Do not

- Swap binaries during active reindex
- Force-push `main` after release tag without ops sign-off
