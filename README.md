# 🍽️ Das Caner Web App

Your smart guide to the best meal values at Leibniz University. Features Caner Score (calories/€), meal voting, AI персонажи, and an **Expert Mode** for advanced users.

---

## ⚡ Features
- **Compare Mensa Meals:** Across Garbsen, Contine, Hauptmensa, and XXXLutz.
- **Caner Score:** Maximize calories per Euro.
- **Dietary Tags:** Quick view with emojis.
- **AI Food Guides:** Get recommendations from Trump 🇺🇸, Bob 👷, and Marvin 🤖.
- **Expert Mode:** For advanced meal analysis and data views.
- **Interactive:** Vote for meals and download menus/vouchers.

---

## 🚀 Quickstart

```shell
git clone [repo-url]
cd caner

python -m venv .venv
.venv\Scripts\activate     # On Windows
uv pip install -r requirements.txt

# Create .secrets & set env vars (see below)
flask db upgrade
python app.py
```

---

## 🔒 .secrets Example

```
SESSION_SECRET=...
MISTRAL_API_KEY=...
CANER_DB_USER=...
CANER_DB_PASSWORD=...
CANER_DB_HOST=...
CANER_DB_NAME=...
```

---

## 🛠️ Stack

- **Python + Flask** / PostgreSQL
- **HTML/CSS/JS**
- **AI API:** Mistral
- **PDF to Data:** pdf2image, Selenium

---

## 🤩 Screenshots

![Caner Logo](static/img/caner.png)
*Add a screenshot or menu here!*

---

## 🙌 Credits

- Meal data: Studentenwerk Hannover
- Menu AI: Mistral
- Restaurant partners: XXXLutz Hesse

---

> 🍴 Hungry for code? PRs welcome! Questions? [Open an issue](../../issues).
