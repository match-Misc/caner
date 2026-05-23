# Caner Development Guide

> Quick reference for AI agents and developers.

## Quick Start

```bash
git clone https://github.com/match-Misc/caner.git
cd caner
cp .env.docker.example .env
docker compose up --build
```

Use `.env.docker.example` as the Docker environment template. Do not commit
`.env` or other files containing secrets. Database tables are created
automatically on application startup.

## Development

Use Docker for application runs, checks, tests, and deployment verification.
Build the app image through the Dockerfile before running checks:

```bash
docker compose build caner
docker compose run --rm --no-deps caner uvx ruff check .
docker compose run --rm --no-deps caner uvx djlint templates --profile=jinja --ignore=H021,H006,H030,H031
```

Before finishing a task, run both Docker-based linters.
Iterate until all required checks pass. Use local `uv` only for dependency
lockfile maintenance when a task explicitly requires dependency changes.

## Deployment

Local deployments build from the Dockerfile:

```bash
docker compose up --build -d
```

Remote machines should pull a prebuilt image instead of building on the server:

```bash
CANER_IMAGE=ghcr.io/match-misc/caner:latest docker compose -f docker-compose.remote.yml pull
CANER_IMAGE=ghcr.io/match-misc/caner:latest docker compose -f docker-compose.remote.yml up -d
```

## Configuration

Required environment variables:
- `SESSION_SECRET`
- `OPENROUTER_API_KEY`
- `POSTGRES_DB`, `POSTGRES_USER`, and `POSTGRES_PASSWORD` for Docker Compose

## Debugging

Check container logs first when investigating errors:

```bash
docker compose logs -f caner
docker compose logs -f postgres
```

## Troubleshooting

- Port in use: change the host port mapping in `docker-compose.yml`.
- Database issues: ensure the `postgres` service is healthy with `docker compose ps`.
- Clean database: run `docker compose down`, remove `./data/postgres`, then run
  `docker compose up --build`.
- Missing dependencies: rebuild the image with `docker compose build caner`.
