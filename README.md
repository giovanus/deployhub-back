# DeployHub Backend

Un mini-PaaS permettant de déployer des conteneurs Docker à partir de dépôts GitHub ou de fichiers Zip contenant un `Dockerfile` ou un `docker-compose.yml`.

## Prérequis

- **Python 3.10+**
- **Docker** (installé et en cours d'exécution)
- **Redis** (installé et en cours d'exécution pour Celery)
- **Git**

---

## Installation

### 1. Cloner le projet
```bash
git clone <url-du-repo>
cd deployhub-back
```

### 2. Créer l'environnement virtuel

**Sur Linux :**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Sur Windows (PowerShell) :**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Installer les dépendances
```bash
pip install -r requirements.txt
```

### 4. Configuration
Créez un fichier `.env` à la racine (ou copiez `.env.example`) :
```env
DATABASE_URL=sqlite:///./sql_app.db
SECRET_KEY=votre_cle_secrete_ici
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

---

## Lancement de l'application

Il est nécessaire de lancer trois composants pour que le système fonctionne pleinement.

### 1. Démarrer Redis (si non lancé)
Assurez-vous que Redis est actif pour la gestion des tâches en arrière-plan.
```bash
redis-cli ping  # Doit répondre PONG
```

### 2. Lancer le serveur API (FastAPI)
```bash
uvicorn app.main:app --reload
```
L'API sera disponible sur : `http://localhost:8000`

### 3. Lancer le Worker Celery (Arrière-plan)
Ouvrez un nouveau terminal, activez l'environnement virtuel et lancez :

**Sur Linux :**
```bash
celery -A app.core.celery_app worker --loglevel=info -Q deployments
```

**Sur Windows :**
*Note: Sous Windows, Celery nécessite l'option `--pool=solo`.*
```bash
celery -A app.core.celery_app worker --loglevel=info -Q deployments --pool=solo
```

---

## Utilisation de l'API

### Déployer depuis GitHub
**POST** `/deployments/github`
```json
{
  "name": "mon-app-web",
  "github_url": "https://github.com/votre-user/votre-repo",
  "branch": "main"
}
```

### Déployer depuis un Zip
**POST** `/deployments/zip` (Multi-part form)
- `name`: "nom-de-l-app"
- `file`: (Le fichier .zip)

### Suivre un déploiement
**GET** `/deployments/{id}`
Permet de voir le `status` (pending, building, running, failed) et l' `app_url` une fois terminé.

---

## ⚠️ Notes importantes sur Docker

### Permissions (Linux uniquement)
Assurez-vous que votre utilisateur a le droit d'accéder au socket Docker sans `sudo` :
```bash
sudo usermod -aG docker $USER
# Redémarrez votre session ou votre ordinateur pour appliquer les changements
```

### Ports
Par défaut, le système mappe le port **8000** à l'intérieur de vos conteneurs vers un port aléatoire (8000-9000) sur votre machine. Assurez-vous que vos applications écoutent sur le port 8000 dans leur Dockerfile.
