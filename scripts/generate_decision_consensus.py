#!/usr/bin/env python3
import json
import re
from pathlib import Path

# Paths
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
STATE_DIR = PROJECT_ROOT / "skills" / "ETF_TW" / "instances" / "etf_master" / "state"
DATA_DIR = PROJECT_ROOT / "skills" / "ETF_TW" / "data"
RULE_STATE_PATH = STATE_DIR / "auto_trade_state.json"
AI_STATE_PATH = STATE_DIR / "ai_decision_response.json"
CONSENSUS_PATH = STATE_DIR / "decision_consensus.json"
STRATEGY_PATH = STATE_DIR / "strategy_link.json"
ETFS_DATA_PATH = DATA_DIR / "etfs.json"

# Strategy Alignment Mapping
STRATEGY_PREFERENCES = {
    "收益優先": ["高股息", "債券型"],
    "核心累積": ["大盤型", "科技型"],
    "平衡配置": ["大盤型", "高股息", "債券型", "科技型"],
    "防守保守": ["債券型", "大盤型"],
    "積極成長": ["科技型", "產業型", "大盤型"]
}

def extract_symbol(text):
    """從建議文字中提取 4-6 位數字的 ETF 代碼 (CR-02)"""
    match = re.search(r'\b(\d{4,6})\b', text)
    return match.group(1) if match else None

def get_action(summary):
    if isinstance(summary, dict):
        summary = summary.get("action", "") or summary.get("decision", "")
    summary = str(summary or "").lower()
    # 更精確的識別，避免 "do not buy" 被誤判為 "buy"
    if "do not buy" in summary or "不要買" in summary or "不要進場" in summary: return "HOLD"
    if "buy" in summary or "買" in summary: return "BUY"
    if "sell" in summary or "賣" in summary: return "SELL"
    return "HOLD"

def safe_read_json(path: Path):
    """安全讀取 JSON 檔案，防止崩潰 (CR-01)"""
    if not path.exists():
        return {}
    try:
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            return {}
        return json.loads(text)
    except (json.JSONDecodeError, OSError, ValueError):
        return {}

def check_strategy_alignment(symbol, strategy_name, etfs_data):
    """檢查標的是否符合當前策略優先級 (Task 1)"""
    if not symbol or not strategy_name:
        return True, "無明確標的或策略"
    
    etf_info = etfs_data.get("etfs", {}).get(symbol)
    if not etf_info:
        return True, f"查無標的 {symbol} 資料"
    
    category = etf_info.get("category")
    prefs = STRATEGY_PREFERENCES.get(strategy_name, [])
    
    if not prefs:
        return True, f"策略 {strategy_name} 未定義偏好"
    
    if category in prefs:
        return True, f"對齊：{category} 符合 {strategy_name} 策略"
    else:
        return False, f"未對齊：{category} 不在 {strategy_name} 優先清單 ({', '.join(prefs)}) 中"

def arbitrate():
    rule_data = safe_read_json(RULE_STATE_PATH)
    ai_data = safe_read_json(AI_STATE_PATH)
    strategy_data = safe_read_json(STRATEGY_PATH)
    etfs_data = safe_read_json(ETFS_DATA_PATH)

    rule_suggest = rule_data.get("last_preview_summary", "無建議")
    ai_suggest = ai_data.get("decision", "尚無建議")
    strategy_name = strategy_data.get("base_strategy", "未設定")
    
    rule_action = get_action(rule_suggest)
    ai_action = get_action(ai_suggest)
    
    # 提取標的並檢查策略對齊
    symbol = extract_symbol(rule_suggest) or extract_symbol(ai_suggest)
    is_aligned, align_msg = check_strategy_alignment(symbol, strategy_name, etfs_data)
    
    consensus = "觀望 / 對齊中"
    hint = "正在等待雙鏈訊號產出..."
    color = "var(--muted)"

    if rule_action == ai_action:
        if rule_action == "BUY":
            consensus = "強勢共識：買入"
            hint = "雙鏈同步看多，技術面與環境面皆支持進場。"
            color = "var(--good)"
        elif rule_action == "SELL":
            consensus = "強勢共識：減碼"
            hint = "雙鏈同步看空，建議優先執行風險規避。"
            color = "var(--bad)"
        else:
            consensus = "穩定共識：持股"
            hint = "目前無明確交易訊號，維持現有配置。"
            color = "var(--muted)"
    else:
        # 衝突處理邏輯
        if ai_action == "HOLD" or ai_action == "SELL":
            consensus = "⚠️ 警示：優先避險"
            hint = "AI 偵測到環境風險或 Wiki 負面背景，建議暫緩規則引擎的買入建議。"
            color = "var(--warn)"
        elif rule_action == "BUY" and ai_action == "BUY": # Should not happen due to equality check above, but for safety
            consensus = "強勢共識：買入"
            color = "var(--good)"
        else:
            consensus = "意見分歧：建議觀望"
            hint = "規則與 AI 判斷不一致，建議人工介入審核詳細診斷報告。"
            color = "var(--warn)"

    # 如果未對齊且共識是買入，降低評級 (Task 3)
    if not is_aligned and "買入" in consensus:
        consensus = f"⚠️ 分歧：{consensus} (策略不匹配)"
        hint = f"{hint} 注意：標的分類不符合「{strategy_name}」核心策略。"
        color = "var(--warn)"

    result = {
        "consensus": consensus,
        "hint": hint,
        "color": color,
        "rule_action": rule_action,
        "ai_action": ai_action,
        "strategy": strategy_name,
        "target_symbol": symbol,
        "aligned": is_aligned,
        "alignment_msg": align_msg,
        "timestamp": strategy_data.get("updated_at")
    }
    
    CONSENSUS_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Consensus generated: {consensus} (Aligned: {is_aligned})")

if __name__ == "__main__":
    arbitrate()
