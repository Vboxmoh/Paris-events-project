#!/bin/bash
# ─────────────────────────────────────────────
# Script d'installation Prometheus + Grafana
# Supervision post-déploiement Paris Events
# ─────────────────────────────────────────────

echo "Installation Prometheus..."
docker run -d \
  --name prometheus \
  --network paris-net \
  --restart always \
  -p 9090:9090 \
  -v /opt/prometheus:/etc/prometheus \
  prom/prometheus \
  --config.file=/etc/prometheus/prometheus.yml

echo "Installation Grafana..."
docker run -d \
  --name grafana \
  --network paris-net \
  --restart always \
  -p 3000:3000 \
  grafana/grafana

echo "✅ Monitoring installé"
echo "Prometheus : http://$(curl -s ifconfig.me):9090"
echo "Grafana    : http://$(curl -s ifconfig.me):3000"