#!/usr/bin/env bash
# Create the Linux VM that cloud-deployment.yml deploys to, on Azure or AWS, and print the GitHub settings it needs.
#
#   bash scripts/deploy/provision-vm.sh azure <name>     # needs the Azure CLI, signed in (az login)
#   bash scripts/deploy/provision-vm.sh aws <name>       # needs the AWS CLI, signed in (aws configure / aws sso login)
#
# <name> (lowercase letters, digits, hyphens) names the resources. On Azure it is also the DNS label, so the public domain is
# <name>.<region>.cloudapp.azure.com and must be unique in that region. On AWS the domain is <elastic-ip>.sslip.io, a public
# DNS name that resolves to the IP, because Let's Encrypt does not issue certificates for amazonaws.com names.
#
# What it creates: an Ubuntu 24.04 VM with a 64 GB disk encrypted at rest, a firewall that allows only 22, 80 and 443, and a
# static public address. deploy/cloud/cloud-init.yaml installs Docker and prepares /opt/asd on first boot. It then waits for that
# setup to finish and checks Docker and /opt/asd over SSH. Run it once per VM; it does not update an existing one.
#
# Optional environment: ASD_REGION (default australiaeast / ap-southeast-2), ASD_VM_SIZE (default Standard_B2ms / t3.large,
# 2 vCPU and 8 GB, enough for the application plus one 3B model for the cloud AI bonus), ASD_SSH_KEY (default
# ~/.ssh/asd-<name>, created if missing; it has no passphrase because GitHub Actions uses it unattended).
set -euo pipefail
export MSYS_NO_PATHCONV=1  # Git Bash on Windows would otherwise rewrite arguments such as /aws/service/... and /dev/sda1

fail() { echo "provision: $*" >&2; exit 1; }
# The Windows builds of az and aws cannot read Git Bash paths such as /tmp/...; give them a native path.
native_path() { if command -v cygpath > /dev/null; then cygpath -w "$1"; else printf '%s' "$1"; fi; }

provider="${1:-}"
name="${2:-}"
[[ "$provider" == azure || "$provider" == aws ]] || fail "usage: provision-vm.sh <azure|aws> <name>"
[[ "$name" =~ ^[a-z][a-z0-9-]{1,40}[a-z0-9]$ ]] || fail "name must be 3 to 42 lowercase letters, digits or hyphens, starting with a letter"
for tool in ssh ssh-keygen; do command -v "$tool" > /dev/null || fail "OpenSSH ($tool) is required"; done

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
key="${ASD_SSH_KEY:-$HOME/.ssh/asd-$name}"
known_hosts="$key.known_hosts"
if [[ ! -f "$key" ]]; then
  mkdir -p "$(dirname "$key")"
  ssh-keygen -q -t ed25519 -N "" -C "asd-deploy-$name" -f "$key"
  echo "provision: created deploy key $key"
fi

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

provision_azure() {
  command -v az > /dev/null || fail "the Azure CLI (az) is not installed"
  az account show --output none 2> /dev/null || fail "sign in first: az login"
  region="${ASD_REGION:-australiaeast}"
  user=asd
  sed "s/__DEPLOY_USER__/$user/g" "$root/deploy/cloud/cloud-init.yaml" > "$work/cloud-init.yaml"

  echo "provision: creating resource group $name and VM $name in $region (about 3 minutes)"
  az group create --name "$name" --location "$region" --output none
  # Standard public IP is static. Azure encrypts managed disks at rest with platform-managed keys by default.
  az vm create --resource-group "$name" --name "$name" --image Ubuntu2404 --size "${ASD_VM_SIZE:-Standard_B2ms}" \
    --admin-username "$user" --ssh-key-values "$(native_path "$key.pub")" --authentication-type ssh \
    --public-ip-sku Standard --public-ip-address-dns-name "$name" --os-disk-size-gb 64 \
    --custom-data "$(native_path "$work/cloud-init.yaml")" --nsg-rule SSH --output none
  az vm open-port --resource-group "$name" --name "$name" --port 80,443 --priority 1010 --output none

  domain="$name.$region.cloudapp.azure.com"
  host="$domain"
  teardown="az group delete --name $name --yes"
  encryption="az disk show --ids \"\$(az vm show -g $name -n $name --query storageProfile.osDisk.managedDisk.id -o tsv)\" --query encryption"
}

