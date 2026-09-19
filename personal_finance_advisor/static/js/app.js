const $ = (selector) => document.querySelector(selector);

let incomeExpenseChart = null;
let categoryChart = null;


/* =========================================================
   HELPERS
========================================================= */

function money(value) {
  return `₹${Number(value || 0).toLocaleString("en-IN", {
    maximumFractionDigits: 2
  })}`;
}

function toast(message) {
  const el = $("#toast");

  if (!el) return;

  el.textContent = message;
  el.classList.add("show");

  setTimeout(() => {
    el.classList.remove("show");
  }, 2500);
}

async function api(url, options = {}) {

  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {})
    },
    ...options
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(data.error || "Something went wrong.");
  }

  return data;
}

function formData(form) {
  return Object.fromEntries(new FormData(form).entries());
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function formatDate(value) {

  if (!value) return "-";

  const d = new Date(value + "T00:00:00");

  return d.toLocaleDateString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric"
  });
}


/* =========================================================
   DASHBOARD
========================================================= */

async function loadDashboard() {

  try {

    const data = await api("/api/dashboard");

    const income = $("#income");
    const expenses = $("#expenses");
    const balance = $("#balance");
    const savingsRate = $("#savingsRate");

    if (income) {
      income.textContent = money(data.income);
    }

    if (expenses) {
      expenses.textContent = money(data.expenses);
    }

    if (balance) {
      balance.textContent = money(data.balance);
    }

    if (savingsRate) {
      savingsRate.textContent = `${data.savings_rate}%`;
    }


    /* =====================================================
       EXPENSE BREAKDOWN
    ====================================================== */

    const categoryList = $("#categoryList");

    if (categoryList) {

      const categories = Object.entries(data.categories || {})
        .filter(([_, amount]) => Number(amount) > 0)
        .sort((a, b) => b[1] - a[1]);

      if (!categories.length) {

        categoryList.innerHTML =
          `<p class="muted">No expenses recorded yet.</p>`;

      } else {

        categoryList.innerHTML = categories.map(
          ([category, amount]) => `

            <div class="category-row">

              <div>
                <strong>${escapeHtml(category)}</strong>
              </div>

              <strong>${money(amount)}</strong>

            </div>

          `
        ).join("");
      }
    }


    /* =====================================================
       BUDGET LIST
    ====================================================== */

    const budgetList = $("#budgetList");

    if (budgetList) {

      const budgets = data.budgets || {};
      const categories = Object.keys(budgets);

      if (!categories.length) {

        budgetList.innerHTML =
          `<p class="muted">No budgets created yet.</p>`;

      } else {

        budgetList.innerHTML = categories.map(category => {

          const budget = Number(budgets[category] || 0);
          const spent = Number(data.categories?.[category] || 0);

          const percentage = budget
            ? Math.min((spent / budget) * 100, 100)
            : 0;

          return `

            <div class="budget-row">

              <div class="budget-row-top">

                <strong>
                  ${escapeHtml(category)}
                </strong>

                <span>
                  ${money(spent)} / ${money(budget)}
                </span>

              </div>

              <div class="progress">

                <div
                  class="progress-bar"
                  style="width:${percentage}%">
                </div>

              </div>

            </div>

          `;

        }).join("");
      }
    }


    /* =====================================================
       SAVING GOALS
    ====================================================== */

    const goalList = $("#goalList");

    if (goalList) {

      const goals = data.goals || [];

      if (!goals.length) {

        goalList.innerHTML =
          `<p class="muted">No saving goals added yet.</p>`;

      } else {

        goalList.innerHTML = goals.map(goal => {

          const target = Number(goal.target || 0);
          const saved = Number(goal.saved || 0);

          const percentage = target
            ? Math.min((saved / target) * 100, 100)
            : 0;

          return `

            <div class="goal-row">

              <div class="goal-row-top">

                <strong>
                  ${escapeHtml(goal.name)}
                </strong>

                <span>
                  ${money(saved)} / ${money(target)}
                </span>

              </div>

              <div class="progress">

                <div
                  class="progress-bar"
                  style="width:${percentage}%">
                </div>

              </div>

              <button
                class="secondary-btn"
                onclick="addSavings(
                  ${goal.id},
                  '${escapeHtml(goal.name)}',
                  ${target},
                  ${saved}
                )">

                + Add Savings

              </button>

            </div>

          `;

        }).join("");
      }
    }


    /* =====================================================
       UPDATE CHARTS
    ====================================================== */

    updateCharts(data);

  } catch (error) {

    console.error(error);
    toast(error.message);

  }
}


