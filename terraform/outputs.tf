output "vm_name" {
  value       = google_compute_instance.eval_vm.name
  description = "The name of the provisioned GCE instance."
}

output "vm_external_ip" {
  value       = google_compute_instance.eval_vm.network_interface[0].access_config[0].nat_ip
  description = "The public IP of the VM (useful for SSH maintenance)."
}
