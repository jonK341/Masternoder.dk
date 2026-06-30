#!/usr/bin/env python3

"""Build MasterNoder2 on the production Linux server and pull tarball locally.

Applies docs/patches/mn2-daemon-v1.3.0-multi-ping.patch when v1.3.0.0 tag is absent upstream.

Usage:

  # Full build
  python scripts/mn2_build_release_remote.py --ask-pass --fast --no-auto-depends --publish --draft

  # 4-step manual (resume-friendly; each stage writes /tmp/mn2-build/.stage-*-done)
  python scripts/mn2_build_release_remote.py --ask-pass --fast --stage prepare
  python scripts/mn2_build_release_remote.py --ask-pass --fast --stage configure
  python scripts/mn2_build_release_remote.py --ask-pass --fast --stage compile
  python scripts/mn2_build_release_remote.py --ask-pass --fast --stage package --publish --draft

  # 2-step aliases
  python scripts/mn2_build_release_remote.py --ask-pass --fast --stage setup
  python scripts/mn2_build_release_remote.py --ask-pass --fast --stage build --publish --draft

  # Other modes
  python scripts/mn2_build_release_remote.py --ask-pass --auto-fast --publish --draft
"""

from __future__ import annotations



import argparse
import hashlib
import json
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



from deploy_ssh_env import connect_deploy_ssh, deploy_host, deploy_user, require_deploy_pass

from mn2_release_config import BASE_TAG, COMPAT_PATCH_REL, MANIFEST_NAME, PATCH_REL, TARGET_VERSION



BUILD_ROOT = "/tmp/mn2-build"

BUILD_LOG = f"{BUILD_ROOT}/build.log"

LOCAL_DIST = os.path.join(ROOT, "dist")

REMOTE_DIST = f"{BUILD_ROOT}/dist"

REMOTE_TAR = f"{REMOTE_DIST}/masternoder2d.tar.gz"

REMOTE_MANIFEST = f"{REMOTE_DIST}/{MANIFEST_NAME}"

REMOTE_PATCH = "/tmp/mn2-daemon-v1.3.0-multi-ping.patch"

REMOTE_COMPAT_PATCH = "/tmp/mn2-daemon-build-compat-modern-host.patch"



def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _repair_manifest_tarball_hash(manifest_path: str, tarball_path: str) -> bool:
    """If manifest tarball_sha256 drifted from tarball, rewrite from actual hash."""
    if not os.path.isfile(manifest_path) or not os.path.isfile(tarball_path):
        return False
    actual = _sha256_file(tarball_path)
    with open(manifest_path, encoding="utf-8") as f:
        doc = json.load(f)
    expected = doc.get("tarball_sha256")
    if expected == actual:
        return False
    print(
        f"WARN: manifest tarball_sha256 stale ({(expected or '')[:16]}…); "
        f"syncing to {actual[:16]}…",
        file=sys.stderr,
    )
    doc["tarball_sha256"] = actual
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2)
        f.write("\n")
    return True



BOOST_DEPENDS_RE = re.compile(

    r"Failed to build Boost\.Build engine|boost.*stamp_configured|funcs\.mk:.*boost",

    re.IGNORECASE,

)

UNSUPPORTED_SSL_RE = re.compile(

    r"unsupported SSL version|Detected unsupported SSL",

    re.IGNORECASE,

)

PATCH_FAIL_RE = re.compile(

    r"patch: \*\*\*\*|can't find file to patch|patch failed|hunk FAILED",

    re.IGNORECASE,

)





def is_boost_depends_failure(output: str) -> bool:

    return bool(BOOST_DEPENDS_RE.search(output))





def is_unsupported_ssl_failure(output: str) -> bool:

    return bool(UNSUPPORTED_SSL_RE.search(output))





def is_patch_failure(output: str) -> bool:

    return bool(PATCH_FAIL_RE.search(output))