/* =========================================================
   FINANCIAL CHARTS
========================================================= */

function updateCharts(data) {

  const incomeCanvas = $("#incomeExpenseChart");
  const categoryCanvas = $("#categoryChart");


  /* =====================================================
     INCOME VS EXPENSE CHART
  ====================================================== */

  if (incomeCanvas && typeof Chart !== "undefined") {

    if (incomeExpenseChart) {
      incomeExpenseChart.destroy();
    }

    incomeExpenseChart = new Chart(
      incomeCanvas.getContext("2d"),
      {
        type: "bar",

        data: {
          labels: ["Income", "Expenses", "Balance"],

          datasets: [
            {
              label: "Amount",

              data: [
                Number(data.income || 0),
                Number(data.expenses || 0),
                Number(data.balance || 0)
              ],

              borderWidth: 1
            }
          ]
        },

        options: {
          responsive: true,

          maintainAspectRatio: false,

          plugins: {
            legend: {
              display: false
            }
          },

          scales: {
            y: {
              beginAtZero: true
            }
          }
        }
      }
    );
  }


  /* =====================================================
     CATEGORY CHART
  ====================================================== */

  if (categoryCanvas && typeof Chart !== "undefined") {

    if (categoryChart) {
      categoryChart.destroy();
    }

    const categoryData = Object.entries(
      data.categories || {}
    ).filter(([_, amount]) => Number(amount) > 0);

    categoryChart = new Chart(
      categoryCanvas.getContext("2d"),
      {
        type: "doughnut",

        data: {

          labels: categoryData.map(
            ([category]) => category
          ),

          datasets: [
            {
              data: categoryData.map(
                ([_, amount]) => Number(amount)
              ),

              borderWidth: 2
            }
          ]
        },

        options: {

          responsive: true,

          maintainAspectRatio: false,

          plugins: {
            legend: {
              position: "bottom"
            }
          }
        }
      }
    );
  }
}


/* =========================================================
   HISTORY
========================================================= */

async function loadHistory() {

  try {

    const [incomeData, expenseData] = await Promise.all([
      api("/api/income"),
      api("/api/expense")
    ]);


    /* =====================================================
       INCOME HISTORY
    ====================================================== */

    const incomeHistory = $("#incomeHistory");

    if (incomeHistory) {

      if (!incomeData.items.length) {

        incomeHistory.innerHTML =
          `<p class="muted">No income entries yet.</p>`;

      } else {

        incomeHistory.innerHTML =
          incomeData.items.map(item => `

            <div class="history-row">

              <div>

                <strong>
                  ${escapeHtml(item.source)}
                </strong>

                <small>
                  ${formatDate(item.date)}
                </small>

              </div>

              <strong>
                ${money(item.amount)}
              </strong>

              <div class="history-actions">

                <button
                  class="secondary-btn"
                  onclick="editIncome(
                    ${item.id},
                    '${escapeHtml(item.source)}',
                    ${item.amount},
                    '${item.date}'
                  )">

                  Edit

                </button>

                <button
                  class="danger-btn"
                  onclick="deleteIncome(${item.id})">

                  Delete

                </button>

              </div>

            </div>

          `).join("");
      }
    }


    /* =====================================================
       EXPENSE HISTORY
    ====================================================== */

    const expenseHistory = $("#expenseHistory");

    if (expenseHistory) {

      if (!expenseData.items.length) {

        expenseHistory.innerHTML =
          `<p class="muted">No expense entries yet.</p>`;

      } else {

        expenseHistory.innerHTML =
          expenseData.items.map(item => `

            <div class="history-row">

              <div>

                <strong>
                  ${escapeHtml(item.title)}
                </strong>

                <small>
                  ${escapeHtml(item.category)}
                  •
                  ${formatDate(item.date)}
                </small>

              </div>

              <strong>
                ${money(item.amount)}
              </strong>

              <div class="history-actions">

                <button
                  class="secondary-btn"
                  onclick="editExpense(
                    ${item.id},
                    '${escapeHtml(item.title)}',
                    '${escapeHtml(item.category)}',
                    ${item.amount},
                    '${item.date}'
                  )">

                  Edit

                </button>

                <button
                  class="danger-btn"
                  onclick="deleteExpense(${item.id})">

                  Delete

                </button>

              </div>

            </div>

          `).join("");
      }
    }

  } catch (error) {

    console.error(error);
    toast(error.message);

  }
}


