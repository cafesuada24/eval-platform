resource "google_service_account" "eval_sa" {
  account_id   = "eval-platform-sa"
  display_name = "EvalPlatform VM Service Account"
}

resource "google_compute_firewall" "allow_ssh" {
  name    = "eval-allow-ssh"
  network = "default"

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
    network = "default"
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
