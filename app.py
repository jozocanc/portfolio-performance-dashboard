"""EAM Client Reporting Dashboard — Streamlit.

Designed as a client-reporting tool an External Asset Manager could hand to an
end client. Mirrors the kind of analytics a Swiss private bank's financial
intermediaries / client-services desk would support.
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.data_pipeline import DB_PATH, refresh_all
from src.metrics import (
    beta_alpha,
    cumulative,
    drawdown_series,
    information_ratio,
    load_prices,
    load_securities,
    load_weights,
    portfolio_returns,
    rolling_sharpe,
    rolling_vol,
    summarize,
    tracking_error,
)

st.set_page_config(
    page_title="EAM Client Reporting | Jozo Cancar",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -- brand styling ---------------------------------------------------------
UBS_RED = "#E60000"
CHARCOAL = "#111418"
MUTED = "#6B7280"
LIGHT = "#F5F5F4"
ACCENT = "#0B3D91"

st.markdown(
    f"""
<style>
.block-container {{ padding-top: 1.4rem; padding-bottom: 3rem; max-width: 1280px; }}
h1, h2, h3 {{ color: {CHARCOAL}; letter-spacing: -0.01em; }}
h1 {{ font-weight: 700; }}
[data-testid="stMetricValue"] {{ font-weight: 600; color: {CHARCOAL}; }}
[data-testid="stMetricLabel"] {{ color: {MUTED}; text-transform: uppercase; font-size: 0.72rem; letter-spacing: 0.06em; }}
.stTabs [data-baseweb="tab-list"] {{ gap: 0.25rem; }}
.stTabs [data-baseweb="tab"] {{ padding: 0.5rem 1rem; font-weight: 500; }}
hr {{ border-color: #E5E7EB; margin: 1rem 0; }}
.small-caption {{ color: {MUTED}; font-size: 0.82rem; }}
</style>
    """,
    unsafe_allow_html=True,
)


# -- data loading ----------------------------------------------------------
@st.cache_data(ttl=60 * 60 * 12)
def _bootstrap_db() -> None:
    """Populate SQLite from yfinance if missing (first run / fresh deploy)."""
    if not DB_PATH.exists() or DB_PATH.stat().st_size < 1024:
        with st.spinner("Loading market data (one-time setup, ~30 seconds)..."):
            refresh_all(period="5y")


@st.cache_data(ttl=60 * 60)
def _load_all():
    _bootstrap_db()
    prices = load_prices()
    weights = load_weights()
    secs = load_securities().set_index("ticker")
    return prices, weights, secs


prices, weights, securities = _load_all()

# -- header ----------------------------------------------------------------
left, right = st.columns([0.7, 0.3])
with left:
    st.markdown("### EAM Client Reporting")
    st.markdown(
        "#### Swiss-core multi-asset mandate · Monthly performance review"
    )
    st.markdown(
        f"<span class='small-caption'>Prepared by Jozo Cancar · Data: Yahoo Finance · "
        f"As of {prices.index.max().strftime('%d %b %Y')}</span>",
        unsafe_allow_html=True,
    )
with right:
    st.markdown(
        f"<div style='text-align:right; margin-top:1.2rem;'>"
        f"<div style='color:{MUTED}; font-size:0.75rem; text-transform:uppercase; letter-spacing:0.08em;'>Mandate</div>"
        f"<div style='font-weight:600; font-size:1.1rem;'>Swiss Balanced · CHF</div></div>",
        unsafe_allow_html=True,
    )
st.markdown("---")

# -- sidebar controls ------------------------------------------------------
with st.sidebar:
    st.markdown("### Reporting Parameters")
    period = st.selectbox(
        "Lookback period",
        options=["1Y", "3Y", "5Y", "Max"],
        index=2,
    )
    benchmark_ticker = st.selectbox(
        "Benchmark",
        options=["^SSMI", "^STOXX50E", "^GSPC"],
        format_func=lambda t: {"^SSMI": "SMI", "^STOXX50E": "EURO STOXX 50", "^GSPC": "S&P 500"}[t],
        index=0,
    )
    rf_input = st.number_input("Risk-free rate (annual)", 0.0, 0.10, 0.01, 0.0025, format="%.4f")
    st.markdown("---")
    st.markdown("#### About this dashboard")
    st.markdown(
        "<span class='small-caption'>Demonstration project simulating EAM client "
        "reporting. Not investment advice. Built with Python, SQLite, Streamlit.</span>",
        unsafe_allow_html=True,
    )

# period filter
end = prices.index.max()
if period == "1Y":
    start = end - pd.DateOffset(years=1)
elif period == "3Y":
    start = end - pd.DateOffset(years=3)
elif period == "5Y":
    start = end - pd.DateOffset(years=5)
else:
    start = prices.index.min()
prices_p = prices.loc[start:end]

# -- compute core series ---------------------------------------------------
port_ret = portfolio_returns(prices_p, weights)
bench_ret = prices_p[benchmark_ticker].pct_change(fill_method=None).dropna()
port_summary = summarize(port_ret, rf=rf_input)
bench_summary = summarize(bench_ret, rf=rf_input)
beta, alpha_ann = beta_alpha(port_ret, bench_ret, rf=rf_input)
ir = information_ratio(port_ret, bench_ret)
te = tracking_error(port_ret, bench_ret)


# -- tabs ------------------------------------------------------------------
overview, performance, risk, allocation, holdings = st.tabs(
    ["Overview", "Performance", "Risk", "Allocation", "Holdings"]
)

with overview:
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Total Return", f"{port_summary.total_return:.2%}")
    k2.metric("Annualized Return", f"{port_summary.annualized_return:.2%}")
    k3.metric("Annualized Vol", f"{port_summary.annualized_vol:.2%}")
    k4.metric("Sharpe", f"{port_summary.sharpe:.2f}")
    k5.metric("Max Drawdown", f"{port_summary.max_drawdown:.2%}")

    st.markdown("#### Growth of CHF 100 — Portfolio vs Benchmark")
    growth = pd.DataFrame(
        {
            "Portfolio": cumulative(port_ret) * 100,
            "Benchmark": cumulative(bench_ret) * 100,
        }
    ).dropna()
    fig = px.line(growth, color_discrete_sequence=[ACCENT, MUTED])
    fig.update_layout(
        height=420,
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis_title=None,
        yaxis_title="Value (CHF)",
        legend_title=None,
        plot_bgcolor="white",
        hovermode="x unified",
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="#EEF0F3")
    st.plotly_chart(fig, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Summary table")
        summary_df = pd.DataFrame(
            {
                "Portfolio": [
                    f"{port_summary.total_return:.2%}",
                    f"{port_summary.annualized_return:.2%}",
                    f"{port_summary.annualized_vol:.2%}",
                    f"{port_summary.sharpe:.2f}",
                    f"{port_summary.sortino:.2f}",
                    f"{port_summary.max_drawdown:.2%}",
                    f"{port_summary.calmar:.2f}",
                    f"{port_summary.positive_days_pct:.1%}",
                ],
                "Benchmark": [
                    f"{bench_summary.total_return:.2%}",
                    f"{bench_summary.annualized_return:.2%}",
                    f"{bench_summary.annualized_vol:.2%}",
                    f"{bench_summary.sharpe:.2f}",
                    f"{bench_summary.sortino:.2f}",
                    f"{bench_summary.max_drawdown:.2%}",
                    f"{bench_summary.calmar:.2f}",
                    f"{bench_summary.positive_days_pct:.1%}",
                ],
            },
            index=[
                "Total return",
                "Annualized return",
                "Annualized volatility",
                "Sharpe ratio",
                "Sortino ratio",
                "Max drawdown",
                "Calmar ratio",
                "Positive days",
            ],
        )
        st.dataframe(summary_df, use_container_width=True)
    with c2:
        st.markdown("#### Relative to benchmark")
        rel_df = pd.DataFrame(
            {
                "Metric": ["Beta", "Alpha (ann.)", "Tracking error", "Information ratio"],
                "Value": [
                    f"{beta:.2f}",
                    f"{alpha_ann:.2%}",
                    f"{te:.2%}",
                    f"{ir:.2f}",
                ],
            }
        )
        st.dataframe(rel_df, use_container_width=True, hide_index=True)
        st.markdown(
            "<span class='small-caption'>Alpha and beta computed via OLS on daily "
            "excess returns. IR = excess mean / tracking error, annualized.</span>",
            unsafe_allow_html=True,
        )


with performance:
    st.markdown("#### Cumulative performance")
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=cumulative(port_ret).index,
            y=(cumulative(port_ret) - 1) * 100,
            name="Portfolio",
            line=dict(color=ACCENT, width=2.2),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=cumulative(bench_ret).index,
            y=(cumulative(bench_ret) - 1) * 100,
            name="Benchmark",
            line=dict(color=MUTED, width=1.6, dash="dash"),
        )
    )
    fig.update_layout(
        height=380,
        margin=dict(l=10, r=10, t=10, b=10),
        yaxis_title="Return (%)",
        plot_bgcolor="white",
        hovermode="x unified",
    )
    fig.update_yaxes(gridcolor="#EEF0F3")
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### Monthly returns heatmap")
    monthly = (1 + port_ret).resample("ME").prod() - 1
    heat = pd.DataFrame(
        {"return": monthly, "year": monthly.index.year, "month": monthly.index.month}
    )
    pivot = heat.pivot(index="year", columns="month", values="return")
    pivot.columns = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][: pivot.shape[1]]
    fig_h = px.imshow(
        pivot.values,
        x=pivot.columns,
        y=pivot.index,
        color_continuous_scale=["#B91C1C", "#FEF3C7", "#166534"],
        color_continuous_midpoint=0,
        aspect="auto",
        text_auto=".1%",
    )
    fig_h.update_layout(
        height=max(260, 32 * len(pivot)),
        margin=dict(l=10, r=10, t=10, b=10),
        coloraxis_colorbar=dict(title="Return"),
    )
    st.plotly_chart(fig_h, use_container_width=True)


with risk:
    st.markdown("#### Drawdown")
    dd = drawdown_series(port_ret) * 100
    fig_dd = go.Figure()
    fig_dd.add_trace(
        go.Scatter(
            x=dd.index, y=dd.values, fill="tozeroy",
            line=dict(color=UBS_RED, width=1.2), name="Drawdown",
        )
    )
    fig_dd.update_layout(
        height=320,
        margin=dict(l=10, r=10, t=10, b=10),
        yaxis_title="Drawdown (%)",
        plot_bgcolor="white",
    )
    fig_dd.update_yaxes(gridcolor="#EEF0F3")
    st.plotly_chart(fig_dd, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Rolling 3-month volatility (annualized)")
        rv = rolling_vol(port_ret, 63) * 100
        fig_rv = px.line(rv, color_discrete_sequence=[ACCENT])
        fig_rv.update_layout(
            height=320, margin=dict(l=10, r=10, t=10, b=10),
            plot_bgcolor="white", showlegend=False, yaxis_title="Vol (%)",
        )
        fig_rv.update_yaxes(gridcolor="#EEF0F3")
        st.plotly_chart(fig_rv, use_container_width=True)
    with c2:
        st.markdown("#### Rolling 3-month Sharpe")
        rs = rolling_sharpe(port_ret, 63, rf=rf_input)
        fig_rs = px.line(rs, color_discrete_sequence=[ACCENT])
        fig_rs.update_layout(
            height=320, margin=dict(l=10, r=10, t=10, b=10),
            plot_bgcolor="white", showlegend=False, yaxis_title="Sharpe",
        )
        fig_rs.update_yaxes(gridcolor="#EEF0F3")
        st.plotly_chart(fig_rs, use_container_width=True)

    st.markdown("#### Return distribution")
    fig_hist = px.histogram(
        port_ret * 100, nbins=60, color_discrete_sequence=[ACCENT],
    )
    fig_hist.update_layout(
        height=300, margin=dict(l=10, r=10, t=10, b=10),
        plot_bgcolor="white", showlegend=False,
        xaxis_title="Daily return (%)", yaxis_title="Frequency",
    )
    fig_hist.update_yaxes(gridcolor="#EEF0F3")
    st.plotly_chart(fig_hist, use_container_width=True)


with allocation:
    alloc_df = (
        weights.to_frame("weight")
        .join(securities, how="left")
        .reset_index()
        .rename(columns={"index": "ticker"})
    )
    alloc_df["weight_pct"] = alloc_df["weight"] * 100

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Asset class")
        by_class = alloc_df.groupby("asset_class")["weight"].sum().reset_index()
        fig_c = px.pie(by_class, names="asset_class", values="weight", hole=0.55,
                       color_discrete_sequence=px.colors.qualitative.Set2)
        fig_c.update_layout(height=330, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig_c, use_container_width=True)
    with c2:
        st.markdown("#### Region")
        by_region = alloc_df.groupby("region")["weight"].sum().reset_index()
        fig_r = px.pie(by_region, names="region", values="weight", hole=0.55,
                       color_discrete_sequence=px.colors.qualitative.Pastel)
        fig_r.update_layout(height=330, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig_r, use_container_width=True)

    st.markdown("#### Currency")
    by_ccy = alloc_df.groupby("currency")["weight"].sum().reset_index()
    fig_f = px.bar(by_ccy, x="currency", y="weight", text_auto=".1%",
                   color_discrete_sequence=[ACCENT])
    fig_f.update_layout(height=300, margin=dict(l=10, r=10, t=10, b=10),
                        plot_bgcolor="white", yaxis_tickformat=".0%")
    fig_f.update_yaxes(gridcolor="#EEF0F3")
    st.plotly_chart(fig_f, use_container_width=True)


with holdings:
    st.markdown("#### Position detail")
    latest = prices_p.iloc[-1]
    first = prices_p.iloc[0]
    perf = (latest / first - 1).reindex(weights.index) * 100
    holdings_df = (
        weights.to_frame("weight")
        .join(securities[["name", "asset_class", "region", "currency"]], how="left")
        .assign(**{"period_return_pct": perf})
        .reset_index()
        .rename(columns={
            "index": "ticker",
            "name": "Name",
            "asset_class": "Asset class",
            "region": "Region",
            "currency": "CCY",
            "weight": "Weight",
            "period_return_pct": f"Return ({period})",
        })
    )
    holdings_df["Weight"] = holdings_df["Weight"].map(lambda x: f"{x:.1%}")
    holdings_df[f"Return ({period})"] = holdings_df[f"Return ({period})"].map(
        lambda x: f"{x:.2f}%" if pd.notna(x) else "—"
    )
    st.dataframe(
        holdings_df[["ticker", "Name", "Asset class", "Region", "CCY", "Weight", f"Return ({period})"]],
        use_container_width=True,
        hide_index=True,
    )
    st.markdown(
        "<span class='small-caption'>Target weights shown. Actual holdings would "
        "drift with market movements between rebalancing dates.</span>",
        unsafe_allow_html=True,
    )
