from flask import Flask, render_template, request, redirect, url_for, send_file, flash
import sqlite3
from datetime import date, datetime
import csv
import io
import os
import calendar

# CONFIG
DB_NAME = "expense_tracker.db"
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret")




# ---------- Database helpers ----------
def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def create_table():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
            category TEXT NOT NULL,
            amount REAL NOT NULL,
            note TEXT
        )
        """
    )
    conn.commit()
    conn.close()


# ---------- Context processor: header stats ----------
@app.context_processor
def inject_header_stats():
    """
    Provide header-level stats to every template:
      - header_display_month (e.g. "December 2025")
      - header_total_income (float)
      - header_total_expense (float)
      - header_balance (float)
      - header_avg_daily (float, avg expense per day in current month)
      - header_days_passed (int)
    Returns safe defaults on error.
    """
    try:
        create_table()  # ensure schema exists
        today = date.today()
        year = today.year
        month = today.month

        current_pattern = f"{year}-{month:02d}-%"

        conn = get_connection()
        cur = conn.cursor()

        cur.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE type='income' AND date LIKE ?",
            (current_pattern,),
        )
        total_income = float(cur.fetchone()[0] or 0.0)

        cur.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE type='expense' AND date LIKE ?",
            (current_pattern,),
        )
        total_expense = float(cur.fetchone()[0] or 0.0)

        conn.close()

        balance = total_income - total_expense

        days_passed = today.day if today.day > 0 else 1
        avg_daily = round(total_expense / days_passed, 2) if days_passed else 0.0

        display_month = datetime(year, month, 1).strftime("%B %Y")

        return {
            "header_display_month": display_month,
            "header_total_income": total_income,
            "header_total_expense": total_expense,
            "header_balance": balance,
            "header_avg_daily": avg_daily,
            "header_days_passed": days_passed,
        }
    except Exception:
        # Safe defaults
        return {
            "header_display_month": "",
            "header_total_income": 0.0,
            "header_total_expense": 0.0,
            "header_balance": 0.0,
            "header_avg_daily": 0.0,
            "header_days_passed": 0,
        }


# ---------- Routes ----------
@app.route("/")
def index():
    """Dashboard: show current month summary and quick links."""
    create_table()
    today = date.today()
    year = today.year
    month = today.month
    pattern = f"{year}-{month:02d}-%"

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE type='income' AND date LIKE ?",
        (pattern,),
    )
    total_income = float(cur.fetchone()[0] or 0.0)

    cur.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE type='expense' AND date LIKE ?",
        (pattern,),
    )
    total_expense = float(cur.fetchone()[0] or 0.0)

    # Expense by category (Current Month)
    cur.execute(
        "SELECT category, SUM(amount) FROM transactions WHERE type='expense' AND date LIKE ? GROUP BY category",
        (pattern,),
    )
    expense_by_category = cur.fetchall()
    category_labels = [row[0] for row in expense_by_category]
    category_values = [float(row[1]) for row in expense_by_category]

    # Monthly Spending Trend (All Time)
    cur.execute(
        "SELECT substr(date, 1, 7) as month, SUM(amount) FROM transactions WHERE type='expense' GROUP BY month ORDER BY month ASC"
    )
    trend_by_month = cur.fetchall()
    
    trend_labels = []
    for row in trend_by_month:
        try:
            m_dt = datetime.strptime(row[0], "%Y-%m")
            trend_labels.append(m_dt.strftime("%B %Y"))
        except ValueError:
            trend_labels.append(row[0])

    trend_values = [float(row[1]) for row in trend_by_month]

    conn.close()

    balance = total_income - total_expense

    return render_template(
        "index.html",
        total_income=total_income,
        total_expense=total_expense,
        balance=balance,
        category_labels=category_labels,
        category_values=category_values,
        trend_labels=trend_labels,
        trend_values=trend_values,
    )


@app.route("/add", methods=["GET", "POST"])
def add_transaction():
    if request.method == "POST":
        t_type = request.form.get("type", "").lower()
        amount_str = request.form.get("amount", "").strip()
        category = request.form.get("category", "").strip()
        note = request.form.get("note", "").strip()
        date_str = request.form.get("date", "").strip()

        # Validation
        if t_type not in ("income", "expense"):
            flash("Type must be income or expense.", "danger")
            return redirect(url_for("add_transaction"))

        try:
            amount = float(amount_str)
        except (ValueError, TypeError):
            flash("Amount must be a number.", "danger")
            return redirect(url_for("add_transaction"))

        if not category:
            flash("Category is required.", "danger")
            return redirect(url_for("add_transaction"))

        if not date_str:
            date_str = date.today().strftime("%Y-%m-%d")
        else:
            try:
                # accept either YYYY-MM-DD or DD-MM-YYYY (common user entry) -- normalize to YYYY-MM-DD
                # Prefer strict YYYY-MM-DD by default; if user sends DD-MM-YYYY, try to parse.
                try:
                    datetime.strptime(date_str, "%Y-%m-%d")
                except ValueError:
                    # attempt DD-MM-YYYY
                    parsed = datetime.strptime(date_str, "%d-%m-%Y")
                    date_str = parsed.strftime("%Y-%m-%d")
            except ValueError:
                flash("Date must be in YYYY-MM-DD or DD-MM-YYYY format.", "danger")
                return redirect(url_for("add_transaction"))

        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO transactions (date, type, category, amount, note) VALUES (?, ?, ?, ?, ?)",
            (date_str, t_type, category, amount, note),
        )
        conn.commit()
        conn.close()

        flash("Transaction added successfully!", "success")
        return redirect(url_for("index"))

    today_str = date.today().strftime("%Y-%m-%d")
    return render_template("add.html", today=today_str)


@app.route("/transactions")
def transactions():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, date, type, category, amount, note FROM transactions ORDER BY date DESC, id DESC"
    )
    rows = cur.fetchall()
    conn.close()
    return render_template("transactions.html", rows=rows)


@app.route("/delete/<int:id>", methods=["POST"])
def delete_transaction(id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM transactions WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    flash("Transaction deleted successfully!", "success")
    return redirect(request.referrer or url_for("index"))


@app.route("/summary", methods=["GET", "POST"])
def summary():
    """
    If POST: expects 'year' (YYYY) and 'month' (MM). Returns summary for that month
    with readable month_name (e.g., 'December 2025') passed as month_name to template.
    """
    data = None
    year = ""
    month = ""
    month_name = ""
    rows = []

    if request.method == "POST":
        year = request.form.get("year", "").strip()
        month = request.form.get("month", "").strip()

        # Basic validation
        if len(year) != 4 or len(month) != 2 or not year.isdigit() or not month.isdigit():
            flash("Year must be YYYY and month must be MM (both numeric).", "danger")
            return redirect(url_for("summary"))

        pattern = f"{year}-{month}-%"

        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE type='income' AND date LIKE ?",
            (pattern,),
        )
        total_income = float(cur.fetchone()[0] or 0.0)

        cur.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE type='expense' AND date LIKE ?",
            (pattern,),
        )
        total_expense = float(cur.fetchone()[0] or 0.0)

        cur.execute(
            "SELECT id, date, type, category, amount, note FROM transactions WHERE date LIKE ? ORDER BY date DESC, id DESC",
            (pattern,),
        )
        rows = cur.fetchall()
        conn.close()

        balance = total_income - total_expense
        data = {"total_income": total_income, "total_expense": total_expense, "balance": balance}

        # convert month number to human name safely
        try:
            month_int = int(month)
            month_name = calendar.month_name[month_int] if 1 <= month_int <= 12 else f"{month}"
        except Exception:
            month_name = f"{year}-{month}"

    return render_template("summary.html", data=data, year=year, month=month, month_name=month_name, rows=rows)


@app.route("/export_csv")
def export_csv():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, date, type, category, amount, note FROM transactions ORDER BY date ASC, id ASC")
    rows = cur.fetchall()
    conn.close()

    if not rows:
        flash("No data to export.", "warning")
        return redirect(url_for("index"))

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Date", "Type", "Category", "Amount", "Note"])
    for row in rows:
        writer.writerow([row["id"], row["date"], row["type"], row["category"], row["amount"], row["note"]])

    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode("utf-8")),
        mimetype="text/csv",
        as_attachment=True,
        download_name="expenses.csv",
    )


# ---------- Run ----------
if __name__ == "__main__":
    create_table()
    app.run(debug=False)

