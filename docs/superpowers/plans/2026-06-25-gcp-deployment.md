# GCP Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Provision a GCP Compute Engine instance using Terraform and configure it to automatically run the production Docker Compose setup with secure ingress via Cloudflare Tunnel.

**Architecture:** A single-instance GCE VM (`e2-medium`) running Ubuntu 22.04 LTS. The VM fetches secrets from GCP instance metadata via a startup script, clones the repository, sets up `.env`, and boots the Docker containers behind a Cloudflare Tunnel.

**Tech Stack:** Terraform, Google Cloud Platform (GCP), Bash, Docker, Docker Compose, Cloudflare Tunnel.

---

### Task 1: Terraform Provider and Variables

**Files:**
- Create: `terraform/providers.tf`
- Create: `terraform/variables.tf`
- Create: `terraform/outputs.tf`

- [ ] **Step 1: Create `terraform/providers.tf`**

Create the provider and version requirements file:
```hcl
terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}
```

- [ ] **Step 2: Create `terraform/variables.tf`**

Create the variables definition file:
```hcl
variable "project_id" {
  type        = string
  description = "The GCP project ID to deploy resources into."
}

variable "region" {
  type        = string
  default     = "us-central1"
  description = "GCP region."
}

variable "zone" {
  type        = string
  default     = "us-central1-a"
  description = "GCP zone."
}

variable "google_api_key" {
  type        = string
  sensitive   = true
  description = "Google Gemini API Key for backend evaluations."
}

variable "cloudflare_tunnel_token" {
  type        = string
  sensitive   = true
  default     = ""
  description = "Cloudflare Tunnel Token for secure ingress."
}

variable "next_public_api_url" {
  type        = string
  default     = ""
  description = "Next.js build-time API URL endpoint."
}
```

- [ ] **Step 3: Create `terraform/outputs.tf`**

Create the output variables file:
```hcl
output "vm_name" {
  value       = google_compute_instance.eval_vm.name
  description = "The name of the provisioned GCE instance."
}

output "vm_external_ip" {
  value       = google_compute_instance.eval_vm.network_interface[0].access_config[0].nat_ip
  description = "The public IP of the VM (useful for SSH maintenance)."
}
```

- [ ] **Step 4: Run validation check**

Run:
```bash
cd terraform && terraform init -backend=false && terraform validate
```
Expected output:
`The configuration is valid.`

- [ ] **Step 5: Commit**

```bash
git add terraform/providers.tf terraform/variables.tf terraform/outputs.tf
git commit -m "infra: initialize terraform providers and variables"
```

---

### Task 2: GCP Resources Definition

**Files:**
- Create: `terraform/main.tf`

- [ ] **Step 1: Create `terraform/main.tf`**

Define the service account, dedicated VPC network, firewall rules, and Compute Engine instance with GCE metadata mapping:
```hcl
resource "google_service_account" "eval_sa" {
  account_id   = "eval-platform-sa"
  display_name = "EvalPlatform VM Service Account"
}

resource "google_compute_network" "eval_vpc" {
  name                    = "eval-platform-vpc"
  auto_create_subnetworks = true
}

resource "google_compute_firewall" "allow_ssh" {
  name    = "eval-allow-ssh"
  network = google_compute_network.eval_vpc.name

  allow {
    protocol = "tcp"
    ports    = ["22", "3000", "8000"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["eval-server"]
}

resource "google_compute_instance" "eval_vm" {
  name         = "eval-platform-demo"
  machine_type = "e2-medium"
  zone         = var.zone
  tags         = ["eval-server"]

  boot_disk {
    initialize_params {
      image = "ubuntu-os-cloud/ubuntu-2204-lts"
      size  = 30
      type  = "pd-balanced"
    }
  }

  network_interface {
    network = google_compute_network.eval_vpc.name
    access_config {
      // Allocate an ephemeral public IP for SSH and outbound updates
    }
  }

  metadata = {
    google_api_key          = var.google_api_key
    cloudflare_tunnel_token = var.cloudflare_tunnel_token
    next_public_api_url     = var.next_public_api_url
  }

  metadata_startup_script = file("${path.module}/scripts/startup.sh")

  service_account {
    email  = google_service_account.eval_sa.email
    scopes = ["cloud-platform"]
  }
}
```

- [ ] **Step 2: Create temporary empty startup script to allow validation**

