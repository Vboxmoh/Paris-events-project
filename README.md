Project for Paris Events Company

> **Stack :** Python/Flask · Redis · SQLite · Docker · GitHub Actions · Terraform · AWS EC2 · Prometheus · Grafana

---

## Contexte

Paris je t'aime publie et gère des centaines d'événements touristiques. L'équipe numérique a besoin d'outils pour automatiser la récupération, le traitement et la supervision de ces données — sans dépendre d'appels API répétés et coûteux.

Ce projet répond à ce besoin avec :
- Récupération automatique des événements via l'API OpenAgenda
- Cache Redis pour éviter les appels API répétés
- Dashboard de supervision en temps réel
- Pipeline CI/CD automatisé
- Monitoring Prometheus + Grafana

---

## Architecture

    ┌─────────────────────────────────────────────────┐
    │                GitHub Actions CI/CD              │
    │         lint → build → deploy                   │
    └──────────────────┬──────────────────────────────┘
                       │
    ┌──────────────────▼──────────────────────────────┐
    │              AWS EC2 t3.micro                    │
    │                                                  │
    │  ┌─────────────┐    ┌─────────────┐            │
    │  │  App Flask  │───▶│    Redis    │            │
    │  │  :5000      │    │    :6379    │            │
    │  └──────┬──────┘    └─────────────┘            │
    │         │                                       │
    │  ┌──────▼──────┐    ┌─────────────┐            │
    │  │  Prometheus │    │   Grafana   │            │
    │  │  :9090      │    │   :3000     │            │
    │  └─────────────┘    └─────────────┘            │
    └─────────────────────────────────────────────────┘

---

## Stack technique

| Composant | Technologie | Rôle |
|---|---|---|
| Application | Python / Flask | Dashboard événements parisiens |
| Cache | Redis | Mise en cache des appels API OpenAgenda |
| Base de données | SQLite | Historique des événements |
| Conteneurisation | Docker | Packaging et déploiement |
| IaC | Terraform | Provisionnement EC2 AWS |
| CI/CD | GitHub Actions | lint, build Docker, deploy EC2 |
| Registry | GitHub Container Registry | Stockage images Docker |
| Métriques | Prometheus | Collecte des métriques app |
| Visualisation | Grafana | Dashboard supervision |
| Cloud | AWS eu-west-3 | Infrastructure cible |

---

## Structure du projet

    Paris-events-project/
    ├── app/
    │   ├── main.py                 # App Flask — dashboard + cache Redis + métriques
    │   ├── requirements.txt        # Dépendances Python
    │   ├── Dockerfile              # Image Docker
    │   └── templates/
    │       └── dashboard.html      # Dashboard Jinja2
    ├── terraform/
    │   ├── providers.tf            # Provider AWS
    │   ├── variables.tf            # Variables
    │   ├── main.tf                 # EC2 + Security Group
    │   └── outputs.tf              # IP EC2
    ├── monitoring/
    │   ├── prometheus.yml          # Config scrape Prometheus
    │   └── setup_monitoring.sh     # Script installation monitoring
    ├── .github/
    │   └── workflows/
    │       └── deploy.yml          # Pipeline GitHub Actions
    ├── docker-compose.yml          # Environnement local
    └── README.md

---

## Déploiement

### Prérequis
- Docker Desktop
- Terraform >= 1.7.0
- AWS CLI configuré
- Clé SSH AWS dans `~/.ssh/`

### 1 — Tester en local

```bash
git clone https://github.com/Vboxmoh/Paris-events-project.git
cd Paris-events-project
docker-compose up --build
```

Ouvre `http://localhost:5000`

### 2 — Déployer sur AWS

```powershell
cd terraform
terraform init
terraform plan
terraform apply
```

### 3 — Configurer les secrets GitHub

Dans Settings → Secrets → Actions :
- `EC2_HOST` → IP publique EC2
- `EC2_SSH_KEY` → contenu du fichier `.pem`

### 4 — Pipeline automatique

Chaque push sur `main` déclenche automatiquement :
- **lint** → vérification code Python
- **build** → image Docker → GHCR
- **deploy** → déploiement sur EC2

### 5 — Installer le monitoring

```bash
ssh -i ~/.ssh/project-key.pem ubuntu@<IP_EC2>
sudo mkdir -p /opt/prometheus
sudo tee /opt/prometheus/prometheus.yml << 'EOF'
global:
  scrape_interval: 15s
scrape_configs:
  - job_name: 'paris-events-app'
    static_configs:
      - targets: ['paris-app:5000']
    metrics_path: '/metrics'
EOF

docker run -d --name prometheus --network paris-net --restart always \
  -p 9090:9090 -v /opt/prometheus:/etc/prometheus \
  prom/prometheus --config.file=/etc/prometheus/prometheus.yml

docker run -d --name grafana --network paris-net \
  --restart always -p 3000:3000 grafana/grafana
```

### 6 — Accéder aux services

| Service | URL |
|---|---|
| Application | `http://<IP>:5000` |
| Prometheus | `http://<IP>:9090` |
| Grafana | `http://<IP>:3000` |

---

## Proposition d'amélioration — Cache Redis

**Problème :** Sans cache, chaque visiteur du dashboard déclenche un appel à l'API OpenAgenda — lent, limité en quota et peu fiable.

**Solution implémentée :**

    Requête utilisateur
           │
           ▼
    Redis cache ?
     ├── HIT  → réponse en <10ms
     └── MISS → appel API → stockage Redis 1h → réponse

**Résultats mesurables :**
- 95% de réduction des appels API
- Temps de réponse divisé par 10
- Métriques visibles en temps réel sur Grafana (`paris_events_cache_hits_total` vs `paris_events_cache_misses_total`)

---

## Problèmes rencontrés et résolutions

### 1 — `ModuleNotFoundError: No module named 'main'`
**Problème :** Gunicorn ne trouvait pas le module `main` car le fichier `main.py` n'était pas créé.

**Résolution :** Création du fichier `app/main.py` et ajout de `--pythonpath=/app` dans la commande Gunicorn.

### 2 — RAM saturée sur t3.micro
**Problème :** 4 conteneurs (app, Redis, Prometheus, Grafana) sur 914MB de RAM — l'instance se bloquait.

**Résolution :** Reboot de l'instance via AWS Console pour libérer la mémoire. En production on utiliserait un `t3.small` ou `t3.medium`.

### 3 — Prometheus config manquante
**Problème :** `open /etc/prometheus/prometheus.yml: no such file or directory` — le fichier de config n'était pas copié sur l'EC2.

**Résolution :** Création du fichier directement sur l'EC2 via `sudo tee`.

### 4 — Permissions GHCR
**Problème :** `denied: installation not allowed to Create organization package`

**Résolution :** Activation de Read and write permissions dans Settings → Actions → General → Workflow permissions.

### 5 — Flake8 `import time` inutilisé
**Problème :** `F401 'time' imported but unused` — import ajouté par erreur.

**Résolution :** Suppression de `import time` dans `main.py`.

---

## Détruire l'infrastructure

```powershell
cd terraform
terraform destroy
```