def fast_retry_hint() -> str:

    return (

        "Tip: depends boost failed on this host — use system libs instead:\n"

        "  python scripts/mn2_build_release_remote.py --ask-pass --fast --no-auto-depends --publish --draft\n"

        "Or try --auto-fast (depends first, auto fallback to --fast):\n"

        "  python scripts/mn2_build_release_remote.py --ask-pass --auto-fast --publish --draft"

    )





def auto_depends_boost_hint() -> str:

    return (

        "Tip: --fast failed, then depends boost also fails on this host — "

        "retry with --fast --no-auto-depends (compat patch fixes modern gcc/boost):\n"

        "  python scripts/mn2_build_release_remote.py --ask-pass --fast --no-auto-depends --publish --draft"

    )





def fast_compile_hint() -> str:

    return (

        "Tip: --fast compile failed — see errors above. "

        "Retry with --no-auto-depends after fixing compat patch issues:\n"

        "  python scripts/mn2_build_release_remote.py --ask-pass --fast --no-auto-depends --publish --draft\n"

        "For a portable static binary (only if depends works on your host):\n"

        "  python scripts/mn2_build_release_remote.py --ask-pass --publish --draft"

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





def upload_patch(ssh, rel_path: str, remote_path: str) -> str:

    local_path = os.path.join(ROOT, rel_path)

    if not os.path.isfile(local_path):

        raise SystemExit(f"Patch not found: {local_path}")

    sftp = ssh.open_sftp()

    with sftp.file(remote_path, "w") as rf:

        with open(local_path, "rb") as lf:

            rf.write(lf.read())

    sftp.close()

    return remote_path





def upload_multi_ping_patch(ssh) -> str:

    return upload_patch(ssh, PATCH_REL, REMOTE_PATCH)





def upload_compat_patch(ssh) -> str:

    return upload_patch(ssh, COMPAT_PATCH_REL, REMOTE_COMPAT_PATCH)





BUILD_LOG_ERROR_GREP = (

    r"error:|Failed to build|Error [0-9]+|fatal error|"

    r"funcs\.mk:.*boost|stamp_configured|Boost\.Build engine"

)





def print_remote_build_errors(ssh) -> None:

    """Print build log path and first error lines from the remote host."""

    grep_pat = BUILD_LOG_ERROR_GREP.replace("'", "'\\''")

    cmd = (

        f"test -f '{BUILD_LOG}' && grep -iE '{grep_pat}' '{BUILD_LOG}' | head -10 || true"

    )

    _, stdout, _ = ssh.exec_command(cmd, timeout=30)

    lines = stdout.read().decode(errors="replace").strip()

    print(f"\nFull log: {BUILD_LOG}", file=sys.stderr)

    if lines:

        print("=== Build errors (from log) ===", file=sys.stderr)

        print(lines, file=sys.stderr)

        return

    tail_cmd = f"test -f '{BUILD_LOG}' && tail -25 '{BUILD_LOG}' || true"

    _, stdout, _ = ssh.exec_command(tail_cmd, timeout=30)

    tail = stdout.read().decode(errors="replace").strip()

    if tail:

        print("=== Last lines of build log ===", file=sys.stderr)

        print(tail, file=sys.stderr)





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

    parser.add_argument(

        "--no-auto-depends",

        action="store_true",

        help="Do not auto-retry with depends when --fast fails (default: retry once)",

    )

    parser.add_argument("--skip-deps", action="store_true", help="Do not apt-install build dependencies")

    parser.add_argument("--jobs", type=int, default=2, help="make -j (depends); fast compile uses -j1")

    parser.add_argument(

        "--stage",

        choices=["prepare", "configure", "compile", "package", "setup", "build", "all"],

        default="all",

        help=(
            "Build stage (MN2_BUILD_STAGE): "
            "prepare=clone+patch; configure=depends+autogen; compile=make; package=tarball; "
            "setup=prepare+configure; build=compile+package; all=full pipeline"
        ),

    )

    parser.add_argument(

        "--branch",

        default="",

        help="Checkout origin branch instead of patch (e.g. release/v1.3.0.0-multi-ping)",

    )

    parser.add_argument("--no-patch", action="store_true", help="Do not upload patch (tag/branch must exist)")

    args = parser.parse_args()

    if args.auto_fast:

        args.fast = False



    auto_depends = not args.no_auto_depends



    pw = require_deploy_pass(force_prompt=args.ask_pass)

    ssh, auth_method, _ = connect_deploy_ssh(pw)

    print(f"== Connected {deploy_user()}@{deploy_host()} ({auth_method}) ==\n")



    remote_build = upload_script(ssh, "mn2_build_release.sh", "mn2_build_release.sh")

    upload_script(ssh, "mn2_build_smoke.sh", "mn2_build_smoke.sh")



    patch_file = ""

    compat_patch_file = upload_compat_patch(ssh)

    print(f"Uploaded compat patch → {compat_patch_file}")

    if not args.no_patch and not args.branch:

        patch_file = upload_multi_ping_patch(ssh)

        print(f"Uploaded patch → {patch_file}")



    def run_remote_build(use_fast: bool) -> tuple[int, str, str]:

        use_dep = "0" if use_fast else "1"

        install_deps = "0" if args.skip_deps else "1"

        branch = args.branch.replace("'", "")

        cmd = (

            f"export BUILD_ROOT={BUILD_ROOT} JOBS={args.jobs} USE_DEPENDS={use_dep} "

            f"INSTALL_BUILD_DEPS={install_deps} VERSION={TARGET_VERSION} BASE_TAG={BASE_TAG} "

            f"MN2_BUILD_STAGE={args.stage} FAST_SINGLE_JOB=1 "

            f"PATCH_FILE='{patch_file}' COMPAT_PATCH_FILE='{compat_patch_file}' CHECKOUT_BRANCH='{branch}'; "

            f"bash {remote_build}"

        )

        mode = "fast (system libs, -j1 compile)" if use_fast else "depends (static)"

        print(

            f"=== Remote build {TARGET_VERSION} [{args.stage}] "

            f"(USE_DEPENDS={use_dep}, {mode}, INSTALL_BUILD_DEPS={install_deps}, JOBS={args.jobs}) "

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

    tried_auto_depends = False



    # auto-fast: depends boost failure → retry with system libs

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



    # auto-depends (default): fast failure → retry with depends (skip patch failures)

    if (

        exit_code != 0

        and args.fast

        and auto_depends

        and not is_patch_failure(combined)

    ):

        print(

            "\n=== fast build failed — auto-retry with depends (USE_DEPENDS=1) ===\n",

            file=sys.stderr,

        )

        tried_auto_depends = True

        exit_code, out, err = run_remote_build(False)

        combined = f"{out}\n{err}"



    if exit_code != 0:

        print(f"\nBuild failed (exit {exit_code})", file=sys.stderr)

        print_remote_build_errors(ssh)

        if is_patch_failure(combined):

            print("Patch apply failed — fix patch/base tag before retrying.", file=sys.stderr)

        elif is_boost_depends_failure(combined):

            if tried_auto_depends:

                print(auto_depends_boost_hint(), file=sys.stderr)

            else:

                print(fast_retry_hint(), file=sys.stderr)

        elif args.fast and is_unsupported_ssl_failure(combined):

            print(fast_ssl_hint(), file=sys.stderr)

        elif args.fast:

            print(fast_compile_hint(), file=sys.stderr)

        elif is_unsupported_ssl_failure(combined):

            print(depends_retry_hint(), file=sys.stderr)

        ssh.close()

        return exit_code



    tarball_stages = {"package", "build", "all"}

    if args.stage not in tarball_stages:

        print(f"\nStage '{args.stage}' complete on remote (no tarball yet).")

        ssh.close()

        return 0



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

        _repair_manifest_tarball_hash(local_manifest, local_tar)



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

