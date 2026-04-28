#!/usr/bin/env python3
"""
stress_test_runner.py — 跑 2008/2020/2022 三個壓力情境，產出對照報告。

用法：
    AGENT_ID=etf_master PYTHONPATH=. .venv/bin/python -m scripts.backtest.stress_test_runner

輸出：
    docs/intelligence-roadmap/backtest-reports/<DATE>-stress-test.md  (markdown)
    docs/intelligence-roadmap/backtest-reports/<DATE>-stress-test.json (raw)

對應計畫：docs/intelligence-roadmap/2026-04-28-A-to-G-plan.md (項目 C)
"""
from __future__ import annotations

import json
import sys
from dataclasses import asdict
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.backtest.fetch_historical_prices import fetch_daily_history
from scripts.backtest.strategy_simulator import (
    SimulationConfig,
    compute_metrics,
    simulate,
    simulate_buy_and_hold,
)


SCENARIOS = [
    {
        "name": "2008 GFC",
        "symbol": "^TWII",
        "symbol_label": "^TWII (台灣加權指數，因 0050 yfinance 資料 2009 起)",
        "start": "2008-01-01",
        "end":   "2009-06-30",
        "narrative": "雷曼破產系統性崩盤，台股加權從 9000+ 跌至 4000 以下、2009 H1 反彈，測試 trailing 是否被連續跌停吞噬、ladder 是否有效逢低布局。",
    },
    {
        "name": "2020 COVID",
        "symbol": "0050.TW",
        "symbol_label": "0050.TW (元大台灣 50)",
        "start": "2020-01-01",
        "end":   "2020-12-31",
        "narrative": "COVID 急跌急回 V 形，2 月底至 3 月暴跌 -30%、4 月起反彈、年末創新高。測試底部是否 panic sell、反彈是否追得上。",
    },
    {
        "name": "2022 Bear",
        "symbol": "0050.TW",
        "symbol_label": "0050.TW (元大台灣 50)",
        "start": "2022-01-01",
        "end":   "2022-12-31",
        "narrative": "升息引發慢熊 -25%，全年陰跌不見急跌。測試 ladder 是否被緩跌吃光、trailing 是否頻繁觸發。",
    },
    {
        "name": "2024 Bull (sample-out)",
        "symbol": "0050.TW",
        "symbol_label": "0050.TW (元大台灣 50)",
        "start": "2024-01-01",
        "end":   "2024-12-31",
        "narrative": "AI 推升的長多年，0050 全年 +50%+。測試策略在強多頭中是否會因 trailing 過早平倉而錯失主升段。",
    },
]


def run_scenario(scenario: dict, *, initial_cash: float = 1_000_000.0,
                 symbol_group: str = "core") -> dict:
    """跑單一情境，回傳結構化結果。"""
    prices = fetch_daily_history(scenario["symbol"], scenario["start"], scenario["end"])
    if prices is None or len(prices) == 0:
        return {
            "name": scenario["name"],
            "error": f"no data for {scenario['symbol']} {scenario['start']}→{scenario['end']}",
        }

    cfg = SimulationConfig(
        initial_cash=initial_cash,
        symbol_group=symbol_group,
        max_position_pct=0.50,
    )
    strat = simulate(prices, cfg)
    bah = simulate_buy_and_hold(prices, initial_cash=initial_cash)

    strat_metrics = compute_metrics(strat.equity_curve)
    bah_metrics = compute_metrics(bah.equity_curve)

    # alpha = 策略 - BAH
    alpha = None
    if strat_metrics["total_return_pct"] is not None and bah_metrics["total_return_pct"] is not None:
        alpha = round(strat_metrics["total_return_pct"] - bah_metrics["total_return_pct"], 2)

    n_buys = sum(1 for t in strat.trades if t.side == "buy")
    n_sells = sum(1 for t in strat.trades if t.side == "sell")
    total_fees = sum(t.fee for t in strat.trades)

    return {
        "name": scenario["name"],
        "symbol": scenario["symbol"],
        "symbol_label": scenario["symbol_label"],
        "period": f"{scenario['start']} → {scenario['end']}",
        "narrative": scenario["narrative"],
        "trading_days": len(prices),
        "first_price": float(prices["Close"].iloc[0]),
        "last_price": float(prices["Close"].iloc[-1]),
        "buy_hold_return_pct": bah_metrics["total_return_pct"],
        "strategy": {
            "metrics": strat_metrics,
            "n_buys": n_buys,
            "n_sells": n_sells,
            "total_fees": round(total_fees, 2),
            "final_equity": round(strat.final_equity, 2),
        },
        "buy_and_hold": {
            "metrics": bah_metrics,
            "final_equity": round(bah.final_equity, 2),
        },
        "alpha_pct": alpha,
    }


