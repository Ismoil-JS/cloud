# TaskFlow — Django Project & Task Manager

A fully containerised Django web application for managing projects and tasks,
deployed to a cloud server with HTTPS and a complete CI/CD pipeline.

Built for the **Distributed Systems and Cloud Computing (6BUIS014C)** module
at Westminster International University in Tashkent.

---

## Features

- **User authentication** — register, login, logout
- **Project management** — create, view, edit, delete projects
- **Task management** — full CRUD with status (To Do / In Progress / Done), priority, due date
- **Kanban-style board** — tasks organised by status within each project
- **Tag system** — many-to-many tags on tasks with colour labels
- **User assignment** — assign tasks to any registered user
- **Admin panel** — full Django admin for all models
- **Health check endpoint** — `/health/` returns JSON app + DB status
- **Responsive UI** — Bootstrap 5, mobile-friendly

---

## Technologies

| Layer | Technology |
|---|---|
| Backend | Django 4.2, Python 3.11, Gunicorn |
| Database | PostgreSQL 15 |
| Proxy | Nginx 1.25 |
| Containerisation | Docker, Docker Compose |
| CI/CD | GitHub Actions |
| Registry | Docker Hub |
| Cloud Server | Eskiz / Azure VM (Ubuntu 24.04) |
| SSL | Let's Encrypt (Certbot) |

---

## Database Schema

```
User (Django built-in)
  |
  |-- owns many --> Project
                      |
                      |-- has many --> Task <--many-to-many--> Tag
                                          |
                                          |-- assigned to --> User (nullable)
```

**Relationships:**
- `Project.owner` → `User` (many-to-one, FK)
- `Task.project` → `Project` (many-to-one, FK)
- `Task.assigned_to` → `User` (many-to-one, FK, nullable)
- `Task.tags` ↔ `Tag` (many-to-many)

---

## Local Setup (without Docker)

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/taskflow.git
cd taskflow

# 2. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate        # Linux / macOS
# or: venv\Scripts\activate     # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy environment file
cp .env.example .env
# Edit .env: set DJANGO_SECRET_KEY and leave DB_ENGINE as sqlite3 for local dev

# 5. Run migrations and create superuser
python manage.py migrate
python manage.py createsuperuser

# 6. Run the development server
python manage.py runserver
# Open: http://localhost:8000
```

---

## Local Setup (with Docker Compose — dev)

```bash
cp .env.example .env
# Edit .env: set DJANGO_SECRET_KEY

docker compose -f docker-compose.dev.yml up -d
docker compose -f docker-compose.dev.yml ps
# Open: http://localhost:8000

# Create a superuser
docker compose -f docker-compose.dev.yml exec web python manage.py createsuperuser
```

---

## Running Tests

```bash
# Without Docker
python manage.py test --verbosity=2

# With Docker (dev compose)
docker compose -f docker-compose.dev.yml exec web python manage.py test

# Using pytest
pytest
```

---

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `DJANGO_SECRET_KEY` | Django secret key (**required**) | insecure dev key |
| `DEBUG` | Enable debug mode | `True` |
| `ALLOWED_HOSTS` | Comma-separated allowed hostnames | `localhost,127.0.0.1` |
| `DB_ENGINE` | Database backend | `django.db.backends.sqlite3` |
| `DB_NAME` | PostgreSQL database name | `taskmanager` |
| `DB_USER` | PostgreSQL user | `taskmanager` |
| `DB_PASSWORD` | PostgreSQL password | *(empty)* |
| `DB_HOST` | PostgreSQL host | `db` |
| `DB_PORT` | PostgreSQL port | `5432` |
| `SECURE_SSL_REDIRECT` | Redirect HTTP to HTTPS | `True` (when `DEBUG=False`) |

---

## Production Deployment

See [SERVER_SETUP.md](SERVER_SETUP.md) for the full step-by-step server provisioning guide.

### Quick summary:
1. Provision an Ubuntu 24.04 VM (Eskiz / Azure)
2. Install Docker, Docker Compose, configure UFW firewall (ports 22, 80, 443)
3. Clone this repo and create a production `.env` on the server
4. Obtain an SSL certificate via Certbot (`sudo certbot certonly --standalone -d yourdomain.com`)
5. Set GitHub Secrets (see below) and push to `main` — CI/CD handles the rest

---

## CI/CD Pipeline (GitHub Actions)

The workflow at [`.github/workflows/deploy.yml`](.github/workflows/deploy.yml)
runs automatically on every push to `main`:

```
Push to main
   │
   ▼
[Test] flake8 lint + Django tests (against PostgreSQL service)
   │  (PR-only: stops here)
   ▼
[Build] docker build → push to Docker Hub (tagged :latest and :<commit-sha>)
   │
   ▼
[Deploy] SSH into server → pull image → docker compose up → migrate → collectstatic
```

### Required GitHub Secrets

Go to **Settings → Secrets and variables → Actions** and add:

| Secret | Value |
|---|---|
| `DOCKERHUB_USERNAME` | Your Docker Hub username |
| `DOCKERHUB_TOKEN` | Docker Hub access token (not your password) |
| `SSH_HOST` | Server IP or domain |
| `SSH_USERNAME` | SSH username (e.g. `azureuser`) |
| `SSH_PRIVATE_KEY` | Contents of your private SSH key (`cat ~/.ssh/deploy_key`) |

---

## Live URLs

| Service | URL |
|---|---|
| Application | `https://yourdomain.com` |
| Admin Panel | `https://yourdomain.com/admin/` |
| Health Check | `https://yourdomain.com/health/` |
| GitHub Repo | `https://github.com/YOUR_USERNAME/taskflow` |
| Docker Hub | `https://hub.docker.com/r/YOUR_USERNAME/taskflow` |

**Test credentials for assessor:**
- Username: `student`
- Password: `TaskFlow2025!`

---

## Project Structure

```
taskflow/
├── .github/workflows/deploy.yml   # CI/CD pipeline
├── config/                        # Django project settings & URLs
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── core/                          # Main application
│   ├── migrations/
│   ├── models.py                  # Project, Task, Tag models
│   ├── views.py                   # All views (CBVs + health check)
│   ├── forms.py                   # ProjectForm, TaskForm, RegisterForm
│   ├── admin.py                   # Admin configuration
│   ├── urls.py                    # URL routing
│   └── tests.py                   # 15+ test cases
├── templates/                     # HTML templates (Bootstrap 5)
│   ├── base.html
│   ├── home.html
│   ├── registration/
│   └── core/
├── static/css/style.css           # Custom styles
├── nginx/
│   ├── nginx.conf                 # Nginx reverse proxy config
│   └── Dockerfile                 # Custom Nginx image
├── Dockerfile                     # Multi-stage production image
├── docker-compose.dev.yml         # Development stack
├── docker-compose.prod.yml        # Production stack
├── entrypoint.sh                  # Wait for DB + migrate + collectstatic
├── gunicorn.conf.py               # Gunicorn worker configuration
├── requirements.txt
├── .env.example
├── .gitignore
├── .dockerignore
└── SERVER_SETUP.md                # Full server provisioning guide
```
