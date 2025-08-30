# 🤖 AGENTS.md - Das Caner Development Guide

> **For AI Agents & Developers**: Complete setup and workflow guide for running Das Caner locally.

## 🚀 Quick Start with uv

### Prerequisites
- **Python 3.13+** installed
- **uv** package manager ([install uv](https://github.com/astral-sh/uv))
- **PostgreSQL** database running locally
- **Git** for version control

### 1. Clone & Setup Environment
```bash
git clone https://github.com/match-Misc/caner.git
cd caner

# uv will automatically create and manage the virtual environment
uv sync
```

### 2. Environment Configuration
Create a `.secrets` file in the project root:

```bash
# Required environment variables
SESSION_SECRET=your-super-secret-session-key-here
MISTRAL_API_KEY=your-mistral-api-key-for-ai-features

# Database configuration
CANER_DB_USER=your-postgres-username
CANER_DB_PASSWORD=your-postgres-password
CANER_DB_HOST=localhost
CANER_DB_NAME=caner_db
```

### 3. Database Setup
```bash
# Ensure PostgreSQL is running, then initialize the database
uv run flask db upgrade
```

### 4. Run the Application
```bash
# Development server (with auto-reload)
uv run python main.py

# Or specify a custom port
uv run python main.py --port 5001
```

Visit `http://localhost:5000` (or your specified port) to access the application.

---

## 🔧 Development Workflow

### Always Use uv
**Never use pip directly** - uv manages the entire dependency and environment lifecycle:

```bash
# Install new dependencies
uv add package-name

# Remove dependencies
uv remove package-name

# Update all dependencies
uv sync --upgrade

# Run any command in the project environment
uv run python script.py
uv run flask db migrate
```

### Development Server
When working on the codebase, assume you're running the dev server in the background:

```bash
# Terminal 1: Development server
uv run python main.py

# Terminal 2: Make changes, test, etc.
# Changes will auto-reload thanks to Flask debug mode
```

### Code Changes & Testing
1. **Make your changes** to Python files, templates, or static assets
2. **Check the running dev server** - changes auto-reload in debug mode
3. **Test functionality** through the web interface
4. **Database changes**: Use `uv run flask db migrate` and `uv run flask db upgrade`

---

## 🏗️ Project Structure

```
caner/
├── app.py                 # Main Flask application
├── main.py               # Entry point with port configuration
├── models.py             # SQLAlchemy database models
├── data_fetcher.py       # Background data fetching
├── data_loader.py        # XML/menu data processing
├── utils/
│   └── xml_parser.py     # XML parsing utilities
├── templates/            # Jinja2 templates
│   ├── base.html
│   └── index.html
├── static/               # Static assets
│   ├── css/
│   ├── js/
│   └── img/
├── requirements.txt      # Legacy pip requirements
├── pyproject.toml        # Modern Python project config
├── uv.lock              # uv dependency lock file
└── .secrets             # Environment variables (create this)
```

---

## 🔑 Configuration

### Required Environment Variables
- `SESSION_SECRET`: Flask session encryption key
- `MISTRAL_API_KEY`: For AI personality features
- `CANER_DB_USER`: PostgreSQL username
- `CANER_DB_PASSWORD`: PostgreSQL password
- `CANER_DB_HOST`: Database host (usually `localhost`)
- `CANER_DB_NAME`: Database name (e.g., `caner_db`)

### Database Setup
```bash
# Create PostgreSQL database
createdb caner_db

# Or via psql
psql -c "CREATE DATABASE caner_db;"
```

---

## 🧪 Testing & Debugging

### Running Tests
```bash
uv run python -m pytest test_downloads.py
```

### Data Fetching
```bash
# Manual data fetch
uv run python data_fetcher.py

# Or use the shell script
./run_data_fecher.sh
```

### Debug Mode
The application runs in debug mode by default, providing:
- Auto-reload on code changes
- Detailed error pages
- Interactive debugger
- Console logging

---

## 🚀 Deployment

### Production Server
```bash
# Using Gunicorn (production WSGI server)
uv run gunicorn --bind 0.0.0.0:8000 --workers 4 app:app

# Or use the provided script
./run_gunicorn.sh
```

### Environment Variables for Production
Ensure these are set in your production environment:
- All database variables
- `SESSION_SECRET` (strong, random key)
- `MISTRAL_API_KEY` (if using AI features)
- `FLASK_ENV=production`

---

## 🤖 AI Features

### Mistral API Integration
The app uses Mistral AI for personality-driven meal recommendations:
- **Donald Trump**: Contine recommendations
- **Bob the Builder**: Hauptmensa recommendations
- **Marvin**: Garbsen analysis
- **Dark Caner**: XXXLutz tips

### MPS (Max Pumper Score)
AI-calculated fitness scores for meals based on:
- Protein content
- Calorie density
- Dietary preferences
- Personal fitness goals

---

## 📊 Key Features

### Meal Analysis
- **Caner Score**: Calories per Euro optimization
- **RKR Score**: Protein per Euro analysis
- **MPS Score**: AI fitness evaluation
- **Color-coded expert mode** for visual feedback

### Data Sources
- **Studentenwerk Hannover**: Official LUH meal data
- **XXXLutz Hesse**: Additional dining options
- **Real-time updates**: Automated menu fetching

---

## 🔍 Troubleshooting

### Common Issues

**Database Connection Failed**
```bash
# Check PostgreSQL is running
pg_isready

# Verify connection
psql -h localhost -U your_username -d caner_db
```

**Missing Dependencies**
```bash
# Re-sync environment
uv sync

# Clear cache if needed
uv cache clean
```

**Port Already in Use**
```bash
# Find process using port 5000
lsof -i :5000

# Kill the process
kill -9 <PID>

# Or use a different port
uv run python main.py --port 5001
```

**AI Features Not Working**
- Verify `MISTRAL_API_KEY` in `.secrets`
- Check API rate limits
- Ensure internet connectivity

---

## 📝 Development Notes

### Code Style
- Follow PEP 8 Python style guide
- Use meaningful variable names
- Add docstrings to functions
- Keep functions focused and small

### Database Migrations
```bash
# Create new migration
uv run flask db migrate -m "Description of changes"

# Apply migration
uv run flask db upgrade
```

### Git Workflow
```bash
# Create feature branch
git checkout -b feature/new-feature

# Commit changes
git add .
git commit -m "Add new feature"

# Push and create PR
git push origin feature/new-feature
```

---

## 🎯 Recent Changes

- ✅ **MPS Color Grading**: Added color coding for MPS values in expert mode (red→green scale)
- ✅ **uv Integration**: Full migration to uv package management
- ✅ **Enhanced Expert Mode**: Improved visual feedback for all scoring systems

---

> **Remember**: Always use `uv run` for any command that needs the project environment. The dev server should be running in the background while you make changes.