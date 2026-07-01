#!/usr/bin/env python3
"""Build MasterNoder2 Qt wallet packages on the production Linux server.

Usage:
  python scripts/mn2_build_qt_release_remote.py
  python scripts/mn2_build_qt_release_remote.py --target linux --fast --publish
  python scripts/mn2_build_qt_release_remote.py --target win --publish --draft
  python scripts/mn2_build_qt_release_remote.py --target all --auto-fast
"""
from __future__ import annotations

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

try:
    import dotenv

    dotenv.load_dotenv(os.path.join(ROOT, ".env"))
except Exception:
    pass

import paramiko
from deploy_ssh_env import connect_deploy_ssh, deploy_host, deploy_user
from mn2_release_config import BASE_TAG, PATCH_REL, TARGET_VERSION

BUILD_ROOT = "/tmp/mn2-build"
LOCAL_DIST = os.path.join(ROOT, "dist")
REMOTE_DIST = f"{BUILD_ROOT}/dist"
REMOTE_PATCH = "/tmp/mn2-daemon-v1.3.0-multi-ping.patch"


def upload_script(ssh, local_name: str, remote_name: str) -> str:
    local_path = os.path.join(ROOT, "scripts", local_name)
    with open(local_path, "r", encoding="utf-8") as f:
        body = f.read()
    sftp = ssh.open_sftp()
    remote_path = f"/tmp/{remote_name}"
    with sftp.file(remote_path, "w") as rf:
        rf.write(body)
    sftp.chmod(remote_path, 0o755)
    sftp.close()
    return remote_path


def upload_patch(ssh) -> str:
    local_path = os.path.join(ROOT, PATCH_REL)
    if not os.path.isfile(local_path):
        raise SystemExit(f"Patch not found: {local_path}")
    sftp = ssh.open_sftp()
    with sftp.file(REMOTE_PATCH, "w") as rf:
        with open(local_path, "rb") as lf:
            rf.write(lf.read())
    sftp.close()
    return REMOTE_PATCH


REMOTE_PATCH_DIR = "/tmp/mn2-patches"


def upload_patches(ssh) -> str:
    os.makedirs_local = os.path.join(ROOT, "docs", "patches")
    sftp = ssh.open_sftp()
    try:
        try:
            sftp.mkdir(REMOTE_PATCH_DIR)
        except OSError:
            pass
        for name in os.listdir(os.makedirs_local):
            if not name.endswith(".patch"):
                continue
            local_path = os.path.join(os.makedirs_local, name)
            remote_path = f"{REMOTE_PATCH_DIR}/{name}"
            with sftp.file(remote_path, "w") as rf:
                with open(local_path, "rb") as lf:
                    rf.write(lf.read())
            print(f"Uploaded patch -> {remote_path}")
    finally:
        sftp.close()
    return REMOTE_PATCH_DIR


