# ─────────────────────────────────────────────
# DATA SOURCE — VPC par défaut
# ─────────────────────────────────────────────
data "aws_vpc" "default" {
  default = true
}

# ─────────────────────────────────────────────
# SECURITY GROUP
# Ouvre les ports nécessaires à l'app
# ─────────────────────────────────────────────
resource "aws_security_group" "app" {
  name        = "${var.project_name}-sg"
  description = "Allow HTTP and SSH"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "App port"
    from_port   = 5000
    to_port     = 5000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Prometheus"
    from_port   = 9090
    to_port     = 9090
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Grafana"
    from_port   = 3000
    to_port     = 3000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name    = "${var.project_name}-sg"
    Project = var.project_name
  }
}

# ─────────────────────────────────────────────
# EC2 — Serveur applicatif
# user_data installe Docker et lance l'app
# automatiquement au premier démarrage
# ─────────────────────────────────────────────
resource "aws_instance" "app" {
  ami                         = "ami-0160e8d70ebc43ee1"
  instance_type               = var.instance_type
  key_name                    = var.key_pair_name
  vpc_security_group_ids      = [aws_security_group.app.id]
  associate_public_ip_address = true

  # ─────────────────────────────────────────────
  # USER DATA — script bash exécuté au démarrage
  # Installe Docker, clone le repo et lance l'app
  # Remplace Ansible pour une infra simple
  # ─────────────────────────────────────────────
  user_data = <<-EOF
    #!/bin/bash
    apt-get update -y
    apt-get install -y docker.io docker-compose
    systemctl start docker
    systemctl enable docker
    usermod -aG docker ubuntu
  EOF

  tags = {
    Name    = "${var.project_name}-app"
    Project = var.project_name
  }
}