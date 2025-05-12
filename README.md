# Das Caner Web App 🤖

Das Caner is a dynamic web application that helps students and staff at Leibniz University Hannover find the best value meals across multiple cafeterias. The app uniquely calculates a "Caner Score" based on calories per euro, helping users maximize their nutritional value for money.

## 🌟 Features

- **Multi-Cafeteria Support**: 
  - Mensa Garbsen
  - Hauptmensa
  - Contine
  - XXXLutz Hesse Markrestaurant

- **Smart Meal Analysis**:
  - Unique Caner Score calculation (kcal/€)
  - Visual Caner Score representation
  - Dietary information with emoji indicators

- **Interactive Features**:
  - Real-time meal voting system
  - Meal recommendations by AI characters:
    - Donald Trump 🇺🇸
    - Bob der Baumeister 👷
    - Marvin the Paranoid Android 🤖

- **Convenient Tools**:
  - XXXLutz voucher management
  - Menu PDF downloads
  - Real-time menu updates
  - Dietary preference indicators

## 🛠️ Technical Stack

- **Backend**: Flask (Python)
- **Database**: PostgreSQL with SQLAlchemy
- **Frontend**: HTML, CSS, JavaScript
- **AI Integration**: Mistral AI API
- **PDF Processing**: pdf2image, Selenium
- **Deployment**: Production-ready with logging and error handling

## 🚀 Setup and Installation

1. **Clone the Repository**
   ```shell
   git clone [repository-url]
   cd CanerProduction
   ```

2. **Set Up Environment**
   ```shell
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   uv pip install -r requirements.txt
   ```

3. **Environment Variables**
   Create a `.secrets` file with:
   ```
   # Security
   SESSION_SECRET=your_secret_key
   MISTRAL_API_KEY=your_mistral_api_key

   # Database Configuration
   CANER_DB_USER=your_db_user
   CANER_DB_PASSWORD=your_db_password
   CANER_DB_HOST=your_db_host
   CANER_DB_NAME=your_db_name
   ```

4. **Database Setup**
   ```shell
   flask db upgrade
   ```

5. **Run the Application**
   ```shell
   python app.py
   ```

## 📊 Data Sources

- Mensa data: XML feed from Studentenwerk Hannover
- XXXLutz menu: Daily updated PDF conversion
- Menu HG: Automated PDF processing with AI analysis

## 🔄 Background Tasks

The application includes several automated background tasks:
- Periodic menu updates (every 4 hours)
- Voucher management
- Menu PDF processing and conversion
- Database synchronization

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

## 📝 License

This project is licensed under the [LICENSE](LICENSE) - see the LICENSE file for details.

## 🙏 Acknowledgments

- Studentenwerk Hannover for the meal data
- XXXLutz Hesse for the restaurant collaboration
- Mistral AI for the recommendation system
- All contributors and users of Das Caner

## 📧 Contact

For support or queries, please open an issue in the GitHub repository.