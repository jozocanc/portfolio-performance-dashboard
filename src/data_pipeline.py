"""ETL: yfinance → SQLite. Clean star-style schema for EAM reporting.

Tables:
  securities(ticker PK, name, asset_class, region, currency)
  prices(ticker, date, close, adj_close, volume)  — composite PK
  portfolio_weights(ticker PK, weight)
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd
import yfinance as yf

from .universe import DEFAULT_PORTFOLIO_WEIGHTS, full_universe


DB_PATH = Path(__file__).resolve().parent.parent / "data" / "eam.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


SCHEMA = """
CREATE TABLE IF NOT EXISTS securities (
    ticker TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    asset_class TEXT NOT NULL,
    region TEXT NOT NULL,
    currency TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS prices (
    ticker TEXT NOT NULL,
    date TEXT NOT NULL,
    close REAL,
    adj_close REAL,
    volume REAL,
    PRIMARY KEY (ticker, date),
    FOREIGN KEY (ticker) REFERENCES securities(ticker)
);

CREATE TABLE IF NOT EXISTS portfolio_weights (
    ticker TEXT PRIMARY KEY,
    weight REAL NOT NULL,
    FOREIGN KEY (ticker) REFERENCES securities(ticker)
);

CREATE INDEX IF NOT EXISTS idx_prices_date ON prices(date);
"""


def connect(db_path: Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    return conn


def load_securities(conn: sqlite3.Connection) -> None:
    rows = [(s.ticker, s.name, s.asset_class, s.region, s.currency) for s in full_universe()]
    conn.executemany(
        "INSERT OR REPLACE INTO securities VALUES (?, ?, ?, ?, ?)",
        rows,
    )
    conn.executemany(
        "INSERT OR REPLACE INTO portfolio_weights VALUES (?, ?)",
        list(DEFAULT_PORTFOLIO_WEIGHTS.items()),
    )
    conn.commit()


def fetch_prices(tickers: list[str], period: str = "5y") -> pd.DataFrame:
    raw = yf.download(
        tickers,
        period=period,
        auto_adjust=False,
        progress=False,
        group_by="ticker",
        threads=True,
    )
    frames: list[pd.DataFrame] = []
    for ticker in tickers:
        try:
            sub = raw[ticker].copy()
        except (KeyError, TypeError):
            continue
        if sub.empty:
            continue
        sub = sub.reset_index().rename(
            columns={
                "Date": "date",
                "Close": "close",
                "Adj Close": "adj_close",
                "Volume": "volume",
            }
        )
        sub["ticker"] = ticker
        sub = sub[["ticker", "date", "close", "adj_close", "volume"]].dropna(
            subset=["close"]
        )
        sub["date"] = sub["date"].dt.strftime("%Y-%m-%d")
        frames.append(sub)
    if not frames:
        return pd.DataFrame(columns=["ticker", "date", "close", "adj_close", "volume"])
    return pd.concat(frames, ignore_index=True)


def load_prices(conn: sqlite3.Connection, period: str = "5y") -> int:
    tickers = [s.ticker for s in full_universe()]
    df = fetch_prices(tickers, period=period)
    if df.empty:
        return 0
    conn.executemany(
        "INSERT OR REPLACE INTO prices(ticker, date, close, adj_close, volume) VALUES (?, ?, ?, ?, ?)",
        df.itertuples(index=False, name=None),
    )
    conn.commit()
    return len(df)


def refresh_all(period: str = "5y") -> int:
    conn = connect()
    try:
        load_securities(conn)
        n = load_prices(conn, period=period)
    finally:
        conn.close()
    return n


if __name__ == "__main__":
    n = refresh_all()
    print(f"Loaded {n:,} price rows into {DB_PATH}")
