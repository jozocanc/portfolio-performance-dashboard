"""Portfolio analytics: returns, risk, drawdown, benchmark-relative metrics.

Conventions:
  - Daily returns from adjusted close (adj_close) to capture dividends + splits
  - Risk-free rate defaults to 0 for clarity; override for Sharpe/Sortino if needed
  - Trading days per year = 252
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .data_pipeline import DB_PATH

TRADING_DAYS = 252


# -- loading ---------------------------------------------------------------

def _connect(db_path: Path = DB_PATH) -> sqlite3.Connection:
    return sqlite3.connect(db_path)


def load_prices(tickers: list[str] | None = None, db_path: Path = DB_PATH) -> pd.DataFrame:
    """Wide panel: index=date, columns=tickers, values=adj_close."""
    with _connect(db_path) as conn:
        if tickers:
            placeholders = ",".join(["?"] * len(tickers))
            q = f"SELECT ticker, date, adj_close FROM prices WHERE ticker IN ({placeholders})"
            df = pd.read_sql_query(q, conn, params=tickers, parse_dates=["date"])
        else:
            df = pd.read_sql_query(
                "SELECT ticker, date, adj_close FROM prices",
                conn,
                parse_dates=["date"],
            )
    return df.pivot(index="date", columns="ticker", values="adj_close").sort_index()


def load_weights(db_path: Path = DB_PATH) -> pd.Series:
    with _connect(db_path) as conn:
        df = pd.read_sql_query("SELECT ticker, weight FROM portfolio_weights", conn)
    return df.set_index("ticker")["weight"]


def load_securities(db_path: Path = DB_PATH) -> pd.DataFrame:
    with _connect(db_path) as conn:
        return pd.read_sql_query("SELECT * FROM securities", conn)


# -- return math -----------------------------------------------------------

def daily_returns(prices: pd.DataFrame) -> pd.DataFrame:
    return prices.pct_change(fill_method=None).dropna(how="all")


def portfolio_returns(
    prices: pd.DataFrame, weights: pd.Series, rebalance: bool = True
) -> pd.Series:
    """Weighted daily returns. `rebalance=True` = daily rebalance to target weights
    (standard for client reporting baselines)."""
    aligned = prices[weights.index.intersection(prices.columns)].dropna(how="any")
    w = weights.reindex(aligned.columns).fillna(0)
    w = w / w.sum()
    rets = aligned.pct_change(fill_method=None).dropna()
    if rebalance:
        return rets.mul(w, axis=1).sum(axis=1)
    # buy-and-hold: weights drift with price
    values = (1 + rets).cumprod().mul(w, axis=1)
    total = values.sum(axis=1)
    return total.pct_change().fillna(values.sum(axis=1).iloc[0] - 1)


def cumulative(returns: pd.Series) -> pd.Series:
    return (1 + returns).cumprod()


# -- summary metrics -------------------------------------------------------

@dataclass
class PerformanceSummary:
    total_return: float
    annualized_return: float
    annualized_vol: float
    sharpe: float
    sortino: float
    max_drawdown: float
    calmar: float
    best_day: float
    worst_day: float
    positive_days_pct: float
    observations: int


def annualized_return(returns: pd.Series) -> float:
    if returns.empty:
        return 0.0
    total = float((1 + returns).prod())
    years = len(returns) / TRADING_DAYS
    if years <= 0 or total <= 0:
        return 0.0
    return total ** (1 / years) - 1


def annualized_vol(returns: pd.Series) -> float:
    return float(returns.std() * np.sqrt(TRADING_DAYS))


def sharpe(returns: pd.Series, rf: float = 0.0) -> float:
    excess = returns - rf / TRADING_DAYS
    vol = excess.std()
    if vol == 0 or np.isnan(vol):
        return 0.0
    return float(excess.mean() / vol * np.sqrt(TRADING_DAYS))


def sortino(returns: pd.Series, rf: float = 0.0) -> float:
    excess = returns - rf / TRADING_DAYS
    downside = excess[excess < 0].std()
    if not downside or np.isnan(downside):
        return 0.0
    return float(excess.mean() / downside * np.sqrt(TRADING_DAYS))


def max_drawdown(returns: pd.Series) -> float:
    curve = cumulative(returns)
    peak = curve.cummax()
    dd = (curve - peak) / peak
    return float(dd.min())


def summarize(returns: pd.Series, rf: float = 0.0) -> PerformanceSummary:
    if returns.empty:
        return PerformanceSummary(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    ar = annualized_return(returns)
    mdd = max_drawdown(returns)
    calmar = ar / abs(mdd) if mdd != 0 else 0.0
    return PerformanceSummary(
        total_return=float((1 + returns).prod() - 1),
        annualized_return=ar,
        annualized_vol=annualized_vol(returns),
        sharpe=sharpe(returns, rf),
        sortino=sortino(returns, rf),
        max_drawdown=mdd,
        calmar=calmar,
        best_day=float(returns.max()),
        worst_day=float(returns.min()),
        positive_days_pct=float((returns > 0).mean()),
        observations=int(returns.count()),
    )


# -- relative performance --------------------------------------------------

def beta_alpha(portfolio: pd.Series, benchmark: pd.Series, rf: float = 0.0) -> tuple[float, float]:
    df = pd.concat([portfolio, benchmark], axis=1, keys=["p", "b"]).dropna()
    if len(df) < 30:
        return 0.0, 0.0
    p = df["p"] - rf / TRADING_DAYS
    b = df["b"] - rf / TRADING_DAYS
    var_b = b.var()
    if var_b == 0 or np.isnan(var_b):
        return 0.0, 0.0
    beta = float(p.cov(b) / var_b)
    alpha_daily = p.mean() - beta * b.mean()
    return beta, float(alpha_daily * TRADING_DAYS)


def tracking_error(portfolio: pd.Series, benchmark: pd.Series) -> float:
    diff = (portfolio - benchmark).dropna()
    return float(diff.std() * np.sqrt(TRADING_DAYS))


def information_ratio(portfolio: pd.Series, benchmark: pd.Series) -> float:
    diff = (portfolio - benchmark).dropna()
    te = diff.std()
    if te == 0 or np.isnan(te):
        return 0.0
    return float(diff.mean() / te * np.sqrt(TRADING_DAYS))


def rolling_vol(returns: pd.Series, window: int = 63) -> pd.Series:
    return returns.rolling(window).std() * np.sqrt(TRADING_DAYS)


def rolling_sharpe(returns: pd.Series, window: int = 63, rf: float = 0.0) -> pd.Series:
    excess = returns - rf / TRADING_DAYS
    mean = excess.rolling(window).mean()
    std = excess.rolling(window).std()
    return mean / std * np.sqrt(TRADING_DAYS)


def drawdown_series(returns: pd.Series) -> pd.Series:
    curve = cumulative(returns)
    peak = curve.cummax()
    return (curve - peak) / peak
