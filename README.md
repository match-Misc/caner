# 🍽️ Das Caner - Smart Student Dining at LUH

> **Never overpay for lunch again!** Your intelligent companion for finding the best meal deals at Leibniz University Hannover.

Das Caner analyzes menus across all university dining halls, calculates value scores, and serves up AI-powered recommendations to help students make the most of their dining budget. Because every Euro counts when you're living the student life! 💸

[![Python](https://img.shields.io/badge/Python-3.13+-blue.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.1.0-green.svg)](https://flask.palletsprojects.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 🌟 Why Das Caner?

**Stop guessing, start optimizing!** As a student at LUH, you face the daily dilemma: where to eat for the best value? Das Caner solves this by:

- 📊 **Data-driven decisions**: Real-time menu analysis across all campus dining options
- 💰 **Budget optimization**: Our signature "Caner Score" (calories/€) finds maximum value
- 🤖 **AI-powered guidance**: Get personalized recommendations from quirky AI personalities
- 📱 **Mobile-friendly**: Check menus on-the-go between lectures
- 🔄 **Always fresh**: Automated daily menu updates

---

## ⚡ Key Features

### 🎯 Smart Meal Comparison
- **Multi-venue analysis**: Garbsen, Hauptmensa, Contine, and XXXLutz Markrestaurant
- **Caner Score algorithm**: Maximize calories per Euro for ultimate value
- **Dietary filters**: Vegetarian 🌱, Vegan 🥬, Gluten-free options clearly marked

### 🤖 AI Food Personalities
Meet your digital dining advisors:
- **🇺🇸 Donald Trump**: "This Contine salad is tremendous, probably the best salad ever!"
- **👷 Bob the Builder**: Practical recommendations for hearty Hauptmensa meals
- **🤖 Marvin**: Pessimistic but logical analysis of Garbsen options
- **🎤 Dark Caner**: Street-smart tips for XXXLutz dining (rap style included!)

### 🔧 Advanced Tools
- **Expert Mode**: Deep-dive analytics for meal planning nerds
- **Voting System**: Rate meals and help fellow students
- **Download Center**: Save menus and vouchers for offline access
- **Dark Mode**: Easy on the eyes during late-night meal planning

---

## 🚀 Quick Start Guide

### Prerequisites
- Python 3.13+
- PostgreSQL database
- Git

### 1. Clone & Setup
```bash
git clone https://github.com/match-Misc/caner.git
cd caner

# Create virtual environment
python -m venv .venv

# Activate (choose your platform)
source .venv/bin/activate          # Linux/macOS
.venv\Scripts\activate            # Windows
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Environment Configuration
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

### 4. Database Setup
```bash
# Initialize database (make sure PostgreSQL is running)
flask db upgrade
```

### 5. Launch the App
```bash
python app.py
```

Visit `http://localhost:5000` and start optimizing your dining experience! 🎉

---

## 📖 Usage Guide

### Finding the Best Deals
1. **Select your date** using the calendar picker
2. **Choose a mensa** from the dropdown (or browse all)
3. **Check the Caner Scores** - higher = better value
4. **Read dietary tags** for your preferences
5. **Ask the AI** for personalized recommendations

### Expert Mode Features
- **Detailed nutritional analysis** per meal
- **Price trend tracking** over time
- **Bulk menu downloads** for planning
- **Advanced filtering options**

### AI Personality Usage
Click on the emoji characters next to each mensa name to get:
- Personalized meal recommendations
- Humorous commentary on daily specials
- Value assessments in unique styles
- Tips for navigating each dining hall

---

## 🛠️ Technical Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Backend** | Python 3.13 + Flask | Web application framework |
| **Database** | PostgreSQL + SQLAlchemy | Data persistence and ORM |
| **Frontend** | Bootstrap 5 + Vanilla JS | Responsive UI components |
| **AI Integration** | Mistral API | Personality-driven recommendations |
| **Data Processing** | pdf2image, Selenium | Menu extraction and parsing |
| **Deployment** | Gunicorn + Gevent | Production WSGI server |

---

## 🖥️ Screenshots

### Main Dashboard
![Caner Dashboard](static/img/caner.png)
*Smart meal comparison with real-time Caner Scores*

### AI Personality Interface
*Get recommendations from your favorite digital dining advisor*

### Expert Mode Analytics
*Deep-dive into nutritional data and pricing trends*

---

## 🤝 Contributing

We welcome contributions from the LUH community! Here's how you can help:

### Development Setup
```bash
# Fork the repository and clone your fork
git clone https://github.com/YOUR-USERNAME/caner.git
cd caner

# Set up development environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt

# Create your feature branch
git checkout -b feature/amazing-new-feature
```

### Contributing Guidelines
- 🐛 **Bug reports**: Use the issue tracker with detailed reproduction steps
- ✨ **Feature requests**: Describe your use case and proposed solution
- 🔧 **Code contributions**: Follow PEP 8, add tests, update documentation
- 📝 **Documentation**: Help make the project more accessible

### Development Commands
```bash
# Run in development mode
python app.py

# Run tests
python -m pytest test_downloads.py

# Data fetching (run periodically)
./run_data_fecher.sh
```

---

## 📚 Additional Resources

### Troubleshooting
- **Database connection issues**: Ensure PostgreSQL is running and credentials are correct
- **Missing AI responses**: Check your Mistral API key in `.secrets`
- **Menu data not updating**: Verify the data fetcher cron job is running

### Related Projects
- [Studentenwerk Hannover](https://www.studentenwerk-hannover.de/) - Official meal data source
- [LUH Campus Info](https://www.uni-hannover.de/) - University information

---

## 🏆 Acknowledgments

- **Data Source**: Studentenwerk Hannover for providing comprehensive meal information
- **AI Power**: Mistral for enabling our personality-driven recommendations
- **Campus Partner**: XXXLutz Hesse for expanding dining options
- **Community**: LUH students for feedback and feature suggestions

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

> 🍴 **Hungry for more?** 
> 
> Star this repo if Das Caner helped you save money on meals! 
> 
> Have questions or suggestions? [Open an issue](../../issues) or contribute to make campus dining better for everyone! 

**Made with ❤️ by students, for students at Leibniz University Hannover**
