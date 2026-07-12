import requests
import sqlite3
import redis
import json
import os
from datetime import datetime
from flask import Flask, render_template

app = Flask(__name__)

# ─────────────────────────────────────────────
# Configuration
# Variables d'environnement pour la portabilité
# entre on-premise et cloud
# ─────────────────────────────────────────────
OPENAGENDA_KEY = os.getenv('OPENAGENDA_KEY', '')
OPENAGENDA_UID = os.getenv('OPENAGENDA_UID', '63963990')
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
DB_PATH = os.getenv('DB_PATH', '/app/data/events.db')
CACHE_TTL = int(os.getenv('CACHE_TTL', 3600))  # 1 heure

# ─────────────────────────────────────────────
# Connexion Redis — cache des événements
# Evite des appels API répétés inutiles
# C'est la proposition d'amélioration :
# sans Redis chaque requête appelle l'API
# avec Redis on économise 95% des appels
# ─────────────────────────────────────────────
try:
    cache = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    cache.ping()
    REDIS_AVAILABLE = True
except Exception:
    REDIS_AVAILABLE = False
    cache = None


def get_db():
    """Connexion SQLite — stockage persistant des événements"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialise la base de données SQLite"""
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS events (
            uid TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            location TEXT,
            date_start TEXT,
            date_end TEXT,
            category TEXT,
            image_url TEXT,
            fetched_at TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()


def fetch_events_from_api():
    """
    Récupère les événements depuis l'API OpenAgenda
    OpenAgenda = plateforme officielle des événements parisiens
    utilisée par la Mairie de Paris et les offices de tourisme
    """
    url = f"https://api.openagenda.com/v2/agendas/{OPENAGENDA_UID}/events"
    params = {
        'key': OPENAGENDA_KEY,
        'size': 20,
        'lang': 'fr',
        'sort': 'timingsWithFeatured.asc',
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get('events', [])
    except Exception as e:
        print(f"API Error: {e}")
        return get_mock_events()


def get_mock_events():
    """
    Données de démonstration si l'API n'est pas disponible
    Simule des événements réalistes de Paris je t'aime
    """
    return [
        {
            'uid': '1001',
            'title': {'fr': 'Visite guidée du Louvre'},
            'description': {'fr': 'Découvrez les chefs-d\'œuvre du Louvre avec un guide expert.'},
            'location': {'name': 'Musée du Louvre', 'city': 'Paris'},
            'dateRange': {'fr': 'Du 1 au 31 juillet 2026'},
            'firstTiming': {'begin': '2026-07-01T09:00:00', 'end': '2026-07-01T12:00:00'},
            'category': 'Culture',
        },
        {
            'uid': '1002',
            'title': {'fr': 'Concert en plein air aux Tuileries'},
            'description': {'fr': 'Profitez d\'un concert gratuit dans le jardin des Tuileries.'},
            'location': {'name': 'Jardin des Tuileries', 'city': 'Paris'},
            'dateRange': {'fr': 'Juillet 2026'},
            'firstTiming': {'begin': '2026-07-15T19:00:00', 'end': '2026-07-15T22:00:00'},
            'category': 'Musique',
        },
        {
            'uid': '1003',
            'title': {'fr': 'Exposition Impressionnisme — Musée d\'Orsay'},
            'description': {'fr': 'Une exposition exceptionnelle sur les maîtres de l\'Impressionnisme.'},
            'location': {'name': 'Musée d\'Orsay', 'city': 'Paris'},
            'dateRange': {'fr': 'Juin - Septembre 2026'},
            'firstTiming': {'begin': '2026-06-01T10:00:00', 'end': '2026-09-30T18:00:00'},
            'category': 'Exposition',
        },
        {
            'uid': '1004',
            'title': {'fr': 'Balade en bateau sur la Seine'},
            'description': {'fr': 'Croisière commentée sur la Seine avec vue sur les monuments.'},
            'location': {'name': 'Port de la Bourdonnais', 'city': 'Paris'},
            'dateRange': {'fr': 'Tous les jours'},
            'firstTiming': {'begin': '2026-07-11T10:00:00', 'end': '2026-07-11T11:30:00'},
            'category': 'Tourisme',
        },
        {
            'uid': '1005',
            'title': {'fr': 'Festival Gastronomique Paris'},
            'description': {'fr': 'Dégustez les meilleures spécialités culinaires parisiennes.'},
            'location': {'name': 'Place de la République', 'city': 'Paris'},
            'dateRange': {'fr': '15-20 juillet 2026'},
            'firstTiming': {'begin': '2026-07-15T12:00:00', 'end': '2026-07-20T22:00:00'},
            'category': 'Gastronomie',
        },
    ]


def get_events():
    """
    Récupère les événements avec stratégie cache-first :
    1. Cherche dans Redis (cache)
    2. Si absent → appelle l'API
    3. Stocke en Redis pour CACHE_TTL secondes
    4. Sauvegarde en SQLite pour l'historique
    """
    cache_key = "paris_events"

    # Étape 1 — Cherche dans le cache Redis
    if REDIS_AVAILABLE:
        cached = cache.get(cache_key)
        if cached:
            print("Cache HIT — données servies depuis Redis")
            return json.loads(cached)

    # Étape 2 — Cache MISS → appel API
    print("Cache MISS — appel API OpenAgenda")
    raw_events = fetch_events_from_api()

    # Étape 3 — Normalise les données
    events = []
    for e in raw_events:
        event = {
            'uid': str(e.get('uid', '')),
            'title': e.get('title', {}).get('fr', 'Sans titre'),
            'description': e.get('description', {}).get('fr', ''),
            'location': e.get('location', {}).get('name', 'Paris'),
            'date_range': e.get('dateRange', {}).get('fr', ''),
            'date_start': e.get('firstTiming', {}).get('begin', ''),
            'category': e.get('category', 'Événement'),
        }
        events.append(event)

    # Étape 4 — Stocke dans Redis
    if REDIS_AVAILABLE:
        cache.setex(cache_key, CACHE_TTL, json.dumps(events))
        print(f"Données mises en cache Redis pour {CACHE_TTL}s")

    # Étape 5 — Sauvegarde dans SQLite
    save_events_to_db(events)

    return events


def save_events_to_db(events):
    """Sauvegarde les événements en SQLite pour l'historique"""
    conn = get_db()
    for e in events:
        conn.execute('''
            INSERT OR REPLACE INTO events
            (uid, title, description, location, date_start, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            e['uid'], e['title'], e['description'],
            e['location'], e['date_start'],
            datetime.now().isoformat()
        ))
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────
# ROUTES FLASK
# ─────────────────────────────────────────────

@app.route('/')
def dashboard():
    """Dashboard principal — rapport des événements parisiens"""
    events = get_events()
    stats = {
        'total': len(events),
        'cache_status': 'Redis actif' if REDIS_AVAILABLE else 'Sans cache',
        'generated_at': datetime.now().strftime('%d/%m/%Y à %H:%M'),
    }
    return render_template('dashboard.html', events=events, stats=stats)


@app.route('/health')
def health():
    """Health check pour le load balancer et monitoring"""
    return {
        'status': 'healthy',
        'redis': REDIS_AVAILABLE,
        'timestamp': datetime.now().isoformat()
    }


@app.route('/api/events')
def api_events():
    """API REST — retourne les événements en JSON"""
    return {'events': get_events(), 'count': len(get_events())}


if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=False)


# Initialisation au chargement par Gunicorn
with app.app_context():
    try:
        init_db()
    except Exception as e:
        print(f"DB init warning: {e}")
