# Self-Hosted GitHub Actions Runner Setup

This documents how to provision the self-hosted runner on Proxmox VE.
The runner is distinct from the deployment target VM.

## Prerequisites

A PVE VM or LXC with:
- Ubuntu 22.04 or Debian 12
- Internet access (to reach GitHub and download runner binary)
- Network access to the deployment target VM

## 1. Install Docker

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
  https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo usermod -aG docker $USER
```

Log out and back in for the group change to take effect.

## 2. Register the GitHub Actions runner

In the GitHub repository: **Settings → Actions → Runners → New self-hosted runner**. Select Linux and follow the on-screen instructions. They look like:

```bash
mkdir actions-runner && cd actions-runner
curl -o actions-runner-linux-x64-<version>.tar.gz -L https://github.com/actions/runner/releases/download/...
tar xzf ./actions-runner-linux-x64-<version>.tar.gz
./config.sh --url https://github.com/<owner>/finance_tracker --token <TOKEN>
```

Use the exact commands shown on the GitHub page (version and token are generated per registration).

## 3. Run as a systemd service

```bash
sudo ./svc.sh install
sudo ./svc.sh start
sudo ./svc.sh status
```

The runner now starts automatically on boot and appears as online in GitHub.

## 4. SSH key for deployment

The private key lives on the runner machine — it never needs to leave the local network.

Generate a key pair on the runner machine:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/deploy_key -N ""
```

Copy the public key to **both** deployment VMs (test and prod):

```bash
ssh-copy-id -i ~/.ssh/deploy_key.pub user@<test-vm-ip>
ssh-copy-id -i ~/.ssh/deploy_key.pub user@<prod-vm-ip>
```

The deploy workflows reference `~/.ssh/deploy_key` directly. No GitHub secret needed for the key.

Add two GitHub Actions secrets:

1. GitHub repo → **Settings → Secrets and variables → Actions → New repository secret**
2. Name: `DEPLOY_TEST_TARGET`, value: `user@<test-vm-ip>` (e.g. `ubuntu@192.168.1.50`)
3. Name: `DEPLOY_PROD_TARGET`, value: `user@<prod-vm-ip>` (e.g. `ubuntu@192.168.1.51`)

The old `DEPLOY_TARGET` secret can be deleted.

## 5. GHCR authentication on deployment VMs

Both test and prod VMs must authenticate with GHCR once to pull images.

On each VM:

1. Create a GitHub Personal Access Token (classic) with `read:packages` scope:
   GitHub → Settings → Developer settings → Personal access tokens (classic) → Generate new token

2. Log in to GHCR:
   ```bash
   echo <PAT> | docker login ghcr.io -u phildue --password-stdin
   ```

3. Verify:
   ```bash
   cat ~/.docker/config.json | grep ghcr
   ```
   Expected: entry for `ghcr.io` present.

Credentials are stored in `~/.docker/config.json` and persist across reboots.

## 6. Deployment target prerequisites

On the deployment VM (`DEPLOY_TARGET`):

```bash
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo usermod -aG docker $USER
sudo mkdir -p /opt/finance_tracker/data
```

The `data/` directory holds `expenses.db` and persists between deploys (rsync excludes it).
