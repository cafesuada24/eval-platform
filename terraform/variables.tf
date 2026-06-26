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
