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

Create `.secrets` file with required environment variables.

```bash
uv run flask db upgrade
uv run python main.py
```

Visit `http://localhost:5000`

## Tech Stack

- **Backend**: Python 3.13 + Flask
- **Database**: PostgreSQL + SQLAlchemy
- **Frontend**: Bootstrap 5 + Vanilla JS
- **AI**: Mistral API

## License

MIT License
