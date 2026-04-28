"""Backtest module — historical strategy simulation for ETF_TW.

Components:
  - strategy_simulator: pure-function core, replays ladder + trailing on OHLC
  - stress_test_runner: drives 2008/2020/2022 scenarios, writes report
  - fetch_historical_prices: yfinance daily fetch + caching

Reports written to docs/intelligence-roadmap/backtest-reports/.
"""