/* =========================================================
   EDIT INCOME
========================================================= */

async function editIncome(
  id,
  oldSource,
  oldAmount,
  oldDate
) {

  const source = prompt(
    "Enter income source:",
    oldSource
  );

  if (source === null) return;

  const amount = prompt(
    "Enter amount:",
    oldAmount
  );

  if (amount === null) return;

  const date = prompt(
    "Enter date (YYYY-MM-DD):",
    oldDate
  );

  if (date === null) return;


  try {

    await api(`/api/income/${id}`, {

      method: "PUT",

      body: JSON.stringify({
        source,
        amount,
        date
      })

    });

    toast("Income updated successfully ✅");

    await loadDashboard();
    await loadHistory();
    await loadReport();
    await loadInsights();

  } catch (error) {

    toast(error.message);

  }
}


/* =========================================================
   DELETE INCOME
========================================================= */

async function deleteIncome(id) {

  if (!confirm("Are you sure you want to delete this income?")) {
    return;
  }

  try {

    await api(`/api/income/${id}`, {
      method: "DELETE"
    });

    toast("Income deleted.");

    await loadDashboard();
    await loadHistory();
    await loadReport();
    await loadInsights();

  } catch (error) {

    toast(error.message);

  }
}


/* =========================================================
   EDIT EXPENSE
========================================================= */

async function editExpense(
  id,
  oldTitle,
  oldCategory,
  oldAmount,
  oldDate
) {

  const title = prompt(
    "Enter expense title:",
    oldTitle
  );

  if (title === null) return;

  const category = prompt(
    "Enter category:",
    oldCategory
  );

  if (category === null) return;

  const amount = prompt(
    "Enter amount:",
    oldAmount
  );

  if (amount === null) return;

  const date = prompt(
    "Enter date (YYYY-MM-DD):",
    oldDate
  );

  if (date === null) return;


  try {

    await api(`/api/expense/${id}`, {

      method: "PUT",

      body: JSON.stringify({
        title,
        category,
        amount,
        date
      })

    });

    toast("Expense updated successfully ✅");

    await loadDashboard();
    await loadHistory();
    await loadReport();
    await loadInsights();

  } catch (error) {

    toast(error.message);

  }
}


/* =========================================================
   DELETE EXPENSE
========================================================= */

async function deleteExpense(id) {

  if (!confirm("Are you sure you want to delete this expense?")) {
    return;
  }

  try {

    await api(`/api/expense/${id}`, {
      method: "DELETE"
    });

    toast("Expense deleted.");

    await loadDashboard();
    await loadHistory();
    await loadReport();
    await loadInsights();

  } catch (error) {

    toast(error.message);

  }
}


