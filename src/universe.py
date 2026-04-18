"""Investment universe — Swiss equities, Swiss/Euro ETFs, global benchmarks.

Mirrors a conservative EAM client book: Swiss blue-chip core, regional ETF
diversification, and benchmark indices for relative-performance reporting.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Security:
    ticker: str
    name: str
    asset_class: str
    region: str
    currency: str


SMI_CONSTITUENTS: list[Security] = [
    Security("NESN.SW", "Nestlé", "Equity", "Switzerland", "CHF"),
    Security("NOVN.SW", "Novartis", "Equity", "Switzerland", "CHF"),
    Security("ROG.SW", "Roche Holding", "Equity", "Switzerland", "CHF"),
    Security("UBSG.SW", "UBS Group", "Equity", "Switzerland", "CHF"),
    Security("ZURN.SW", "Zurich Insurance", "Equity", "Switzerland", "CHF"),
    Security("ABBN.SW", "ABB", "Equity", "Switzerland", "CHF"),
    Security("CFR.SW", "Richemont", "Equity", "Switzerland", "CHF"),
    Security("SREN.SW", "Swiss Re", "Equity", "Switzerland", "CHF"),
    Security("LONN.SW", "Lonza Group", "Equity", "Switzerland", "CHF"),
    Security("GIVN.SW", "Givaudan", "Equity", "Switzerland", "CHF"),
]

ETFS: list[Security] = [
    Security("CSSMI.SW", "iShares SMI ETF", "Equity ETF", "Switzerland", "CHF"),
    Security("CSSX5E.SW", "iShares Core EURO STOXX 50", "Equity ETF", "Europe", "EUR"),
    Security("CSSPX.SW", "iShares Core S&P 500 (CH)", "Equity ETF", "US", "USD"),
    Security("AGGH.SW", "iShares Core Global Agg Bond", "Bond ETF", "Global", "USD"),
    Security("GLD", "SPDR Gold Shares", "Commodity", "Global", "USD"),
]

BENCHMARKS: list[Security] = [
    Security("^SSMI", "SMI Index", "Index", "Switzerland", "CHF"),
    Security("^STOXX50E", "EURO STOXX 50", "Index", "Europe", "EUR"),
    Security("^GSPC", "S&P 500", "Index", "US", "USD"),
]


def full_universe() -> list[Security]:
    return SMI_CONSTITUENTS + ETFS + BENCHMARKS


DEFAULT_PORTFOLIO_WEIGHTS: dict[str, float] = {
    "NESN.SW": 0.08,
    "NOVN.SW": 0.07,
    "ROG.SW": 0.07,
    "UBSG.SW": 0.05,
    "ZURN.SW": 0.05,
    "ABBN.SW": 0.04,
    "SREN.SW": 0.04,
    "LONN.SW": 0.03,
    "GIVN.SW": 0.03,
    "CSSMI.SW": 0.14,
    "CSSX5E.SW": 0.12,
    "CSSPX.SW": 0.14,
    "AGGH.SW": 0.10,
    "GLD": 0.04,
}