Run:
```bash
mkdir -p terraform/scripts && touch terraform/scripts/startup.sh
```

- [ ] **Step 3: Run validation check**

Run:
```bash
terraform validate
```
Expected output:
`The configuration is valid.`

- [ ] **Step 4: Commit**

```bash
git add terraform/main.tf terraform/scripts/startup.sh
git commit -m "infra: define terraform resources for VM, firewall, and SA"
```

---

### Task 3: Setup VM Startup Bootstrap Script

**Files:**
- Modify: `terraform/scripts/startup.sh`

- [ ] **Step 1: Write the full startup script**

Replace the contents of `terraform/scripts/startup.sh` with the system provisioning logic:
```bash
#!/bin/bash
# GCP GCE Startup Script
set -e

echo "=== System Update and Dependencies ==="
apt-get update && apt-get upgrade -y
apt-get install -y curl git apt-transport-https ca-certificates gnupg lsb-release

# Install Docker Engine
echo "=== Installing Docker ==="
mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Query GCP Metadata Server for application secrets
echo "=== Loading Secrets from Metadata Server ==="
METADATA_URL="http://metadata.google.internal/computeMetadata/v1/instance/attributes"
GOOGLE_API_KEY=$(curl -H "Metadata-Flavor: Google" "$METADATA_URL/google_api_key")
CLOUDFLARE_TUNNEL_TOKEN=$(curl -H "Metadata-Flavor: Google" "$METADATA_URL/cloudflare_tunnel_token")
NEXT_PUBLIC_API_URL=$(curl -H "Metadata-Flavor: Google" "$METADATA_URL/next_public_api_url")

# Automatically set relative API path if NEXT_PUBLIC_API_URL is empty (triggers Next.js reverse proxy)
if [ -z "$NEXT_PUBLIC_API_URL" ]; then
  echo "NEXT_PUBLIC_API_URL is empty. Setting to relative path /api to utilize Next.js API proxy."
  NEXT_PUBLIC_API_URL="/api"
fi

# Setup App Directory
cd /home/ubuntu
if [ ! -d "eval-platform" ]; then
  echo "=== Cloning Repository ==="
  git clone https://github.com/your-username/eval-platform.git
fi
cd eval-platform

# Generate Production .env File
echo "=== Creating .env ==="
cat <<EOF > .env
GOOGLE_API_KEY=$GOOGLE_API_KEY
CLOUDFLARE_TUNNEL_TOKEN=$CLOUDFLARE_TUNNEL_TOKEN
NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
EOF
chmod 600 .env

# Create Database Volume Path and seed default metrics/prompts
echo "=== Seeding default metrics and prompts to persistent volume ==="
mkdir -p data/fixtures
cp -r backend/fixtures/default_metrics data/fixtures/
cp -r backend/fixtures/prompts data/fixtures/
chown -R ubuntu:ubuntu /home/ubuntu/eval-platform

# Spin Up Containers
echo "=== Launching Docker Compose Workloads ==="
if [ -z "$CLOUDFLARE_TUNNEL_TOKEN" ]; then
  echo "No Cloudflare Tunnel Token detected. Running in Direct IP mode (excluding tunnel)."
  docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d backend frontend
else
  echo "Cloudflare Tunnel Token detected. Running all services including tunnel."
  docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d
fi

echo "=== Deployment Successfully Completed ==="
```

- [ ] **Step 2: Check bash script syntax**

Run:
```bash
bash -n terraform/scripts/startup.sh
```
Expected: No output (which means valid syntax).

- [ ] **Step 3: Commit**

```bash
git add terraform/scripts/startup.sh
git commit -m "infra: write GCE bootstrap startup script"
```

---

### Task 4: Deployment Documentation and Configuration Template

**Files:**
- Create: `terraform/terraform.tfvars.example`

- [ ] **Step 1: Create `terraform/terraform.tfvars.example`**

Write the configuration variables template:
```hcl
project_id              = "your-gcp-project-id"
region                  = "us-central1"
zone                    = "us-central1-a"
google_api_key          = "AIzaSy..."
cloudflare_tunnel_token = "ey..."
next_public_api_url     = "https://eval-api.yourdomain.com"
```

- [ ] **Step 2: Commit**

```bash
git add terraform/terraform.tfvars.example
git commit -m "infra: add terraform tfvars config template"
```
