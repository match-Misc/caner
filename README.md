# 🍽️ Das Caner - Intelligente Essensauswahl für Studenten an der LUH

> Eine Anwendung zur Analyse von Speiseplänen an der Leibniz Universität Hannover.

Das Caner analysiert Speisepläne aller Universitätsmensen, berechnet Wertscores und bietet KI-gestützte Empfehlungen, um Studenten bei der Optimierung ihres Essensbudgets zu helfen.

[![Python](https://img.shields.io/badge/Python-3.13+-blue.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.1.0-green.svg)](https://flask.palletsprojects.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Warum Das Caner?

Als Student an der LUH hilft Das Caner bei der Entscheidung, wo man am besten isst:

- 📊 **Datenbasierte Entscheidungen**: Echtzeit-Analyse der Speisepläne aller Campus-Optionen
- 💰 **Budgetoptimierung**: Der Caner Score (Kalorien/€) findet den besten Wert
- 🤖 **KI-gestützte Empfehlungen**: Personalisierte Vorschläge von KI-Persönlichkeiten
- 📱 **Mobilfreundlich**: Speisepläne unterwegs prüfen
- 🔄 **Immer aktuell**: Automatische tägliche Speiseplan-Updates

---

## Hauptfunktionen

### Intelligente Essensvergleiche
- **Mehrere Standorte**: Garbsen, Hauptmensa, Contine und XXXLutz Markrestaurant
- **Caner Score Algorithmus**: Maximierung von Kalorien pro Euro
- **Ernährungsfilter**: Vegetarisch 🌱, Vegan 🥬, Glutenfrei gekennzeichnet

### KI-Essenspersönlichkeiten
Treffen Sie Ihre digitalen Essensberater:
- **🇺🇸 Donald Trump**: Empfehlungen für Contine-Gerichte
- **👷 Bob the Builder**: Praktische Vorschläge für Hauptmensa
- **🤖 Marvin**: Logische Analyse von Garbsen-Optionen
- **🎤 Dark Caner**: Tipps für XXXLutz (mit Rap-Stil)

### Erweiterte Tools
- **Expertenmodus**: Detaillierte Analysen für Essensplanung
- **Bewertungssystem**: Gerichte bewerten und anderen Studenten helfen
- **Download-Bereich**: Speisepläne und Gutscheine offline speichern
- **Dunkler Modus**: Für nächtliche Essensplanung

---

## Schnellstart-Anleitung

### Voraussetzungen
- Python 3.13+
- PostgreSQL-Datenbank
- Git

### 1. Klonen & Einrichten
```bash
git clone https://github.com/match-Misc/caner.git
cd caner

# Virtuelle Umgebung erstellen
python -m venv .venv

# Aktivieren (je nach Plattform)
source .venv/bin/activate          # Linux/macOS
.venv\Scripts\activate            # Windows
```

### 2. Abhängigkeiten installieren
```bash
pip install -r requirements.txt
```

### 3. Umgebungskonfiguration
Erstelle eine `.secrets`-Datei im Projektverzeichnis:

```bash
# Erforderliche Umgebungsvariablen
SESSION_SECRET=dein-super-geheimer-session-schluessel-hier
MISTRAL_API_KEY=dein-mistral-api-schluessel-fuer-ki-features

# Datenbankkonfiguration
CANER_DB_USER=dein-postgres-benutzername
CANER_DB_PASSWORD=dein-postgres-passwort
CANER_DB_HOST=localhost
CANER_DB_NAME=caner_db
```

### 4. Datenbank einrichten
```bash
# Datenbank initialisieren (PostgreSQL muss laufen)
flask db upgrade
```

### 5. Anwendung starten
```bash
python app.py
```

Besuche `http://localhost:5000` und optimiere dein Essenserlebnis!

---

## Benutzerhandbuch

### Beste Angebote finden
1. **Datum auswählen** mit dem Kalender
2. **Mensa wählen** aus der Dropdown-Liste (oder alle durchsuchen)
3. **Caner Scores prüfen** - höher = besserer Wert
4. **Ernährungskennzeichnungen** für deine Vorlieben lesen
5. **KI nach Empfehlungen fragen**

### Expertenmodus-Funktionen
- **Detaillierte Nährwertanalyse** pro Gericht
- **Preistrend-Verfolgung** über Zeit
- **Massen-Downloads** für Planung
- **Erweiterte Filteroptionen**

### KI-Persönlichkeiten nutzen
Klicke auf die Emojis neben den Mensanamen für:
- Personalisierte Gerichtsempfehlungen
- Kommentare zu Tagesgerichten
- Wertbewertungen in verschiedenen Stilen
- Tipps zur Navigation in den Mensas

---

## Technischer Stack

| Komponente | Technologie | Zweck |
|------------|-------------|-------|
| **Backend** | Python 3.13 + Flask | Web-Framework |
| **Datenbank** | PostgreSQL + SQLAlchemy | Datenpersistenz und ORM |
| **Frontend** | Bootstrap 5 + Vanilla JS | Responsive UI-Komponenten |
| **KI-Integration** | Mistral API | Persönlichkeitsbasierte Empfehlungen |
| **Datenverarbeitung** | pdf2image, Selenium | Speiseplan-Extraktion und -Parsing |
| **Deployment** | Gunicorn + Gevent | Produktions-WSGI-Server |

---

## Screenshots

### Haupt-Dashboard
![Caner Dashboard](static/img/caner.png)
*Intelligenter Essensvergleich mit Echtzeit-Caner Scores*

### KI-Persönlichkeiten-Schnittstelle
*Empfehlungen von deinem Lieblings-KI-Essensberater*

### Expertenmodus-Analysen
*Tiefgehende Nährwert- und Preistrend-Daten*

---

## Mitwirken

Beiträge von der LUH-Community sind willkommen! So kannst du helfen:

### Entwicklungs-Setup
```bash
# Repository forken und klonen
git clone https://github.com/YOUR-USERNAME/caner.git
cd caner

# Entwicklungs-Umgebung einrichten
python -m venv .venv
source .venv/bin/activate  # oder .venv\Scripts\activate auf Windows
pip install -r requirements.txt

# Feature-Branch erstellen
git checkout -b feature/tolles-neues-feature
```

### Mitwirkungsrichtlinien
- 🐛 **Bug-Reports**: Issue-Tracker mit detaillierten Reproduktionsschritten
- ✨ **Feature-Anfragen**: Beschreibe deinen Anwendungsfall und Vorschlag
- 🔧 **Code-Beiträge**: PEP 8 folgen, Tests hinzufügen, Dokumentation aktualisieren
- 📝 **Dokumentation**: Das Projekt zugänglicher machen

### Entwicklungs-Befehle
```bash
# Im Entwicklungsmodus laufen lassen
python app.py

# Tests ausführen
python -m pytest test_downloads.py

# Daten abrufen (regelmäßig ausführen)
./run_data_fecher.sh
```

---

## Zusätzliche Ressourcen

### Fehlerbehebung
- **Datenbankverbindungsprobleme**: PostgreSQL läuft und Zugangsdaten korrekt
- **Fehlende KI-Antworten**: Mistral API-Schlüssel in `.secrets` prüfen
- **Speiseplandaten nicht aktualisiert**: Cron-Job für Datenabruf prüfen

### Verwandte Projekte
- [Studentenwerk Hannover](https://www.studentenwerk-hannover.de/) - Offizielle Essensdatenquelle
- [LUH Campus Info](https://www.uni-hannover.de/) - Universitätsinformationen

---

## Danksagungen

- **Datenquelle**: Studentenwerk Hannover für umfassende Essensinformationen
- **KI-Unterstützung**: Mistral für persönlichkeitsbasierte Empfehlungen
- **Campus-Partner**: XXXLutz Hesse für erweiterte Essensoptionen
- **Community**: LUH-Studenten für Feedback und Feature-Vorschläge

---

## Lizenz

Dieses Projekt ist unter der MIT-Lizenz lizenziert - siehe [LICENSE](LICENSE) für Details.

---

Fragen oder Vorschläge? [Eröffne ein Issue](../../issues) oder trage bei, um das Campus-Essen für alle zu verbessern!

Erstellt von Studenten für Studenten an der Leibniz Universität Hannover