/* =========================================================
   SAVINGS
========================================================= */

async function addSavings(
  id,
  name,
  target,
  currentSaved
) {

  const saved = prompt(
    `How much have you saved for "${name}"?\n\nTarget: ${money(target)}`,
    currentSaved
  );

  if (saved === null) return;


  try {

    await api(`/api/goal/${id}`, {

      method: "PUT",

      body: JSON.stringify({
        saved
      })

    });

    toast("Savings updated successfully 🎯");

    await loadDashboard();
    await loadInsights();

  } catch (error) {

    toast(error.message);

  }
}


/* =========================================================
   SMART FINANCIAL INSIGHTS
========================================================= */

async function loadInsights() {

  try {

    const data = await api("/api/insights");

    const list = $("#insightsList");

    if (!list) return;


    if (!data.insights || !data.insights.length) {

      list.innerHTML =
        `<p class="muted">No insights available yet.</p>`;

      return;
    }


    list.innerHTML = data.insights.map(insight => {

      let icon = "💡";

      if (insight.type === "warning") {
        icon = "⚠️";
      }

      if (insight.type === "success") {
        icon = "✅";
      }

      if (insight.type === "goal") {
        icon = "🎯";
      }

      if (insight.type === "info") {
        icon = "ℹ️";
      }


      return `

        <div class="insight-item ${escapeHtml(insight.type)}">

          <div class="insight-icon">
            ${icon}
          </div>

          <div class="insight-content">

            <strong>
              ${escapeHtml(insight.title)}
            </strong>

            <p>
              ${escapeHtml(insight.message)}
            </p>

          </div>

        </div>

      `;

    }).join("");


  } catch (error) {

    console.error(error);

    const list = $("#insightsList");

    if (list) {

      list.innerHTML =
        `<p class="muted">${escapeHtml(error.message)}</p>`;

    }

  }
}


/* =========================================================
   MONTHLY REPORT
========================================================= */

async function loadReport() {

  try {

    const data = await api("/api/report");

    const report = $("#report");

    if (!report) return;


    report.innerHTML = `

      <div class="report-item">
        <span>Month</span>
        <strong>${escapeHtml(data.month)}</strong>
      </div>

      <div class="report-item">
        <span>Income</span>
        <strong>${money(data.income)}</strong>
      </div>

      <div class="report-item">
        <span>Expenses</span>
        <strong>${money(data.expenses)}</strong>
      </div>

      <div class="report-item">
        <span>Savings</span>
        <strong>${money(data.savings)}</strong>
      </div>

      <div class="report-item">
        <span>Top Category</span>
        <strong>${escapeHtml(data.top_category)}</strong>
      </div>

    `;

  } catch (error) {

    console.error(error);
    toast(error.message);

  }
}


/* =========================================================
   ADD INCOME FORM
========================================================= */

const incomeForm = $("#incomeForm");

if (incomeForm) {

  incomeForm.addEventListener(
    "submit",
    async (event) => {

      event.preventDefault();

      try {

        const data = formData(incomeForm);

        await api("/api/income", {

          method: "POST",

          body: JSON.stringify(data)

        });

        incomeForm.reset();

        toast("Income added successfully 💰");

        await loadDashboard();
        await loadHistory();
        await loadReport();
        await loadInsights();

      } catch (error) {

        toast(error.message);

      }

    }
  );
}


/* =========================================================
   ADD EXPENSE FORM
========================================================= */

const expenseForm = $("#expenseForm");

if (expenseForm) {

  expenseForm.addEventListener(
    "submit",
    async (event) => {

      event.preventDefault();

      try {

        const data = formData(expenseForm);

        await api("/api/expense", {

          method: "POST",

          body: JSON.stringify(data)

        });

        expenseForm.reset();

        toast("Expense added successfully 💸");

        await loadDashboard();
        await loadHistory();
        await loadReport();
        await loadInsights();

      } catch (error) {

        toast(error.message);

      }

    }
  );
}


