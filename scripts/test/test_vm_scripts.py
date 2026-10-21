"""Offline tests for rollback-vm.sh, backup-data.sh and restore-data.sh.

They mirror the layout deploy-vm.sh writes, under a temporary ASD_ROOT, with a stub `docker` that records its
arguments. Linux only: the scripts rely on real symlinks and readlink, exactly as on the deployment VM.
"""

import json
import os
import shutil
import sqlite3
import stat
import subprocess  # noqa: S404 - fixed argv, no shell
import sys
from pathlib import Path

import pytest

DEPLOY = Path(__file__).resolve().parents[1] / "deploy"
OLD, NEW = "a" * 40, "b" * 40
BASH = shutil.which("bash") or "bash"
pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="needs Linux symlink and readlink semantics")


@pytest.fixture
def vm(tmp_path):
    """A temporary ASD_ROOT plus a stub docker; returns an object with helpers."""
    root = tmp_path / "asd"
    (root / "releases").mkdir(parents=True)
    (root / "data").mkdir()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    stub = bin_dir / "docker"
    stub.write_text('#!/usr/bin/env bash\necho "$*" >> "$STUB_LOG"\n'
                    'if [[ "$1" == "ps" ]]; then [[ -z "${STUB_NO_CONTAINERS:-}" ]] && echo abc123; exit 0; fi\n'
                    'if [[ "$1" == "inspect" ]]; then cat "${STUB_ENV_FILE:-/dev/null}"; exit 0; fi\n'
                    '[[ -n "${STUB_FAIL_ON:-}" && "$*" == *"$STUB_FAIL_ON"* ]] && exit 1\nexit 0\n')
    stub.chmod(stub.stat().st_mode | stat.S_IEXEC)
    log = tmp_path / "docker.log"

    class Vm:
        pass

    helper = Vm()
    helper.root, helper.log = root, log

    def release(sha, previous=None, revision=None, files=True):
        path = root / "releases" / sha
        path.mkdir()
        if files:
            (path / "compose.json").write_text("{}")
            (path / "revision.txt").write_text((revision or sha) + "\n")
        if previous is not None:
            (path / "previous-release.txt").write_text(str(previous) + "\n")
        return path

    def activate(path):
        link = root / "current"
        if link.is_symlink():
            link.unlink()
        link.symlink_to(path)

    def run(script, *args, fail_on="", env_extra=None):
        env = {**os.environ, "ASD_ROOT": str(root), "PATH": f"{bin_dir}:{os.environ['PATH']}",
               "STUB_LOG": str(log), "STUB_FAIL_ON": fail_on, **(env_extra or {})}
        return subprocess.run([BASH, str(DEPLOY / script), *args], capture_output=True, text=True,  # noqa: S603
                              env=env, timeout=60, check=False)

    def docker_calls():
        return log.read_text().splitlines() if log.exists() else []

    def database(student, name, rows):
        folder = root / "data" / f"student-{student}"
        folder.mkdir(exist_ok=True)
        connection = sqlite3.connect(folder / name)
        connection.execute("CREATE TABLE IF NOT EXISTS t (v TEXT)")
        connection.execute("DELETE FROM t")
        connection.executemany("INSERT INTO t VALUES (?)", [(r,) for r in rows])
        connection.commit()
        connection.close()
        return folder / name

    def rows(path):
        connection = sqlite3.connect(path)
        try:
            return sorted(r[0] for r in connection.execute("SELECT v FROM t"))
        finally:
            connection.close()

    helper.release, helper.activate, helper.run = release, activate, run
    helper.docker_calls, helper.database, helper.rows = docker_calls, database, rows
    return helper


# -- rollback ---------------------------------------------------------------------------------------------------

def two_releases(vm):
    old = vm.release(OLD)
    new = vm.release(NEW, previous=old)
    vm.activate(new)
    return old, new


def test_rollback_starts_the_previous_release_then_repoints_current(vm):
    old, new = two_releases(vm)

    result = vm.run("rollback-vm.sh")

    assert result.returncode == 0, result.stderr
    assert Path(os.readlink(vm.root / "current")) == old
    assert (old / "rolled-back-from.txt").read_text().strip() == str(new)
    calls = vm.docker_calls()
    assert calls[0].endswith(f"{old}/compose.json config --quiet")
    assert calls[1].endswith(f"{old}/compose.json up --detach --no-build --wait --wait-timeout 240")
    assert "--project-name asd-cloud" in calls[1]


