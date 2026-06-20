#!/usr/bin/env python3
"""Build MasterNoder2 v1.2.3.0 on the production Linux server and pull tarball locally.

Installs apt build deps automatically (autoconf, boost, ssl, …) when missing.

Usage:
  python scripts/mn2_build_release_remote.py --ask-pass
  python scripts/mn2_build_release_remote.py --ask-pass --publish
  python scripts/mn2_build_release_remote.py --ask-pass --publish --draft
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
from deploy_ssh_env import deploy_host, deploy_user, require_deploy_pass
from mn2_release_config import MANIFEST_NAME, TARGET_VERSION

BUILD_ROOT = "/tmp/mn2-build"
LOCAL_DIST = os.path.join(ROOT, "dist")
REMOTE_DIST = f"{BUILD_ROOT}/dist"
REMOTE_TAR = f"{REMOTE_DIST}/masternoder2d.tar.gz"
REMOTE_MANIFEST = f"{REMOTE_DIST}/{MANIFEST_NAME}"


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


def main() -> int:
    parser = argparse.ArgumentParser(description="Remote MN2 v1.2.3.0 Linux build")
    parser.add_argument("--ask-pass", action="store_true")
    parser.add_argument("--publish", action="store_true", help="Run mn2_publish_release.py after download")
    parser.add_argument("--draft", action="store_true", help="With --publish: create draft release")
    parser.add_argument("--fast", action="store_true",
                        help="System libs only (faster; often fails with OpenSSL 3.x — default is depends)")
    parser.add_argument("--rebuild-depends", action="store_true",
                        help="Force full depends rebuild (default: skip if already built)")
    parser.add_argument("--skip-deps", action="store_true", help="Do not apt-install build dependencies")
    parser.add_argument("--jobs", type=int, default=2, help="make -j")
    args = parser.parse_args()

    pw = require_deploy_pass(force_prompt=args.ask_pass)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(deploy_host(), username=deploy_user(), password=pw, timeout=30)

    remote_build = upload_script(ssh, "mn2_build_release.sh", "mn2_build_release.sh")
    upload_script(ssh, "mn2_build_smoke.sh", "mn2_build_smoke.sh")

    use_dep = "0" if args.fast else "1"
    install_deps = "0" if args.skip_deps else "1"
    skip_dep_build = "0" if args.rebuild_depends else "1"
    cmd = (
        f"export BUILD_ROOT={BUILD_ROOT} JOBS={args.jobs} USE_DEPENDS={use_dep} "
        f"INSTALL_BUILD_DEPS={install_deps} SKIP_DEPENDS_BUILD={skip_dep_build} "
        f"VERSION={TARGET_VERSION}; "
        f"bash {remote_build} 2>&1 | tee /tmp/mn2-build.log; "
        f"test ${{PIPESTATUS[0]}} -eq 0"
    )
    print(
        f"=== Remote build (USE_DEPENDS={use_dep}, INSTALL_BUILD_DEPS={install_deps}, "
        f"JOBS={args.jobs}, VERSION={TARGET_VERSION}) — may take 15–60 min ===\n"
    )
    _, stdout, stderr = ssh.exec_command(cmd, get_pty=True, timeout=7200)
    exit_code = stdout.channel.recv_exit_status()
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    print(out)
    if err.strip():
        print(err, file=sys.stderr)
    if exit_code != 0:
        print(f"\nBuild failed (exit {exit_code})", file=sys.stderr)
        _, tail_out, _ = ssh.exec_command("tail -n 80 /tmp/mn2-build.log 2>/dev/null", timeout=30)
        tail = tail_out.read().decode(errors="replace").strip()
        if tail:
            print("\n=== Last 80 lines of /tmp/mn2-build.log ===", file=sys.stderr)
            print(tail, file=sys.stderr)
        print(
            "Tip: look for BUILD FAIL / SMOKE FAIL / Error 1 above. "
            "Depends is skipped by default; use --rebuild-depends only if needed.",
            file=sys.stderr,
        )
        ssh.close()
        return exit_code

    os.makedirs(LOCAL_DIST, exist_ok=True)
    local_tar = os.path.join(LOCAL_DIST, "masternoder2d.tar.gz")
    local_manifest = os.path.join(LOCAL_DIST, MANIFEST_NAME)
    sftp = ssh.open_sftp()
    try:
        sftp.get(REMOTE_TAR, local_tar)
        try:
            sftp.get(REMOTE_TAR + ".sha256", local_tar + ".sha256")
        except OSError:
            pass
        try:
            sftp.get(REMOTE_MANIFEST, local_manifest)
        except OSError:
            pass
    finally:
        sftp.close()
    ssh.close()

    size = os.path.getsize(local_tar)
    print(f"\nDownloaded {local_tar} ({size:,} bytes)")
    if os.path.isfile(local_manifest):
        print(f"Downloaded {local_manifest}")

    if args.publish:
        import subprocess

        pub_cmd = [
            sys.executable,
            os.path.join(ROOT, "scripts", "mn2_publish_release.py"),
            "--tarball",
            local_tar,
            "--skip-tag",
        ]
        if os.path.isfile(local_manifest):
            pub_cmd.extend(["--manifest", local_manifest])
        if args.draft:
            pub_cmd.append("--draft")
        pub = subprocess.run(pub_cmd, cwd=ROOT)
        if pub.returncode == 0:
            print("\nRun: python scripts/mn2_release_status.py --tarball dist/masternoder2d.tar.gz")
            print("Then: python scripts/mn2_daemon_upgrade_remote.py --ask-pass --apply")
        return pub.returncode

    print("Publish (draft recommended first):")
    print(
        f"  python scripts/mn2_publish_release.py --tarball {local_tar} "
        f"--manifest {local_manifest} --skip-tag --draft"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
