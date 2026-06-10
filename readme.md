# Blitz

Blitz is a small full-stack example project containing a FastAPI backend, static frontend pages, redis for quick reads, mysql as main DB and supporting Docker configuration for easy deployment.

## Docker Compose

This repository includes a `docker-compose.yml` that defines a small stack:

- `db` (MySQL 8.0) — container_name: `mysql-db`, exposes host port `3306`.
- `redis` (Redis 7) — container_name: `redis-cache`, exposes port `6379`.
- `backend` — built from `./backend` (container_name: `blitz-app`). The backend expects the database at `DB_HOST=db:3306` and Redis at `redis:6379`. The FastAPI app listens on port `8080` inside the container (proxied by nginx).
- `nginx` — container_name: `blitz-nginx`, maps host port `80` to container port `80` and serves `frontend/` while proxying `/api/` to the backend.

Steps to run the full stack from the repository root:

```bash
docker-compose up --build -d
```

Follow logs for the whole stack or a single service:

```bash
docker-compose logs -f        # all services
docker-compose logs -f backend  # single service
```

Populate the MySQL DB (the compose mounts `database/1_populate.sql` to init the DB, but you can also run it manually):

```bash
# If you need to run the SQL manually against the running mysql-db container
docker exec -i mysql-db mysql -u root -proot_password sales < database/1_populate.sql
```

Open the frontend at `http://localhost/` (nginx serves static files). API requests are proxied at `http://localhost/api/` to the backend (FastAPI running in `blitz-app` container).

## Local Development

The primary supported deployment method is Docker Compose (see above).

## Configuration notes

- Check `docker-compose.yml` for environment variables (DB credentials, ports). Ensure those values match when running local DB instances.
- `portals/nginx/nginx.conf` contains example routing. Adjust upstream/backend hostnames and ports if you run services on different addresses/ports.

## File map

- `backend/main.py` — FastAPI application entrypoint.
- `backend/requirements.txt` — Python dependencies for the backend.
- `frontend/` — Static UI pages.
- `database/1_populate.sql` — SQL script to create/seed database.
- `docker-compose.yml` — Compose file to build and run services in Docker.
- `portals/nginx/nginx.conf` — Example nginx reverse-proxy/static config.

## Troubleshooting

- If containers fail to start, run `docker-compose logs -f` to inspect errors.
- If the backend is unreachable, confirm the service port in `docker-compose.yml` and in `nginx.conf` match the Uvicorn port.
- When running locally, ensure your virtual environment's Python version matches the project's requirements (Python 3.13 is present in the repo venv).