def test_rollback_does_not_touch_data(vm):
    two_releases(vm)
    db = vm.database(1, "accommodation.db", ["keep me"])
    before = db.read_bytes()

    assert vm.run("rollback-vm.sh").returncode == 0
    assert db.read_bytes() == before


def test_rollback_refuses_when_no_release_is_installed(vm):
    result = vm.run("rollback-vm.sh")

    assert result.returncode != 0 and "no current release" in result.stderr
    assert vm.docker_calls() == []


def test_rollback_refuses_when_the_current_release_has_no_previous(vm):
    vm.activate(vm.release(NEW))

    result = vm.run("rollback-vm.sh")

    assert result.returncode != 0 and "nothing to roll back to" in result.stderr
    assert vm.docker_calls() == []


def test_rollback_refuses_when_previous_is_the_same_revision(vm):
    new = vm.release(NEW)
    (new / "previous-release.txt").write_text(f"{new}\n")  # a redeploy of the same sha
    vm.activate(new)

    result = vm.run("rollback-vm.sh")

    assert result.returncode != 0 and "same revision" in result.stderr
    assert vm.docker_calls() == []


@pytest.mark.parametrize("recorded", ["/etc", "/srv/elsewhere/" + "a" * 40, "../../etc/passwd", "garbage"])
def test_rollback_refuses_a_previous_path_outside_the_releases_directory(vm, recorded):
    new = vm.release(NEW, previous=recorded)
    vm.activate(new)

    result = vm.run("rollback-vm.sh")

    assert result.returncode != 0 and "not under" in result.stderr
    assert vm.docker_calls() == [] and Path(os.readlink(vm.root / "current")) == new


def test_rollback_refuses_when_the_previous_release_is_incomplete(vm):
    old = vm.release(OLD, files=False)
    vm.activate(vm.release(NEW, previous=old))

    result = vm.run("rollback-vm.sh")

    assert result.returncode != 0 and "missing its files" in result.stderr
    assert vm.docker_calls() == []


def test_rollback_refuses_when_the_previous_revision_does_not_match_its_directory(vm):
    old = vm.release(OLD, revision="c" * 40)
    vm.activate(vm.release(NEW, previous=old))

    result = vm.run("rollback-vm.sh")

    assert result.returncode != 0 and "does not match" in result.stderr


def test_a_failed_start_leaves_current_unchanged_and_says_so(vm):
    old, new = two_releases(vm)

    result = vm.run("rollback-vm.sh", fail_on=" up ")

    assert result.returncode != 0 and "was NOT changed" in result.stderr
    assert Path(os.readlink(vm.root / "current")) == new
    assert not (old / "rolled-back-from.txt").exists()


# -- backup ------------------------------------------------------------------------------------------------------

def only_backup(vm):
    folders = sorted(p for p in (vm.root / "backups").iterdir())
    assert len(folders) == 1, folders
    return folders[0]


def test_backup_copies_every_database_consistently_with_checksums(vm):
    for student in range(1, 6):
        vm.database(student, f"s{student}.db", [f"row-{student}-a", f"row-{student}-b"])

    result = vm.run("backup-data.sh")

    assert result.returncode == 0, result.stderr
    backup = only_backup(vm)
    for student in range(1, 6):
        copy = backup / f"student-{student}" / f"s{student}.db"
        assert vm.rows(copy) == [f"row-{student}-a", f"row-{student}-b"]
    checked = subprocess.run(["sha256sum", "--check", "--quiet", "SHA256SUMS"], cwd=backup,  # noqa: S603, S607
                             capture_output=True, text=True, check=False)
    assert checked.returncode == 0, checked.stderr
    assert len((backup / "SHA256SUMS").read_text().splitlines()) == 5


def test_backup_is_safe_while_a_writer_holds_the_database_open(vm):
    db = vm.database(1, "live.db", ["before"])
    writer = sqlite3.connect(db)
    writer.execute("PRAGMA journal_mode=WAL")
    writer.execute("INSERT INTO t VALUES ('written-but-uncheckpointed')")
    writer.commit()  # committed data sits in the WAL, which a plain file copy of live.db would miss

    result = vm.run("backup-data.sh")
    writer.close()

    assert result.returncode == 0, result.stderr
    assert vm.rows(only_backup(vm) / "student-1" / "live.db") == ["before", "written-but-uncheckpointed"]


