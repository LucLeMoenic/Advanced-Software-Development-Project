"""Offline tests for scripts/ci/retry-transient.sh (needs bash, as on the Actions runners)."""

import shutil
import subprocess  # noqa: S404 - fixed argv, no shell
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "ci" / "retry-transient.sh"
BASH = shutil.which("bash")
pytestmark = pytest.mark.skipif(BASH is None, reason="bash is required")

REGISTRY_500 = ("ERROR: unexpected status from HEAD request to "
                "https://registry-1.docker.io/v2/library/nginx/manifests/stable-alpine: 500 Internal Server Error")


def run(tmp_path, body, attempts=3):
    """Run the wrapper around a command that follows `body` (bash), counting how often it ran."""
    counter = tmp_path / "count"
    counter.write_text("0")
    command = tmp_path / "command.sh"
    command.write_text(
        "n=$(( $(cat '" + counter.as_posix() + "') + 1 )); echo $n > '" + counter.as_posix() + "'\n" + body, encoding="utf-8")
    result = subprocess.run(  # noqa: S603 - bash and repository paths only
        [BASH, SCRIPT.as_posix(), str(attempts), "0", BASH, command.as_posix()],
        capture_output=True, text=True, timeout=60, check=False)
    return result, int(counter.read_text())


def test_success_runs_once_and_passes_through(tmp_path):
    result, runs = run(tmp_path, "echo built\n")

    assert result.returncode == 0 and runs == 1 and "built" in result.stdout


def test_transient_registry_error_is_retried_until_it_succeeds(tmp_path):
    body = f'if [ "$n" -lt 3 ]; then echo "{REGISTRY_500}" >&2; exit 1; fi\necho built\n'

    result, runs = run(tmp_path, body)

    assert result.returncode == 0 and runs == 3
    assert result.stderr.count("retrying in") == 2


def test_persistent_transient_error_gives_up_after_the_attempt_limit_and_keeps_the_exit_code(tmp_path):
    result, runs = run(tmp_path, f'echo "{REGISTRY_500}" >&2\nexit 7\n', attempts=3)

    assert result.returncode == 7 and runs == 3
    assert "still failing after 3 attempts" in result.stderr


def test_a_genuine_build_error_is_never_retried(tmp_path):
    result, runs = run(tmp_path, 'echo "Dockerfile:9 error: COPY failed: file not found" >&2\nexit 1\n')

    assert result.returncode == 1 and runs == 1
    assert "not retrying" in result.stderr


@pytest.mark.parametrize("message", [
    "failed to authorize: Unavailable: error reading from server: EOF",
    "net/http: TLS handshake timeout",
    "dial tcp: i/o timeout",
    "toomanyrequests: You have reached your pull rate limit",
])
def test_other_transient_network_errors_are_retried(tmp_path, message):
    body = f'if [ "$n" -lt 2 ]; then echo "{message}" >&2; exit 1; fi\n'

    result, runs = run(tmp_path, body)

    assert result.returncode == 0 and runs == 2


@pytest.mark.parametrize("arguments", [[], ["3"], ["0", "1", "true"], ["3", "x", "true"], ["3", "1"]])
def test_bad_arguments_are_rejected(arguments):
    result = subprocess.run([BASH, SCRIPT.as_posix(), *arguments], capture_output=True, text=True,  # noqa: S603
                            timeout=30, check=False)

    assert result.returncode != 0
