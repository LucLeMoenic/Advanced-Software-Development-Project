"""Offline tests for provision-vm.sh.

Stub `az`, `aws`, `ssh` and `ssh-keygen` record their arguments, so nothing is created in a cloud. Linux only, like
test_vm_scripts.py: the script runs under the VM-side bash and coreutils.
"""

import os
import shutil
import stat
import subprocess  # noqa: S404 - fixed argv, no shell
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "deploy" / "provision-vm.sh"
BASH = shutil.which("bash") or "bash"
pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="runs the script with Linux bash and coreutils")

STUBS = {
    # Keeps a copy of the first-boot file, which the script deletes on exit.
    "az": 'echo "az $*" >> "$STUB_LOG"\n'
          'previous=""; for arg in "$@"; do [[ "$previous" == --custom-data ]] && cp "$arg" "$STUB_DIR/cloud-init.yaml"; previous="$arg"; done\n',
    "aws": 'echo "aws $*" >> "$STUB_LOG"\n'
           'for arg in "$@"; do [[ "$arg" == file://*cloud-init.yaml ]] && cp "${arg#file://}" "$STUB_DIR/cloud-init.yaml"; done\n'
           'case "$2" in\n'
           '  create-security-group) echo sg-0abc ;;\n'
           '  get-parameters) echo ami-0abc ;;\n'
           '  run-instances) echo i-0abc ;;\n'
           '  allocate-address) echo eipalloc-0abc ;;\n'
           '  describe-addresses) echo 203.0.113.10 ;;\n'
           'esac\n',
    "ssh": 'echo "ssh $*" >> "$STUB_LOG"\n'
           'if [[ "$*" == *"cloud-init status --wait"* ]]; then echo "status: ${STUB_SETUP:-done}"; fi\n',
    "ssh-keygen": 'while [[ $# -gt 0 ]]; do [[ "$1" == -f ]] && { touch "$2" "$2.pub"; }; shift; done\n',
}


@pytest.fixture
def provision(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name, body in STUBS.items():
        stub = bin_dir / name
        stub.write_text("#!/usr/bin/env bash\n" + body)
        stub.chmod(stub.stat().st_mode | stat.S_IEXEC)
    log = tmp_path / "calls.log"

    def run(*args, env_extra=None):
        env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}", "HOME": str(tmp_path), "STUB_LOG": str(log),
               "STUB_DIR": str(tmp_path), **(env_extra or {})}
        result = subprocess.run([BASH, str(SCRIPT), *args], capture_output=True, text=True,  # noqa: S603
                                env=env, timeout=60, check=False)
        result.calls = log.read_text().splitlines() if log.exists() else []
        result.cloud_init = (tmp_path / "cloud-init.yaml").read_text() if (tmp_path / "cloud-init.yaml").exists() else ""
        return result

    return run


def test_azure_creates_an_ssh_only_vm_opens_https_and_prints_the_github_settings(provision):
    result = provision("azure", "asd-demo")

    assert result.returncode == 0, result.stderr
    create = next(call for call in result.calls if call.startswith("az vm create"))
    for argument in ("--image Ubuntu2404", "--admin-username asd", "--authentication-type ssh",
                     "--public-ip-address-dns-name asd-demo", "--public-ip-sku Standard", "--nsg-rule SSH"):
        assert argument in create
    assert "az vm open-port --resource-group asd-demo --name asd-demo --port 80,443 --priority 1010 --output none" in result.calls
    assert 'gh variable set CLOUD_DOMAIN --body "asd-demo.australiaeast.cloudapp.azure.com"' in result.stdout
    assert 'gh variable set CLOUD_HOST --body "asd-demo.australiaeast.cloudapp.azure.com"' in result.stdout
    assert 'gh variable set CLOUD_USER --body "asd"' in result.stdout
    assert "az group delete --name asd-demo --yes" in result.stdout


def test_azure_first_boot_setup_is_for_the_deploy_user(provision):
    result = provision("azure", "asd-demo")

    assert "usermod -aG docker asd" in result.cloud_init
    assert "-o asd -g asd /opt/asd /opt/asd/releases /opt/asd/data /opt/asd/backups /opt/asd/bin" in result.cloud_init
    assert "__DEPLOY_USER__" not in result.cloud_init


def test_aws_encrypts_the_disk_opens_only_ssh_and_https_and_uses_an_sslip_domain(provision):
    result = provision("aws", "asd-demo")

    assert result.returncode == 0, result.stderr
    run = next(call for call in result.calls if call.startswith("aws ec2 run-instances"))
    assert "Encrypted=true" in run and "--image-id ami-0abc" in run and "--security-group-ids sg-0abc" in run
    ports = [call.split("--port ")[1].split()[0] for call in result.calls if "authorize-security-group-ingress" in call]
    assert ports == ["22", "80", "443"]
    assert "aws ec2 associate-address --instance-id i-0abc --allocation-id eipalloc-0abc --output text" in result.calls
    assert 'gh variable set CLOUD_HOST --body "203.0.113.10"' in result.stdout
    assert 'gh variable set CLOUD_DOMAIN --body "203-0-113-10.sslip.io"' in result.stdout
    assert 'gh variable set CLOUD_USER --body "ubuntu"' in result.stdout
    assert "usermod -aG docker ubuntu" in result.cloud_init


def test_the_region_and_size_can_be_overridden(provision):
    result = provision("azure", "asd-demo", env_extra={"ASD_REGION": "eastus", "ASD_VM_SIZE": "Standard_B4ms"})

    assert "--size Standard_B4ms" in next(call for call in result.calls if call.startswith("az vm create"))
    assert 'gh variable set CLOUD_DOMAIN --body "asd-demo.eastus.cloudapp.azure.com"' in result.stdout


def test_the_vm_is_checked_for_docker_and_opt_asd_after_first_boot(provision):
    result = provision("azure", "asd-demo")

    checks = [call for call in result.calls if call.startswith("ssh ")]
    assert any("cloud-init status --wait" in call for call in checks)
    assert any("docker compose version" in call and "test -w /opt/asd/releases" in call for call in checks)
    assert all("StrictHostKeyChecking=accept-new" in call and "asd-demo.known_hosts" in call for call in checks)


def test_a_failed_first_boot_setup_fails_and_points_at_its_log(provision):
    result = provision("azure", "asd-demo", env_extra={"STUB_SETUP": "error"})

    assert result.returncode == 1
    assert "cloud-init-output.log" in result.stderr
    assert "gh variable set" not in result.stdout


@pytest.mark.parametrize("name", ["", "ab", "Upper-case", "-leading", "trailing-", "semi;colon", "a" * 43])
def test_unsafe_names_are_refused_before_any_cloud_call(provision, name):
    result = provision("azure", name)

    assert result.returncode == 1
    assert "name must be" in result.stderr
    assert result.calls == []


def test_an_unknown_provider_is_refused_before_any_cloud_call(provision):
    result = provision("gcp", "asd-demo")

    assert result.returncode == 1
    assert "usage: provision-vm.sh <azure|aws> <name>" in result.stderr
    assert result.calls == []
