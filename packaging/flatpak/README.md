# MasterNoder2 daemon Flatpak

Wraps the **prebuilt** `masternoder2d` release tarball (no C++ compile inside Flatpak).

```bash
# after scripts/mn2_build_release.sh
bash scripts/mn2_build_flatpak.sh
```

Produces `dk.masternoder.MasterNoder2.flatpak` under `$BUILD_ROOT/dist`.
