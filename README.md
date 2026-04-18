# EAM Client Reporting Dashboard

A production-style performance and risk dashboard modeled on the kind of
reporting an **External Asset Manager (EAM)** serviced through a Swiss private
bank (e.g., UBS FIM Client Services) would deliver to end clients.

Built end-to-end in Python: ingestion, storage, analytics, and a live
Streamlit front end. Swiss blue-chip core, regional ETF diversification,
benchmark-relative attribution, risk analytics, and a client-facing UI.

**Live demo:** _deployed link added after first build_

---

## What it does

- **Ingests** daily prices for 15 Swiss + regional securities and 3 benchmark
  indices (SMI, EURO STOXX 50, S&P 500) from Yahoo Finance.
- **Stores** the data in a SQLite warehouse with a clean star-style schema
  (`securities`, `prices`, `portfolio_weights`).
- **Computes** the full analyst stack: total and annualized return, volatility,
  Sharpe, Sortino, max drawdown, Calmar, beta, alpha, tracking error,
  information ratio, rolling metrics, and drawdown curves.
- **Reports** through a Streamlit dashboard with five tabs — Overview,
  Performance, Risk, Allocation, Holdings — styled as an EAM client report.

## Why it exists

This project was built as a portfolio piece for analyst roles in Swiss
private banking and wealth management — specifically the kind of work
that supports external asset managers who custody client assets at a Swiss
universal bank. It demonstrates:

- SQL + Python data engineering against a warehoused dataset
- Core performance and risk analytics implemented from scratch
- Business-intelligence delivery via a live, clickable dashboard
- Client-reporting presentation appropriate for a non-technical audience

## Stack

| Layer | Tool |
|---|---|
| Ingestion | `yfinance` |
| Storage | SQLite |
| Analytics | `pandas`, `numpy` |
| Dashboard | Streamlit + Plotly |
| Deployment | Streamlit Community Cloud |

## Project structure

```
ubs-eam-dashboard/
├── app.py                # Streamlit front end
├── requirements.txt
├── src/
│   ├── universe.py       # Investment universe + target weights
│   ├── data_pipeline.py  # yfinance → SQLite ETL
│   └── metrics.py        # Returns, risk, benchmark-relative analytics
├── data/                 # SQLite warehouse (gitignored)
└── docs/                 # Methodology notes
```

## Run locally

```bash
git clone https://github.com/jozocanc/ubs-eam-dashboard.git
cd ubs-eam-dashboard
pip install -r requirements.txt
python -m src.data_pipeline     # pulls ~22k price rows into SQLite
streamlit run app.py
```

## Methodology highlights

- **Returns**: daily percentage change on adjusted close (captures dividends
  and splits).
- **Portfolio construction**: daily-rebalanced target-weight book; weights
  are a plausible Swiss-core balanced mandate, not a live portfolio.
- **Sharpe / Sortino**: excess over a user-selectable annual risk-free rate,
  annualized by √252.
- **Beta / Alpha**: OLS of daily excess returns on benchmark excess returns,
  annualized.
- **Information ratio**: mean of active return / tracking error, annualized.

## Disclaimer

Demonstration project. Target weights are illustrative, not investment advice.
Data from Yahoo Finance — may differ from institutional-grade feeds.

---

Built by **[Jozo Cancar](https://www.linkedin.com/in/jozo-cancar-91b470300/)**
— MSBA, Florida Atlantic University · Swiss citizen · EN / DE / HR / FR.
