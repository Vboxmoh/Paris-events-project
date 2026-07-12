output "app_public_ip" {
  description = "IP publique EC2"
  value       = aws_instance.app.public_ip
}

output "app_url" {
  description = "URL de l'application"
  value       = "http://${aws_instance.app.public_ip}:5000"
}