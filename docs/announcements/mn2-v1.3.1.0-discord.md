# Discord announcement — MasterNoder2 v1.3.1.0

Generated: 2026-11-10 08:39 UTC
Ready: **False** (missing: MasterNoder2-qt-linux.tar.gz, MasterNoder2-qt-win.zip, QT_RELEASE_MANIFEST.json)
Assets seen: masternoder2d.tar.gz, masternoder2d.tar.gz.sha256, RELEASE_MANIFEST.json

## Embed title

MasterNoder2 v1.3.1.0 downloads

## Embed body

**MasterNoder2 v1.3.1.0 — wallet & daemon downloads (PENDING BUILD)**

Platform UI **9.2.6.5** now paints **on-chain** balance and creates deposit addresses so website users feed the network with real receive paths.

**GitHub release:** https://github.com/jonK341/MasterNoder2/releases/tag/v1.3.1.0
**Asset check:** missing: MasterNoder2-qt-linux.tar.gz, MasterNoder2-qt-win.zip, QT_RELEASE_MANIFEST.json

**Downloads**
• [masternoder2d.tar.gz](https://github.com/jonK341/MasterNoder2/releases/download/v1.3.1.0/masternoder2d.tar.gz)
• [RELEASE_MANIFEST.json](https://github.com/jonK341/MasterNoder2/releases/download/v1.3.1.0/RELEASE_MANIFEST.json)
• [MasterNoder2-qt-linux.tar.gz](https://github.com/jonK341/MasterNoder2/releases/download/v1.3.1.0/MasterNoder2-qt-linux.tar.gz)
• [MasterNoder2-qt-win.zip](https://github.com/jonK341/MasterNoder2/releases/download/v1.3.1.0/MasterNoder2-qt-win.zip)
• [QT_RELEASE_MANIFEST.json](https://github.com/jonK341/MasterNoder2/releases/download/v1.3.1.0/QT_RELEASE_MANIFEST.json)

**Compile (when source updates)**
1. `bash scripts/mn2_build_release.sh` → daemon tarball + `RELEASE_MANIFEST.json`
2. `bash scripts/mn2_build_qt_release.sh` → Linux/Windows Qt + `QT_RELEASE_MANIFEST.json`
3. `python scripts/mn2_publish_release.py --tarball … --manifest … --qt-assets`
4. Re-run this script with `--post` once assets are live.

Site portal: /wallets
Spork gates 112/114 stay OFF until an operator signs them.

## Operator notes

Full release notes live in `scripts/mn2_release_config.py` (`RELEASE_NOTES`).
Do not paste deploy hostnames into this draft.