def format_report_md(results: list[dict], generated_at: str) -> str:
    lines: list[str] = []
    lines.append("# ETF_TW 壓力情境回測報告")
    lines.append("")
    lines.append(f"**產出時間：** {generated_at}")
    lines.append("**初始資金：** 1,000,000 TWD")
    lines.append("**策略：** ladder buy（跌幅階梯）+ trailing stop（core 群組 6%，鎖利模式 ≥+20% 收緊至 3%）")
    lines.append("**手續費假設：** 買賣 0.1425% 券商 + 賣出 0.1% 證交稅")
    lines.append("**對照組：** Buy-and-Hold（首日全買、末日全賣）")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Summary table
    lines.append("## 總覽")
    lines.append("")
    lines.append("| 情境 | 期間 | 策略總報酬 | BAH 總報酬 | Alpha | 策略最大回撤 | BAH 最大回撤 | 策略 Sharpe | BAH Sharpe |")
    lines.append("|------|------|-----------|-----------|-------|------------|------------|------------|-----------|")
    for r in results:
        if "error" in r:
            lines.append(f"| {r['name']} | — | ❌ {r['error']} | | | | | | |")
            continue
        s = r["strategy"]["metrics"]
        b = r["buy_and_hold"]["metrics"]
        alpha = r["alpha_pct"]
        alpha_str = f"{alpha:+.2f}%" if alpha is not None else "—"
        lines.append(
            f"| {r['name']} | {r['period']} | "
            f"{s['total_return_pct']:+.2f}% | {b['total_return_pct']:+.2f}% | "
            f"**{alpha_str}** | {s['max_drawdown_pct']:.2f}% | {b['max_drawdown_pct']:.2f}% | "
            f"{s['sharpe_ratio']:.2f} | {b['sharpe_ratio']:.2f} |"
        )
    lines.append("")
    lines.append("---")
    lines.append("")

    # Per-scenario detail
    for r in results:
        lines.append(f"## {r['name']}")
        lines.append("")
        if "error" in r:
            lines.append(f"⚠️ **錯誤：** {r['error']}")
            lines.append("")
            continue
        lines.append(f"**標的：** {r['symbol_label']}")
        lines.append(f"**期間：** {r['period']}（{r['trading_days']} 個交易日）")
        lines.append(f"**起始價：** {r['first_price']:.2f}　**末日價：** {r['last_price']:.2f}")
        lines.append("")
        lines.append(f"**情境敘述：** {r['narrative']}")
        lines.append("")

        s = r["strategy"]
        b = r["buy_and_hold"]
        sm = s["metrics"]
        bm = b["metrics"]

        lines.append("| 指標 | 策略 | Buy-and-Hold | 差異 |")
        lines.append("|------|------|--------------|------|")
        lines.append(f"| 總報酬 | {sm['total_return_pct']:+.2f}% | {bm['total_return_pct']:+.2f}% | {(sm['total_return_pct'] - bm['total_return_pct']):+.2f}% |")
        lines.append(f"| 年化報酬 | {sm['annualized_return_pct']:+.2f}% | {bm['annualized_return_pct']:+.2f}% | — |")
        lines.append(f"| 年化波動 | {sm['annualized_volatility_pct']:.2f}% | {bm['annualized_volatility_pct']:.2f}% | — |")
        lines.append(f"| 最大回撤 | {sm['max_drawdown_pct']:.2f}% | {bm['max_drawdown_pct']:.2f}% | — |")
        lines.append(f"| Sharpe Ratio | {sm['sharpe_ratio']:.2f} | {bm['sharpe_ratio']:.2f} | — |")
        lines.append(f"| 最長連續虧損 | {sm['max_consecutive_loss_days']} 日 | {bm['max_consecutive_loss_days']} 日 | — |")
        lines.append(f"| 最終資產 | {s['final_equity']:,.0f} | {b['final_equity']:,.0f} | {(s['final_equity'] - b['final_equity']):+,.0f} |")
        lines.append("")
        lines.append(f"**策略行為：** 觸發 ladder 買進 {s['n_buys']} 次、trailing 賣出 {s['n_sells']} 次、手續費共 {s['total_fees']:,.0f} TWD")
        lines.append("")

        # 解讀
        verdict = []
        if r["alpha_pct"] is not None:
            if r["alpha_pct"] > 1:
                verdict.append(f"✅ 策略在此情境**勝過 BAH** {r['alpha_pct']:+.2f}%")
            elif r["alpha_pct"] < -1:
                verdict.append(f"❌ 策略在此情境**輸給 BAH** {r['alpha_pct']:+.2f}%")
            else:
                verdict.append(f"➖ 策略與 BAH 相當（差距 {r['alpha_pct']:+.2f}%）")

        # 回撤比較
        if sm["max_drawdown_pct"] > bm["max_drawdown_pct"]:
            verdict.append(f"✅ 策略最大回撤 ({sm['max_drawdown_pct']:.1f}%) **小於** BAH ({bm['max_drawdown_pct']:.1f}%) — trailing 起到保護作用")
        else:
            verdict.append(f"⚠️ 策略最大回撤 ({sm['max_drawdown_pct']:.1f}%) **大於或等於** BAH ({bm['max_drawdown_pct']:.1f}%)")

        # Sharpe
        if sm["sharpe_ratio"] > bm["sharpe_ratio"] + 0.1:
            verdict.append(f"✅ 策略 Sharpe ({sm['sharpe_ratio']:.2f}) 優於 BAH ({bm['sharpe_ratio']:.2f}) — 風險調整後報酬較佳")
        elif sm["sharpe_ratio"] < bm["sharpe_ratio"] - 0.1:
            verdict.append(f"⚠️ 策略 Sharpe ({sm['sharpe_ratio']:.2f}) 低於 BAH ({bm['sharpe_ratio']:.2f})")

        if verdict:
            lines.append("**解讀：**")
            for v in verdict:
                lines.append(f"- {v}")
            lines.append("")

        lines.append("---")
        lines.append("")

    # Overall conclusion
    lines.append("## 整體結論")
    lines.append("")
    valid = [r for r in results if "error" not in r and r.get("alpha_pct") is not None]
    if valid:
        avg_alpha = sum(r["alpha_pct"] for r in valid) / len(valid)
        wins = sum(1 for r in valid if r["alpha_pct"] > 1)
        losses = sum(1 for r in valid if r["alpha_pct"] < -1)
        lines.append(f"- 平均 alpha：{avg_alpha:+.2f}%")
        lines.append(f"- 勝過 BAH：{wins} 個情境　持平：{len(valid) - wins - losses} 個　輸給 BAH：{losses} 個")
        lines.append("")

        # 觀察策略部位規模
        avg_dd = sum(r["strategy"]["metrics"]["max_drawdown_pct"] for r in valid) / len(valid)
        avg_bah_dd = sum(r["buy_and_hold"]["metrics"]["max_drawdown_pct"] for r in valid) / len(valid)
        lines.append(f"- 策略平均最大回撤：{avg_dd:.2f}%　vs BAH 平均：{avg_bah_dd:.2f}%")

        if abs(avg_dd) < 2.0:
            lines.append("")
            lines.append("### ⚠️ 結構性發現：部位規模過小")
            lines.append("")
            lines.append(f"策略最大回撤平均僅 {avg_dd:.2f}%，意味著**部位實際上極小**。")
            lines.append("這解釋了為何在熊市中『相對勝出』、在牛市中『遠遠落後』——策略幾乎不持倉。")
            lines.append("")
            lines.append("**根本原因：**")
            lines.append("1. 1M TWD 起始資金，ladder 每次只加碼 2,000–10,000 TWD")
            lines.append("2. trailing stop（core 6%）動輒觸發清倉，部位無法累積")
            lines.append("3. 沒有『初始建倉』機制 — 完全依賴跌幅觸發的逢低買入")
            lines.append("")
            lines.append("**這比較像極保守的零股 DCA，不是真正的擇時策略。**")
            lines.append("")
            lines.append("**建議的下一步調整（非 D–G 計畫，是骨架調整）：**")
            lines.append("- 加入『初始建倉』：起始資金的 30–50% 分批進場（DCA 啟動）")
            lines.append("- 放寬 trailing stop（core 從 6% 改 10–15%）")
            lines.append("- ladder 金額按 cash * 比例計算，而非寫死 TWD")
            lines.append("- 在 2024 Bull 樣本外驗證調整後的策略，目標 Alpha > -10%")
        elif avg_alpha > 0:
            lines.append("- ✅ 策略整體有正 alpha，可以繼續優化（D / E / F / G）")
        else:
            lines.append("- ⚠️ 策略整體無 alpha，應先檢討策略骨架")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 重要注意事項")
    lines.append("")
    lines.append("1. **僅供策略骨架體檢**：本回測使用單檔標的、簡化單日決策、固定 group=core，不代表實單表現。")
    lines.append("2. **2008 情境用 ^TWII 代理**：因為 yfinance 對 0050 的歷史資料只到 2009-01-02。")
    lines.append("3. **未納入** 滑價、停牌、漲跌停、配息再投資、以 VWAP 而非收盤價成交、watchlist 多檔輪動、A 計畫的 macro regime gate。")
    lines.append("4. **過度擬合風險**：本回測規則為事後設定，若未來放上樣本外資料表現可能變差。")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    out_dir = ROOT / "docs/intelligence-roadmap/backtest-reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    md_path = out_dir / f"{today}-stress-test.md"
    json_path = out_dir / f"{today}-stress-test.json"

    print(f"Running {len(SCENARIOS)} scenarios...")
    results = []
    for s in SCENARIOS:
        print(f"  → {s['name']} ({s['symbol']})", flush=True)
        r = run_scenario(s)
        results.append(r)

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report_md = format_report_md(results, generated_at)
    md_path.write_text(report_md, encoding="utf-8")
    json_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\nREPORT_OK")
    print(f"  Markdown: {md_path}")
    print(f"  JSON:     {json_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
