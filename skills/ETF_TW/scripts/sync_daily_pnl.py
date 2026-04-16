#!/usr/bin/env python3
import os
import json
import datetime
import sys

# Ensure scripts directory is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from instance_identity import get_instance_id_fallback

INSTANCE_ID = get_instance_id_fallback()
STATE_DIR = os.path.join("skills", "ETF_TW", "instances", INSTANCE_ID, "state")
REDLINES_FILE = os.path.join(STATE_DIR, "safety_redlines.json")
DAILY_PNL_FILE = os.path.join(STATE_DIR, "daily_pnl.json")

DEFAULT_REDLINES = {
    "max_buy_amount_twd": 500000.0,
    "max_buy_amount_pct": 50.0,
    "max_buy_shares": 200,          # User requirement: 200
    "max_concentration_pct": 30.0,  # User requirement: 30%
    "daily_loss_limit_pct": 5.0,
    "ai_confidence_threshold": 0.7, # Mapping "Medium" to 0.7
    "ai_confidence_level": "Medium", # Add for UI clarity
    "enabled": True
}

def safe_load_json(file_path, default):
    if not os.path.exists(file_path):
        return default
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return default

def safe_save_json(file_path, data):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def update_daily_baseline():
    """每日第一次執行時，記錄當前 total_equity 作為 starting_equity_of_day"""
    today = datetime.date.today().isoformat()
    
    redlines = safe_load_json(REDLINES_FILE, DEFAULT_REDLINES)
    # Ensure redlines file exists with defaults if missing
    if not os.path.exists(REDLINES_FILE):
        safe_save_json(REDLINES_FILE, redlines)
        
    daily_pnl = safe_load_json(DAILY_PNL_FILE, {})
    
    # Check if we need to update for a new day
    if daily_pnl.get("date") != today:
        # Fetch current equity from portfolio_snapshot.json
        snapshot_file = os.path.join(STATE_DIR, "portfolio_snapshot.json")
        snapshot = safe_load_json(snapshot_file, {})
        current_equity = snapshot.get("total_equity", 0.0)
        
        daily_pnl = {
            "date": today,
            "starting_equity_of_day": current_equity,
            "current_equity": current_equity,
            "circuit_breaker_triggered": False,
            "last_updated": datetime.datetime.now().isoformat()
        }
        safe_save_json(DAILY_PNL_FILE, daily_pnl)
        print(f"Daily baseline updated for {today}: {current_equity}")
    else:
        print(f"Daily baseline already exists for {today}")

def check_circuit_breaker():
    """計算損益百分比，若損失超過 daily_loss_limit_pct，標記觸發"""
    daily_pnl = safe_load_json(DAILY_PNL_FILE, {})
    if not daily_pnl:
        return
        
    redlines = safe_load_json(REDLINES_FILE, DEFAULT_REDLINES)
    limit_pct = redlines.get("daily_loss_limit_pct", 5.0)
    
    # Update current equity from snapshot
    snapshot_file = os.path.join(STATE_DIR, "portfolio_snapshot.json")
    snapshot = safe_load_json(snapshot_file, {})
    current_equity = snapshot.get("total_equity", 0.0)
    
    starting_equity = daily_pnl.get("starting_equity_of_day", 0.0)
    if starting_equity > 0:
        loss_pct = (current_equity - starting_equity) / starting_equity * 100
        # loss_pct will be negative for losses
        if loss_pct <= -limit_pct:
            daily_pnl["circuit_breaker_triggered"] = True
            print(f"CIRCUIT BREAKER TRIGGERED: Loss {loss_pct:.2f}% exceeds limit {limit_pct}%")
        
        daily_pnl["current_equity"] = current_equity
        daily_pnl["pnl_pct"] = loss_pct
        daily_pnl["last_updated"] = datetime.datetime.now().isoformat()
        safe_save_json(DAILY_PNL_FILE, daily_pnl)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--update-baseline", action="store_true")
    args = parser.parse_args()
    
    if args.update_baseline:
        update_daily_baseline()
    
    check_circuit_breaker()
