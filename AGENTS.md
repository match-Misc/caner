# 🤖 AGENTS.md - Das Caner Development Guide

> Quick reference for AI agents and developers.

## 🚀 Quick Start

```bash
git clone https://github.com/match-Misc/caner.git
cd caner
uv sync
```

Create `.secrets` file with required environment variables (see `.secrets.example` or ask for template).

Initialize database and run:
```bash
uv run flask db upgrade
uv run python main.py
```

## 🔧 Development

**Always use `uv`**:
- `uv add package-name` - install dependencies
- `uv run python script.py` - run scripts
- `uv run flask db migrate/upgrade` - database migrations

**Run tests and linting**:
```bash
uvx ruff check .                    # Lint code
uv run python -m pytest test_downloads.py  # Run tests
```

> ⚠️ **Before finishing a task**: Run `uvx ruff check .` and fix all issues. Iterate until no errors remain.

## 🧪 Debugging

Application runs in debug mode with auto-reload. Check console output for errors.

## 🔑 Configuration

Required in `.secrets`:
- `SESSION_SECRET`
- `MISTRAL_API_KEY`
- `CANER_DB_USER`, `CANER_DB_PASSWORD`, `CANER_DB_HOST`, `CANER_DB_NAME`

## 🚨 Troubleshooting

**Port in use**: `uv run python main.py --port 5001`

**Database issues**: Ensure PostgreSQL is running and credentials are correct.

**Missing dependencies**: `uv sync`
