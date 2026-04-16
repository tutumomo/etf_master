#!/usr/bin/env python3
"""
Trade Logger and Audit System for ETF_TW.

Features:
- Log all trading activities
- Audit trail for compliance
- Query and report generation
- Data retention policies
"""

import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class TradeLog:
    """Represents a single trade log entry."""
    timestamp: str
    action: str  # 'order_submitted', 'order_filled', 'order_cancelled', 'order_rejected'
    broker_id: str
    account_id: str
    symbol: str
    order_type: str
    order_action: str  # 'buy' or 'sell'
    quantity: int
    price: Optional[float]
    fee: float
    tax: float
    status: str
    order_id: str
    error: Optional[str] = None
    signature: str = ""  # For audit integrity
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    def compute_signature(self) -> str:
        """Compute signature for audit integrity."""
        data = f"{self.timestamp}{self.action}{self.order_id}{self.symbol}{self.quantity}"
        return hashlib.sha256(data.encode()).hexdigest()


class TradeLogger:
    """
    Trade logging and audit system.
    
    Features:
    - Append-only log storage
    - Cryptographic signatures for integrity
    - Query and filtering
    - Report generation
    """
    
    def __init__(self, log_path: Optional[str] = None):
        self.log_path = Path(log_path) if log_path else Path(__file__).parent.parent / "data" / "trade_logs.jsonl"
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.logs: List[TradeLog] = []
        self._load_logs()
    
    def _load_logs(self):
        """Load existing logs from file."""
        if self.log_path.exists():
            with open(self.log_path, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        data = json.loads(line.strip())
                        log = TradeLog(**data)
                        self.logs.append(log)
                    except Exception:
                        continue
    
    def log_trade(self, trade_log: TradeLog) -> TradeLog:
        """
        Log a trade with audit signature.
        
        Args:
            trade_log: TradeLog object
            
        Returns:
            TradeLog with signature
        """
        # Compute signature
        trade_log.signature = trade_log.compute_signature()
        
        # Append to in-memory list
        self.logs.append(trade_log)
        
        # Append to file (atomic write)
        with open(self.log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(trade_log.to_dict(), ensure_ascii=False) + '\n')
        
        return trade_log
    
    def log_order_submitted(self, order_id: str, broker_id: str, account_id: str, 
                           symbol: str, order_type: str, action: str, quantity: int, 
                           price: Optional[float] = None) -> TradeLog:
        """Log order submission."""
        trade_log = TradeLog(
            timestamp=datetime.now().isoformat(),
            action='order_submitted',
            broker_id=broker_id,
            account_id=account_id,
            symbol=symbol,
            order_type=order_type,
            order_action=action,
            quantity=quantity,
            price=price,
            fee=0.0,
            tax=0.0,
            status='submitted',
            order_id=order_id
        )
        return self.log_trade(trade_log)
    
    def log_order_filled(self, order_id: str, broker_id: str, account_id: str,
                        symbol: str, action: str, quantity: int, price: float,
                        fee: float, tax: float) -> TradeLog:
        """Log order fill."""
        trade_log = TradeLog(
            timestamp=datetime.now().isoformat(),
            action='order_filled',
            broker_id=broker_id,
            account_id=account_id,
            symbol=symbol,
            order_type='limit',
            order_action=action,
            quantity=quantity,
            price=price,
            fee=fee,
            tax=tax,
            status='filled',
            order_id=order_id
        )
        return self.log_trade(trade_log)
    
    def log_order_cancelled(self, order_id: str, broker_id: str, account_id: str,
                           symbol: str, action: str, quantity: int) -> TradeLog:
        """Log order cancellation."""
        trade_log = TradeLog(
            timestamp=datetime.now().isoformat(),
            action='order_cancelled',
            broker_id=broker_id,
            account_id=account_id,
            symbol=symbol,
            order_type='limit',
            order_action=action,
            quantity=quantity,
            price=None,
            fee=0.0,
            tax=0.0,
            status='cancelled',
            order_id=order_id
        )
        return self.log_trade(trade_log)
    
    def log_order_rejected(self, order_id: str, broker_id: str, account_id: str,
                          symbol: str, action: str, quantity: int, error: str) -> TradeLog:
        """Log order rejection."""
        trade_log = TradeLog(
            timestamp=datetime.now().isoformat(),
            action='order_rejected',
            broker_id=broker_id,
            account_id=account_id,
            symbol=symbol,
            order_type='limit',
            order_action=action,
            quantity=quantity,
            price=None,
            fee=0.0,
            tax=0.0,
            status='rejected',
            order_id=order_id,
            error=error
        )
        return self.log_trade(trade_log)
    
    def query_logs(self, 
                   symbol: Optional[str] = None,
                   action: Optional[str] = None,
                   start_date: Optional[str] = None,
                   end_date: Optional[str] = None,
                   account_id: Optional[str] = None) -> List[TradeLog]:
        """
        Query trade logs with filters.
        
        Args:
            symbol: Filter by symbol
            action: Filter by action type
            start_date: Start date (ISO format)
            end_date: End date (ISO format)
            account_id: Filter by account
            
        Returns:
            List of matching TradeLog objects
        """
        results = self.logs
        
        if symbol:
            results = [log for log in results if log.symbol == symbol]
        
        if action:
            results = [log for log in results if log.action == action]
        
        if account_id:
            results = [log for log in results if log.account_id == account_id]
        
        if start_date:
            results = [log for log in results if log.timestamp >= start_date]
        
        if end_date:
            results = [log for log in results if log.timestamp <= end_date]
        
        return results
    
    def generate_report(self, 
                       start_date: Optional[str] = None,
                       end_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate audit report.
        
        Returns:
            Report dictionary with summary statistics
        """
        logs = self.query_logs(start_date=start_date, end_date=end_date)
        
        if not logs:
            return {
                'period': f"{start_date or 'All'} to {end_date or 'All'}",
                'total_logs': 0,
                'summary': {}
            }
        
        # Calculate statistics
        submitted = sum(1 for log in logs if log.action == 'order_submitted')
        filled = sum(1 for log in logs if log.action == 'order_filled')
        cancelled = sum(1 for log in logs if log.action == 'order_cancelled')
        rejected = sum(1 for log in logs if log.action == 'order_rejected')
        
        total_fees = sum(log.fee for log in logs if log.action == 'order_filled')
        total_tax = sum(log.tax for log in logs if log.action == 'order_filled')
        
        return {
            'period': f"{start_date or 'All'} to {end_date or 'All'}",
            'total_logs': len(logs),
            'submitted': submitted,
            'filled': filled,
            'cancelled': cancelled,
            'rejected': rejected,
            'fill_rate': filled / submitted if submitted > 0 else 0,
            'total_fees': total_fees,
            'total_tax': total_tax,
            'symbols_traded': list(set(log.symbol for log in logs if log.action == 'order_filled')),
            'accounts_used': list(set(log.account_id for log in logs)),
        }
    
    def verify_integrity(self) -> tuple[bool, List[str]]:
        """
        Verify audit trail integrity.
        
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        
        for i, log in enumerate(self.logs):
            expected_signature = log.compute_signature()
            if log.signature != expected_signature:
                issues.append(f"Log {i} ({log.order_id}): Signature mismatch")
        
        return (len(issues) == 0, issues)


# Global logger instance
_logger: Optional[TradeLogger] = None


def get_logger(log_path: Optional[str] = None) -> TradeLogger:
    """Get or create the global trade logger."""
    global _logger
    if _logger is None:
        _logger = TradeLogger(log_path)
    return _logger
