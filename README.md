# 🍽️ Das Caner Web App

Smart & fun meal value for Leibniz University—pick the best cafeteria food by Caner Score (calories per €), vote, and get AI meal tips!

---

## ⚡ Highlights
- **Compare Mensa Meals** at multiple locations (Garbsen, Contine, Hauptmensa, XXXLutz)
- **Caner Score:** See most calories for your buck!
- **Emoji Dietary Tags** for quick orientation
- **AI Food Guides:** Trump 🇺🇸, Bob 👷, Marvin 🤖—with real recommendations
- **Vote for Meals** & download current menus or vouchers

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
