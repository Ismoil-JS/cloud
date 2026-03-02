# Technical Report — TaskFlow Django DevOps Project
# DSCC_CW1_[YOUR_STUDENT_ID].pdf

**Module:** Distributed Systems and Cloud Computing (6BUIS014C)
**Student Name:** [Your Full Name]
**Student ID:** [Your ID]
**Submission Date:** 05 March 2026
**Word Count:** [fill in before submission]

---

## Contents

1. Application Overview ................ 2
2. Containerisation Strategy ........... 3
3. Deployment Configuration ............ 5
4. CI/CD Pipeline ...................... 7
5. Challenges and Solutions ............ 9
6. GitHub Repository ................... 10

---

## A. Application Overview (~120 words)

TaskFlow is a Django-based project and task management web application built as
a practical demonstration of modern DevOps practices. The application allows
authenticated users to create projects, add tasks with priorities and due dates,
assign tasks to colleagues, and track progress through a Kanban-style board with
three status columns (To Do, In Progress, Done).

The technology stack comprises Django 4.2 as the web framework, PostgreSQL 15
as the relational database, Nginx 1.25 as a reverse proxy, and Gunicorn as the
production WSGI server. All components run as Docker containers orchestrated with
Docker Compose. The application is deployed to an Eskiz cloud Ubuntu server and
served securely over HTTPS.

**Database schema overview:** Three custom models — `Project`, `Task`, and `Tag`
— extend Django's built-in `User` model. `Project` has a many-to-one relationship
with `User` (owner). `Task` has a many-to-one relationship with `Project` and a
nullable many-to-one to `User` (assigned_to). `Task` has a many-to-many
relationship with `Tag`.

[INSERT: Screenshot of the running application homepage and admin panel]

---

## B. Containerisation Strategy (~280 words)

### Dockerfile — Multi-Stage Build

The Dockerfile uses a two-stage build to minimise the final image size:

**Stage 1 — Builder:** Uses `python:3.11-slim` with build-time system
dependencies (`gcc`, `libpq-dev`) to compile C extensions (psycopg2). A Python
virtual environment is created at `/opt/venv` and all packages from
`requirements.txt` are installed here.

**Stage 2 — Production:** A second `python:3.11-slim` base discards all build
tools. Only the runtime library `libpq5` is installed. The virtual environment
is copied from the builder using `COPY --from=builder`. Application source is
copied with `--chown=appuser:appgroup`, and a non-root user (`appuser`, UID 1000)
runs the process, reducing the attack surface. The result is an image of
approximately 180 MB — well below the 200 MB target.

[INSERT: Screenshot of `docker images` showing image size comparison]

### docker-compose.yml Structure

Two Compose files separate concerns:

- `docker-compose.dev.yml` — development stack with live code mounting
  and Django `runserver`
- `docker-compose.prod.yml` — production stack pulling images from Docker Hub

The production stack has three services:
- `db` (postgres:15-alpine) with a named volume `postgres_data` for persistence
- `web` (taskflow image) with Gunicorn; depends on `db` being healthy
- `nginx` (custom Nginx image) exposing ports 80 and 443, sharing
  `static_volume` and `media_volume` read-only

All services communicate on a custom Docker bridge network `app_network`, so
only Nginx is reachable from outside.

### Environment Variable Management

Sensitive values (`DJANGO_SECRET_KEY`, `DB_PASSWORD`) are never committed to
Git. A `.env.example` file documents required variables. On the server, a `.env`
file is created manually and consumed by `env_file:` directives in Compose.
The `.dockerignore` excludes `.env*` files from the Docker build context.

### entrypoint.sh

A shell script waits for PostgreSQL to accept connections, then runs
`manage.py migrate` and `collectstatic` before starting Gunicorn. This ensures
the database is ready before Django attempts to connect on startup.

[INSERT: Screenshot of `docker compose ps` showing all three services running]
[INSERT: Screenshot of Dockerfile contents]

---

## C. Deployment Configuration (~250 words)

### Server Setup (Eskiz Cloud / Azure VM)

An Ubuntu 24.04 LTS virtual machine was provisioned on the Eskiz cloud
(alternatively Azure for Students). After connecting via SSH, the server was
updated (`apt update && apt upgrade`) and Docker Engine was installed from
Docker's official repository — not Ubuntu's outdated package — following the
GPG key and repository setup from the Week 6 seminar materials.

[INSERT: Screenshot of `docker --version` and `docker compose version` output on server]

### UFW Firewall Configuration

UFW was configured with a default deny-incoming policy. Ports 22 (SSH),
80 (HTTP), and 443 (HTTPS) were explicitly allowed before enabling the firewall,
preventing lockout. Database port 5432 is deliberately not exposed externally;
PostgreSQL is only reachable by the `web` container via the internal Docker network.

[INSERT: Screenshot of `sudo ufw status verbose`]

### Nginx and Gunicorn Configuration

Nginx acts as the entry point for all HTTP/HTTPS traffic. Static files
(`/static/`) are served directly from the `static_volume` Docker volume without
hitting Django, reducing latency. All other requests are proxied to the Gunicorn
upstream at `web:8000` with the `X-Forwarded-For` header set for correct IP
logging. Security headers (`X-Frame-Options`, `X-Content-Type-Options`, HSTS)
are added to all responses.

