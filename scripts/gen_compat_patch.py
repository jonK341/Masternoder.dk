#!/usr/bin/env python3
"""Regenerate docs/patches/mn2-daemon-build-compat-modern-host.patch from MasterNoder2."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

BASE_TAG = "v1.2.3.0"
COMPAT_PATHS = [
    "src/httpserver.cpp",
    "src/init.cpp",
    "src/main.cpp",
    "src/miner.cpp",
    "src/net.cpp",
    "src/rpc/protocol.cpp",
    "src/rpc/server.cpp",
    "src/script/script.h",
    "src/torcontrol.cpp",
    "src/util.cpp",
    "src/util.h",
    "src/validationinterface.cpp",
    "src/wallet/wallet.cpp",
    "src/wallet/walletdb.cpp",
]


def run(cmd: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, check=check, text=True, capture_output=True)


def write_utf8_lf(path: Path, content: str) -> None:
    normalized = content.replace("\r\n", "\n").replace("\r", "\n")
    if not normalized.endswith("\n"):
        normalized += "\n"
    path.write_bytes(normalized.encode("utf-8"))


def regenerate(mn2: Path, repo: Path, out: Path, verify: bool = True) -> tuple[int, int, int]:
    multi_ping = repo / "docs/patches/mn2-daemon-v1.3.0-multi-ping.patch"
    if not multi_ping.is_file():
        raise SystemExit(f"missing multi-ping patch: {multi_ping}")
    if not (mn2 / ".git").is_dir():
        raise SystemExit(f"not a git repo: {mn2}")

    run(["git", "checkout", "-f", BASE_TAG], cwd=mn2)
    run(["git", "clean", "-fd"], cwd=mn2)
    run(["git", "apply", str(multi_ping)], cwd=mn2)
    run(["git", "add", "-A"], cwd=mn2)
    multi_tree = run(["git", "write-tree"], cwd=mn2).stdout.strip()

    compat_seed = out if out.is_file() and out.stat().st_size > 0 else None
    embedded = repo / "docs/patches/mn2-daemon-build-compat-modern-host.patch.embed"
    if embedded.is_file():
        # Prefer .embed so new fixes are not dropped when regenerating over a stale .patch.
        compat_seed = embedded
    elif compat_seed is None:
        raise SystemExit(
            "compat patch is empty and no embedded seed; apply GCC/Boost fixes in MN2 then re-run with --from-tree"
        )

    apply = run(["git", "apply", str(compat_seed)], cwd=mn2, check=False)
    if apply.returncode != 0:
        raise SystemExit(f"git apply compat seed failed:\n{apply.stderr}")

    diff = run(["git", "diff", multi_tree, "--", *COMPAT_PATHS], cwd=mn2).stdout
    write_utf8_lf(out, diff)

    file_count = diff.count("diff --git ")
    line_count = len(diff.splitlines())

    check_code = 0
    if verify:
        run(["git", "checkout", "-f", BASE_TAG], cwd=mn2)
        run(["git", "clean", "-fd"], cwd=mn2)
        run(["git", "apply", str(multi_ping)], cwd=mn2)
        check = run(["git", "apply", "--check", str(out)], cwd=mn2, check=False)
        check_code = check.returncode
        if check_code != 0:
            print(check.stderr, file=sys.stderr)

    return line_count, file_count, check_code


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mn2",
        type=Path,
        default=None,
        help="MasterNoder2 source directory (default: REPO_ROOT/external/MasterNoder2)",
    )
    parser.add_argument(
        "--repo",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Masternoder.dk repo root",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output patch path",
    )
    parser.add_argument("--no-verify", action="store_true")
    args = parser.parse_args()

    repo = args.repo.resolve()
    mn2 = (args.mn2 or repo / "external" / "MasterNoder2").resolve()
    out = (args.out or repo / "docs/patches/mn2-daemon-build-compat-modern-host.patch").resolve()

    lines, files, code = regenerate(mn2, repo, out, verify=not args.no_verify)
    print(f"Wrote {out}")
    print(f"files={files} lines={lines} verify_exit={code}")


if __name__ == "__main__":
    main()
