# Das Caner - Smart Student Dining Web Application

Always follow these instructions first and only fallback to search or bash commands if the information here is incomplete or found to be in error.

## Project Overview
Das Caner is a Flask web application that helps university students at LUH find the best meal deals across campus dining halls. It features AI-powered recommendations, real-time menu analysis, and automated data fetching.

**Tech Stack:**
- Backend: Python 3.12+ with Flask 3.1.0
- Database: PostgreSQL with SQLAlchemy ORM
- Frontend: Bootstrap 5 + Vanilla JavaScript
- AI Features: Mistral API integration
- Data Processing: Selenium WebDriver + pdf2image
- Production: Gunicorn with gevent workers

## Working Effectively

### Bootstrap Environment (REQUIRED FIRST STEPS)
Run these commands in order. NEVER SKIP steps or the application will fail:

```bash
# 1. Create and activate Python virtual environment (takes ~5 seconds)
python3 -m venv .venv
source .venv/bin/activate

# 2. Install system dependencies (takes 60-180 seconds, NEVER CANCEL)
sudo apt update && sudo apt install -y postgresql postgresql-contrib poppler-utils

# 3. Install Python dependencies (takes ~30 seconds, NEVER CANCEL)
pip install -r requirements.txt

# 4. Start PostgreSQL service
sudo systemctl start postgresql

# 5. Create test database and user (takes ~30 seconds)
sudo -u postgres psql -c "CREATE USER caner_test WITH PASSWORD 'test123';"
sudo -u postgres psql -c "CREATE DATABASE caner_test OWNER caner_test;"
```

### Create Environment Configuration
Create `.secrets` file in project root with these exact contents:
```bash
# Required environment variables
SESSION_SECRET=test-secret-key-for-development-only
MISTRAL_API_KEY=fake-api-key-for-testing

# Database configuration
CANER_DB_USER=caner_test
CANER_DB_PASSWORD=test123
CANER_DB_HOST=localhost
CANER_DB_NAME=caner_test
```

### Run the Application

**Development Server:**
```bash
# Option 1: Direct Flask development server (recommended for development)
python main.py
# Takes ~3 seconds to start. NEVER CANCEL before seeing "Debugger is active!"
# Serves on http://localhost:5000

# Option 2: Flask app module (alternative)
python app.py
# Takes ~3 seconds to start
```

**Production Server:**
```bash
# Gunicorn production server
gunicorn app:app
# Takes ~3 seconds to start. NEVER CANCEL.
# Default configuration uses 1 gevent worker on port 8000
```

### Data Operations
```bash
# Fetch external menu data (requires internet access)
python data_fetcher.py
# Takes 30-60 seconds. NEVER CANCEL. Will timeout on network-restricted environments.
```

## Validation Requirements

### CRITICAL: After making ANY changes, ALWAYS validate:

1. **Environment Setup Validation:**
   ```bash
   source .venv/bin/activate && python -c "import flask, psycopg2; print('Dependencies OK')"
   ```

2. **Database Connection Test:**
   ```bash
   python -c "from app import app; print('Database connection:', app.config['SQLALCHEMY_DATABASE_URI'])"
   ```

3. **Application Startup Test:**
   ```bash
   timeout 10 python main.py
   # Must see "Debugger is active!" before timeout
   ```

4. **HTTP Response Test:**
   ```bash
   # In separate terminal while app is running:
   curl -s http://localhost:5000 | head -5
   # Must return valid HTML starting with <!DOCTYPE html>
   ```

### Manual Testing Scenarios
After making changes, ALWAYS test these user workflows:

1. **Main Page Load:**
   - Navigate to http://localhost:5000
   - Verify page loads without errors
   - Check that Bootstrap styling is applied
   - Confirm menu dropdowns are populated

2. **Mensa Selection:**
   - Select different mensa options from dropdown
   - Verify date picker functionality
   - Test meal filtering and sorting

3. **AI Personality Features:**
   - Click on AI personality icons
   - Test recommendation modal dialogs
   - Verify Mistral API integration (if configured)

## Repository Structure

### Key Files and Directories
```
/home/runner/work/caner/caner/
├── app.py              # Main Flask application (278 lines)
├── main.py             # Development server entry point
├── data_fetcher.py     # Automated data fetching script
├── models.py           # Database models and schema
├── requirements.txt    # Python dependencies
├── pyproject.toml      # Project configuration
├── .secrets           # Environment variables (create manually)
├── static/            # Web assets (CSS, JS, images)
│   ├── css/
│   ├── js/
│   ├── img/
│   ├── menu/          # Downloaded menu PDFs
│   └── vouchers/      # Downloaded voucher PDFs
├── templates/         # Jinja2 HTML templates
├── utils/
│   └── xml_parser.py  # XML parsing utilities
└── run_*.sh          # Shell scripts for production deployment
```

### Important Code Locations
- **Database Models:** `models.py` - All SQLAlchemy models
- **Route Handlers:** `app.py` lines 500-1200 - All Flask routes
- **Data Processing:** `utils/xml_parser.py` - Menu data parsing
- **Frontend Logic:** `static/js/script.js` - JavaScript interactions
- **Styling:** `static/css/` - Custom CSS styles

## Common Issues and Solutions

### Known Working Commands
These commands are validated and work correctly:
```bash
# Virtual environment (5 seconds)
python3 -m venv .venv && source .venv/bin/activate

# Dependencies (30 seconds, NEVER CANCEL)
pip install -r requirements.txt  

# Database setup (30 seconds)
sudo -u postgres createuser caner_test -P
sudo -u postgres createdb caner_test -O caner_test

# Application startup (3 seconds)
python main.py  # Development
gunicorn app:app  # Production
```

### Known Issues
- **Test Suite:** `test_downloads.py` has import errors (references non-existent functions)
- **External Data:** Data fetching fails in network-restricted environments (expected)
- **UV Package Manager:** Scripts reference `uv` but it's not included in requirements
- **Gevent Compatibility:** Some threading errors in development mode (normal, doesn't affect functionality)

### Build and Deployment
- **No Build Step:** This is a pure Python Flask application with no compilation
- **No Linting Tools:** Project doesn't include pytest, black, or flake8
- **Static Files:** Served directly by Flask, no bundling required
- **Database Migrations:** Handled automatically by SQLAlchemy `db.create_all()`

## Timeout Guidelines
**CRITICAL: NEVER CANCEL these operations before timeout**

- **System package installation:** 60-180 seconds
- **Python dependency installation:** 30-60 seconds  
- **Application startup:** 10 seconds maximum
- **Database connection:** 5 seconds maximum
- **Data fetching:** 60-120 seconds (external network dependent)

## Development Workflow

### Making Changes
1. Always activate virtual environment first: `source .venv/bin/activate`
2. Make your code changes
3. Test application startup: `timeout 10 python main.py`
4. Validate with curl: `curl -s http://localhost:5000`
5. Test specific functionality manually in browser
6. Check application logs in `app.log` for errors

### Database Changes
- Database schema is automatically updated on application startup
- No manual migrations required
- To reset database: Drop and recreate `caner_test` database

### Production Deployment
- Use `gunicorn app:app` for production
- Configuration in `gunicorn.conf.py`
- Shell scripts in project root for automated deployment
- Requires external PostgreSQL database with proper credentials in `.secrets`

Remember: This application requires external network access for full functionality but can run in development mode without it.