provision_aws() {
  command -v aws > /dev/null || fail "the AWS CLI (aws) is not installed"
  aws sts get-caller-identity --output text > /dev/null 2>&1 || fail "sign in first: aws configure (or aws sso login)"
  export AWS_DEFAULT_REGION="${ASD_REGION:-ap-southeast-2}"
  user=ubuntu  # the Ubuntu AMI's default account, which receives the key pair
  sed "s/__DEPLOY_USER__/$user/g" "$root/deploy/cloud/cloud-init.yaml" > "$work/cloud-init.yaml"

  echo "provision: creating key pair, security group and instance $name in $AWS_DEFAULT_REGION (about 2 minutes)"
  aws ec2 import-key-pair --key-name "$name" --public-key-material "fileb://$(native_path "$key.pub")" --output text > /dev/null
  group="$(aws ec2 create-security-group --group-name "$name" --description "ASD gateway: SSH, HTTP, HTTPS" \
    --query GroupId --output text)"
  for port in 22 80 443; do
    aws ec2 authorize-security-group-ingress --group-id "$group" --protocol tcp --port "$port" --cidr 0.0.0.0/0 --output text > /dev/null
  done
  ami="$(aws ssm get-parameters --names /aws/service/canonical/ubuntu/server/24.04/stable/current/amd64/hvm/ebs-gp3/ami-id \
    --query 'Parameters[0].Value' --output text)"
  instance="$(aws ec2 run-instances --image-id "$ami" --instance-type "${ASD_VM_SIZE:-t3.large}" --key-name "$name" \
    --security-group-ids "$group" --user-data "file://$(native_path "$work/cloud-init.yaml")" \
    --block-device-mappings 'DeviceName=/dev/sda1,Ebs={VolumeSize=64,VolumeType=gp3,Encrypted=true}' \
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$name}]" \
    --query 'Instances[0].InstanceId' --output text)"
  aws ec2 wait instance-running --instance-ids "$instance"
  allocation="$(aws ec2 allocate-address --domain vpc --tag-specifications "ResourceType=elastic-ip,Tags=[{Key=Name,Value=$name}]" \
    --query AllocationId --output text)"
  aws ec2 associate-address --instance-id "$instance" --allocation-id "$allocation" --output text > /dev/null
  host="$(aws ec2 describe-addresses --allocation-ids "$allocation" --query 'Addresses[0].PublicIp' --output text)"

  domain="${host//./-}.sslip.io"
  teardown="aws ec2 terminate-instances --instance-ids $instance && aws ec2 wait instance-terminated --instance-ids $instance && aws ec2 release-address --allocation-id $allocation && aws ec2 delete-security-group --group-id $group && aws ec2 delete-key-pair --key-name $name"
  encryption="aws ec2 describe-volumes --filters Name=attachment.instance-id,Values=$instance --query 'Volumes[].Encrypted'"
}

"provision_$provider"

ssh_vm() { ssh -i "$key" -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new \
  -o UserKnownHostsFile="$known_hosts" "$user@$host" "$@"; }

echo "provision: waiting for SSH on $host"
for attempt in $(seq 1 30); do
  ssh_vm true 2> /dev/null && break
  [[ "$attempt" -lt 30 ]] || fail "SSH to $user@$host did not come up within 5 minutes"
  sleep 10
done
# The host key is recorded on this first connection to a VM created moments ago; GitHub Actions then pins it (CLOUD_KNOWN_HOSTS).
echo "provision: waiting for first-boot setup (Docker install; a few minutes)"
# cloud-init exits 2 for "done with warnings", so judge the reported status rather than the exit code.
setup="$(ssh_vm "cloud-init status --wait" || true)"
[[ "$setup" == *"status: done"* ]] \
  || fail "first-boot setup did not finish cleanly ($setup); inspect it with: ssh -i $key $user@$host 'sudo cat /var/log/cloud-init-output.log'"
# A new SSH session, so the deploy user's docker group membership applies.
ssh_vm "docker compose version > /dev/null && test -w /opt/asd/releases && test -w /opt/asd/data && test -d /opt/asd/bin" \
  || fail "the VM is up but Docker or /opt/asd is not ready for $user"

cat << EOF

provision: the VM is ready. Domain: https://$domain

Give the Cloud Deployment workflow access (GitHub CLI, from this repository):

  gh variable set CLOUD_HOST --body "$host"
  gh variable set CLOUD_USER --body "$user"
  gh variable set CLOUD_DOMAIN --body "$domain"
  gh secret set CLOUD_SSH_KEY < "$key"
  gh secret set CLOUD_KNOWN_HOSTS < "$known_hosts"

Then deploy: gh workflow run cloud-deployment.yml --ref main
(or Actions > Cloud Deployment > Run workflow; set ai_services, for example ai,mcp,rag,multi-agent, for the cloud AI bonus).

Disk encryption evidence (bonus B6): $encryption
SSH from this machine:  ssh -i "$key" -o UserKnownHostsFile="$known_hosts" $user@$host
Delete everything (stops all charges): $teardown
EOF
