# Personal Finance Advisor Bot

A student-friendly Flask + SQLite personal finance web application. It records income and expenses, calculates monthly balance and savings rate, supports category budgets and saving goals, generates a monthly summary, and can use Gemini for data-based financial guidance.

## Features

- Monthly income tracking
- Daily/weekly expense tracking by category
- Dashboard with income, expenses, balance and savings rate
- Category-wise expense breakdown
- Category budgets with over-budget detection
- Saving goals
- Monthly financial report
- AI advisor using the user's stored financial data
- Local fallback advice when Gemini is not configured

## Run locally (Windows)

1. Open this folder in VS Code.
2. Create a virtual environment:

```powershell
python -m venv venv
```

3. Activate it:

```powershell
venv\Scripts\Activate.ps1
```

4. Install packages:

```powershell
pip install -r requirements.txt
```

5. Optional Gemini setup:
   - Copy `.env.example` to `.env`.
   - Put your Gemini API key after `GEMINI_API_KEY=`.
   - Never commit `.env` to GitHub.

6. Start the app:

```powershell
python app.py
```

7. Open the local address shown by Flask, usually `http://127.0.0.1:5000`.

## Project structure

```text
personal_finance_advisor/
├── app.py
├── requirements.txt
├── .env.example
├── README.md
├── templates/
│   └── index.html
└── static/
    ├── css/
    │   └── style.css
    └── js/
        └── app.js
```

## Important project note

This is a budgeting/financial education tool, not a regulated financial-advice service. The AI prompt intentionally avoids personalized investment, tax, loan, or securities recommendations.

## Suggested next development steps

1. Add user authentication.
2. Add transaction history and delete/edit actions.
3. Add date/month filters.
4. Add spending trend charts.
5. Add PDF monthly reports.
6. Add stronger input validation and tests.
7. Add a proper AI chat history table.
8. Deploy the application after local testing.
