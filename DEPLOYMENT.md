# SmartSpend AI: Streamlit Community Cloud Deployment Guide

This guide walks you through deploying **SmartSpend AI** to **Streamlit Community Cloud** with public access and zero reviewer setup.

---

## 📋 Prerequisites

1. A free [GitHub Account](https://github.com/).
2. A free [Streamlit Community Cloud Account](https://share.streamlit.io/).
3. *(Optional)* A Google Gemini API Key from [Google AI Studio](https://aistudio.google.com/).

---

## 🚀 Step 1: Push Code to GitHub

1. Initialize Git in the project root:
   ```bash
   cd smartspend-ai
   git init
   git branch -M main
   ```

2. Add all project files and commit:
   ```bash
   git add .
   git commit -m "feat: initial commit of SmartSpend AI with 6-month demo & dual engine"
   ```

3. Create a new public repository on GitHub named `smartspend-ai`.

4. Link and push to GitHub:
   ```bash
   git remote add origin https://github.com/<YOUR_GITHUB_USERNAME>/smartspend-ai.git
   git push -u origin main
   ```

---

## ☁️ Step 2: Deploy to Streamlit Community Cloud

1. Log in to [share.streamlit.io](https://share.streamlit.io/).
2. Click the **"New app"** button.
3. Fill in the deployment form:
   - **Repository:** `<YOUR_GITHUB_USERNAME>/smartspend-ai`
   - **Branch:** `main`
   - **Main file path:** `app.py`
   - **App URL:** Customize if desired (e.g. `smartspend-ai.streamlit.app`)
4. Expand **Advanced settings...** at the bottom of the form.

---

## 🔐 Step 3: Configure Streamlit Secrets (Gemini API Key)

In the **Advanced settings** popup, locate the **Secrets** text area and enter your Google Gemini API Key in TOML format:

```toml
GEMINI_API_KEY = "AIzaSyYourActualGeminiApiKeyHere..."
```

> **Note on Zero-Setup / Missing Key:**
> If you leave Secrets blank or do not provide a key, **SmartSpend AI will still work 100% flawlessly!** The built-in rule-based fallback engine automatically handles all parsing, calculations, 50/30/20 breakdowns, and grounded chat responses without ever showing an error screen.

Click **Save**, then click **Deploy!**

---

## 🔍 Step 4: Verification & Live Demo Testing

Once deployment completes (usually 1-2 minutes):

1. **Verify Landing Page:**
   - Confirm the modern dark theme, hero banner, and feature cards appear.
   - Click **"🚀 Try Demo Account"**.
   - Ensure the notification confirms: *"Loaded 300+ realistic INR transactions across 6 months!"*

2. **Verify Dashboard:**
   - Check that KPI cards (Total Income, Total Expenses, Net Savings, Savings Rate, MoM Changes) display real INR numbers (e.g., `₹5,28,000`).
   - Interact with the Plotly Category Doughnut, Monthly Income vs Expense Bars, and Daily Spending Trend line.

3. **Verify Chat Copilot:**
   - Click one of the quick prompt chips: *"Where am I overspending?"* or *"Can I afford a ₹60,000 phone?"*.
   - Verify the assistant responds in under 4 sentences, cites real figures from the ledger, and ends with an actionable tip and disclaimer.
   - Test a natural language input: *"Spent 450 on Zomato yesterday"* or Hinglish *"Aaj chai pe 20 rupay gaye"*.

4. **Verify AI Insights & Forecasting:**
   - Observe the 0-100 Financial Health score gauge.
   - Inspect the 3-Month Linear Regression expense projection chart.
   - Check the 50/30/20 breakdown cards and Z-score spending anomaly cards.

5. **Verify Reports & PDF:**
   - Go to **Reports & Imports** -> **Download PDF & CSV**.
   - Click **"Compile Executive PDF"** and download the resulting file. Open it to confirm clean formatting, tables, and KPIs.

---

## 🛡️ Cloud Persistence & Disk Reset Handling

Streamlit Community Cloud operates on ephemeral containers. Whenever the free cloud instance reboots or sleeps:
- `SmartSpend AI` automatically detects if the session database is uninitialized.
- It triggers `seed_demo_data()` silently on first load, ensuring that external reviewers and internship evaluators always see populated charts and metrics upon opening the public URL!
