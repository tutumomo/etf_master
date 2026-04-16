
# ... (現有 API 點) ...

@app.get("/api/history/{symbol}")
async def get_history(symbol: str, period: str = "d"):
    path = STATE / "market_intelligence.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Intelligence data not found")
    
    try:
        raw_text = path.read_text(encoding="utf-8").replace("NaN", "null")
        data = json.loads(raw_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"JSON Parse Error: {e}")
        
    intel = data.get("intelligence", {}).get(symbol)
    if not intel:
        raise HTTPException(status_code=404, detail=f"History for {symbol} not ready")
    
    # 週期參數處理 (對應 10-02-PLAN)
    # 假設 data_engine 已經處理了不同週期的資料 (若無，則需依需求補充)
    # 這裡暫時依照 existing 格式返回
    raw_history = intel.get("history_30d", [])
    if period == "w":
         raw_history = intel.get("history_weekly", []) or raw_history
    elif period == "m":
         raw_history = intel.get("history_monthly", []) or raw_history

    history = [p for p in raw_history if p.get("c") is not None and p.get("o") is not None]
    indicators = {k: intel[k] for k in ("sma5", "sma20", "sma60", "rsi", "macd", "macd_signal") if k in intel}
    
    return {"symbol": symbol, "history": history, "indicators": indicators}
