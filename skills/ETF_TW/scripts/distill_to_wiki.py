#!/usr/bin/env python3
"""
distill_to_wiki.py — 將最新市場數據沉澱至 llm-wiki 知識庫

從 ETF_TW instance state 讀取最新報價、技術指標、市場情境，
更新對應的 wiki entity 頁面的「最新市場數據」區塊。
不覆寫 wiki 頁面的基礎說明，只更新/追加數據快照。
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

from etf_core.context import get_state_dir
from etf_core.state_io import safe_load_json

TW_TZ = ZoneInfo('Asia/Taipei')
WIKI_DIR = Path.home() / '.hermes' / 'profiles' / 'etf_master' / 'wiki'

# 也嘗試從 config 讀取 wiki 路徑
def _get_wiki_dir() -> Path:
    config_path = Path.home() / '.hermes' / 'profiles' / 'etf_master' / 'config.yaml'
    try:
        import yaml  # type: ignore
        with open(config_path) as f:
            cfg = yaml.safe_load(f)
        raw = cfg.get('skills', {}).get('config', {}).get('wiki', {}).get('path', '')
        if raw:
            p = Path(raw.replace('~', str(Path.home())))
            if p.exists():
                return p
    except Exception:
        pass
    return WIKI_DIR


def _load_states() -> dict:
    state_dir = get_state_dir()
    return {
        'market_cache': safe_load_json(state_dir / 'market_cache.json', {}),
        'tape': safe_load_json(state_dir / 'intraday_tape_context.json', {}),
        'watchlist': safe_load_json(state_dir / 'watchlist.json', {}),
        'market_context': safe_load_json(state_dir / 'market_context_taiwan.json', {}),
    }


def _find_wiki_entity(wiki_dir: Path, symbol: str) -> Path | None:
    """找到對應 symbol 的 wiki entity 檔案"""
    entity_dir = wiki_dir / 'entities'
    if not entity_dir.exists():
        return None
    # 搜尋檔名包含 symbol 的檔案（不區分大小寫）
    sym_lower = symbol.lower()
    for f in entity_dir.glob('*.md'):
        if sym_lower in f.stem.lower():
            return f
    return None


def _build_snapshot_block(symbol: str, quote: dict, tape_signal: dict | None, now_str: str) -> str:
    """建立市場數據快照 markdown 區塊"""
    price = quote.get('current_price', 0)
    change_pct = quote.get('change_pct')
    volume = quote.get('volume')
    source = quote.get('source', 'unknown')

    lines = [
        f'## 最新市場數據快照',
        f'',
        f'> 自動更新於 {now_str}（來源：{source}）',
        f'',
        f'| 欄位 | 數值 |',
        f'|------|------|',
        f'| 現價 | NT$ {price:.2f} |',
    ]
    if change_pct is not None:
        lines.append(f'| 漲跌幅 | {change_pct:+.2f}% |')
    if volume:
        lines.append(f'| 成交量 | {volume:,} |')

    if tape_signal:
        rsi = tape_signal.get('rsi_14')
        macd = tape_signal.get('macd_signal')
        trend = tape_signal.get('trend_20d')
        sentiment = tape_signal.get('tape_sentiment_label')
        if rsi is not None:
            lines.append(f'| RSI(14) | {rsi:.1f} |')
        if macd:
            lines.append(f'| MACD 訊號 | {macd} |')
        if trend is not None:
            lines.append(f'| 20日趨勢 | {trend:+.1f}% |')
        if sentiment:
            lines.append(f'| 盤感標籤 | {sentiment} |')

    lines.append('')
    return '\n'.join(lines)


def _update_wiki_entity(filepath: Path, snapshot_block: str) -> bool:
    """更新 wiki entity 檔案的快照區塊，保留其他內容"""
    content = filepath.read_text(encoding='utf-8')

    # 替換已有的快照區塊，或在檔尾追加
    pattern = r'## 最新市場數據快照\n.*?(?=\n## |\Z)'
    if re.search(pattern, content, flags=re.DOTALL):
        new_content = re.sub(pattern, snapshot_block.rstrip(), content, flags=re.DOTALL)
    else:
        new_content = content.rstrip() + '\n\n' + snapshot_block

    filepath.write_text(new_content, encoding='utf-8')
    return True


def main() -> int:
    wiki_dir = _get_wiki_dir()
    if not wiki_dir.exists():
        print(f'[distill_to_wiki] wiki 目錄不存在：{wiki_dir}，跳過')
        return 0

    states = _load_states()
    quotes = states['market_cache'].get('quotes', {})
    tape_signals = {
        row.get('symbol'): row
        for row in states['tape'].get('watchlist_signals', [])
    }
    watchlist_items = states['watchlist'].get('items', [])
    now_str = datetime.now(TW_TZ).strftime('%Y-%m-%d %H:%M')

    updated = 0
    skipped = 0

    for item in watchlist_items:
        symbol = item.get('symbol', '')
        quote = quotes.get(symbol, {})
        price = float(quote.get('current_price') or 0)

        if price <= 0:
            skipped += 1
            continue

        entity_file = _find_wiki_entity(wiki_dir, symbol)
        if not entity_file:
            skipped += 1
            continue

        tape_signal = tape_signals.get(symbol)
        snapshot = _build_snapshot_block(symbol, quote, tape_signal, now_str)

        try:
            _update_wiki_entity(entity_file, snapshot)
            updated += 1
            print(f'[distill_to_wiki] ✓ {symbol} → {entity_file.name}')
        except Exception as e:
            print(f'[distill_to_wiki] ✗ {symbol} 更新失敗：{e}')
            skipped += 1

    print(f'[distill_to_wiki] 完成：更新 {updated} 個 wiki 頁面，跳過 {skipped} 個')
    return 0


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(
        description='將最新市場數據沉澱至 llm-wiki 知識庫（更新 wiki entity 頁面的數據快照）'
    )
    parser.add_argument('--dry-run', action='store_true', help='模擬執行，不寫入 wiki')
    args = parser.parse_args()
    if args.dry_run:
        print('[distill_to_wiki] dry-run 模式：不寫入 wiki')
        raise SystemExit(0)
    raise SystemExit(main())
