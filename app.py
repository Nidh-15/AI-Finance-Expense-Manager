
import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import plotly.express as px
from datetime import date
from io import BytesIO
from reportlab.pdfgen import canvas

# ==========================================
# 1. PAGE CONFIGURATION
# ==========================================

st.set_page_config(
    page_title="AI Finance Manager",
    page_icon="💰",
    layout="wide"
)

st.title("💰 AI Finance & Expense Manager")
st.caption("Track your money, understand your spending and plan ahead.")

# ==========================================
# 2. DATABASE CONNECTION
# ==========================================

conn = sqlite3.connect("finance_manager.db", check_same_thread=False)

conn.execute("""
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    transaction_type TEXT NOT NULL,
    amount REAL NOT NULL,
    transaction_date TEXT NOT NULL
)
""")

conn.commit()

# ==========================================
# 3. DATABASE FUNCTIONS
# ==========================================

def add_transaction(title, category, transaction_type, amount, transaction_date):
    conn.execute("""
        INSERT INTO transactions
        (title, category, transaction_type, amount, transaction_date)
        VALUES (?, ?, ?, ?, ?)
    """, (title, category, transaction_type, amount, str(transaction_date)))

    conn.commit()


def get_transactions():
    df = pd.read_sql_query(
        "SELECT * FROM transactions ORDER BY transaction_date DESC",
        conn
    )

    if not df.empty:
        df["transaction_date"] = pd.to_datetime(
            df["transaction_date"]
        )

    return df


def delete_transaction(transaction_id):
    conn.execute(
        "DELETE FROM transactions WHERE id = ?",
        (transaction_id,)
    )
    conn.commit()


# ==========================================
# 4. ADD TRANSACTION
# ==========================================

st.sidebar.header("➕ Add Transaction")

with st.sidebar.form("transaction_form"):

    title = st.text_input("Transaction Title")

    category = st.selectbox(
        "Category",
        [
            "Food",
            "Travel",
            "Shopping",
            "Bills",
            "Education",
            "Health",
            "Entertainment",
            "Salary",
            "Other"
        ]
    )

    transaction_type = st.selectbox(
        "Transaction Type",
        ["Income", "Expense"]
    )

    amount = st.number_input(
        "Amount (₹)",
        min_value=0.0,
        step=100.0
    )

    transaction_date = st.date_input(
        "Transaction Date",
        value=date.today()
    )

    submitted = st.form_submit_button(
        "Add Transaction",
        use_container_width=True
    )

    if submitted:

        if not title.strip():
            st.error("Please enter a transaction title.")

        elif amount <= 0:
            st.error("Please enter an amount greater than zero.")

        else:
            add_transaction(
                title,
                category,
                transaction_type,
                amount,
                transaction_date
            )

            st.success("Transaction added successfully!")
            st.rerun()


# ==========================================
# 5. LOAD TRANSACTION DATA
# ==========================================

df = get_transactions()

if df.empty:

    st.info(
        "No transactions available. "
        "Add your first transaction using the sidebar."
    )

    st.stop()


# ==========================================
# 6. FINANCIAL ANALYSIS
# ==========================================

income = df.loc[
    df["transaction_type"] == "Income", "amount"
].sum()

expenses = df.loc[
    df["transaction_type"] == "Expense", "amount"
].sum()

balance = income - expenses

st.subheader("📊 Financial Overview")

col1, col2, col3 = st.columns(3)

col1.metric("Total Income", f"₹{income:,.2f}")
col2.metric("Total Expenses", f"₹{expenses:,.2f}")
col3.metric("Net Balance", f"₹{balance:,.2f}")


# ==========================================
# 7. EXPENSE CHARTS
# ==========================================

st.divider()
st.subheader("📈 Expense Analysis")

expense_df = df[
    df["transaction_type"] == "Expense"
].copy()

if not expense_df.empty:

    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:

        category_data = expense_df.groupby(
            "category"
        )["amount"].sum().reset_index()

        fig_pie = px.pie(
            category_data,
            names="category",
            values="amount",
            title="Expenses by Category",
            hole=0.4
        )

        st.plotly_chart(
            fig_pie,
            use_container_width=True
        )

    with chart_col2:

        daily_data = expense_df.groupby(
            expense_df["transaction_date"].dt.date
        )["amount"].sum().reset_index()

        daily_data.columns = ["Date", "Amount"]

        fig_bar = px.bar(
            daily_data,
            x="Date",
            y="Amount",
            title="Daily Expenses",
            color="Amount"
        )

        st.plotly_chart(
            fig_bar,
            use_container_width=True
        )