def test_backup_with_no_databases_fails_and_leaves_no_empty_backup(vm):
    result = vm.run("backup-data.sh")

    assert result.returncode != 0 and "no databases found" in result.stderr
    assert list((vm.root / "backups").iterdir()) == []


def test_backup_keeps_only_the_newest_timestamped_backups_and_spares_other_folders(vm):
    vm.database(1, "a.db", ["x"])
    backups = vm.root / "backups"
    for day in range(1, 10):
        (backups / f"2026010{day}T000000Z").mkdir(parents=True)
    (backups / "pre-restore-20260101T000000Z").mkdir()

    result = vm.run("backup-data.sh")  # default ASD_BACKUP_KEEP=7

    assert result.returncode == 0
    names = sorted(p.name for p in backups.iterdir() if p.name[0].isdigit())
    assert len(names) == 7  # default keep=7 with 10 timestamped backups -> 7 remain
    assert "pre-restore-20260101T000000Z" in {p.name for p in backups.iterdir()}
    assert "20260101T000000Z" not in names and "20260102T000000Z" not in names


def test_backup_rejects_an_invalid_keep_value(vm):
    vm.database(1, "a.db", ["x"])
    env_run = subprocess.run([BASH, str(DEPLOY / "backup-data.sh")], capture_output=True, text=True,  # noqa: S603
                             env={**os.environ, "ASD_ROOT": str(vm.root), "ASD_BACKUP_KEEP": "0"}, timeout=30, check=False)

    assert env_run.returncode != 0 and "positive integer" in env_run.stderr


# -- restore -----------------------------------------------------------------------------------------------------

def prepared(vm):
    two_releases(vm)
    db = vm.database(1, "accommodation.db", ["original-1", "original-2"])
    assert vm.run("backup-data.sh").returncode == 0
    return db, only_backup(vm)


def test_restore_without_yes_changes_nothing(vm):
    db, backup = prepared(vm)
    vm.database(1, "accommodation.db", ["damaged"])

    result = vm.run("restore-data.sh", str(backup))

    assert result.returncode != 0 and "--yes" in result.stderr
    assert vm.rows(db) == ["damaged"] and vm.docker_calls() == []


def test_restore_replaces_live_data_after_snapshotting_it_and_restarts_services(vm):
    db, backup = prepared(vm)
    vm.database(1, "accommodation.db", ["damaged"])
    (db.parent / "accommodation.db-wal").write_bytes(b"stale")

    result = vm.run("restore-data.sh", str(backup), "--yes")

    assert result.returncode == 0, result.stderr
    # Check the filesystem BEFORE opening the database: opening it with SQLite can itself clear a stale WAL file,
    # which would hide a restore script that forgot to remove it.
    assert not (db.parent / "accommodation.db-wal").exists()
    assert vm.rows(db) == ["original-1", "original-2"]
    snapshot = next(p for p in (vm.root / "backups").iterdir() if p.name.startswith("pre-restore-"))
    assert vm.rows(snapshot / "student-1" / "accommodation.db") == ["damaged"]
    calls = vm.docker_calls()
    assert calls[0].endswith("compose.json stop") and calls[-1].endswith("--wait-timeout 240")


def test_restore_refuses_a_tampered_backup_and_changes_nothing(vm):
    db, backup = prepared(vm)
    vm.database(1, "accommodation.db", ["live"])
    copy = backup / "student-1" / "accommodation.db"
    copy.write_bytes(copy.read_bytes() + b"tamper")

    result = vm.run("restore-data.sh", str(backup), "--yes")

    assert result.returncode != 0 and "checksum mismatch" in result.stderr
    assert vm.rows(db) == ["live"] and vm.docker_calls() == []
    assert not any(p.name.startswith("pre-restore-") for p in (vm.root / "backups").iterdir())


def test_restore_refuses_a_backup_outside_the_backups_directory(vm, tmp_path):
    prepared(vm)
    outside = tmp_path / "elsewhere"
    outside.mkdir()

    result = vm.run("restore-data.sh", str(outside), "--yes")

    assert result.returncode != 0 and "must be inside" in result.stderr


def test_restore_refuses_a_directory_that_is_not_a_complete_backup(vm):
    prepared(vm)
    incomplete = vm.root / "backups" / "20260101T000000Z"
    incomplete.mkdir()

    result = vm.run("restore-data.sh", str(incomplete), "--yes")

    assert result.returncode != 0 and "no SHA256SUMS" in result.stderr


