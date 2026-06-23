#!/usr/bin/env python3
"""Build MasterNoder2 on the production Linux server and pull tarball locally.

Applies docs/patches/mn2-daemon-v1.3.0-multi-ping.patch when v1.3.0.0 tag is absent upstream.

Usage:
  python scripts/mn2_build_release_remote.py --ask-pass
  python scripts/mn2_build_release_remote.py --ask-pass --publish --draft
  python scripts/mn2_build_release_remote.py --ask-pass --fast   # system libs (quicker, less portable)
  python scripts/mn2_build_release_remote.py --ask-pass --auto-fast --publish --draft
"""
from __future__ import annotations

import argparse
import os
import re
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
from mn2_release_config import BASE_TAG, MANIFEST_NAME, PATCH_REL, TARGET_VERSION

BUILD_ROOT = "/tmp/mn2-build"
LOCAL_DIST = os.path.join(ROOT, "dist")
REMOTE_DIST = f"{BUILD_ROOT}/dist"
REMOTE_TAR = f"{REMOTE_DIST}/masternoder2d.tar.gz"
REMOTE_MANIFEST = f"{REMOTE_DIST}/{MANIFEST_NAME}"
REMOTE_PATCH = "/tmp/mn2-daemon-v1.3.0-multi-ping.patch"

BOOST_DEPENDS_RE = re.compile(
    r"Failed to build Boost\.Build engine|boost.*stamp_configured|funcs\.mk:.*boost",
    re.IGNORECASE,
)
UNSUPPORTED_SSL_RE = re.compile(
    r"unsupported SSL version|Detected unsupported SSL",
    re.IGNORECASE,
)


def is_boost_depends_failure(output: str) -> bool:
    return bool(BOOST_DEPENDS_RE.search(output))


def is_unsupported_ssl_failure(output: str) -> bool:
    return bool(UNSUPPORTED_SSL_RE.search(output))


def fast_retry_hint() -> str:
    return (
        "Tip: depends boost failed — retry with system libs:\n"
        "  python scripts/mn2_build_release_remote.py --ask-pass --fast --publish --draft"
    )


def depends_retry_hint() -> str:
    return (
        "Tip: OpenSSL 3 system libs need depends build (portable, bundled OpenSSL):\n"
        "  python scripts/mn2_build_release_remote.py --ask-pass --publish --draft"
    )


def fast_ssl_hint() -> str:
    return (
        "Tip: --fast uses --with-unsupported-ssl for OpenSSL 3 hosts. "
        "Pull latest build script and retry, or use depends (preferred):\n"
        "  python scripts/mn2_build_release_remote.py --ask-pass --publish --draft"
    )


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


def main() -> int:
    parser = argparse.ArgumentParser(description=f"Remote MN2 {TARGET_VERSION} Linux build")
    parser.add_argument("--ask-pass", action="store_true")
    parser.add_argument("--publish", action="store_true", help="Run mn2_publish_release.py after download")
    parser.add_argument("--draft", action="store_true", help="With --publish: create draft release")
    parser.add_argument(
        "--fast",
        action="store_true",
        help="System libs build (USE_DEPENDS=0; uses --with-unsupported-ssl on OpenSSL 3)",
    )
    parser.add_argument(
        "--auto-fast",
        action="store_true",
        help="If depends boost fails, retry once with --fast (system libs)",
    )
    parser.add_argument("--skip-deps", action="store_true", help="Do not apt-install build dependencies")
    parser.add_argument("--jobs", type=int, default=2, help="make -j")
    parser.add_argument(
        "--branch",
        default="",
        help="Checkout origin branch instead of patch (e.g. release/v1.3.0.0-multi-ping)",
    )
    parser.add_argument("--no-patch", action="store_true", help="Do not upload patch (tag/branch must exist)")
    args = parser.parse_args()
    if args.auto_fast:
        args.fast = False

    pw = require_deploy_pass(force_prompt=args.ask_pass)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(deploy_host(), username=deploy_user(), password=pw, timeout=30)

    remote_build = upload_script(ssh, "mn2_build_release.sh", "mn2_build_release.sh")
    upload_script(ssh, "mn2_build_smoke.sh", "mn2_build_smoke.sh")

    patch_file = ""
    if not args.no_patch and not args.branch:
        patch_file = upload_patch(ssh)
        print(f"Uploaded patch → {patch_file}")

    def run_remote_build(use_fast: bool) -> tuple[int, str, str]:
        use_dep = "0" if use_fast else "1"
        install_deps = "0" if args.skip_deps else "1"
        branch = args.branch.replace("'", "")
        cmd = (
            f"export BUILD_ROOT={BUILD_ROOT} JOBS={args.jobs} USE_DEPENDS={use_dep} "
            f"INSTALL_BUILD_DEPS={install_deps} VERSION={TARGET_VERSION} BASE_TAG={BASE_TAG} "
            f"PATCH_FILE='{patch_file}' CHECKOUT_BRANCH='{branch}'; "
            f"bash {remote_build}"
        )
        print(
            f"=== Remote build {TARGET_VERSION} "
            f"(USE_DEPENDS={use_dep}, INSTALL_BUILD_DEPS={install_deps}, JOBS={args.jobs}) "
            f"— may take 30–90 min ===\n"
        )
        _, stdout, stderr = ssh.exec_command(cmd, get_pty=True, timeout=10800)
        exit_code = stdout.channel.recv_exit_status()
        out = stdout.read().decode(errors="replace")
        err = stderr.read().decode(errors="replace")
        print(out)
        if err.strip():
            print(err, file=sys.stderr)
        return exit_code, out, err

    exit_code, out, err = run_remote_build(args.fast)
    combined = f"{out}\n{err}"
    if (
        exit_code != 0
        and args.auto_fast
        and not args.fast
        and is_boost_depends_failure(combined)
        and not is_unsupported_ssl_failure(combined)
    ):
        print("\n=== depends boost failed — auto-retry with system libs (--fast) ===\n", file=sys.stderr)
        exit_code, out, err = run_remote_build(True)
        combined = f"{out}\n{err}"

    if exit_code != 0:
        print(f"\nBuild failed (exit {exit_code})", file=sys.stderr)
        if args.fast and is_unsupported_ssl_failure(combined):
            print(fast_ssl_hint(), file=sys.stderr)
        elif args.fast:
            print("Tip: re-run without --fast for depends build (portable static binary).", file=sys.stderr)
        elif is_unsupported_ssl_failure(combined):
            print(depends_retry_hint(), file=sys.stderr)
        elif is_boost_depends_failure(combined):
            print(fast_retry_hint(), file=sys.stderr)
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