else:
    st.info("Add some expense transactions to see charts.")


# ==========================================
# 8. EXPENSE FORECASTING
# ==========================================

st.divider()
st.subheader("🔮 Expense Forecast")

if len(expense_df) > 0:

    monthly_data = expense_df.copy()

    monthly_data["Month"] = (
        monthly_data["transaction_date"].dt.to_period("M")
    )

    monthly_expenses = monthly_data.groupby(
        "Month"
    )["amount"].sum().reset_index()

    if len(monthly_expenses) >= 2:

        x = np.arange(len(monthly_expenses))
        y = monthly_expenses["amount"].values

        slope, intercept = np.polyfit(x, y, 1)

        next_month_expense = slope * len(x) + intercept

        next_month_expense = max(0, next_month_expense)

        st.metric(
            "Estimated Next Month Expenses",
            f"₹{next_month_expense:,.2f}"
        )

        st.caption(
            "This estimate uses a simple linear trend "
            "from your recorded monthly expenses. "
            "It is not a guaranteed prediction."
        )

        forecast_chart = px.line(
            monthly_expenses,
            x="Month",
            y="amount",
            markers=True,
            title="Monthly Expense Trend"
        )

        st.plotly_chart(
            forecast_chart,
            use_container_width=True
        )

    else:
        st.info(
            "Add expenses across at least two different months "
            "to calculate a trend-based forecast."
        )

else:
    st.info("Add expense transactions to generate a forecast.")


# ==========================================
# 9. TRANSACTION HISTORY
# ==========================================

st.divider()
st.subheader("📋 Transaction History")

display_df = df.copy()

display_df["transaction_date"] = (
    display_df["transaction_date"].dt.strftime("%Y-%m-%d")
)

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True
)


# ==========================================
# 10. DELETE TRANSACTION
# ==========================================

st.subheader("🗑️ Delete Transaction")

transaction_ids = df["id"].tolist()

selected_id = st.selectbox(
    "Select Transaction ID",
    transaction_ids
)

if st.button("Delete Selected Transaction"):

    delete_transaction(selected_id)

    st.success("Transaction deleted successfully!")
    st.rerun()


# ==========================================
# 11. PDF RECEIPT GENERATION
# ==========================================

st.divider()
st.subheader("🧾 Generate PDF Receipt")

selected_receipt_id = st.selectbox(
    "Select Transaction for Receipt",
    transaction_ids,
    key="receipt_select"
)

if st.button("Generate Receipt"):

    selected_row = df[
        df["id"] == selected_receipt_id
    ].iloc[0]

    pdf_buffer = BytesIO()

    pdf = canvas.Canvas(pdf_buffer)

    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawString(50, 780, "Finance Manager Receipt")

    pdf.setFont("Helvetica", 12)

    pdf.drawString(50, 730, f"Receipt ID: {selected_row['id']}")
    pdf.drawString(50, 700, f"Title: {selected_row['title']}")
    pdf.drawString(50, 670, f"Category: {selected_row['category']}")
    pdf.drawString(50, 640, f"Type: {selected_row['transaction_type']}")
    pdf.drawString(50, 610, f"Amount: Rs. {selected_row['amount']:.2f}")
    pdf.drawString(
        50,
        580,
        f"Date: {selected_row['transaction_date'].strftime('%Y-%m-%d')}"
    )

    pdf.drawString(50, 520, "Thank you for using Finance Manager!")

    pdf.save()

    st.download_button(
        label="Download PDF Receipt",
        data=pdf_buffer.getvalue(),
        file_name=f"receipt_{selected_receipt_id}.pdf",
        mime="application/pdf"
    )


# ==========================================
# 12. CSV EXPORT
# ==========================================

st.divider()
st.subheader("📥 Export Your Transactions")

csv_data = df.to_csv(index=False).encode("utf-8")

st.download_button(
    label="Download Transactions CSV",
    data=csv_data,
    file_name="finance_transactions.csv",
    mime="text/csv"
)


# ==========================================
# 13. FOOTER
# ==========================================

st.divider()

st.caption(
    "AI Finance & Expense Manager | Built using Python, "
    "Streamlit, SQLite, Pandas, NumPy and Plotly"
)