/* =========================================================
   BUDGET FORM
========================================================= */

const budgetForm = $("#budgetForm");

if (budgetForm) {

  budgetForm.addEventListener(
    "submit",
    async (event) => {

      event.preventDefault();

      try {

        const data = formData(budgetForm);

        await api("/api/budget", {

          method: "POST",

          body: JSON.stringify(data)

        });

        budgetForm.reset();

        toast("Budget saved successfully 📊");

        await loadDashboard();
        await loadInsights();

      } catch (error) {

        toast(error.message);

      }

    }
  );
}


/* =========================================================
   SAVING GOAL FORM
========================================================= */

const goalForm = $("#goalForm");

if (goalForm) {

  goalForm.addEventListener(
    "submit",
    async (event) => {

      event.preventDefault();

      try {

        const data = formData(goalForm);

        await api("/api/goal", {

          method: "POST",

          body: JSON.stringify(data)

        });

        goalForm.reset();

        toast("Saving goal added 🎯");

        await loadDashboard();
        await loadInsights();

      } catch (error) {

        toast(error.message);

      }

    }
  );
}


/* =========================================================
   AI ADVISOR
========================================================= */

const advisorForm = $("#advisorForm");

if (advisorForm) {

  advisorForm.addEventListener(
    "submit",
    async (event) => {

      event.preventDefault();

      const questionInput = $("#advisorQuestion");
      const answerBox = $("#advisorAnswer");

      if (!questionInput || !answerBox) return;

      const question = questionInput.value.trim();

      if (!question) {

        toast("Please enter a question.");

        return;
      }


      answerBox.innerHTML =
        `<p class="muted">Thinking... 🤖</p>`;


      try {

        const data = await api("/api/advisor", {

          method: "POST",

          body: JSON.stringify({
            question
          })

        });


        answerBox.innerHTML = `

          <div class="advisor-response">

            ${escapeHtml(
              data.answer || "No answer available."
            )}

          </div>

        `;

      } catch (error) {

        answerBox.innerHTML =
          `<p class="muted">${escapeHtml(error.message)}</p>`;

      }

    }
  );
}


/* =========================================================
   REFRESH REPORT
========================================================= */

const refreshReport = $("#refreshReport");

if (refreshReport) {

  refreshReport.addEventListener(
    "click",
    async () => {

      await loadReport();

      toast("Report refreshed 📊");

    }
  );
}


/* =========================================================
   CURRENT MONTH
========================================================= */

const currentMonth = $("#currentMonth");

if (currentMonth) {

  currentMonth.textContent =
    new Date().toLocaleDateString(
      "en-IN",
      {
        month: "long",
        year: "numeric"
      }
    );
}
/* =========================================================
   FINANCIAL HEALTH SCORE
========================================================= */

async function loadHealthScore() {

  try {

    const data = await api("/api/health-score");

    const score = $("#healthScore");
    const status = $("#healthStatus");

    const saving = $("#savingScore");
    const budget = $("#budgetScore");
    const spending = $("#spendingScore");
    const goals = $("#goalScore");

    if (score) {
      score.textContent = data.score;
    }

    if (status) {
      status.textContent = data.status;
    }

    if (saving) {
      saving.textContent = `${data.breakdown.saving}/100`;
    }

    if (budget) {
      budget.textContent = `${data.breakdown.budget}/100`;
    }

    if (spending) {
      spending.textContent = `${data.breakdown.spending}/100`;
    }

    if (goals) {
      goals.textContent = `${data.breakdown.goals}/100`;
    }

  } catch (error) {

    console.error("Health Score Error:", error);

    const status = $("#healthStatus");

    if (status) {
      status.textContent = "Unable to calculate";
    }

  }
}


/* =========================================================
   INITIAL LOAD
========================================================= */

loadDashboard();
loadHistory();
loadReport();
loadInsights();
loadHealthScore();