Gunicorn is configured in `gunicorn.conf.py` with `workers = CPU * 2 + 1`,
a 30-second timeout, and `max_requests = 1000` to prevent memory leaks.

### SSL/HTTPS

A free TLS certificate was obtained via Let's Encrypt using Certbot in
standalone mode. The certificate is stored at
`/etc/letsencrypt/live/DOMAIN/fullchain.pem` on the host and mounted
read-only into the Nginx container. Nginx redirects all HTTP traffic to HTTPS,
and Django's `SECURE_SSL_REDIRECT=True` setting enforces HTTPS at the application
layer as well. Auto-renewal is handled by Certbot's systemd timer.

[INSERT: Screenshot of browser showing padlock/HTTPS on your domain]
[INSERT: Screenshot of `sudo certbot certificates` output]

### Domain Configuration

An A record was added in the DNS registrar pointing `yourdomain.com` to the
server's public IP address. The application is accessible at
`https://yourdomain.com`.

---

## D. CI/CD Pipeline (~250 words)

### GitHub Actions Workflow

The workflow file `.github/workflows/deploy.yml` defines a three-job pipeline
triggered on every push to the `main` branch and on pull requests.

**Job 1 — Test:**
- Spins up a PostgreSQL 15 service container alongside the runner
- Sets up Python 3.11 with pip caching for speed
- Installs all dependencies from `requirements.txt`
- Runs `flake8` linting across `core/` and `config/` directories
- Runs `python manage.py test` with the PostgreSQL test database
- Pull requests stop here — they never build or deploy

**Job 2 — Build** (`needs: test`, push-to-main only):
- Logs into Docker Hub using the `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` secrets
- Builds the multi-stage Docker image using `docker/build-push-action`
- Tags the image as `:latest` and `:<commit-sha>` for traceability and rollback
- Pushes both tags to Docker Hub using GitHub Actions layer cache

**Job 3 — Deploy** (`needs: build`, push-to-main only):
- SSHs into the server using `appleboy/ssh-action` with the `SSH_PRIVATE_KEY` secret
- Pulls the new `:latest` image
- Restarts containers with `docker compose up -d --remove-orphans`
- Runs `manage.py migrate` and `collectstatic` inside the running `web` container
- Prunes old unused images to free disk space

### Secrets Management

No credentials appear in code. Six GitHub repository secrets are used:
`DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`, `SSH_HOST`, `SSH_USERNAME`,
`SSH_PRIVATE_KEY` (dedicated deploy key, not the developer's personal key).
The `.env` file on the server holds Django and database credentials and is never
committed to Git (excluded by `.gitignore`).

[INSERT: Screenshot of GitHub Actions tab showing successful green pipeline run]
[INSERT: Screenshot showing all three jobs (Test → Build → Deploy) green]

---

## E. Challenges and Solutions (~200 words)

**Challenge 1: collectstatic during Docker build**

Running `collectstatic` inside the Dockerfile requires a `DJANGO_SECRET_KEY`
to be set, but secrets must not be baked into images. The solution was to move
static file collection to the `entrypoint.sh` script that runs at container
start-up, where environment variables from the `.env` file are available. This
also means static files always reflect the correct settings.

**Challenge 2: Database not ready on container start**

When `docker compose up` starts all services simultaneously, the Django
container would crash because PostgreSQL was not yet accepting connections.
The fix was a Python wait-loop in `entrypoint.sh` that retries the psycopg2
connection up to 30 times with one-second intervals. Although `depends_on:
condition: service_healthy` in Compose also helps, the explicit wait loop
provides an extra layer of resilience.

**Challenge 3: Firewall configuration on Azure**

Enabling UFW without first allowing SSH (port 22) would lock the administrator
out of the server permanently. The lesson — always add `ufw allow 22/tcp`
*before* `ufw enable` — reflects the critical sequence taught in Week 6.

**Lessons learned:** Infrastructure-as-code (Compose, Dockerfiles) removes
environment inconsistencies. Automating tests in CI prevents broken code from
reaching production. Secrets management is a non-negotiable security practice.

**Future improvements:** Add Redis for session caching, integrate Sentry for
error monitoring, add coverage reporting to CI, and implement HTTPS inside
the `docker-compose.prod.yml` using automated Certbot renewal.

---

## GitHub Repository

**Repository URL:** https://github.com/YOUR_USERNAME/taskflow

[INSERT: Screenshot of GitHub repository main page showing files and README]
[INSERT: Screenshot of commit history (minimum 15 meaningful commits with timestamps)]
[INSERT: Screenshot of at least one closed Pull Request (feature branch merged to main)]
[INSERT: Screenshot of GitHub Secrets configuration page (names visible, values hidden)]

**Docker Hub:** https://hub.docker.com/r/YOUR_USERNAME/taskflow

[INSERT: Screenshot of Docker Hub repository showing pushed image tags]

---

## References

Docker Inc. (2024) *Docker Documentation*. Available at: https://docs.docker.com [Accessed: March 2026].

GitHub (2024) *GitHub Actions Documentation*. Available at: https://docs.github.com/actions [Accessed: March 2026].

Let's Encrypt (2024) *Certbot Documentation*. Available at: https://certbot.eff.org/docs [Accessed: March 2026].

Mozilla (2024) *Nginx Configuration Generator*. Available at: https://ssl-config.mozilla.org [Accessed: March 2026].
