from datetime import date, datetime
import os

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from flask_sqlalchemy import SQLAlchemy

load_dotenv()

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///finance.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


# =========================================================
# DATABASE MODELS
# =========================================================

class Income(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    source = db.Column(db.String(120), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    entry_date = db.Column(
        db.Date,
        nullable=False,
        default=date.today
    )


class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(80), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    entry_date = db.Column(
        db.Date,
        nullable=False,
        default=date.today
    )


class Budget(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(80), nullable=False, unique=True)
    amount = db.Column(db.Float, nullable=False)


class SavingGoal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    target = db.Column(db.Float, nullable=False)
    saved = db.Column(db.Float, nullable=False, default=0)


# =========================================================
# CATEGORIES
# =========================================================

CATEGORIES = [
    "Food",
    "Rent",
    "Transport",
    "Education",
    "Healthcare",
    "Entertainment",
    "Shopping",
    "Bills",
    "Other"
]


# =========================================================
# MONTHLY TOTALS
# =========================================================

def month_totals(year=None, month=None):

    today = date.today()

    year = year or today.year
    month = month or today.month

    incomes = Income.query.filter(
        db.extract("year", Income.entry_date) == year,
        db.extract("month", Income.entry_date) == month
    ).all()

    expenses = Expense.query.filter(
        db.extract("year", Expense.entry_date) == year,
        db.extract("month", Expense.entry_date) == month
    ).all()

    income_total = sum(item.amount for item in incomes)
    expense_total = sum(item.amount for item in expenses)

    by_category = {
        category: 0
        for category in CATEGORIES
    }

    for item in expenses:

        by_category[item.category] = (
            by_category.get(item.category, 0)
            + item.amount
        )

    return income_total, expense_total, by_category


# =========================================================
# LOCAL FINANCIAL ADVICE
# =========================================================

def build_local_advice():

    income, expenses, by_category = month_totals()

    balance = income - expenses

    savings_rate = (
        balance / income * 100
        if income
        else 0
    )

    top = (
        max(
            by_category.items(),
            key=lambda x: x[1]
        )
        if by_category
        else ("None", 0)
    )

    suggestions = []

    if income == 0:

        suggestions.append(
            "Add your monthly income first so the advisor can calculate a realistic plan."
        )

    if top[1] > 0:

        suggestions.append(
            f"Your highest expense category is "
            f"{top[0]} at ₹{top[1]:,.0f}. "
            f"Review whether part of it can be reduced."
        )

    if income and expenses > income:

        suggestions.append(
            "Your expenses are higher than your recorded income. "
            "Review non-essential spending and set category limits."
        )

    elif income and savings_rate < 20:

        suggestions.append(
            "Your current recorded savings rate is below 20%. "
            "Try setting one small weekly spending limit."
        )

    elif income:

        suggestions.append(
            "Your recorded expenses are below income. "
            "Consider assigning a fixed amount to a savings goal each month."
        )

    suggestions.append(
        "Use the Budget section to compare planned spending with actual expenses."
    )

    return "\n".join(
        f"• {suggestion}"
        for suggestion in suggestions
    )


# =========================================================
# GEMINI AI ADVICE
# =========================================================

def gemini_advice(question):

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        return None

    try:

        from google import genai

        income, expenses, by_category = month_totals()

        budgets = {
            budget.category: budget.amount
            for budget in Budget.query.all()
        }

        context = {

            "monthly_income": round(
                income,
                2
            ),

            "monthly_expenses": round(
                expenses,
                2
            ),

            "balance": round(
                income - expenses,
                2
            ),

            "expense_by_category": {
                key: round(value, 2)
                for key, value in by_category.items()
                if value
            },

            "budgets": budgets
        }

        prompt = f"""
You are a personal finance education assistant
inside a student project.

Use only the supplied financial data.

Do not claim to be a licensed financial advisor.

Avoid personalized investment, tax, loan,
or securities recommendations.

Give practical budgeting and saving guidance.

User data:
{context}

User question:
{question}

Answer in simple language.

Mention relevant numbers from the data when useful.

Give 2-4 actionable suggestions.
"""

        client = genai.Client(
            api_key=api_key
        )

        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt
        )

        return (
            response.text.strip()
            if response.text
            else None
        )

    except Exception as exc:

        app.logger.warning(
            "Gemini unavailable: %s",
            exc
        )

        return None


# =========================================================
# HOME PAGE
# =========================================================

@app.route("/")
def dashboard():

    return render_template(
        "index.html",
        categories=CATEGORIES
    )


# =========================================================
# DASHBOARD
# =========================================================

@app.get("/api/dashboard")
def dashboard_data():

    income, expenses, by_category = month_totals()

    budgets = {
        budget.category: budget.amount
        for budget in Budget.query.all()
    }

    goals = SavingGoal.query.all()

    return jsonify({

        "income": round(
            income,
            2
        ),

        "expenses": round(
            expenses,
            2
        ),

        "balance": round(
            income - expenses,
            2
        ),

        "savings_rate": round(
            (income - expenses) / income * 100,
            1
        ) if income else 0,

        "categories": {
            key: round(value, 2)
            for key, value in by_category.items()
        },

        "budgets": budgets,

        "goals": [
            {
                "id": goal.id,
                "name": goal.name,
                "target": goal.target,
                "saved": goal.saved
            }
            for goal in goals
        ]

    })


# =========================================================
# INCOME
# =========================================================

@app.post("/api/income")
def add_income():

    data = request.get_json() or {}

    source = str(
        data.get("source", "")
    ).strip()

    try:

        amount = float(
            data.get("amount", 0)
        )

    except (TypeError, ValueError):

        amount = 0

    try:

        entry_date = (
            datetime.strptime(
                data["date"],
                "%Y-%m-%d"
            ).date()
            if data.get("date")
            else date.today()
        )

    except ValueError:

        return jsonify({
            "error": "Enter a valid date."
        }), 400

    if not source or amount <= 0:

        return jsonify({
            "error": "Enter a valid source and positive amount."
        }), 400

    db.session.add(
        Income(
            source=source,
            amount=amount,
            entry_date=entry_date
        )
    )

    db.session.commit()

    return jsonify({
        "message": "Income added."
    })


@app.get("/api/income")
def list_income():

    items = Income.query.order_by(
        Income.entry_date.desc(),
        Income.id.desc()
    ).all()

    return jsonify({

        "items": [

            {
                "id": item.id,
                "source": item.source,
                "amount": item.amount,
                "date": item.entry_date.isoformat()
            }

            for item in items

        ]

    })


@app.put("/api/income/<int:income_id>")
def update_income(income_id):

    item = db.session.get(
        Income,
        income_id
    )

    if not item:

        return jsonify({
            "error": "Income entry not found."
        }), 404

    data = request.get_json() or {}

    source = str(
        data.get("source", "")
    ).strip()

    try:

        amount = float(
            data.get("amount", 0)
        )

    except (TypeError, ValueError):

        amount = 0

    if data.get("date"):

        try:

            entry_date = datetime.strptime(
                data["date"],
                "%Y-%m-%d"
            ).date()

        except ValueError:

            return jsonify({
                "error": "Enter a valid date."
            }), 400

    else:

        entry_date = item.entry_date

    if not source or amount <= 0:

        return jsonify({
            "error": "Enter a valid source and positive amount."
        }), 400

    item.source = source
    item.amount = amount
    item.entry_date = entry_date

    db.session.commit()

    return jsonify({
        "message": "Income updated."
    })


@app.delete("/api/income/<int:income_id>")
def delete_income(income_id):

    item = db.session.get(
        Income,
        income_id
    )

    if not item:

        return jsonify({
            "error": "Income entry not found."
        }), 404

    db.session.delete(item)
    db.session.commit()

    return jsonify({
        "message": "Income deleted."
    })


# =========================================================
# EXPENSE
# =========================================================

@app.post("/api/expense")
def add_expense():

    data = request.get_json() or {}

    title = str(
        data.get("title", "")
    ).strip()

    category = str(
        data.get("category", "Other")
    ).strip()

    try:

        amount = float(
            data.get("amount", 0)
        )

    except (TypeError, ValueError):

        amount = 0

    try:

        entry_date = (
            datetime.strptime(
                data["date"],
                "%Y-%m-%d"
            ).date()
            if data.get("date")
            else date.today()
        )

    except ValueError:

        return jsonify({
            "error": "Enter a valid date."
        }), 400

    if (
        not title
        or amount <= 0
        or category not in CATEGORIES
    ):

        return jsonify({
            "error": "Enter valid expense details."
        }), 400

    db.session.add(
        Expense(
            title=title,
            category=category,
            amount=amount,
            entry_date=entry_date
        )
    )

    db.session.commit()

    return jsonify({
        "message": "Expense added."
    })


@app.get("/api/expense")
def list_expenses():

    items = Expense.query.order_by(
        Expense.entry_date.desc(),
        Expense.id.desc()
    ).all()

    return jsonify({

        "items": [

            {
                "id": item.id,
                "title": item.title,
                "category": item.category,
                "amount": item.amount,
                "date": item.entry_date.isoformat()
            }

            for item in items

        ]

    })


@app.put("/api/expense/<int:expense_id>")
def update_expense(expense_id):

    item = db.session.get(
        Expense,
        expense_id
    )

    if not item:

        return jsonify({
            "error": "Expense entry not found."
        }), 404

    data = request.get_json() or {}

    title = str(
        data.get("title", "")
    ).strip()

    category = str(
        data.get("category", "Other")
    ).strip()

    try:

        amount = float(
            data.get("amount", 0)
        )

    except (TypeError, ValueError):

        amount = 0

    if data.get("date"):

        try:

            entry_date = datetime.strptime(
                data["date"],
                "%Y-%m-%d"
            ).date()

        except ValueError:

            return jsonify({
                "error": "Enter a valid date."
            }), 400

    else:

        entry_date = item.entry_date

    if (
        not title
        or amount <= 0
        or category not in CATEGORIES
    ):

        return jsonify({
            "error": "Enter valid expense details."
        }), 400

    item.title = title
    item.category = category
    item.amount = amount
    item.entry_date = entry_date

    db.session.commit()

    return jsonify({
        "message": "Expense updated."
    })


@app.delete("/api/expense/<int:expense_id>")
def delete_expense(expense_id):

    item = db.session.get(
        Expense,
        expense_id
    )

    if not item:

        return jsonify({
            "error": "Expense entry not found."
        }), 404

    db.session.delete(item)
    db.session.commit()

    return jsonify({
        "message": "Expense deleted."
    })


# =========================================================
# BUDGET
# =========================================================

@app.post("/api/budget")
def set_budget():

    data = request.get_json() or {}

    category = str(
        data.get("category", "")
    ).strip()

    try:

        amount = float(
            data.get("amount", 0)
        )

    except (TypeError, ValueError):

        amount = 0

    if (
        category not in CATEGORIES
        or amount <= 0
    ):

        return jsonify({
            "error": "Enter a valid category and budget."
        }), 400

    budget = Budget.query.filter_by(
        category=category
    ).first()

    if budget:

        budget.amount = amount

    else:

        db.session.add(
            Budget(
                category=category,
                amount=amount
            )
        )

    db.session.commit()

    return jsonify({
        "message": "Budget saved."
    })


# =========================================================
# SAVING GOALS
# =========================================================

@app.post("/api/goal")
def add_goal():

    data = request.get_json() or {}

    name = str(
        data.get("name", "")
    ).strip()

    try:

        target = float(
            data.get("target", 0)
        )

    except (TypeError, ValueError):

        target = 0

    if not name or target <= 0:

        return jsonify({
            "error": "Enter a valid goal and target."
        }), 400

    db.session.add(
        SavingGoal(
            name=name,
            target=target,
            saved=0
        )
    )

    db.session.commit()

    return jsonify({
        "message": "Saving goal added."
    })


@app.put("/api/goal/<int:goal_id>")
def update_goal(goal_id):

    goal = db.session.get(
        SavingGoal,
        goal_id
    )

    if not goal:

        return jsonify({
            "error": "Saving goal not found."
        }), 404

    data = request.get_json() or {}

    try:

        saved = float(
            data.get("saved", 0)
        )

    except (TypeError, ValueError):

        return jsonify({
            "error": "Enter a valid savings amount."
        }), 400

    if saved < 0:

        return jsonify({
            "error": "Savings cannot be negative."
        }), 400

    if saved > goal.target:

        return jsonify({
            "error": "Saved amount cannot exceed the target."
        }), 400

    goal.saved = saved

    db.session.commit()

    return jsonify({
        "message": "Saving goal updated."
    })


# =========================================================
# SMART FINANCIAL INSIGHTS
# =========================================================

@app.get("/api/insights")
def financial_insights():

    income, expenses, by_category = month_totals()

    budgets = {
        budget.category: budget.amount
        for budget in Budget.query.all()
    }

    goals = SavingGoal.query.all()

    insights = []

    # Income check
    if income == 0:

        insights.append({

            "type": "info",

            "title": "Add your income",

            "message":
                "Add your monthly income to get personalized financial insights."

        })

    else:

        # Expense vs income
        if expenses > income:

            insights.append({

                "type": "warning",

                "title":
                    "Expenses are higher than income",

                "message":
                    f"Your expenses are "
                    f"₹{expenses - income:,.0f} "
                    f"higher than your recorded income."

            })

        else:

            savings = income - expenses

            insights.append({

                "type": "success",

                "title":
                    "Positive monthly balance",

                "message":
                    f"You currently have "
                    f"₹{savings:,.0f} remaining "
                    f"after recorded expenses."

            })

        # Highest category
        active_categories = {
            key: value
            for key, value in by_category.items()
            if value > 0
        }

        if active_categories:

            top_category, top_amount = max(
                active_categories.items(),
                key=lambda x: x[1]
            )

            insights.append({

                "type": "warning",

                "title":
                    "Highest spending category",

                "message":
                    f"{top_category} is your highest "
                    f"spending category at "
                    f"₹{top_amount:,.0f}."

            })

        # Budget analysis
        for category, budget in budgets.items():

            spent = by_category.get(
                category,
                0
            )

            if spent > budget:

                insights.append({

                    "type": "warning",

                    "title":
                        f"{category} budget exceeded",

                    "message":
                        f"You have spent "
                        f"₹{spent:,.0f} against a "
                        f"budget of ₹{budget:,.0f}."

                })

            elif (
                budget > 0
                and spent >= budget * 0.8
            ):

                insights.append({

                    "type": "info",

                    "title":
                        f"{category} budget almost reached",

                    "message":
                        f"You have used "
                        f"{spent / budget * 100:.0f}% "
                        f"of your {category} budget."

                })

        # Saving rate
        savings_rate = (
            (income - expenses) / income * 100
            if income
            else 0
        )

        if savings_rate >= 20:

            insights.append({

                "type": "success",

                "title":
                    "Good saving progress",

                "message":
                    f"Your current saving rate is "
                    f"{savings_rate:.1f}%."

            })

        elif savings_rate >= 0:

            insights.append({

                "type": "info",

                "title":
                    "Improve your saving rate",

                "message":
                    f"Your current saving rate is "
                    f"{savings_rate:.1f}%. "
                    f"Consider reducing "
                    f"non-essential spending."

            })

    # Saving goals
    for goal in goals:

        remaining = goal.target - goal.saved

        if remaining > 0:

            insights.append({

                "type": "goal",

                "title":
                    f"Goal: {goal.name}",

                "message":
                    f"₹{remaining:,.0f} more needed "
                    f"to reach your saving goal."

            })

        else:

            insights.append({

                "type": "success",

                "title":
                    f"Goal completed: {goal.name}",

                "message":
                    "Congratulations! You have "
                    "reached this saving goal."

            })

    return jsonify({
        "insights": insights
    })


# =========================================================
# AI FINANCE ADVISOR
# =========================================================

@app.post("/api/advisor")
def advisor():

    data = request.get_json() or {}

    question = str(
        data.get("question", "")
    ).strip()

    if not question:

        return jsonify({
            "error": "Ask a question first."
        }), 400

    answer = (
        gemini_advice(question)
        or build_local_advice()
    )

    return jsonify({

        "answer": answer,

        "ai_enabled":
            bool(
                os.getenv("GEMINI_API_KEY")
            )

    })


# =========================================================
# MONTHLY REPORT
# =========================================================

@app.get("/api/report")
def report():

    income, expenses, by_category = month_totals()

    return jsonify({

        "month":
            date.today().strftime("%B %Y"),

        "income":
            round(income, 2),

        "expenses":
            round(expenses, 2),

        "savings":
            round(
                income - expenses,
                2
            ),

        "top_category":
            max(
                by_category.items(),
                key=lambda x: x[1]
            )[0]
            if any(by_category.values())
            else "None",

        "categories": {
            key: round(value, 2)
            for key, value in by_category.items()
        }

    })


# =========================================================
# FINANCIAL HEALTH SCORE
# =========================================================

@app.get("/api/health-score")
def health_score():

    income, expenses, by_category = month_totals()

    budgets = {
        budget.category: budget.amount
        for budget in Budget.query.all()
    }

    goals = SavingGoal.query.all()


    # -----------------------------------------------------
    # 1. SAVING SCORE
    # -----------------------------------------------------

    if income <= 0:

        saving_score = 0

    else:

        savings = income - expenses

        savings_rate = (
            savings / income
        ) * 100

        if savings_rate >= 30:
            saving_score = 100

        elif savings_rate >= 20:
            saving_score = 85

        elif savings_rate >= 10:
            saving_score = 70

        elif savings_rate >= 5:
            saving_score = 50

        elif savings_rate >= 0:
            saving_score = 30

        else:
            saving_score = 10


    # -----------------------------------------------------
    # 2. BUDGET SCORE
    # -----------------------------------------------------

    if not budgets:

        budget_score = 50

    else:

        category_scores = []

        for category, budget in budgets.items():

            if budget <= 0:
                continue

            spent = by_category.get(
                category,
                0
            )

            if spent <= budget:

                category_scores.append(100)

            elif spent <= budget * 1.10:

                category_scores.append(70)

            elif spent <= budget * 1.25:

                category_scores.append(40)

            else:

                category_scores.append(20)

        budget_score = (
            round(
                sum(category_scores)
                / len(category_scores)
            )
            if category_scores
            else 50
        )


    # -----------------------------------------------------
    # 3. SPENDING SCORE
    # -----------------------------------------------------

    if income <= 0:

        spending_score = 0

    elif expenses <= income * 0.50:

        spending_score = 100

    elif expenses <= income * 0.70:

        spending_score = 85

    elif expenses <= income * 0.85:

        spending_score = 70

    elif expenses <= income:

        spending_score = 50

    else:

        spending_score = 20


    # -----------------------------------------------------
    # 4. GOAL SCORE
    # -----------------------------------------------------

    if not goals:

        goal_score = 50

    else:

        goal_percentages = []

        for goal in goals:

            if goal.target > 0:

                percentage = (
                    goal.saved
                    / goal.target
                ) * 100

                goal_percentages.append(
                    min(percentage, 100)
                )

        goal_score = (
            round(
                sum(goal_percentages)
                / len(goal_percentages)
            )
            if goal_percentages
            else 50
        )


    # -----------------------------------------------------
    # FINAL SCORE
    # -----------------------------------------------------

    final_score = round(
        (
            saving_score
            + budget_score
            + spending_score
            + goal_score
        ) / 4
    )


    # -----------------------------------------------------
    # SCORE STATUS
    # -----------------------------------------------------

    if final_score >= 80:

        status = "Excellent"

    elif final_score >= 60:

        status = "Good"

    elif final_score >= 40:

        status = "Needs Improvement"

    else:

        status = "Needs Attention"


    # -----------------------------------------------------
    # SCORE EXPLANATION
    # -----------------------------------------------------

    reasons = []

    if saving_score < 60:

        reasons.append(
            "Your savings rate is low. "
            "Try to save a fixed amount every month."
        )

    if budget_score < 60:

        reasons.append(
            "Set category-wise budgets "
            "to control your spending."
        )

    if spending_score < 60:

        reasons.append(
            "Your spending is relatively high "
            "compared with your income."
        )

    if goal_score == 0:

        reasons.append(
            "Add a saving goal to start "
            "tracking your progress."
        )

    if not reasons:

        reasons.append(
            "Your financial habits are "
            "currently well balanced."
        )


    # -----------------------------------------------------
    # RETURN HEALTH SCORE
    # -----------------------------------------------------

    return jsonify({

        "score": final_score,

        "status": status,

        "breakdown": {

            "saving": saving_score,

            "budget": budget_score,

            "spending": spending_score,

            "goals": goal_score

        },

        "reasons": reasons

    })


# =========================================================
# CREATE DATABASE
# =========================================================

with app.app_context():

    db.create_all()


# =========================================================
# RUN APP
# =========================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )