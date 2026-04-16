#!/usr/bin/env python3
"""
Unified Broker Manager for ETF_TW.
Orchestrates multiple broker adapters and manages account routing.
"""

from typing import Dict, List, Any, Optional
from pathlib import Path
import logging

try:
    from account_manager import get_account_manager, AccountManager
    from adapters.base import BaseAdapter, get_adapter, Order
except ImportError:
    from scripts.account_manager import get_account_manager, AccountManager
    from scripts.adapters.base import BaseAdapter, get_adapter, Order

# Define BaseBrokerAdapter as an alias for BaseAdapter for conceptual alignment
BaseBrokerAdapter = BaseAdapter

class BrokerManager:
    """
    Unified manager to route trading logic to the correct broker adapter.
    Uses AccountManager for configuration and adapter lifecycle.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        self.account_manager = get_account_manager(config_path)
        self.logger = logging.getLogger("ETF_TW.BrokerManager")
        
    def get_adapter(self, account_alias: Optional[str] = None) -> BaseBrokerAdapter:
        """Get the adapter for a specific account alias."""
        return self.account_manager.get_adapter(account_alias)
    
    async def get_all_positions(self) -> Dict[str, List[Any]]:
        """Fetch positions from all configured accounts."""
        results = {}
        for account in self.account_manager.list_accounts():
            alias = account['alias']
            try:
                adapter = self.get_adapter(alias)
                if await adapter.authenticate():
                    results[alias] = await adapter.get_positions(account['account_id'])
                else:
                    self.logger.warning(f"Failed to authenticate account: {alias}")
            except Exception as e:
                self.logger.error(f"Error fetching positions for {alias}: {e}")
        return results

    async def get_total_balance(self) -> Dict[str, Any]:
        """Fetch balances from all configured accounts."""
        balances = {}
        for account in self.account_manager.list_accounts():
            alias = account['alias']
            try:
                adapter = self.get_adapter(alias)
                if await adapter.authenticate():
                    balances[alias] = await adapter.get_account_balance(account['account_id'])
            except Exception as e:
                self.logger.error(f"Error fetching balance for {alias}: {e}")
        return balances

    def list_available_accounts(self) -> List[Dict[str, Any]]:
        """List all accounts with their capabilities."""
        return self.account_manager.list_accounts()

# Global singleton
_manager: Optional[BrokerManager] = None

def get_broker_manager(config_path: Optional[str] = None) -> BrokerManager:
    global _manager
    if _manager is None or config_path is not None:
        _manager = BrokerManager(config_path)
    return _manager
