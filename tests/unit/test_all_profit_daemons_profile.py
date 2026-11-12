import os
import subprocess

from scripts.all_profit_daemons import PROFILE_INTERVALS, resolve_profile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_known_profiles_pass_through():
    for name in PROFILE_INTERVALS:
        assert resolve_profile(name) == name
    assert resolve_profile(" Standard ") == "standard"


def test_unknown_or_empty_profile_falls_back_to_max():
    assert resolve_profile("paypal") == "max"
    assert resolve_profile("") == "max"
    assert resolve_profile(None) == "max"


def test_cron_and_daemon_shell_scripts_are_executable_in_git():
    out = subprocess.run(
        ["git", "ls-files", "-s", "cron/*.sh", "scripts/run_profit_daemon_server.sh"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout.splitlines()
    assert out
    not_exec = [line.split()[-1] for line in out if not line.startswith("100755")]
    assert not_exec == []
