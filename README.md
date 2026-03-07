# 🍽️ Das Caner - Intelligente Essensauswahl für Studierende an der LUH

Eine Anwendung zur Analyse von Speiseplänen an der Leibniz Universität Hannover.

## Features

- 📊 Echtzeit-Analyse der Speisepläne aller Campus-Optionen
- 💰 Caner Score (Kalorien/€) für beste Werte
- 🤖 KI-gestützte Empfehlungen von Persönlichkeiten
- 📱 Mobilfreundlich und mit Dunklem Modus

## Quick Start

```bash
git clone https://github.com/match-Misc/caner.git
cd caner
uv sync
```

Copy the example environment file and fill in your values:

```bash
cp .env.example .env
```

Run the application:

```bash
uv run python main.py
```

Visit `http://localhost:5000`

## Development

**Always use `uv`**:

- `uv add package-name` - install dependencies
- `uv run python script.py` - run scripts

**Run tests and linting**:

```bash
uvx ruff check .                    # Lint code
uv run python -m pytest test_downloads.py  # Run tests
```

> ⚠️ **Before finishing a task**: Run `uvx ruff check .` and fix all issues. Iterate until no errors remain.

## Docker Deployment

Alternatively, you can run the application using Docker:

```bash
# 1. Copy the example secrets file and fill in your values
cp .env.docker.example .env

# 2. Build the Docker image
docker build -t caner .

# 3. Run the container
docker run -p 30823:30823 --env-file .env caner
```

Or use Docker Compose:

```bash
# Build and run
docker compose up --build

# Run in background
docker compose up -d

# View logs
docker compose logs -f
```

The web app will be available at `http://localhost:30823`

## Tech Stack

- **Backend**: Python 3.13 + Flask
- **Database**: PostgreSQL + SQLAlchemy
- **Frontend**: Bootstrap 5 + Vanilla JS
- **AI**: Mistral API

## Configuration

Required in `.env`:

- `SESSION_SECRET`
- `MISTRAL_API_KEY`
- `DATABASE_URL`

## Troubleshooting

**Port in use**: `uv run python main.py --port 5001`

**Database issues**: Ensure PostgreSQL is running and credentials are correct.

**Missing dependencies**: `uv sync`

## License

MIT License