def test_restore_requires_a_current_release_to_restart(vm):
    vm.database(1, "a.db", ["x"])
    assert vm.run("backup-data.sh").returncode == 0
    backup = only_backup(vm)

    result = vm.run("restore-data.sh", str(backup), "--yes")

    assert result.returncode != 0 and "no current release" in result.stderr


# -- private by default: backups and restore snapshots ---------------------------------------------------------------

def mode(path):
    return stat.S_IMODE(path.stat().st_mode)


def test_backups_are_private_even_when_the_callers_umask_is_permissive(vm):
    vm.database(1, "a.db", ["x"])
    previous = os.umask(0o022)  # the default on most systems: new files would be world-readable
    try:
        assert vm.run("backup-data.sh").returncode == 0
    finally:
        os.umask(previous)

    backup = only_backup(vm)
    assert mode(vm.root / "backups") == 0o700 and mode(backup) == 0o700 and mode(backup / "student-1") == 0o700
    assert mode(backup / "student-1" / "a.db") == 0o600 and mode(backup / "SHA256SUMS") == 0o600


def test_the_pre_restore_snapshot_is_private_even_when_the_callers_umask_is_permissive(vm):
    two_releases(vm)
    vm.database(1, "a.db", ["x"])
    assert vm.run("backup-data.sh").returncode == 0
    previous = os.umask(0o022)
    try:
        result = vm.run("restore-data.sh", str(only_backup(vm)), "--yes")
    finally:
        os.umask(previous)

    assert result.returncode == 0, result.stderr
    snapshot = next(p for p in (vm.root / "backups").iterdir() if p.name.startswith("pre-restore-"))
    assert mode(snapshot) == 0o700


# -- data-security audit (B6) ------------------------------------------------------------------------------------------

CLEAN_COMPOSE = {"services": {"student1-backend": {"environment": {"AI_ENABLED": "false", "MCP_ENABLED": "false", "LITEAPI_KEY": ""}},
                              "student3-backend": {"environment": {"AI_ENABLED": "false"}}}}


def audited(vm, compose=CLEAN_COMPOSE, container_env="OTHER=1\nLITEAPI_KEY=\nASPNETCORE_HTTP_PORTS=8080\n", private=True, no_containers=False):
    """Build a VM that passes the audit, then let each test spoil one thing. Returns the audit result."""
    release = vm.release(NEW)
    (release / "compose.json").write_text(json.dumps(compose))
    vm.activate(release)
    vm.database(1, "accommodation.db", ["x"])
    (vm.root / "backups").mkdir(exist_ok=True)
    if private:
        for folder in (vm.root / "data", vm.root / "data" / "student-1", vm.root / "backups"):
            folder.chmod(0o700)
        (vm.root / "data" / "student-1" / "accommodation.db").chmod(0o600)
    env_file = vm.root.parent / "container-env.txt"
    env_file.write_text(container_env)
    extra = {"STUB_ENV_FILE": str(env_file)}
    if no_containers:
        extra["STUB_NO_CONTAINERS"] = "1"
    return vm.run("audit-data-security.sh", env_extra=extra)


def test_a_protected_deployment_passes_every_automated_check_and_flags_what_it_cannot_know(vm):
    result = audited(vm)

    assert result.returncode == 0, result.stdout + result.stderr
    for check in ("perms:data", "perms:backups", "env:secrets", "compose:secrets", "files:credentials"):
        assert any(line.startswith("PASS") and check in line for line in result.stdout.splitlines()), check
    assert any(line.startswith("MANUAL") and "disk:encryption" in line for line in result.stdout.splitlines())


def test_a_world_readable_database_fails_and_names_the_fix(vm):
    vm.release  # noqa: B018 - fixture used below
    result = audited(vm, private=False)
    (vm.root / "data" / "student-1" / "accommodation.db").chmod(0o644)

    result = vm.run("audit-data-security.sh", env_extra={"STUB_ENV_FILE": str(vm.root.parent / "container-env.txt")})

    assert result.returncode == 1
    assert any(line.startswith("FAIL") and "perms:data" in line and "chmod -R o-rwx" in line for line in result.stdout.splitlines())


def test_a_world_writable_backups_directory_fails(vm):
    audited(vm)
    (vm.root / "backups").chmod(0o777)

    result = vm.run("audit-data-security.sh", env_extra={"STUB_ENV_FILE": str(vm.root.parent / "container-env.txt")})

    assert result.returncode == 1
    assert any(line.startswith("FAIL") and "perms:backups" in line for line in result.stdout.splitlines())