def main() -> int:
    parser = argparse.ArgumentParser(description=f"Remote MN2 Qt {TARGET_VERSION} build")
    parser.add_argument("--ask-pass", action="store_true")
    parser.add_argument(
        "--target",
        choices=("linux", "win", "all"),
        default="linux",
        help="linux=MasterNoder2-qt-linux.tar.gz, win=MasterNoder2-qt-win.zip",
    )
    parser.add_argument("--publish", action="store_true", help="Upload Qt assets to GitHub release after download")
    parser.add_argument("--draft", action="store_true", help="With --publish: ensure release is draft first")
    parser.add_argument("--fast", action="store_true", help="System libs (linux only; USE_DEPENDS=0)")
    parser.add_argument("--auto-fast", action="store_true", help="Retry linux build with --fast if depends fails")
    parser.add_argument("--skip-deps", action="store_true")
    parser.add_argument("--jobs", type=int, default=2)
    parser.add_argument("--branch", default="")
    parser.add_argument("--no-patch", action="store_true")
    args = parser.parse_args()

    if args.target == "win" and args.fast:
        print("Windows Qt cross-compile requires depends (no --fast).", file=sys.stderr)
        return 2

    pw = None
    if args.ask_pass:
        from deploy_ssh_env import require_deploy_pass

        pw = require_deploy_pass(force_prompt=True)
    ssh, auth_method, _ = connect_deploy_ssh(password=pw)
    print(f"Connected to {deploy_user()}@{deploy_host()} via {auth_method}")

    remote_build = upload_script(ssh, "mn2_build_qt_release.sh", "mn2_build_qt_release.sh")
    patch_dir = upload_patches(ssh)
    patch_file = f"{patch_dir}/mn2-daemon-v1.3.0-multi-ping.patch"
    if args.no_patch or args.branch:
        patch_file = ""
    elif not os.path.isfile(os.path.join(ROOT, PATCH_REL)):
        patch_file = ""

    def run_remote(use_fast: bool) -> tuple[int, str]:
        use_dep = "0" if use_fast else "1"
        install_deps = "0" if args.skip_deps else "1"
        branch = args.branch.replace("'", "")
        cmd = (
            f"export BUILD_ROOT={BUILD_ROOT} JOBS={args.jobs} USE_DEPENDS={use_dep} "
            f"INSTALL_BUILD_DEPS={install_deps} VERSION={TARGET_VERSION} BASE_TAG={BASE_TAG} "
            f"PATCH_FILE='{patch_file}' CHECKOUT_BRANCH='{branch}' TARGET={args.target} "
            f"COMPAT_PATCH_DIR={patch_dir}; "
            f"bash {remote_build} --target {args.target}"
        )
        print(
            f"=== Remote Qt build {TARGET_VERSION} target={args.target} "
            f"(USE_DEPENDS={use_dep}) — may take 60–120 min ===\n"
        )
        _, stdout, stderr = ssh.exec_command(cmd, get_pty=True, timeout=14400)
        exit_code = stdout.channel.recv_exit_status()
        out = stdout.read().decode(errors="replace")
        err = stderr.read().decode(errors="replace")
        print(out)
        if err.strip():
            print(err, file=sys.stderr)
        return exit_code, out + err

    exit_code, combined = run_remote(args.fast)
    if exit_code != 0 and args.auto_fast and not args.fast and "boost" in combined.lower():
        print("\n=== depends failed — auto-retry linux with system libs ===\n", file=sys.stderr)
        if args.target == "all":
            print("Retrying linux only (--fast); run win separately.", file=sys.stderr)
        exit_code, _ = run_remote(True)

    if exit_code != 0:
        print(f"\nQt build failed (exit {exit_code})", file=sys.stderr)
        ssh.close()
        return exit_code

    os.makedirs(LOCAL_DIST, exist_ok=True)
    assets = []
    for name in ("MasterNoder2-qt-linux.tar.gz", "MasterNoder2-qt-win.zip", "QT_RELEASE_MANIFEST.json"):
        remote = f"{REMOTE_DIST}/{name}"
        local = os.path.join(LOCAL_DIST, name)
        sftp = ssh.open_sftp()
        try:
            sftp.get(remote, local)
            assets.append(local)
            try:
                sftp.get(remote + ".sha256", local + ".sha256")
            except OSError:
                pass
        except OSError:
            pass
        finally:
            sftp.close()
    ssh.close()

    if not assets:
        print("No Qt assets downloaded.", file=sys.stderr)
        return 1

    for path in assets:
        print(f"Downloaded {path} ({os.path.getsize(path):,} bytes)")

    if args.publish:
        import subprocess

        pub = subprocess.run(
            [
                sys.executable,
                os.path.join(ROOT, "scripts", "mn2_publish_release.py"),
                "--qt-assets",
                "--skip-tag",
                *(["--draft"] if args.draft else []),
            ],
            cwd=ROOT,
        )
        return pub.returncode

    print("Publish Qt assets:")
    print("  python scripts/mn2_publish_release.py --qt-assets --skip-tag")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