def test_a_secret_in_a_container_environment_fails_and_its_value_is_never_printed(vm):
    secret = "sk-live-do-not-print-0123456789"  # noqa: S105  # pragma: allowlist secret  (a fake value the audit must never echo)
    result = audited(vm, container_env=f"OTHER=1\nLITEAPI_KEY={secret}\nDB_PASSWORD=hunter2-also-secret\n")

    assert result.returncode == 1
    line = next(l for l in result.stdout.splitlines() if l.startswith("FAIL") and "env:secrets" in l)
    assert "LITEAPI_KEY" in line and "DB_PASSWORD" in line
    assert secret not in result.stdout + result.stderr and "hunter2" not in result.stdout + result.stderr


def test_empty_secret_variables_and_ordinary_variables_are_not_flagged(vm):
    result = audited(vm, container_env="LITEAPI_KEY=\nAPI_KEY=\nPATH=/usr/bin\nASPNETCORE_HTTP_PORTS=8080\n")

    assert result.returncode == 0, result.stdout


def test_a_non_empty_api_key_in_the_release_bundle_fails_and_names_the_service(vm):
    compose = {"services": {"student1-backend": {"environment": {"LITEAPI_KEY": "abc"}}, "student2-backend": {"environment": {}}}}

    result = audited(vm, compose=compose)

    assert result.returncode == 1
    assert any(l.startswith("FAIL") and "compose:secrets" in l and "student1-backend" in l for l in result.stdout.splitlines())


@pytest.mark.parametrize("name", [".env", ".env.production", "id_ed25519", "id_rsa.pub", "server.pem", "tls.key", "credentials.json"])
def test_credential_files_left_under_the_application_root_fail(vm, name):
    audited(vm)
    (vm.root / "releases" / name).write_text("x")

    result = vm.run("audit-data-security.sh", env_extra={"STUB_ENV_FILE": str(vm.root.parent / "container-env.txt")})

    assert result.returncode == 1
    assert any(l.startswith("FAIL") and "files:credentials" in l and name in l for l in result.stdout.splitlines())


def test_enabled_ai_flags_are_reported_as_information_not_failures(vm):
    compose = {"services": {"student3-backend": {"environment": {"AI_ENABLED": "true", "MCP_ENABLED": "false", "RAG_ENABLED": "true"}}}}

    result = audited(vm, compose=compose)

    assert result.returncode == 0, result.stdout
    info = next(l for l in result.stdout.splitlines() if l.startswith("INFO"))
    assert "AI_ENABLED=true" in info and "RAG_ENABLED=true" in info and "MCP_ENABLED" not in info


def test_a_clean_baseline_reports_every_flag_false(vm):
    info = next(l for l in audited(vm).stdout.splitlines() if l.startswith("INFO"))

    assert "every *_ENABLED flag is false" in info


def test_the_audit_fails_when_there_is_no_current_release_to_inspect(vm):
    result = vm.run("audit-data-security.sh", env_extra={"STUB_NO_CONTAINERS": "1"})

    assert result.returncode == 1
    assert any(l.startswith("FAIL") and "compose:secrets" in l for l in result.stdout.splitlines())


def test_missing_data_and_backups_directories_and_no_containers_are_noted_not_failed(vm):
    release = vm.release(NEW)
    (release / "compose.json").write_text(json.dumps(CLEAN_COMPOSE))
    vm.activate(release)
    (vm.root / "data").rmdir()

    result = vm.run("audit-data-security.sh", env_extra={"STUB_NO_CONTAINERS": "1"})

    assert result.returncode == 0, result.stdout
    manual = [l for l in result.stdout.splitlines() if l.startswith("MANUAL")]
    assert {"perms:data", "perms:backups", "env:secrets"} <= {part for line in manual for part in line.split()}


def test_the_audit_changes_nothing(vm):
    audited(vm, private=False)
    before = sorted((str(p.relative_to(vm.root)), mode(p)) for p in vm.root.rglob("*"))

    vm.run("audit-data-security.sh", env_extra={"STUB_ENV_FILE": str(vm.root.parent / "container-env.txt")})

    assert sorted((str(p.relative_to(vm.root)), mode(p)) for p in vm.root.rglob("*")) == before
